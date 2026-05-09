"""
bookings/selectors.py — read-only queries only.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from django.db.models import QuerySet, Sum, Count, Q
from django.shortcuts import get_object_or_404

from .models import Booking, BookingStatus


def get_booking_by_id(booking_id: UUID) -> Booking:
    return get_object_or_404(
        Booking.objects.select_related(
            "guest", "room_category", "room", "organization", "cancelled_by"
        ).prefetch_related("history__changed_by", "payments"),
        pk=booking_id,
    )


def get_booking_for_guest(booking_id: UUID, guest) -> Booking:
    """Booking that belongs to a specific guest — or 404."""
    return get_object_or_404(
        Booking.objects.select_related("room_category", "room", "organization")
        .prefetch_related("history"),
        pk=booking_id,
        guest=guest,
    )


def get_guest_bookings(guest, status: Optional[str] = None) -> QuerySet:
    qs = (
        Booking.objects.filter(guest=guest)
        .select_related("room_category", "room")
        .order_by("-created_at")
    )
    if status:
        qs = qs.filter(status=status)
    return qs


def get_active_bookings() -> QuerySet:
    return (
        Booking.objects.filter(
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]
        )
        .select_related("guest", "room_category", "room")
        .order_by("check_in")
    )


def get_bookings_filtered(
    search: str = "",
    status: str = "",
    check_in_from: Optional[date] = None,
    check_in_to: Optional[date] = None,
    category_id: Optional[int] = None,
) -> QuerySet:
    """Filtered queryset for the staff management table."""
    qs = (
        Booking.objects.select_related("guest", "room_category", "room", "organization")
        .order_by("-created_at")
    )
    if search:
        qs = qs.filter(
            Q(confirmation_number__icontains=search)
            | Q(guest_last_name__icontains=search)
            | Q(guest_first_name__icontains=search)
            | Q(guest_email__icontains=search)
            | Q(guest_phone__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if check_in_from:
        qs = qs.filter(check_in__gte=check_in_from)
    if check_in_to:
        qs = qs.filter(check_in__lte=check_in_to)
    if category_id:
        qs = qs.filter(room_category_id=category_id)
    return qs


def get_bookings_for_period(start: date, end: date) -> QuerySet:
    return (
        Booking.objects.filter(check_in__gte=start, check_out__lte=end)
        .select_related("guest", "room_category")
        .order_by("check_in")
    )


def get_today_arrivals() -> QuerySet:
    from django.utils import timezone
    today = timezone.localdate()
    return (
        Booking.objects.filter(status=BookingStatus.CONFIRMED, check_in=today)
        .select_related("guest", "room_category")
    )


def get_today_departures() -> QuerySet:
    from django.utils import timezone
    today = timezone.localdate()
    return (
        Booking.objects.filter(status=BookingStatus.CHECKED_IN, check_out=today)
        .select_related("guest", "room_category", "room")
    )


def check_category_availability(category_id: int, check_in: date, check_out: date) -> bool:
    from apps.hotel.selectors import get_available_room_for_category
    return get_available_room_for_category(category_id, check_in, check_out) is not None


def check_room_availability(room_id: int, check_in: date, check_out: date) -> bool:
    """Check if a specific room has availability for the given period"""
    try:
        from apps.hotel.models import Room
        room = Room.objects.get(id=room_id)
        return room.has_availability(check_in, check_out)
    except Room.DoesNotExist:
        return False


def get_revenue_stats(start: date, end: date) -> dict:
    result = (
        Booking.objects.filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__gte=start, check_in__lte=end,
        )
        .aggregate(total_revenue=Sum("total_price"), total_bookings=Count("id"))
    )
    return {
        "total_revenue":  result["total_revenue"]  or 0,
        "total_bookings": result["total_bookings"] or 0,
    }
