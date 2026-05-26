"""
apps/reports/selectors.py — aggregation queries for PDF/Excel reports.
"""

from datetime import date
from decimal import Decimal
from django.db.models import (
    Sum, Count, Avg, Q, F, Max, Min,
    ExpressionWrapper, IntegerField,
)
from django.db.models.functions import TruncMonth, TruncDate


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

def bookings_overlapping_period(start: date, end: date) -> Q:
    """Bookings whose stay overlaps [start, end] inclusive."""
    return Q(check_in__lte=end, check_out__gte=start)


def get_bookings_report_data(start: date, end: date):
    """Full booking list for the given period."""
    from apps.bookings.models import Booking
    return list(
        Booking.objects
        .filter(bookings_overlapping_period(start, end))
        .select_related("guest", "room_category", "room", "organization")
        .order_by("check_in")
    )


def get_bookings_summary(start: date, end: date) -> dict:
    """Aggregate totals for the bookings PDF header."""
    from apps.bookings.models import Booking, BookingStatus
    qs = Booking.objects.filter(bookings_overlapping_period(start, end))
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
            ExpressionWrapper(
                F("check_out") - F("check_in"),
                output_field=IntegerField(),
            )
        ),
    )


def get_revenue_by_month(year: int) -> list[dict]:
    """Monthly revenue breakdown for a given year."""
    from apps.bookings.models import Booking, BookingStatus
    rows = (
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
    data_by_month = {
        row["month"].month: {
            "month": row["month"],
            "revenue": row["revenue"] or Decimal("0"),
            "bookings": row["bookings"] or 0,
        }
        for row in rows
    }
    return [
        data_by_month.get(
            month,
            {"month": date(year, month, 1), "revenue": Decimal("0"), "bookings": 0},
        )
        for month in range(1, 13)
    ]


def get_occupancy_by_category(start: date, end: date) -> list[dict]:
    """Booking count and revenue per room category for a date range."""
    from apps.bookings.models import Booking, BookingStatus
    return list(
        Booking.objects
        .filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
        )
        .filter(bookings_overlapping_period(start, end))
        .values("room_category__name")
        .annotate(
            bookings=Count("id"),
            revenue=Sum("total_price"),
            avg_nights=Avg(
                ExpressionWrapper(
                    F("check_out") - F("check_in"),
                    output_field=IntegerField(),
                )
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
        bookings = list(Booking.objects.filter(
            room=room,
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__lte=end,
            check_out__gte=start,
        ))
        nights = sum(b.nights for b in bookings)
        revenue = sum((b.total_price for b in bookings), Decimal("0"))
        total_days = (end - start).days or 1
        result.append({
            "number":    room.full_number,
            "floor":     room.floor,
            "category":  room.category.name,
            "status":    room.get_status_display(),
            "bookings":  len(bookings),
            "nights":    nights,
            "revenue":   float(revenue),
            "occupancy": min(round(nights / total_days * 100, 1), 100.0),
        })

    return result


def get_occupancy_summary(start: date, end: date) -> dict:
    """Aggregate occupancy stats for the PDF header."""
    from apps.hotel.models import Room
    from apps.bookings.models import Booking, BookingStatus

    total_rooms = Room.objects.count()
    total_days  = (end - start).days or 1

    bookings = list(Booking.objects.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
        check_in__lte=end,
        check_out__gte=start,
    ))

    total_nights = sum(b.nights for b in bookings)
    total_revenue = sum((b.total_price for b in bookings), Decimal("0"))
    max_nights   = total_rooms * total_days

    return {
        "total_rooms":    total_rooms,
        "total_days":     total_days,
        "total_bookings": len(bookings),
        "total_revenue":  total_revenue,
        "total_nights":   total_nights,
        "avg_occupancy":  round(total_nights / max_nights * 100, 1) if max_nights else 0,
    }
