"""
bookings/services.py — all write operations and business logic.

Rules:
  - Every public function is wrapped in @transaction.atomic
  - Services call Celery tasks, never the other way around
  - Services never touch request/response objects
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.hotel.models import RoomCategory
from apps.hotel.selectors import get_available_room_for_category
from .models import Booking, BookingStatus, BookingHistory
from .selectors import check_category_availability
from .price_calculator import PriceCalculator

PENDING_BOOKING_TTL_HOURS = 24


class BookingUnavailableError(Exception):
    """No rooms available for the requested period."""


class BookingStateError(Exception):
    """State transition not allowed."""


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@transaction.atomic
def create_booking(
    guest,
    room_category: RoomCategory,
    check_in: date,
    check_out: date,
    guest_first_name: str,
    guest_last_name: str,
    guest_phone: str,
    guest_email: str,
    guest_patronymic: str = "",
    adults: int = 1,
    children: int = 0,
    room=None,
    organization=None,
    special_requests: str = "",
    arrival_time=None,
    source: str = "website",
    internal_notes: str = "",
    discount_amount: Decimal = Decimal("0"),
    discount_reason: str = "",
    created_by=None,
) -> Booking:
    """
    Create a new booking in PENDING state.
    Raises BookingUnavailableError if no rooms are available.
    """
    if not check_category_availability(room_category.pk, check_in, check_out):
        raise BookingUnavailableError(
            "К сожалению, на выбранные даты нет свободных номеров этой категории."
        )

    # Use advanced price calculator
    calculator = PriceCalculator(room_category)
    price_info = calculator.calculate_total_price(
        check_in, check_out, adults, children, organization
    )
    
    price_per_night = price_info['price_per_night']
    total_price = price_info['final_total']
    
    # Use calculated discount if no manual discount provided
    if discount_amount == Decimal("0") and price_info['discount_amount'] > 0:
        discount_amount = price_info['discount_amount']
        discount_reason = price_info['discount_reason']

    booking = Booking.objects.create(
        guest=guest,
        room_category=room_category,
        room=room,
        organization=organization,
        guest_first_name=guest_first_name,
        guest_last_name=guest_last_name,
        guest_patronymic=guest_patronymic,
        guest_phone=guest_phone,
        guest_email=guest_email,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        price_per_night=price_per_night,
        total_price=total_price,
        discount_amount=discount_amount,
        discount_reason=discount_reason,
        special_requests=special_requests,
        arrival_time=arrival_time,
        source=source,
        internal_notes=internal_notes,
        created_by=created_by,
        status=BookingStatus.PENDING,
        auto_cancel_at=timezone.now() + timedelta(hours=PENDING_BOOKING_TTL_HOURS),
    )

    # Audit log
    BookingHistory.objects.create(
        booking=booking,
        action=BookingHistory.Action.CREATED,
        status_after=BookingStatus.PENDING,
        changed_by=created_by or guest,
        note="Бронирование создано.",
    )

    # Async email — "бронь создана, ожидает подтверждения"
    try:
        from apps.notifications.tasks import send_booking_created_email
        send_booking_created_email.delay(str(booking.pk))
    except Exception:
        pass  # Don't fail booking creation if Celery is unavailable

    return booking


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

@transaction.atomic
def confirm_booking(booking_id, actor=None) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    booking.confirm(actor=actor)
    # Email — "бронь подтверждена менеджером"
    try:
        from apps.notifications.tasks import send_booking_confirmed_email
        send_booking_confirmed_email.delay(str(booking.pk))
    except Exception:
        pass
    return booking


@transaction.atomic
def cancel_booking(booking_id, reason: str = "", actor=None) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if not booking.can_be_cancelled:
        raise BookingStateError("Эту бронь нельзя отменить.")
    booking.cancel(reason=reason, actor=actor)
    # Email — "бронь отменена вручную"
    try:
        from apps.notifications.tasks import send_booking_cancelled_email
        send_booking_cancelled_email.delay(str(booking.pk))
    except Exception:
        pass
    return booking


@transaction.atomic
def perform_check_in(booking_id, room_id=None, actor=None) -> Booking:
    booking = (
        Booking.objects.select_for_update()
        .select_related("room_category")
        .get(pk=booking_id)
    )
    
    # Use specified room or pre-assigned room or find one automatically
    if room_id:
        from apps.hotel.models import Room
        try:
            room = Room.objects.get(id=room_id)
            if not room.has_availability(booking.check_in, booking.check_out):
                raise BookingUnavailableError(f"Номер {room.full_number} недоступен на выбранные даты.")
        except Room.DoesNotExist:
            raise BookingUnavailableError("Указанный номер не найден.")
    else:
        room = booking.room or get_available_room_for_category(
            booking.room_category_id, booking.check_in, booking.check_out
        )
    
    if room is None:
        raise BookingUnavailableError("Нет свободных физических номеров для заселения.")
    
    booking.check_in_guest(room=room, actor=actor)
    _update_guest_crm_on_checkin(booking)
    return booking


@transaction.atomic
def perform_check_out(booking_id, actor=None) -> Booking:
    booking = (
        Booking.objects.select_for_update()
        .select_related("guest")
        .get(pk=booking_id)
    )
    booking.check_out_guest(actor=actor)
    _update_guest_crm_on_checkout(booking)
    return booking


@transaction.atomic
def perform_no_show(booking_id, actor=None) -> Booking:
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    booking.mark_no_show(actor=actor)
    return booking


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _update_guest_crm_on_checkin(booking: Booking):
    from apps.crm.models import ClientProfile
    ClientProfile.objects.get_or_create(user=booking.guest)


def _update_guest_crm_on_checkout(booking: Booking):
    from apps.crm.models import ClientProfile
    profile, _ = ClientProfile.objects.get_or_create(user=booking.guest)
    profile.total_stays  += 1
    profile.total_nights += booking.nights
    profile.total_spent  += booking.total_price
    if not profile.first_stay_date:
        profile.first_stay_date = booking.check_in
    profile.last_stay_date = booking.check_out
    profile.recalculate_tier()
    profile.save(update_fields=[
        "total_stays", "total_nights", "total_spent",
        "first_stay_date", "last_stay_date", "updated_at",
    ])
