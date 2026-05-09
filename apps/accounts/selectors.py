"""Account selectors."""

from django.db.models import Count, Sum, Q


def get_user_booking_stats(user) -> dict:
    """Aggregated booking stats for the personal cabinet dashboard."""
    from apps.bookings.models import Booking, BookingStatus
    qs = Booking.objects.filter(guest=user)
    return {
        "total":     qs.count(),
        "active":    qs.filter(status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED]).count(),
        "checked_in": qs.filter(status=BookingStatus.CHECKED_IN).count(),
        "completed": qs.filter(status=BookingStatus.CHECKED_OUT).count(),
        "cancelled": qs.filter(status=BookingStatus.CANCELLED).count(),
        "total_spent": qs.filter(
            status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]
        ).aggregate(s=Sum("total_price"))["s"] or 0,
        "total_nights": qs.filter(
            status=BookingStatus.CHECKED_OUT
        ).aggregate(s=Sum("adults"))["s"] or 0,  # approximate
    }


def get_user_crm_profile(user):
    """Return CRM profile for the user, or None if not exists."""
    try:
        return user.crm_profile
    except Exception:
        return None


def get_user_stay_history(user):
    """Completed stays for the 'История проживания' section."""
    from apps.bookings.models import Booking, BookingStatus
    return (
        Booking.objects.filter(
            guest=user,
            status=BookingStatus.CHECKED_OUT,
        )
        .select_related("room_category", "room")
        .order_by("-check_out")
    )
