"""
apps/reports/selectors.py — aggregation queries for PDF/Excel reports.
"""

from datetime import date
from django.db.models import (
    Sum, Count, Avg, Q, F, Max, Min,
    ExpressionWrapper, DecimalField, FloatField,
)
from django.db.models.functions import TruncMonth, TruncDate


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

def get_bookings_report_data(start: date, end: date):
    """Full booking list for the given period."""
    from apps.bookings.models import Booking
    return list(
        Booking.objects
        .filter(check_in__gte=start, check_out__lte=end)
        .select_related("guest", "room_category", "room", "organization")
        .order_by("check_in")
    )


def get_bookings_summary(start: date, end: date) -> dict:
    """Aggregate totals for the bookings PDF header."""
    from apps.bookings.models import Booking, BookingStatus
    qs = Booking.objects.filter(check_in__gte=start, check_out__lte=end)
    return qs.aggregate(
        total=Count("id"),
        confirmed=Count("id", filter=Q(status__in=[
            BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT
        ])),
        cancelled=Count("id", filter=Q(status=BookingStatus.CANCELLED)),
        revenue=Sum("total_price", filter=Q(status__in=[
            BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT
        ])),
        avg_nights=Avg(
            ExpressionWrapper(F("check_out") - F("check_in"), output_field=DecimalField())
        ),
    )


def get_revenue_by_month(year: int) -> list[dict]:
    """Monthly revenue breakdown for a given year."""
    from apps.bookings.models import Booking, BookingStatus
    return list(
        Booking.objects
        .filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__year=year,
        )
        .annotate(month=TruncMonth("check_in"))
        .values("month")
        .annotate(revenue=Sum("total_price"), bookings=Count("id"))
        .order_by("month")
    )


def get_occupancy_by_category(start: date, end: date) -> list[dict]:
    """Booking count and revenue per room category for a date range."""
    from apps.bookings.models import Booking, BookingStatus
    return list(
        Booking.objects
        .filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__gte=start,
            check_out__lte=end,
        )
        .values("room_category__name")
        .annotate(
            bookings=Count("id"),
            revenue=Sum("total_price"),
            avg_nights=Avg(
                ExpressionWrapper(F("check_out") - F("check_in"), output_field=DecimalField())
            ),
        )
        .order_by("-revenue")
    )


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

def get_clients_report_data(search: str = "", loyalty_tier: str = "", status: str = ""):
    """Full client list for the clients PDF report."""
    from apps.crm.models import ClientProfile
    from django.db.models import Q as DQ

    qs = (
        ClientProfile.objects
        .select_related("user", "organization", "assigned_manager")
        .annotate(total_bookings=Count("user__bookings", distinct=True))
        .order_by("-total_spent")
    )
    if search:
        qs = qs.filter(
            DQ(user__first_name__icontains=search) |
            DQ(user__last_name__icontains=search) |
            DQ(user__email__icontains=search)
        )
    if loyalty_tier:
        qs = qs.filter(loyalty_tier=loyalty_tier)
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def get_clients_summary() -> dict:
    """Aggregate totals for the clients PDF header."""
    from apps.crm.models import ClientProfile
    return ClientProfile.objects.aggregate(
        total=Count("id"),
        vip=Count("id", filter=Q(status="vip")),
        blacklisted=Count("id", filter=Q(is_blacklisted=True)),
        total_revenue=Sum("total_spent"),
        avg_stays=Avg("total_stays"),
    )


# ---------------------------------------------------------------------------
# Room occupancy
# ---------------------------------------------------------------------------

def get_room_occupancy_report(start: date, end: date) -> list[dict]:
    """
    Per-room occupancy stats for the given period.
    Returns list of dicts with room info + booking count + nights + revenue.
    """
    from apps.hotel.models import Room
    from apps.bookings.models import Booking, BookingStatus

    rooms = Room.objects.select_related("category").order_by("category__sort_order", "floor", "number")
    result = []

    for room in rooms:
        bookings = Booking.objects.filter(
            room=room,
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__gte=start,
            check_out__lte=end,
        )
        agg = bookings.aggregate(
            count=Count("id"),
            nights=Sum(
                ExpressionWrapper(F("check_out") - F("check_in"), output_field=DecimalField())
            ),
            revenue=Sum("total_price"),
        )
        total_days = (end - start).days or 1
        nights = float(agg["nights"] or 0)
        result.append({
            "number":    room.number,
            "floor":     room.floor,
            "category":  room.category.name,
            "status":    room.get_status_display(),
            "bookings":  agg["count"] or 0,
            "nights":    int(nights),
            "revenue":   float(agg["revenue"] or 0),
            "occupancy": round(nights / total_days * 100, 1),
        })

    return result


def get_occupancy_summary(start: date, end: date) -> dict:
    """Aggregate occupancy stats for the PDF header."""
    from apps.hotel.models import Room
    from apps.bookings.models import Booking, BookingStatus

    total_rooms = Room.objects.count()
    total_days  = (end - start).days or 1

    agg = Booking.objects.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
        check_in__gte=start,
        check_out__lte=end,
    ).aggregate(
        total_bookings=Count("id"),
        total_revenue=Sum("total_price"),
        total_nights=Sum(
            ExpressionWrapper(F("check_out") - F("check_in"), output_field=DecimalField())
        ),
    )

    total_nights = float(agg["total_nights"] or 0)
    max_nights   = total_rooms * total_days

    return {
        "total_rooms":    total_rooms,
        "total_days":     total_days,
        "total_bookings": agg["total_bookings"] or 0,
        "total_revenue":  agg["total_revenue"] or 0,
        "total_nights":   int(total_nights),
        "avg_occupancy":  round(total_nights / max_nights * 100, 1) if max_nights else 0,
    }
