"""
apps/analytics/selectors.py

All read-only analytics queries.
Used by MetricsView in apps/dashboard/views.py.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q, Avg, F
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone


# ---------------------------------------------------------------------------
# Visitors
# ---------------------------------------------------------------------------

def get_visitor_stats(days: int = 30) -> dict:
    """
    Unique visitors (by session_key) and page views for the last N days.
    Returns daily breakdown for chart + totals.
    """
    from apps.analytics.models import PageView

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    qs = PageView.objects.filter(viewed_at__date__gte=start)

    # Daily breakdown
    daily = (
        qs
        .annotate(day=TruncDate("viewed_at"))
        .values("day")
        .annotate(
            views=Count("id"),
            unique=Count("session_key", distinct=True),
        )
        .order_by("day")
    )

    # Build full date range (fill gaps with 0)
    daily_map = {row["day"]: row for row in daily}
    labels, views_data, unique_data = [], [], []
    for i in range(days):
        d = start + timedelta(days=i)
        row = daily_map.get(d, {"views": 0, "unique": 0})
        labels.append(d.strftime("%d.%m"))
        views_data.append(row["views"])
        unique_data.append(row["unique"])

    totals = qs.aggregate(
        total_views=Count("id"),
        unique_visitors=Count("session_key", distinct=True),
        auth_visitors=Count("user", filter=Q(user__isnull=False), distinct=True),
    )

    return {
        "labels":          labels,
        "views":           views_data,
        "unique":          unique_data,
        "total_views":     totals["total_views"] or 0,
        "unique_visitors": totals["unique_visitors"] or 0,
        "auth_visitors":   totals["auth_visitors"] or 0,
    }


def get_page_type_breakdown(days: int = 30) -> list[dict]:
    """Views by page type for the last N days."""
    from apps.analytics.models import PageView

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    rows = (
        PageView.objects
        .filter(viewed_at__date__gte=start)
        .values("page_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    label_map = {
        "home":            "Главная",
        "room_list":       "Список номеров",
        "room_detail":     "Страница номера",
        "booking_form":    "Форма бронирования",
        "booking_success": "Успешное бронирование",
        "about":           "О нас",
        "contacts":        "Контакты",
        "other":           "Другое",
    }
    color_map = {
        "home":            "#c9a84c",
        "room_list":       "#6ea8fe",
        "room_detail":     "#20c997",
        "booking_form":    "#ffc107",
        "booking_success": "#28a745",
        "about":           "#adb5bd",
        "contacts":        "#adb5bd",
        "other":           "#555",
    }
    return [
        {
            "page_type": r["page_type"],
            "label":     label_map.get(r["page_type"], r["page_type"]),
            "count":     r["count"],
            "color":     color_map.get(r["page_type"], "#888"),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Conversion funnel
# ---------------------------------------------------------------------------

def get_conversion_funnel(days: int = 30) -> dict:
    """
    Booking conversion funnel for the last N days.

    Steps:
      1. Visitors (unique sessions on public pages)
      2. Room views (unique sessions on room_detail)
      3. Booking form opens (unique sessions on booking_form)
      4. Bookings created
      5. Bookings confirmed

    Returns rates between each step.
    """
    from apps.analytics.models import PageView
    from apps.bookings.models import Booking, BookingStatus

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    start_dt = timezone.make_aware(
        __import__("datetime").datetime.combine(start, __import__("datetime").time.min)
    )

    visitors = PageView.objects.filter(
        viewed_at__date__gte=start
    ).values("session_key").distinct().count()

    room_viewers = PageView.objects.filter(
        viewed_at__date__gte=start,
        page_type="room_detail",
    ).values("session_key").distinct().count()

    form_openers = PageView.objects.filter(
        viewed_at__date__gte=start,
        page_type="booking_form",
    ).values("session_key").distinct().count()

    bookings_created = Booking.objects.filter(
        created_at__gte=start_dt
    ).count()

    bookings_confirmed = Booking.objects.filter(
        created_at__gte=start_dt,
        status__in=[
            BookingStatus.CONFIRMED,
            BookingStatus.CHECKED_IN,
            BookingStatus.CHECKED_OUT,
        ],
    ).count()

    def rate(a, b):
        return round(a / b * 100, 1) if b > 0 else 0

    return {
        "steps": [
            {"label": "Посетители",          "value": visitors,           "color": "#6ea8fe"},
            {"label": "Просмотр номеров",     "value": room_viewers,       "color": "#c9a84c"},
            {"label": "Открыли форму",        "value": form_openers,       "color": "#ffc107"},
            {"label": "Создали бронь",        "value": bookings_created,   "color": "#20c997"},
            {"label": "Подтверждённые брони", "value": bookings_confirmed, "color": "#28a745"},
        ],
        "rates": {
            "visit_to_room":    rate(room_viewers,       visitors),
            "room_to_form":     rate(form_openers,       room_viewers),
            "form_to_booking":  rate(bookings_created,   form_openers),
            "booking_to_confirm": rate(bookings_confirmed, bookings_created),
            "overall":          rate(bookings_confirmed, visitors),
        },
        "period_days": days,
    }


# ---------------------------------------------------------------------------
# Occupancy metrics
# ---------------------------------------------------------------------------

def get_occupancy_trend(days: int = 30) -> dict:
    """
    Daily occupancy rate for the last N days.
    Uses DailyMetrics if available, falls back to live calculation.
    """
    from apps.analytics.models import DailyMetrics
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import Room

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    total_rooms = Room.objects.count() or 1

    # Try DailyMetrics first (pre-aggregated)
    metrics_qs = DailyMetrics.objects.filter(
        date__gte=start
    ).order_by("date")

    metrics_map = {m.date: float(m.occupancy_rate) for m in metrics_qs}

    labels, occupancy_data, adr_data = [], [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%d.%m"))

        if d in metrics_map:
            occupancy_data.append(metrics_map[d])
        else:
            # Live calculation for dates without pre-aggregated data
            occupied = Booking.objects.filter(
                status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN],
                check_in__lte=d,
                check_out__gt=d,
            ).count()
            occupancy_data.append(round(occupied / total_rooms * 100, 1))

    avg_occupancy = round(sum(occupancy_data) / len(occupancy_data), 1) if occupancy_data else 0

    return {
        "labels":        labels,
        "occupancy":     occupancy_data,
        "avg_occupancy": avg_occupancy,
        "period_days":   days,
    }


def get_occupancy_by_category() -> list[dict]:
    """Occupancy rate per room category (current month)."""
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import RoomCategory, Room

    today = timezone.localdate()
    first_of_month = today.replace(day=1)

    categories = RoomCategory.objects.filter(is_active=True).prefetch_related("rooms")
    result = []
    for cat in categories:
        total_rooms = cat.rooms.count()
        if not total_rooms:
            continue
        bookings = Booking.objects.filter(
            room_category=cat,
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__gte=first_of_month,
        ).count()
        result.append({
            "name":     cat.name,
            "bookings": bookings,
            "rooms":    total_rooms,
            "rate":     round(bookings / total_rooms * 100, 1) if total_rooms else 0,
        })
    return sorted(result, key=lambda x: -x["bookings"])


# ---------------------------------------------------------------------------
# Popular rooms
# ---------------------------------------------------------------------------

def get_popular_room_categories(limit: int = 8) -> list[dict]:
    """
    Most booked room categories with revenue, avg nights, avg rating.
    """
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import RoomCategory

    today = timezone.localdate()
    start = today.replace(day=1).replace(month=1)  # YTD

    rows = (
        Booking.objects
        .filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__gte=start,
        )
        .values("room_category__id", "room_category__name", "room_category__base_price_per_night")
        .annotate(
            bookings=Count("id"),
            revenue=Sum("total_price"),
            avg_nights=Avg(
                F("check_out") - F("check_in")
            ),
        )
        .order_by("-bookings")[:limit]
    )

    result = []
    for r in rows:
        result.append({
            "id":          r["room_category__id"],
            "name":        r["room_category__name"],
            "base_price":  r["room_category__base_price_per_night"],
            "bookings":    r["bookings"],
            "revenue":     float(r["revenue"] or 0),
            "avg_nights":  round(float(r["avg_nights"].days if r["avg_nights"] else 0), 1),
        })
    return result


def get_room_revenue_chart() -> dict:
    """Revenue per room category for the current year — horizontal bar chart."""
    from apps.bookings.models import Booking, BookingStatus

    today = timezone.localdate()
    rows = (
        Booking.objects
        .filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            check_in__year=today.year,
        )
        .values("room_category__name")
        .annotate(revenue=Sum("total_price"), bookings=Count("id"))
        .order_by("-revenue")[:8]
    )
    labels   = [r["room_category__name"] for r in rows]
    revenues = [float(r["revenue"] or 0) for r in rows]
    counts   = [r["bookings"] for r in rows]
    return {"labels": labels, "revenues": revenues, "counts": counts}


# ---------------------------------------------------------------------------
# Bookings trend
# ---------------------------------------------------------------------------

def get_bookings_trend(days: int = 30) -> dict:
    """Daily new bookings for the last N days."""
    from apps.bookings.models import Booking, BookingStatus

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    start_dt = timezone.make_aware(
        __import__("datetime").datetime.combine(start, __import__("datetime").time.min)
    )

    daily = (
        Booking.objects
        .filter(created_at__gte=start_dt)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total=Count("id"),
            confirmed=Count("id", filter=Q(status__in=[
                BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT
            ])),
            cancelled=Count("id", filter=Q(status=BookingStatus.CANCELLED)),
        )
        .order_by("day")
    )

    daily_map = {row["day"]: row for row in daily}
    labels, total_data, confirmed_data, cancelled_data = [], [], [], []
    for i in range(days):
        d = start + timedelta(days=i)
        row = daily_map.get(d, {"total": 0, "confirmed": 0, "cancelled": 0})
        labels.append(d.strftime("%d.%m"))
        total_data.append(row["total"])
        confirmed_data.append(row["confirmed"])
        cancelled_data.append(row["cancelled"])

    return {
        "labels":    labels,
        "total":     total_data,
        "confirmed": confirmed_data,
        "cancelled": cancelled_data,
    }


# ---------------------------------------------------------------------------
# Summary KPIs for metrics page
# ---------------------------------------------------------------------------

def get_metrics_summary(days: int = 30) -> dict:
    """All top-level KPIs for the metrics dashboard."""
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import Room
    from apps.accounts.models import User

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    start_dt = timezone.make_aware(
        __import__("datetime").datetime.combine(start, __import__("datetime").time.min)
    )
    prev_start_dt = start_dt - timedelta(days=days)

    # Current period
    bookings_cur = Booking.objects.filter(created_at__gte=start_dt)
    revenue_cur  = bookings_cur.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]
    ).aggregate(s=Sum("total_price"))["s"] or Decimal("0")

    # Previous period (for comparison)
    bookings_prev = Booking.objects.filter(
        created_at__gte=prev_start_dt, created_at__lt=start_dt
    )
    revenue_prev = bookings_prev.filter(
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]
    ).aggregate(s=Sum("total_price"))["s"] or Decimal("0")

    def delta(cur, prev):
        if prev and prev > 0:
            return round((float(cur) - float(prev)) / float(prev) * 100, 1)
        return 0

    # Visitors
    from apps.analytics.models import PageView
    visitors_cur  = PageView.objects.filter(viewed_at__date__gte=start).values("session_key").distinct().count()
    visitors_prev = PageView.objects.filter(
        viewed_at__date__gte=start - timedelta(days=days),
        viewed_at__date__lt=start,
    ).values("session_key").distinct().count()

    # New users
    new_users_cur  = User.objects.filter(created_at__gte=start_dt).count()
    new_users_prev = User.objects.filter(
        created_at__gte=prev_start_dt, created_at__lt=start_dt
    ).count()

    # Conversion
    form_opens = PageView.objects.filter(
        viewed_at__date__gte=start, page_type="booking_form"
    ).values("session_key").distinct().count()
    bookings_count = bookings_cur.count()
    conversion = round(bookings_count / form_opens * 100, 1) if form_opens > 0 else 0

    # Occupancy
    total_rooms = Room.objects.count() or 1
    occupied    = Room.objects.filter(status="occupied").count()
    occupancy   = round(occupied / total_rooms * 100, 1)

    return {
        "period_days":    days,
        "visitors":       visitors_cur,
        "visitors_delta": delta(visitors_cur, visitors_prev),
        "new_users":      new_users_cur,
        "new_users_delta":delta(new_users_cur, new_users_prev),
        "bookings":       bookings_count,
        "bookings_delta": delta(bookings_count, bookings_prev.count()),
        "revenue":        float(revenue_cur),
        "revenue_delta":  delta(revenue_cur, revenue_prev),
        "conversion":     conversion,
        "occupancy":      occupancy,
        "total_rooms":    total_rooms,
        "occupied_rooms": occupied,
    }
