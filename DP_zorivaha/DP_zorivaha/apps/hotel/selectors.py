"""
hotel/selectors.py — read-only queries only.
"""

from datetime import date
from typing import Optional

from django.db.models import QuerySet, Prefetch, Count, Q

from .models import RoomCategory, Room, Amenity, RoomImage


# ---------------------------------------------------------------------------
# Public selectors
# ---------------------------------------------------------------------------

def get_active_room_categories() -> QuerySet:
    """All active categories with prefetched amenities and primary image."""
    return (
        RoomCategory.objects.filter(is_active=True)
        .prefetch_related(
            "amenities",
            Prefetch(
                "images",
                queryset=RoomImage.objects.filter(is_primary=True).order_by("sort_order"),
                to_attr="primary_images",
            ),
        )
        .annotate(room_count=Count("rooms", filter=Q(rooms__status="available")))
        .order_by("sort_order", "name")
    )


def get_featured_room_categories(limit: int = 3) -> QuerySet:
    """Featured categories for the homepage."""
    return (
        RoomCategory.objects.filter(is_active=True, is_featured=True)
        .prefetch_related(
            "amenities",
            Prefetch(
                "images",
                queryset=RoomImage.objects.filter(is_primary=True),
                to_attr="primary_images",
            ),
        )
        .order_by("sort_order")[:limit]
    )


def get_room_category_by_slug(slug: str) -> RoomCategory:
    """Single active category or 404."""
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        RoomCategory.objects
        .prefetch_related(
            "amenities",
            "images",
            Prefetch(
                "reviews",
                queryset=__import__(
                    "apps.hotel.models", fromlist=["RoomReview"]
                ).RoomReview.objects.filter(is_approved=True)
                .select_related("guest")
                .order_by("-created_at")[:10],
                to_attr="approved_reviews",
            ),
        )
        .annotate(
            available_rooms=Count("rooms", filter=Q(rooms__status="available")),
            total_rooms=Count("rooms"),
        ),
        slug=slug,
        is_active=True,
    )


def get_available_categories(check_in: date, check_out: date, guests: int = 1) -> QuerySet:
    """Categories with at least one free room for the given period."""
    from apps.bookings.models import Booking, BookingStatus

    available_category_ids = []
    
    # Check each category for availability
    for category in RoomCategory.objects.filter(is_active=True, max_guests__gte=guests):
        rooms = Room.objects.filter(
            category=category,
            status=Room.RoomStatus.AVAILABLE,
        )
        
        # Check if any room has availability
        for room in rooms:
            if room.has_availability(check_in, check_out):
                available_category_ids.append(category.id)
                break

    return (
        RoomCategory.objects.filter(
            id__in=available_category_ids,
            is_active=True,
            max_guests__gte=guests,
        )
        .prefetch_related(
            "amenities",
            Prefetch(
                "images",
                queryset=RoomImage.objects.filter(is_primary=True),
                to_attr="primary_images",
            ),
        )
        .order_by("sort_order")
    )


def get_all_amenities() -> QuerySet:
    return Amenity.objects.all().order_by("category", "sort_order", "name")


# ---------------------------------------------------------------------------
# Staff selectors
# ---------------------------------------------------------------------------

def get_all_room_categories_for_staff() -> QuerySet:
    """All categories (including inactive) for the management panel."""
    return (
        RoomCategory.objects.all()
        .prefetch_related("amenities")
        .annotate(
            total_rooms=Count("rooms"),
            available_rooms=Count("rooms", filter=Q(rooms__status="available")),
            occupied_rooms=Count("rooms", filter=Q(rooms__status="occupied")),
        )
        .order_by("sort_order", "name")
    )


def get_room_category_for_edit(pk: int) -> RoomCategory:
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        RoomCategory.objects.prefetch_related("amenities", "images"),
        pk=pk,
    )


def get_all_rooms_for_staff(
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    floor: Optional[int] = None,
    search: str = "",
) -> QuerySet:
    """Filtered room list for the management panel."""
    qs = (
        Room.objects.select_related("category")
        .prefetch_related("extra_amenities")
        .order_by("category__sort_order", "floor", "number")
    )
    if category_id:
        qs = qs.filter(category_id=category_id)
    if status:
        qs = qs.filter(status=status)
    if floor:
        qs = qs.filter(floor=floor)
    if search:
        qs = qs.filter(number__icontains=search)
    return qs


def get_room_for_edit(pk: int) -> Room:
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        Room.objects.select_related("category").prefetch_related("extra_amenities"),
        pk=pk,
    )


def get_rooms_by_category(category_id: int, status: Optional[str] = None) -> QuerySet:
    qs = Room.objects.filter(category_id=category_id).select_related("category")
    if status:
        qs = qs.filter(status=status)
    return qs


def get_available_room_for_category(
    category_id: int, check_in: date, check_out: date
) -> Optional[Room]:
    """Find one free physical room for check-in assignment."""
    from apps.bookings.models import Booking, BookingStatus

    # Get all rooms for this category
    rooms = Room.objects.filter(
        category_id=category_id,
        status=Room.RoomStatus.AVAILABLE,
    ).order_by("number", "subdivision")

    for room in rooms:
        if room.has_availability(check_in, check_out):
            return room
    
    return None


def get_available_rooms_for_category(
    category_id: int, check_in: date, check_out: date
) -> QuerySet:
    """Get all available rooms for a category during the given period."""
    from apps.bookings.models import Booking, BookingStatus

    available_rooms = []
    rooms = Room.objects.filter(
        category_id=category_id,
        status=Room.RoomStatus.AVAILABLE,
    ).order_by("number", "subdivision")

    for room in rooms:
        if room.has_availability(check_in, check_out):
            available_rooms.append(room.id)
    
    return Room.objects.filter(id__in=available_rooms)


def get_room_stats() -> dict:
    """Aggregate room counts by status for the dashboard."""
    from django.db.models import Count
    stats = Room.objects.aggregate(
        total=Count("id"),
        available=Count("id", filter=Q(status="available")),
        occupied=Count("id", filter=Q(status="occupied")),
        maintenance=Count("id", filter=Q(status="maintenance")),
        cleaning=Count("id", filter=Q(status="cleaning")),
        blocked=Count("id", filter=Q(status="blocked")),
    )
    total = stats["total"] or 1
    stats["occupancy_pct"] = round(stats["occupied"] / total * 100, 1)
    return stats
