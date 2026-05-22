"""
hotel/services.py

Business logic for hotel room management.
All write operations go through here — never directly in views.
"""

from django.db import transaction
from django.utils.text import slugify

from apps.core.utils import slugify_ru
from .models import Amenity, RoomCategory, Room, RoomImage


# ---------------------------------------------------------------------------
# RoomCategory
# ---------------------------------------------------------------------------

@transaction.atomic
def create_room_category(cleaned_data: dict, actor=None) -> RoomCategory:
    """Create a new room category from validated form data."""
    amenities = cleaned_data.pop("amenities", [])
    new_amenity_names = cleaned_data.pop("new_amenities", [])

    # Auto-generate slug if not provided
    if not cleaned_data.get("slug"):
        cleaned_data["slug"] = _unique_slug(cleaned_data["name"])

    category = RoomCategory.objects.create(**cleaned_data)
    category.amenities.set(_merge_amenities(amenities, new_amenity_names))
    return category


@transaction.atomic
def update_room_category(category: RoomCategory, cleaned_data: dict, actor=None) -> RoomCategory:
    """Update an existing room category."""
    amenities = cleaned_data.pop("amenities", None)
    new_amenity_names = cleaned_data.pop("new_amenities", [])

    for field, value in cleaned_data.items():
        setattr(category, field, value)
    category.save()

    if amenities is not None:
        category.amenities.set(_merge_amenities(amenities, new_amenity_names))
    return category


def delete_room_category(category: RoomCategory) -> None:
    """
    Soft-delete: deactivate the category instead of physical deletion.
    Physical rooms are preserved; they just won't appear on the public site.
    """
    category.is_active = False
    category.save(update_fields=["is_active", "updated_at"])


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

@transaction.atomic
def create_room(cleaned_data: dict, actor=None) -> Room:
    """Create a new physical room."""
    extra_amenities = cleaned_data.pop("extra_amenities", [])
    room = Room.objects.create(**cleaned_data)
    if extra_amenities:
        room.extra_amenities.set(extra_amenities)
    return room


@transaction.atomic
def update_room(room: Room, cleaned_data: dict, actor=None) -> Room:
    """Update an existing physical room."""
    extra_amenities = cleaned_data.pop("extra_amenities", None)

    for field, value in cleaned_data.items():
        setattr(room, field, value)
    room.save()

    if extra_amenities is not None:
        room.extra_amenities.set(extra_amenities)
    return room


def update_room_status(room: Room, new_status: str, actor=None) -> Room:
    """Change room status with a single DB write."""
    room.status = new_status
    room.save(update_fields=["status", "updated_at"])
    return room


def delete_room(room: Room) -> None:
    """Physical delete — only allowed if room has no active bookings."""
    from apps.bookings.models import Booking, BookingStatus
    active = Booking.objects.filter(
        room=room,
        status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN],
    ).exists()
    if active:
        raise ValueError(
            f"Нельзя удалить номер {room.number}: есть активные бронирования."
        )
    room.delete()


# ---------------------------------------------------------------------------
# RoomImage
# ---------------------------------------------------------------------------

@transaction.atomic
def add_room_image(category: RoomCategory, image_file, caption: str = "",
                   alt_text: str = "", is_primary: bool = False,
                   sort_order: int = 0) -> RoomImage:
    """Attach an image to a room category."""
    img = RoomImage.objects.create(
        category=category,
        image=image_file,
        caption=caption,
        alt_text=alt_text,
        is_primary=is_primary,
        sort_order=sort_order,
    )
    return img


def delete_room_image(image: RoomImage) -> None:
    """Delete an image and its file from storage."""
    # Delete the file from storage
    if image.image:
        image.image.delete(save=False)
    image.delete()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_slug(name: str) -> str:
    """Generate a unique slug from a Russian/Latin name."""
    base = slugify_ru(name) or slugify(name)
    slug = base
    counter = 1
    while RoomCategory.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _merge_amenities(selected_amenities, new_amenity_names: list[str]) -> list[Amenity]:
    """Return selected amenities plus newly created ones without duplicates."""
    amenities = list(selected_amenities or [])
    existing_ids = {amenity.pk for amenity in amenities if amenity.pk}

    for name in new_amenity_names:
        amenity = Amenity.objects.filter(name__iexact=name).first()
        if amenity is None:
            amenity = Amenity.objects.create(name=name)
        if amenity.pk not in existing_ids:
            amenities.append(amenity)
            existing_ids.add(amenity.pk)

    return amenities
