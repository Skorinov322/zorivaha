"""
hotel/models.py

Models:
  Amenity         — удобство (Wi-Fi, бассейн, спа, …)
  RoomCategory    — тип номера (Стандарт, Делюкс, Люкс, …)
  RoomImage       — галерея фотографий категории
  Room            — физический номер в гостинице
  SeasonalPrice   — сезонные цены (переопределяют базовую цену категории)
  RoomReview      — отзыв гостя о номере
"""

import datetime
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, OrderedModel
from apps.core.utils import slugify_ru


# ---------------------------------------------------------------------------
# Amenity
# ---------------------------------------------------------------------------

class AmenityCategory(models.TextChoices):
    COMFORT = "comfort", _("Комфорт")
    TECH = "tech", _("Технологии")
    FOOD = "food", _("Питание")
    WELLNESS = "wellness", _("Здоровье и красота")
    SERVICE = "service", _("Сервис")


class Amenity(TimeStampedModel, OrderedModel):
    """
    A single amenity / feature that can be attached to room categories.
    Examples: Wi-Fi, кондиционер, мини-бар, джакузи.
    """

    name = models.CharField(_("название"), max_length=100, unique=True)
    icon = models.CharField(
        _("иконка Bootstrap Icons"), max_length=60, default="bi-check-circle",
        help_text=_("Например: bi-wifi, bi-tv, bi-cup-hot")
    )
    category = models.CharField(
        _("категория"), max_length=20,
        choices=AmenityCategory.choices, default=AmenityCategory.COMFORT,
        db_index=True,
    )
    is_highlighted = models.BooleanField(
        _("выделить на сайте"), default=False,
        help_text=_("Показывать в карточке номера крупно")
    )

    class Meta:
        verbose_name = _("удобство")
        verbose_name_plural = _("удобства")
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# RoomCategory
# ---------------------------------------------------------------------------

class RoomCategory(TimeStampedModel, OrderedModel):
    """
    Room type / category.
    One category → many physical rooms.
    Pricing is stored here; SeasonalPrice overrides it for date ranges.

    Examples: Стандарт, Делюкс, Люкс, Президентский люкс.
    """

    class BedType(models.TextChoices):
        SINGLE = "single", _("Одна кровать")
        DOUBLE = "double", _("Двуспальная")
        TWIN = "twin", _("Две раздельные")
        KING = "king", _("King-size")
        BUNK = "bunk", _("Двухъярусная")

    # ---- Identity ----
    name = models.CharField(_("название"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), unique=True, max_length=120)
    description = models.TextField(_("описание"))
    short_description = models.CharField(_("краткое описание"), max_length=255)

    # ---- Capacity ----
    max_guests = models.PositiveSmallIntegerField(
        _("макс. гостей"), default=2,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    bed_type = models.CharField(
        _("тип кровати"), max_length=20,
        choices=BedType.choices, default=BedType.DOUBLE,
    )
    area_sqm = models.PositiveSmallIntegerField(_("площадь (м²)"), default=25)

    # ---- Pricing ----
    base_price_per_night = models.DecimalField(
        _("базовая цена за ночь"), max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    weekend_price_per_night = models.DecimalField(
        _("цена за ночь (выходные)"), max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text=_("Если не указана — используется базовая цена"),
    )

    # ---- Media ----
    thumbnail = models.ImageField(
        _("превью"), upload_to="rooms/thumbnails/%Y/%m/", null=True, blank=True
    )

    # ---- Features ----
    amenities = models.ManyToManyField(
        Amenity, verbose_name=_("удобства"),
        blank=True, related_name="categories",
    )

    # ---- Visibility ----
    is_active = models.BooleanField(_("активна"), default=True, db_index=True)
    is_featured = models.BooleanField(
        _("показывать на главной"), default=False, db_index=True
    )

    class Meta:
        verbose_name = _("категория номера")
        verbose_name_plural = _("категории номеров")
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("hotel:room_category_detail", kwargs={"slug": self.slug})

    def get_effective_price(self, date: datetime.date = None) -> Decimal:
        """
        Return the price for a specific date.
        Priority: SeasonalPrice > weekend_price > base_price.
        """
        if date is None:
            date = datetime.date.today()

        # Check seasonal overrides
        seasonal = self.seasonal_prices.filter(
            start_date__lte=date, end_date__gte=date
        ).first()
        if seasonal:
            return seasonal.price_per_night

        # Weekend surcharge
        if self.weekend_price_per_night and date.weekday() >= 5:
            return self.weekend_price_per_night

        return self.base_price_per_night

    @property
    def average_rating(self) -> float:
        """Cached average from RoomReview."""
        result = self.reviews.filter(is_approved=True).aggregate(
            avg=models.Avg("rating")
        )
        return round(result["avg"] or 0, 1)

    @property
    def review_count(self) -> int:
        return self.reviews.filter(is_approved=True).count()

    def save(self, *args, **kwargs):
        # Auto-generate transliterated slug from name if not provided
        if not self.slug:
            base = slugify_ru(self.name)
            if not base:
                # fallback to Django's slugify
                from django.utils.text import slugify
                base = slugify(self.name)
            slug = base
            counter = 2
            # Ensure uniqueness
            while RoomCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# RoomImage
# ---------------------------------------------------------------------------

class RoomImage(TimeStampedModel, OrderedModel):
    """Gallery images for a room category."""

    category = models.ForeignKey(
        RoomCategory, on_delete=models.CASCADE,
        related_name="images", verbose_name=_("категория"),
    )
    image = models.ImageField(
        _("изображение"), upload_to="rooms/gallery/%Y/%m/"
    )
    caption = models.CharField(_("подпись"), max_length=200, blank=True)
    alt_text = models.CharField(
        _("alt текст"), max_length=200, blank=True,
        help_text=_("Для SEO и доступности"),
    )
    is_primary = models.BooleanField(_("главное фото"), default=False)

    class Meta:
        verbose_name = _("фото номера")
        verbose_name_plural = _("фото номеров")
        ordering = ["-is_primary", "sort_order"]

    def __str__(self) -> str:
        return f"{self.category.name} — фото #{self.pk}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per category
        if self.is_primary:
            RoomImage.objects.filter(
                category=self.category, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class Room(TimeStampedModel):
    """
    A physical room in the hotel.
    Linked to a RoomCategory for pricing and description.
    Supports subdivisions (e.g., 303a, 303b) and multiple occupancy for economy rooms.
    """

    class RoomStatus(models.TextChoices):
        AVAILABLE = "available", _("Свободен")
        OCCUPIED = "occupied", _("Занят")
        MAINTENANCE = "maintenance", _("На обслуживании")
        CLEANING = "cleaning", _("Уборка")
        BLOCKED = "blocked", _("Заблокирован")

    # ---- Identity ----
    category = models.ForeignKey(
        RoomCategory, on_delete=models.PROTECT,
        related_name="rooms", verbose_name=_("категория"),
    )
    number = models.CharField(_("номер комнаты"), max_length=10)
    subdivision = models.CharField(
        _("подразделение"), max_length=5, blank=True,
        help_text=_("Например: а, б, в для разделения номера на части")
    )
    floor = models.PositiveSmallIntegerField(_("этаж"), default=1)
    
    # ---- Multiple occupancy support ----
    max_guests_per_room = models.PositiveSmallIntegerField(
        _("макс. персон в номере"), default=1,
        validators=[MinValueValidator(1)],
        help_text=_("Максимальное количество персон, которые могут одновременно проживать в номере")
    )

    # ---- Status ----
    status = models.CharField(
        _("статус"), max_length=20,
        choices=RoomStatus.choices, default=RoomStatus.AVAILABLE,
        db_index=True,
    )

    # ---- Physical details ----
    has_balcony = models.BooleanField(_("балкон"), default=False)
    has_sea_view = models.BooleanField(_("вид на море"), default=False)
    has_mountain_view = models.BooleanField(_("вид на горы"), default=False)
    extra_amenities = models.ManyToManyField(
        Amenity, verbose_name=_("доп. удобства"),
        blank=True, related_name="rooms",
        help_text=_("Удобства конкретного номера сверх категории"),
    )

    # ---- Internal ----
    notes = models.TextField(_("внутренние заметки"), blank=True)
    last_cleaned_at = models.DateTimeField(
        _("последняя уборка"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("номер")
        verbose_name_plural = _("номера")
        ordering = ["floor", "number", "subdivision"]
        indexes = [
            models.Index(fields=["status", "category"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["number", "subdivision"],
                name="unique_room_number_subdivision"
            )
        ]

    def __str__(self) -> str:
        room_display = f"Номер {self.number}"
        if self.subdivision:
            room_display += self.subdivision
        return f"{room_display} ({self.category.name}, {self.floor} эт.)"

    @property
    def full_number(self) -> str:
        """Returns full room number including subdivision (e.g., '303а')"""
        return f"{self.number}{self.subdivision}" if self.subdivision else self.number

    @property
    def is_available(self) -> bool:
        return self.status == self.RoomStatus.AVAILABLE

    @property
    def allows_multiple_bookings(self) -> bool:
        """Check if this room allows multiple concurrent bookings"""
        return self.max_guests_per_room > 1

    def get_current_occupancy_count(self) -> int:
        """Get current number of guests in active bookings for this room."""
        from apps.bookings.models import BookingStatus
        totals = self.bookings.filter(
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]
        ).aggregate(
            adults=models.Sum("adults"),
            children=models.Sum("children"),
        )
        return (totals["adults"] or 0) + (totals["children"] or 0)

    def has_availability(self, check_in, check_out) -> bool:
        """Check if the room still has at least one free guest place."""
        return self.available_capacity(check_in, check_out) > 0

    def has_capacity_for(self, check_in, check_out, guests: int) -> bool:
        """Check if the room can fit the requested number of guests."""
        return self.available_capacity(check_in, check_out) >= guests

    def available_capacity(self, check_in, check_out) -> int:
        """Return free guest places for the given period."""
        from apps.bookings.models import BookingStatus
        
        booked = self.bookings.filter(
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN],
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).aggregate(
            adults=models.Sum("adults"),
            children=models.Sum("children"),
        )
        booked_guests = (booked["adults"] or 0) + (booked["children"] or 0)
        return max(self.max_guests_per_room - booked_guests, 0)

    def mark_clean(self):
        from django.utils import timezone
        self.status = self.RoomStatus.AVAILABLE
        self.last_cleaned_at = timezone.now()
        self.save(update_fields=["status", "last_cleaned_at", "updated_at"])


# ---------------------------------------------------------------------------
# SeasonalPrice
# ---------------------------------------------------------------------------

class SeasonalPrice(TimeStampedModel):
    """
    Price override for a room category during a specific date range.
    Examples: Новый год, майские праздники, летний сезон.
    """

    category = models.ForeignKey(
        RoomCategory, on_delete=models.CASCADE,
        related_name="seasonal_prices", verbose_name=_("категория"),
    )
    name = models.CharField(
        _("название периода"), max_length=100,
        help_text=_("Например: Новогодние праздники 2025"),
    )
    start_date = models.DateField(_("начало периода"), db_index=True)
    end_date = models.DateField(_("конец периода"), db_index=True)
    price_per_night = models.DecimalField(
        _("цена за ночь"), max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    min_nights = models.PositiveSmallIntegerField(
        _("минимум ночей"), default=1,
        help_text=_("Минимальный срок бронирования в этот период"),
    )

    class Meta:
        verbose_name = _("сезонная цена")
        verbose_name_plural = _("сезонные цены")
        ordering = ["start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F("start_date")),
                name="seasonal_price_end_after_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.category.name}: {self.name} ({self.start_date} – {self.end_date})"


# ---------------------------------------------------------------------------
# RoomReview
# ---------------------------------------------------------------------------

class RoomReview(TimeStampedModel):
    """
    ⚠️ DEPRECATED: This model will be removed in v2.0
    
    Use apps.reviews.Review instead - it has more features:
    - Multiple rating categories (cleanliness, comfort, staff, etc.)
    - Moderation workflow
    - Response from management
    - Better audit trail
    
    Migration guide: docs/DEPRECATION_PLAN.md
    Migration script: python manage.py migrate_room_reviews
    
    ---
    
    Guest review for a room category after checkout.
    One review per booking.
    """

    category = models.ForeignKey(
        RoomCategory, on_delete=models.CASCADE,
        related_name="reviews", verbose_name=_("категория"),
    )
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="room_reviews", verbose_name=_("гость"),
    )
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="room_review_legacy",
        verbose_name=_("бронирование"),
    )

    # ---- Ratings (1–5) ----
    rating = models.PositiveSmallIntegerField(
        _("общая оценка"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    cleanliness_rating = models.PositiveSmallIntegerField(
        _("чистота"), null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    service_rating = models.PositiveSmallIntegerField(
        _("сервис"), null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comfort_rating = models.PositiveSmallIntegerField(
        _("комфорт"), null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    # ---- Content ----
    title = models.CharField(_("заголовок"), max_length=200, blank=True)
    body = models.TextField(_("текст отзыва"))

    # ---- Moderation ----
    is_approved = models.BooleanField(
        _("одобрен"), default=False, db_index=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_reviews",
        verbose_name=_("одобрил"),
    )
    approved_at = models.DateTimeField(_("одобрен в"), null=True, blank=True)

    class Meta:
        verbose_name = _("отзыв")
        verbose_name_plural = _("отзывы")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["guest", "booking"],
                name="unique_review_per_booking",
            )
        ]

    def __str__(self) -> str:
        return f"Отзыв {self.guest} — {self.category.name} ({self.rating}★)"
