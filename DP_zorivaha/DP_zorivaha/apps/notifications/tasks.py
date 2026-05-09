"""
apps/notifications/tasks.py

Celery tasks for sending transactional emails.

Every task:
  1. Loads the Booking from DB
  2. Renders HTML template + strips plain-text fallback
  3. Creates EmailLog(status=PENDING) BEFORE sending
  4. Sends via Django EmailMultiAlternatives (SMTP)
  5. Updates EmailLog → SENT or FAILED
  6. Retries up to 3 times on failure (60 s delay)

Tasks:
  send_booking_created_email       — бронь создана (статус: новая)
  send_booking_confirmed_email     — бронь подтверждена менеджером
  send_booking_cancelled_email     — бронь отменена вручную
  send_booking_auto_cancelled_email— бронь отменена автоматически (истёк срок)
  send_checkin_reminder_email      — напоминание о заезде за 24 ч
  send_no_show_email               — незаезд (гость не явился)

  # Legacy alias — kept for backward compatibility
  send_booking_confirmation_email  → alias for send_booking_created_email
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core send helper
# ---------------------------------------------------------------------------

def _send_email(
    subject: str,
    template: str,
    context: dict,
    to: list[str],
    booking=None,
    email_type: str = "custom",
) -> None:
    """
    Render template → create EmailLog(PENDING) → send → update log.

    Raises on SMTP failure so Celery can retry the task.
    """
    from apps.notifications.models import EmailLog

    html_content = render_to_string(template, context)
    text_content = strip_tags(html_content)

    # Resolve recipient name from booking if available
    recipient_name = ""
    if booking:
        recipient_name = booking.guest_full_name

    log = EmailLog.objects.create(
        recipient_email=to[0] if to else "",
        recipient_name=recipient_name,
        email_type=email_type,
        subject=subject,
        body_html=html_content,
        body_text=text_content,
        booking=booking,
        status=EmailLog.EmailStatus.PENDING,
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        log.mark_sent()
        logger.info(
            "[email] SENT type=%-25s to=%-35s subject=%s",
            email_type, to[0] if to else "?", subject,
        )

    except Exception as exc:
        log.mark_failed(str(exc))
        logger.error(
            "[email] FAILED type=%s to=%s error=%s",
            email_type, to[0] if to else "?", exc,
        )
        raise  # re-raise → Celery retries


# ---------------------------------------------------------------------------
# 1. Бронь создана (статус: Новая)
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.notifications.tasks.send_booking_created_email",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_booking_created_email(self, booking_id: str) -> None:
    """
    Sent immediately after a guest creates a booking.
    Status at this point: PENDING (awaiting manager confirmation).
    Template: booking_created.html
    """
    from apps.bookings.models import Booking
    from apps.notifications.models import EmailLog

    try:
        booking = Booking.objects.select_related("guest", "room_category").get(pk=booking_id)
        _send_email(
            subject=f"Заявка #{booking.confirmation_number} принята — Зори Ваха",
            template="notifications/email/booking_created.html",
            context={"booking": booking},
            to=[booking.guest_email],
            booking=booking,
            email_type=EmailLog.EmailType.BOOKING_CONFIRMATION,
        )
    except Exception as exc:
        logger.error("[email] booking_created failed for %s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# 2. Бронь подтверждена менеджером
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.notifications.tasks.send_booking_confirmed_email",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_booking_confirmed_email(self, booking_id: str) -> None:
    """
    Sent when a manager confirms the booking (status → CONFIRMED).
    Template: booking_confirmation.html
    """
    from apps.bookings.models import Booking
    from apps.notifications.models import EmailLog

    try:
        booking = Booking.objects.select_related("guest", "room_category").get(pk=booking_id)
        _send_email(
            subject=f"Бронь #{booking.confirmation_number} подтверждена — Зори Ваха",
            template="notifications/email/booking_confirmation.html",
            context={"booking": booking},
            to=[booking.guest_email],
            booking=booking,
            email_type=EmailLog.EmailType.BOOKING_CONFIRMATION,
        )
    except Exception as exc:
        logger.error("[email] booking_confirmed failed for %s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# 3. Бронь отменена вручную
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.notifications.tasks.send_booking_cancelled_email",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_booking_cancelled_email(self, booking_id: str) -> None:
    """
    Sent when a booking is manually cancelled (by guest or staff).
    Template: booking_cancelled.html
    """
    from apps.bookings.models import Booking
    from apps.notifications.models import EmailLog

    try:
        booking = Booking.objects.select_related("guest", "room_category").get(pk=booking_id)
        _send_email(
            subject=f"Бронь #{booking.confirmation_number} отменена — Зори Ваха",
            template="notifications/email/booking_cancelled.html",
            context={"booking": booking},
            to=[booking.guest_email],
            booking=booking,
            email_type=EmailLog.EmailType.BOOKING_CANCELLED,
        )
    except Exception as exc:
        logger.error("[email] booking_cancelled failed for %s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# 4. Автоматическая отмена (истёк срок подтверждения)
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.notifications.tasks.send_booking_auto_cancelled_email",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_booking_auto_cancelled_email(self, booking_id: str) -> None:
    """
    Sent when Celery Beat auto-cancels a PENDING booking
    because the manager didn't confirm it within 24 hours.
    Template: booking_auto_cancelled.html
    """
    from apps.bookings.models import Booking
    from apps.notifications.models import EmailLog

    try:
        booking = Booking.objects.select_related("guest", "room_category").get(pk=booking_id)
        _send_email(
            subject=f"Бронь #{booking.confirmation_number} автоматически отменена — Зори Ваха",
            template="notifications/email/booking_auto_cancelled.html",
            context={"booking": booking},
            to=[booking.guest_email],
            booking=booking,
            email_type=EmailLog.EmailType.BOOKING_CANCELLED,
        )
    except Exception as exc:
        logger.error("[email] booking_auto_cancelled failed for %s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# 5. Напоминание о заезде (за 24 ч)
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.notifications.tasks.send_checkin_reminder_email",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_checkin_reminder_email(self, booking_id: str) -> None:
    """
    Sent the day before check-in (daily at 10:00 via Celery Beat).
    Template: checkin_reminder.html
    """
    from apps.bookings.models import Booking
    from apps.notifications.models import EmailLog

    try:
        booking = Booking.objects.select_related("guest", "room_category").get(pk=booking_id)
        _send_email(
            subject=f"Напоминание о заезде завтра — Зори Ваха",
            template="notifications/email/checkin_reminder.html",
            context={"booking": booking},
            to=[booking.guest_email],
            booking=booking,
            email_type=EmailLog.EmailType.BOOKING_REMINDER,
        )
    except Exception as exc:
        logger.error("[email] checkin_reminder failed for %s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# 6. Незаезд
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="apps.notifications.tasks.send_no_show_email",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_no_show_email(self, booking_id: str) -> None:
    """
    Sent when mark_no_show_bookings task marks a booking as NO_SHOW.
    Template: no_show.html
    """
    from apps.bookings.models import Booking
    from apps.notifications.models import EmailLog

    try:
        booking = Booking.objects.select_related("guest", "room_category").get(pk=booking_id)
        _send_email(
            subject=f"Бронь #{booking.confirmation_number} — незаезд — Зори Ваха",
            template="notifications/email/no_show.html",
            context={"booking": booking},
            to=[booking.guest_email],
            booking=booking,
            email_type=EmailLog.EmailType.BOOKING_CANCELLED,
        )
    except Exception as exc:
        logger.error("[email] no_show failed for %s: %s", booking_id, exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Legacy alias (backward compatibility)
# ---------------------------------------------------------------------------

# Old name used in some places — routes to the "created" email
send_booking_confirmation_email = send_booking_created_email
