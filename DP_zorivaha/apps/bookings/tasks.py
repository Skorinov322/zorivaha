"""
apps/bookings/tasks.py

Periodic Celery tasks for the bookings domain.

Tasks:
  auto_cancel_expired_bookings  — отменяет PENDING брони с истёкшим auto_cancel_at
  mark_no_show_bookings         — помечает CONFIRMED брони как NO_SHOW если гость
                                  не заехал в течение NO_SHOW_GRACE_HOURS после check_in
  send_checkin_reminders        — отправляет напоминание о заезде за 24 ч

Логика no-show (главная задача):
  1. Найти все CONFIRMED брони, у которых:
       check_in < сегодня  И  (now - check_in) >= NO_SHOW_GRACE_HOURS
  2. Для каждой:
       a. Вызвать booking.mark_no_show()  → статус = NO_SHOW
       b. Если был назначен номер — освободить его (AVAILABLE)
       c. Записать в BookingHistory (уже делает mark_no_show через _log)
       d. Отправить email гостю через Celery (send_no_show_email)
  3. Вернуть статистику: {"processed": N, "errors": M}
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Сколько часов после даты заезда ждём гостя перед тем как ставить no-show
NO_SHOW_GRACE_HOURS: int = 24


# ---------------------------------------------------------------------------
# auto_cancel_expired_bookings
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.bookings.tasks.auto_cancel_expired_bookings",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def auto_cancel_expired_bookings(self) -> dict:
    """
    Cancel all PENDING bookings whose auto_cancel_at deadline has passed.

    Scheduled: every 15 minutes via Celery Beat.
    """
    from .models import Booking, BookingStatus
    from apps.notifications.tasks import send_booking_auto_cancelled_email  # noqa — used below

    now = timezone.now()
    expired_qs = (
        Booking.objects
        .filter(
            status=BookingStatus.PENDING,
            auto_cancel_at__lte=now,
            auto_cancel_at__isnull=False,
        )
        .select_related("guest")
    )

    cancelled_count = 0
    error_count     = 0

    for booking in expired_qs:
        try:
            with transaction.atomic():
                booking.cancel(
                    reason="Автоматическая отмена: истёк срок подтверждения.",
                    actor=None,
                )
            # Отдельный шаблон для автоотмены
            from apps.notifications.tasks import send_booking_auto_cancelled_email
            send_booking_auto_cancelled_email.delay(str(booking.pk))
            cancelled_count += 1
            logger.info(
                "[auto_cancel] Cancelled booking %s (guest: %s)",
                booking.confirmation_number, booking.guest_email,
            )
        except Exception as exc:
            error_count += 1
            logger.error(
                "[auto_cancel] Failed to cancel booking %s: %s",
                booking.confirmation_number, exc,
            )

    logger.info(
        "[auto_cancel] Done. cancelled=%d errors=%d",
        cancelled_count, error_count,
    )
    return {"cancelled": cancelled_count, "errors": error_count}


# ---------------------------------------------------------------------------
# mark_no_show_bookings  ← ГЛАВНАЯ ЗАДАЧА
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.bookings.tasks.mark_no_show_bookings",
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
)
def mark_no_show_bookings(self) -> dict:
    """
    Mark CONFIRMED bookings as NO_SHOW if the guest didn't arrive
    within NO_SHOW_GRACE_HOURS (24h) after the check_in date.

    Scheduled: every hour via Celery Beat.

    Algorithm:
      1. Find CONFIRMED bookings where check_in < today AND
         now >= check_in_datetime + NO_SHOW_GRACE_HOURS
      2. For each booking:
         a. Call booking.mark_no_show()  → status = NO_SHOW, writes BookingHistory
         b. If a room was pre-assigned → set room.status = AVAILABLE
         c. Send no-show notification email to guest (async)
    """
    from .models import Booking, BookingStatus
    from apps.hotel.models import Room
    from apps.notifications.tasks import send_no_show_email

    now   = timezone.now()
    today = timezone.localdate()

    # Deadline: check_in date + grace period has already passed
    # We compare against naive date: check_in < today means the day has passed.
    # Then we additionally verify the full datetime threshold.
    grace_threshold = now - timedelta(hours=NO_SHOW_GRACE_HOURS)

    # Convert grace_threshold to a date for the DB filter
    # (check_in is a DateField, so we compare dates)
    grace_date = grace_threshold.date()

    candidates = (
        Booking.objects
        .filter(
            status=BookingStatus.CONFIRMED,
            check_in__lte=grace_date,   # check_in date is on or before the grace date
        )
        .select_related("guest", "room", "room_category")
        # Exclude bookings that were already processed today
        # (idempotency guard via updated_at is handled by status check)
    )

    processed_count = 0
    error_count     = 0

    for booking in candidates:
        # Double-check: ensure the full 24h window has passed
        # check_in is a date → combine with midnight in the project timezone
        from django.utils.timezone import make_aware
        import datetime
        check_in_midnight = make_aware(
            datetime.datetime.combine(booking.check_in, datetime.time.min)
        )
        if now < check_in_midnight + timedelta(hours=NO_SHOW_GRACE_HOURS):
            # Grace period not yet expired for this booking
            continue

        try:
            with transaction.atomic():
                # 1. Mark as no-show (writes BookingHistory internally)
                booking.mark_no_show(actor=None)

                # 2. Free the room if it was pre-assigned
                if booking.room and booking.room.status == Room.RoomStatus.OCCUPIED:
                    booking.room.status = Room.RoomStatus.AVAILABLE
                    booking.room.save(update_fields=["status", "updated_at"])
                    logger.info(
                        "[no_show] Room %s freed (was pre-assigned to booking %s)",
                        booking.room.number, booking.confirmation_number,
                    )

            # 3. Send email notification (outside transaction — non-critical)
            send_no_show_email.delay(str(booking.pk))

            processed_count += 1
            logger.info(
                "[no_show] Marked as NO_SHOW: booking=%s guest=%s check_in=%s",
                booking.confirmation_number,
                booking.guest_email,
                booking.check_in,
            )

        except Exception as exc:
            error_count += 1
            logger.error(
                "[no_show] Failed to process booking %s: %s",
                booking.confirmation_number, exc,
            )

    logger.info(
        "[no_show] Done. processed=%d errors=%d",
        processed_count, error_count,
    )
    return {"processed": processed_count, "errors": error_count}


# ---------------------------------------------------------------------------
# send_checkin_reminders
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.bookings.tasks.send_checkin_reminders",
    max_retries=3,
    default_retry_delay=300,
    acks_late=True,
)
def send_checkin_reminders(self) -> dict:
    """
    Send reminder emails to guests checking in tomorrow.

    Scheduled: daily at 10:00 via Celery Beat.
    """
    from .models import Booking, BookingStatus
    from apps.notifications.tasks import send_checkin_reminder_email

    tomorrow = (timezone.now() + timedelta(days=1)).date()
    bookings = (
        Booking.objects
        .filter(status=BookingStatus.CONFIRMED, check_in=tomorrow)
        .select_related("guest")
    )

    sent_count = 0
    for booking in bookings:
        send_checkin_reminder_email.delay(str(booking.pk))
        sent_count += 1

    logger.info("[reminders] Queued %d check-in reminder emails.", sent_count)
    return {"reminders_sent": sent_count}
