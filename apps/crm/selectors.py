"""
crm/selectors.py — read-only queries for CRM module.
"""

from typing import Optional
from django.db.models import QuerySet, Count, Sum, Prefetch, Q

from .models import ClientProfile, AdminComment, Interaction, Task, Organization


# ---------------------------------------------------------------------------
# ClientProfile
# ---------------------------------------------------------------------------

def get_all_clients(
    search: str = "",
    status: str = "",
    client_type: str = "",
    loyalty_tier: str = "",
) -> QuerySet:
    """Filtered client list for the CRM dashboard."""
    qs = (
        ClientProfile.objects.select_related("user", "assigned_manager", "organization")
        .annotate(
            total_bookings=Count("user__bookings", distinct=True),
            active_bookings=Count(
                "user__bookings",
                filter=Q(user__bookings__status__in=["pending", "confirmed", "checked_in"]),
                distinct=True,
            ),
        )
        .order_by("-total_spent", "-user__created_at")
    )
    if search:
        qs = qs.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__phone__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if client_type:
        qs = qs.filter(client_type=client_type)
    if loyalty_tier:
        qs = qs.filter(loyalty_tier=loyalty_tier)
    return qs


def get_client_profile_detail(user_id: int) -> ClientProfile:
    """Full client profile with all related data for the detail page."""
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        ClientProfile.objects
        .select_related("user", "assigned_manager", "organization", "preferred_room_category")
        .prefetch_related(
            Prefetch(
                "admin_comments",
                queryset=AdminComment.objects.select_related("author").order_by("-is_pinned", "-created_at"),
            ),
            Prefetch(
                "interactions",
                queryset=Interaction.objects.select_related("staff", "booking").order_by("-created_at")[:20],
                to_attr="recent_interactions",
            ),
            Prefetch(
                "tasks",
                queryset=Task.objects.select_related("assigned_to").filter(
                    status__in=["open", "in_progress"]
                ).order_by("-priority", "due_date"),
                to_attr="open_tasks",
            ),
            Prefetch(
                "user__bookings",
                queryset=__import__(
                    "apps.bookings.models", fromlist=["Booking"]
                ).Booking.objects.select_related("room_category", "room")
                .order_by("-created_at"),
                to_attr="all_bookings",
            ),
        ),
        user_id=user_id,
    )


def get_client_booking_history(user_id: int) -> QuerySet:
    """All bookings for a client, ordered by date."""
    from apps.bookings.models import Booking
    return (
        Booking.objects.filter(guest_id=user_id)
        .select_related("room_category", "room", "organization")
        .order_by("-check_in")
    )


def get_client_stats(profile: ClientProfile) -> dict:
    """Aggregate stats for a client profile detail page."""
    from apps.bookings.models import Booking, BookingStatus
    bookings = Booking.objects.filter(guest=profile.user)
    return {
        "total":      bookings.count(),
        "active":     bookings.filter(status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]).count(),
        "completed":  bookings.filter(status=BookingStatus.CHECKED_OUT).count(),
        "cancelled":  bookings.filter(status=BookingStatus.CANCELLED).count(),
        "no_show":    bookings.filter(status=BookingStatus.NO_SHOW).count(),
        "total_spent": profile.total_spent,
        "total_nights": profile.total_nights,
        "loyalty_points": profile.loyalty_points,
    }


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def get_open_tasks(manager=None) -> QuerySet:
    qs = (
        Task.objects.filter(status__in=["open", "in_progress"])
        .select_related("assigned_to", "client__user", "booking")
        .order_by("-priority", "due_date")
    )
    if manager:
        qs = qs.filter(assigned_to=manager)
    return qs


def get_all_tasks(status: str = "", priority: str = "") -> QuerySet:
    qs = (
        Task.objects.select_related("assigned_to", "client__user", "booking", "created_by")
        .order_by("-priority", "due_date", "-created_at")
    )
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    return qs


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

def get_all_organizations(search: str = "") -> QuerySet:
    qs = (
        Organization.objects.filter(is_active=True)
        .annotate(client_count=Count("clients", distinct=True))
        .order_by("name")
    )
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(inn__icontains=search)
            | Q(contact_person__icontains=search)
        )
    return qs


def get_organization_detail(pk: int) -> Organization:
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        Organization.objects.prefetch_related(
            Prefetch("clients", queryset=ClientProfile.objects.select_related("user"))
        ),
        pk=pk,
    )


# ---------------------------------------------------------------------------
# CRM Dashboard metrics
# ---------------------------------------------------------------------------

def get_crm_dashboard_metrics() -> dict:
    from apps.bookings.models import Booking, BookingStatus
    from django.utils import timezone
    today = timezone.localdate()

    return {
        "total_clients":    ClientProfile.objects.count(),
        "vip_clients":      ClientProfile.objects.filter(status="vip").count(),
        "blacklisted":      ClientProfile.objects.filter(is_blacklisted=True).count(),
        "open_tasks":       Task.objects.filter(status__in=["open", "in_progress"]).count(),
        "overdue_tasks":    Task.objects.filter(
            status__in=["open", "in_progress"],
            due_date__lt=today,
        ).count(),
        "new_clients_month": ClientProfile.objects.filter(
            created_at__year=today.year,
            created_at__month=today.month,
        ).count(),
    }
