"""
apps/analytics/tasks.py

Periodic Celery tasks for analytics aggregation.

Tasks:
  calculate_daily_metrics   — рассчитывает KPI за вчерашний день
  snapshot_monthly_revenue  — снимок выручки за прошлый месяц (1-го числа)
"""

import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.analytics.tasks.calculate_daily_metrics",
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def calculate_daily_metrics(self, target_date_str: str = None) -> dict:
    """
    Calculate and store DailyMetrics for a given date (default: yesterday).

    Scheduled: daily at 02:00 via Celery Beat.

    Args:
        target_date_str: ISO date string "YYYY-MM-DD" (optional, for backfill)
    """
    import datetime
    from apps.analytics.models import DailyMetrics
    from apps.bookings.models import Booking, BookingStatus
    from apps.hotel.models import Room
    from django.db.models import Count, Sum, Q

    if target_date_str:
        target_date = datetime.date.fromisoformat(target_date_str)
    else:
        target_date = (timezone.now() - datetime.timedelta(days=1)).date()

    try:
        with transaction.atomic():
            # Room counts
            room_stats = Room.objects.aggregate(
                total=Count("id"),
                available=Count("id", filter=Q(status="available")),
                occupied=Count("id", filter=Q(status="occupied")),
            )
            total_rooms    = room_stats["total"] or 0
            occupied_rooms = room_stats["occupied"] or 0
            available_rooms= room_stats["available"] or 0

            # Booking counts for the target date
            booking_stats = Booking.objects.filter(
                check_in__lte=target_date,
                check_out__gt=target_date,
            ).aggregate(
                checked_in=Count("id", filter=Q(status=BookingStatus.CHECKED_IN)),
            )

            # Revenue: bookings that checked in on target_date
            revenue_data = Booking.objects.filter(
                check_in=target_date,
                status__in=[
                    BookingStatus.CONFIRMED,
                    BookingStatus.CHECKED_IN,
                    BookingStatus.CHECKED_OUT,
                ],
            ).aggregate(
                total=Sum("total_price"),
                count=Count("id"),
            )
            total_revenue  = revenue_data["total"] or Decimal("0")
            new_bookings   = revenue_data["count"] or 0

            # New guests (first booking on this date)
            new_guests = Booking.objects.filter(
                check_in=target_date,
                status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT],
            ).values("guest_id").distinct().count()

            # Upsert DailyMetrics
            metrics, _ = DailyMetrics.objects.update_or_create(
                date=target_date,
                defaults={
                    "total_rooms":    total_rooms,
                    "occupied_rooms": occupied_rooms,
                    "available_rooms":available_rooms,
                    "total_revenue":  total_revenue,
                    "new_bookings":   new_bookings,
                    "new_guests":     new_guests,
                },
            )
            metrics.calculate_kpis()

        logger.info("[analytics] Daily metrics calculated for %s", target_date)
        return {"date": str(target_date), "revenue": float(total_revenue)}

    except Exception as exc:
        logger.error("[analytics] Failed to calculate metrics for %s: %s", target_date, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="apps.analytics.tasks.snapshot_monthly_revenue",
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def snapshot_monthly_revenue(self) -> dict:
    """
    Create a RevenueSnapshot for the previous month.

    Scheduled: 1st of every month at 01:00 via Celery Beat.
    """
    import datetime
    from apps.analytics.models import RevenueSnapshot, DailyMetrics
    from django.db.models import Sum, Count, Avg

    today = timezone.localdate()
    # Previous month
    first_of_this_month = today.replace(day=1)
    last_month_end      = first_of_this_month - datetime.timedelta(days=1)
    year  = last_month_end.year
    month = last_month_end.month

    try:
        with transaction.atomic():
            from apps.bookings.models import Booking, BookingStatus
            from django.db.models import Sum, Count

            data = Booking.objects.filter(
                check_in__year=year,
                check_in__month=month,
                status__in=[
                    BookingStatus.CONFIRMED,
                    BookingStatus.CHECKED_IN,
                    BookingStatus.CHECKED_OUT,
                ],
            ).aggregate(
                total_revenue=Sum("total_price"),
                total_bookings=Count("id"),
            )

            # Average occupancy from DailyMetrics
            occ = DailyMetrics.objects.filter(
                date__year=year, date__month=month
            ).aggregate(avg_occ=Avg("occupancy_rate"))

            snapshot, _ = RevenueSnapshot.objects.update_or_create(
                year=year, month=month,
                defaults={
                    "total_revenue":  data["total_revenue"]  or 0,
                    "total_bookings": data["total_bookings"] or 0,
                    "avg_occupancy":  occ["avg_occ"]         or 0,
                },
            )

        logger.info("[analytics] Revenue snapshot created for %d/%d", month, year)
        return {"year": year, "month": month, "revenue": float(snapshot.total_revenue)}

    except Exception as exc:
        logger.error("[analytics] Failed to snapshot revenue for %d/%d: %s", month, year, exc)
        raise self.retry(exc=exc)
