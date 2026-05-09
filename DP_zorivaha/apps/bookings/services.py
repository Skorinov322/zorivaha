"""
bookings/services.py — all write operations and business logic.

Rules:
  - Every public function is wrapped in @transaction.atomic
  - Services call Celery tasks, never the other way around
  - Services never touch request/response objects
"""

import uuid
import math
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

    def __init__(self, message: str, alternatives=None, contact_phone: str = ""):
        super().__init__(message)
        self.alternatives = alternatives or []
        self.contact_phone = contact_phone


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
    occupancy_type: str = "solo",
    early_check_in: bool = False,
    room=None,
    organization=None,
    special_requests: str = "",
    arrival_time=None,
    source: str = "website",
    internal_notes: str = "",
    discount_amount: Decimal = Decimal("0"),
    discount_reason: str = "",
    discount_percent: int = None,
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

    calculator = PriceCalculator(room_category)
    price_info = calculator.calculate_total_price(
        check_in, check_out, adults, children, occupancy_type, early_check_in, organization
    )

    price_per_night = price_info["price_per_night"]
    total_price     = price_info["final_total"]

    # Calculate discount from percent if provided
    if discount_percent and discount_percent > 0:
        discount_amount = (total_price * Decimal(str(discount_percent)) / Decimal("100")).quantize(Decimal("0.01"))
        if not discount_reason:
            discount_reason = f"Скидка {discount_percent}%"

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
        occupancy_type=occupancy_type,
        early_check_in=early_check_in,
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
# Create group booking
# ---------------------------------------------------------------------------

@transaction.atomic
def create_booking_group(
    guest,
    room_category: RoomCategory,
    check_in: date,
    check_out: date,
    guest_first_name: str,
    guest_last_name: str,
    guest_phone: str,
    guest_email: str,
    adults: int,
    children: int = 0,
    early_check_in: bool = False,
    guest_patronymic: str = "",
    organization=None,
    special_requests: str = "",
    arrival_time=None,
    source: str = "website",
    internal_notes: str = "",
    discount_amount: Decimal = Decimal("0"),
    discount_reason: str = "",
    created_by=None,
) -> list:
    """
    Создаёт N броней в одной транзакции, связанных общим group_id.

    Алгоритм:
    1. Рассчитать total_persons = adults + children
    2. Получить список свободных номеров (SELECT FOR UPDATE)
    3. Распределить персон по номерам (_distribute_persons)
    4. Если номеров недостаточно — raise BookingUnavailableError с alternatives
    5. Рассчитать цену для каждой брони
    6. Создать N объектов Booking с одинаковым group_id
    7. Запустить Celery-задачу send_group_booking_email
    8. Вернуть список созданных броней
    """
    from apps.hotel.selectors import get_available_rooms_for_group, get_alternative_categories
    from apps.bookings.price_calculator import PriceCalculator, calculate_paid_persons
    from apps.content.models import SiteContent
    from apps.hotel.models import Room as RoomModel

    total_persons = adults + children

    # Получаем все доступные номера с блокировкой строк
    all_available = RoomModel.objects.select_for_update().filter(
        category=room_category,
        status=RoomModel.RoomStatus.AVAILABLE,
    ).order_by("floor", "number", "subdivision")

    # Фильтруем по доступности дат
    date_available = []
    for room in all_available:
        if room.has_availability(check_in, check_out):
            date_available.append(room)

    # Считаем сколько номеров нужно жадным алгоритмом
    remaining = total_persons
    rooms_to_use = []
    for room in date_available:
        if remaining <= 0:
            break
        rooms_to_use.append(room)
        remaining -= room.max_guests_per_room

    if remaining > 0:
        # Недостаточно номеров — собираем альтернативы
        contact_phone = SiteContent.get("contact_phone", "")
        alternatives = list(get_alternative_categories(
            check_in=check_in,
            check_out=check_out,
            total_persons=total_persons,
            exclude_category_id=room_category.pk,
        ))
        raise BookingUnavailableError(
            f"К сожалению, в категории «{room_category.name}» недостаточно свободных номеров "
            f"для размещения {total_persons} персон на выбранные даты.",
            alternatives=alternatives,
            contact_phone=contact_phone,
        )

    # Распределяем персон по номерам
    distribution = _distribute_persons(total_persons, rooms_to_use)

    # Общий group_id для всех броней
    group_uuid = uuid.uuid4()

    # Рассчитываем платных персон
    calculator = PriceCalculator(room_category)
    paid_persons_total = calculate_paid_persons(adults, children)

    created_bookings = []
    auto_cancel_time = timezone.now() + timedelta(hours=PENDING_BOOKING_TTL_HOURS)

    for i, room in enumerate(rooms_to_use):
        persons_in_room = distribution[i]

        # Распределяем платных персон пропорционально
        paid_in_room = min(persons_in_room, paid_persons_total)
        paid_persons_total -= paid_in_room

        price_info = calculator.calculate_group_booking_price(
            check_in=check_in,
            check_out=check_out,
            paid_persons=max(paid_in_room, 1),
            early_check_in=early_check_in,
        )

        booking = Booking.objects.create(
            guest=guest,
            room_category=room_category,
            room=None,  # назначается администратором при заселении
            group_id=group_uuid,
            organization=organization,
            guest_first_name=guest_first_name,
            guest_last_name=guest_last_name,
            guest_patronymic=guest_patronymic,
            guest_phone=guest_phone,
            guest_email=guest_email,
            check_in=check_in,
            check_out=check_out,
            # Для доп. номеров группы ставим минимум 1 взрослого (constraint adults >= 1).
            # Реальное распределение персон отражается в цене (paid_in_room).
            adults=adults if i == 0 else max(persons_in_room, 1),
            children=children if i == 0 else 0,
            occupancy_type="solo",
            early_check_in=early_check_in,
            price_per_night=price_info["price_per_night"],
            total_price=price_info["final_total"],
            discount_amount=discount_amount,
            discount_reason=discount_reason,
            special_requests=special_requests,
            arrival_time=arrival_time,
            source=source,
            internal_notes=internal_notes,
            created_by=created_by,
            status=BookingStatus.PENDING,
            auto_cancel_at=auto_cancel_time,
        )

        BookingHistory.objects.create(
            booking=booking,
            action=BookingHistory.Action.CREATED,
            status_after=BookingStatus.PENDING,
            changed_by=created_by or guest,
            note=f"Групповое бронирование создано. Номер {i + 1} из {len(rooms_to_use)}.",
        )

        created_bookings.append(booking)

    # Отправляем одно письмо для всей группы
    try:
        from apps.notifications.tasks import send_group_booking_email
        send_group_booking_email.delay(str(group_uuid))
    except Exception:
        pass  # Не прерываем создание броней при ошибке Celery

    return created_bookings


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


@transaction.atomic
def undo_check_in(booking_id, actor=None) -> Booking:
    """Отменить заселение: checked_in → confirmed."""
    booking = (
        Booking.objects.select_for_update()
        .select_related("room")
        .get(pk=booking_id)
    )
    booking.undo_check_in(actor=actor)
    return booking


@transaction.atomic
def undo_check_out(booking_id, actor=None) -> Booking:
    """Отменить выселение: checked_out → checked_in."""
    booking = (
        Booking.objects.select_for_update()
        .select_related("room")
        .get(pk=booking_id)
    )
    booking.undo_check_out(actor=actor)
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


def _distribute_persons(total_persons: int, rooms: list) -> list:
    """
    Распределяет персон по номерам жадным алгоритмом.
    Каждый номер заполняется до max_guests_per_room.
    Возвращает список количества персон для каждой брони.

    Пример: 7 персон, rooms=[cap=3, cap=3, cap=3] → [3, 3, 1]
    """
    distribution = []
    remaining = total_persons
    for room in rooms:
        if remaining <= 0:
            break
        in_this_room = min(remaining, room.max_guests_per_room)
        distribution.append(in_this_room)
        remaining -= in_this_room
    return distribution
