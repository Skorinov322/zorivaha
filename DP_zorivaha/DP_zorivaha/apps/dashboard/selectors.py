"""
apps/dashboard/selectors.py — read-only queries for the admin dashboard.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone


# ---------------------------------------------------------------------------
# Main KPI metrics
# ---------------------------------------------------------------------------

def get_dashboard_metrics() -> dict:
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import Room

    today          = timezone.localdate()
    first_of_month = today.replace(day=1)
    last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)
    last_month_end   = first_of_month - timedelta(days=1)

    bookings = Booking.objects.aggregate(
        pending=Count("id", filter=Q(status=BookingStatus.PENDING)),
        confirmed=Count("id", filter=Q(status=BookingStatus.CONFIRMED)),
        checked_in=Count("id", filter=Q(status=BookingStatus.CHECKED_IN)),
        today_arrivals=Count("id", filter=Q(status=BookingStatus.CONFIRMED, check_in=today)),
        today_departures=Count("id", filter=Q(status=BookingStatus.CHECKED_IN, check_out=today)),
        total_active=Count("id", filter=Q(status__in=[
            BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN
        ])),
    )

    rooms = Room.objects.aggregate(
        total=Count("id"),
        available=Count("id", filter=Q(status=Room.RoomStatus.AVAILABLE)),
        occupied=Count("id", filter=Q(status=Room.RoomStatus.OCCUPIED)),
        maintenance=Count("id", filter=Q(status=Room.RoomStatus.MAINTENANCE)),
        cleaning=Count("id", filter=Q(status=Room.RoomStatus.CLEANING)),
    )

    # Revenue this month
    revenue_this_month = Booking.objects.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
        check_in__gte=first_of_month,
    ).aggregate(total=Sum("total_price"))["total"] or Decimal("0")

    # Revenue last month (for comparison)
    revenue_last_month = Booking.objects.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
        check_in__gte=last_month_start,
        check_in__lte=last_month_end,
    ).aggregate(total=Sum("total_price"))["total"] or Decimal("0")

    # Revenue change %
    if revenue_last_month > 0:
        revenue_change = round(
            (float(revenue_this_month) - float(revenue_last_month))
            / float(revenue_last_month) * 100, 1
        )
    else:
        revenue_change = 0

    total = rooms["total"] or 1
    return {
        "bookings":            bookings,
        "rooms":               rooms,
        "revenue_this_month":  float(revenue_this_month),
        "revenue_last_month":  float(revenue_last_month),
        "revenue_change":      revenue_change,
        "occupancy_rate":      round(rooms["occupied"] / total * 100, 1),
    }


# ---------------------------------------------------------------------------
# Revenue chart data (last 12 months)
# ---------------------------------------------------------------------------

def get_revenue_chart_data() -> dict:
    """Monthly revenue for the last 12 months — used by Chart.js."""
    from apps.bookings.models import Booking, BookingStatus
    from django.db.models.functions import TruncMonth

    today = timezone.localdate()
    start = (today.replace(day=1) - timedelta(days=365)).replace(day=1)

    rows = (
        Booking.objects
        .filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__gte=start,
        )
        .annotate(month=TruncMonth("check_in"))
        .values("month")
        .annotate(revenue=Sum("total_price"), bookings=Count("id"))
        .order_by("month")
    )

    labels   = []
    revenues = []
    counts   = []
    for row in rows:
        labels.append(row["month"].strftime("%b %Y"))
        revenues.append(float(row["revenue"] or 0))
        counts.append(row["bookings"])

    return {"labels": labels, "revenues": revenues, "counts": counts}


# ---------------------------------------------------------------------------
# Occupancy calendar data (current month)
# ---------------------------------------------------------------------------

def get_occupancy_calendar(year: int = None, month: int = None) -> list[dict]:
    """
    Returns day-by-day occupancy for a given month.
    Each entry: {date, occupied, total, pct, bookings_list}
    """
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import Room
    import calendar

    today = timezone.localdate()
    year  = year  or today.year
    month = month or today.month

    total_rooms = Room.objects.count() or 1
    _, days_in_month = calendar.monthrange(year, month)

    result = []
    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        occupied = Booking.objects.filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN],
            check_in__lte=d,
            check_out__gt=d,
        ).count()
        result.append({
            "date":     d,
            "day":      day,
            "occupied": occupied,
            "total":    total_rooms,
            "pct":      round(occupied / total_rooms * 100),
            "is_today": d == today,
            "is_past":  d < today,
        })
    return result


# ---------------------------------------------------------------------------
# Booking status breakdown (for donut chart)
# ---------------------------------------------------------------------------

def get_booking_status_breakdown() -> list[dict]:
    from apps.bookings.models import Booking, BookingStatus

    rows = (
        Booking.objects
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    color_map = {
        "pending":    "#ffc107",
        "confirmed":  "#28a745",
        "checked_in": "#6ea8fe",
        "checked_out":"#20c997",
        "cancelled":  "#dc3545",
        "no_show":    "#6c757d",
    }
    label_map = dict(BookingStatus.choices)
    return [
        {
            "status": r["status"],
            "label":  label_map.get(r["status"], r["status"]),
            "count":  r["count"],
            "color":  color_map.get(r["status"], "#888"),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Room status grid
# ---------------------------------------------------------------------------

def get_room_status_grid() -> list[dict]:
    from apps.hotel.models import Room

    rooms = (
        Room.objects
        .select_related("category")
        .order_by("floor", "number")
    )
    color_map = {
        "available":   ("#28a745", "Свободен"),
        "occupied":    ("#6ea8fe", "Занят"),
        "cleaning":    ("#ffc107", "Уборка"),
        "maintenance": ("#dc3545", "Обслуживание"),
        "blocked":     ("#6c757d", "Заблокирован"),
    }
    result = []
    for room in rooms:
        color, label = color_map.get(room.status, ("#888", room.get_status_display()))
        result.append({
            "number":   room.number,
            "floor":    room.floor,
            "category": room.category.name,
            "status":   room.status,
            "label":    label,
            "color":    color,
            "pk":       room.pk,
        })
    return result


# ---------------------------------------------------------------------------
# Recent activity feed
# ---------------------------------------------------------------------------

def get_recent_activity(limit: int = 15) -> list[dict]:
    """Combined feed: recent booking history entries."""
    from apps.bookings.models import BookingHistory

    entries = (
        BookingHistory.objects
        .select_related("booking", "changed_by")
        .order_by("-created_at")[:limit]
    )
    icon_map = {
        "created":    ("bi-plus-circle",      "#28a745"),
        "confirmed":  ("bi-check-circle",     "#6ea8fe"),
        "checked_in": ("bi-door-open",        "#c9a84c"),
        "checked_out":("bi-door-closed",      "#20c997"),
        "cancelled":  ("bi-x-circle",         "#dc3545"),
        "no_show":    ("bi-person-x",         "#6c757d"),
        "payment":    ("bi-credit-card",      "#ffc107"),
        "modified":   ("bi-pencil",           "#adb5bd"),
    }
    result = []
    for e in entries:
        icon, color = icon_map.get(e.action, ("bi-circle", "#888"))
        result.append({
            "time":    e.created_at,
            "action":  e.get_action_display(),
            "booking": e.booking.confirmation_number,
            "booking_pk": str(e.booking.pk),
            "actor":   e.changed_by.get_short_name() if e.changed_by else "Система",
            "note":    e.note,
            "icon":    icon,
            "color":   color,
        })
    return result


# ---------------------------------------------------------------------------
# Messages (CRM)
# ---------------------------------------------------------------------------

def get_unread_messages(user) -> int:
    from apps.crm.models import Message
    return Message.objects.filter(
        recipient=user,
        status=Message.MessageStatus.UNREAD,
    ).count()


def get_recent_messages(user, limit: int = 5):
    from apps.crm.models import Message
    return (
        Message.objects
        .filter(recipient=user)
        .select_related("sender", "booking")
        .order_by("-created_at")[:limit]
    )


# ---------------------------------------------------------------------------
# Management table
# ---------------------------------------------------------------------------

def get_all_bookings_for_management(status: str = "", search: str = ""):
    from apps.bookings.models import Booking
    qs = (
        Booking.objects
        .select_related("guest", "room_category", "room")
        .order_by("-created_at")
    )
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(confirmation_number__icontains=search)
            | Q(guest_last_name__icontains=search)
            | Q(guest_first_name__icontains=search)
            | Q(guest_email__icontains=search)
        )
    return qs
