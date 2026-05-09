"""
analytics/models.py

Models:
  DailyMetrics      — агрегированные метрики за день (occupancy, revenue, …)
  PageView          — лог просмотров страниц (для анализа трафика)
  BookingFunnel     — воронка бронирования (search → view → book)
  RevenueSnapshot   — ежемесячный снимок выручки для графиков

Данные пишутся Celery-задачами, читаются в dashboard/reports.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# DailyMetrics
# ---------------------------------------------------------------------------

class DailyMetrics(models.Model):
    """
    Pre-aggregated daily snapshot of hotel KPIs.
    Populated by a nightly Celery Beat task.
    One record per date — unique constraint enforced.

    KPIs:
      occupancy_rate  — % занятых номеров
      adr             — Average Daily Rate (средняя цена за ночь)
      revpar          — Revenue Per Available Room
      total_revenue   — выручка за день
    """

    date = models.DateField(_("дата"), unique=True, db_index=True)

    # ---- Occupancy ----
    total_rooms = models.PositiveSmallIntegerField(_("всего номеров"), default=0)
    occupied_rooms = models.PositiveSmallIntegerField(_("занято номеров"), default=0)
    available_rooms = models.PositiveSmallIntegerField(_("свободно номеров"), default=0)
    occupancy_rate = models.DecimalField(
        _("загрузка (%)"), max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )

    # ---- Revenue ----
    total_revenue = models.DecimalField(
        _("выручка"), max_digits=14, decimal_places=2, default=Decimal("0")
    )
    adr = models.DecimalField(
        _("ADR (средняя цена)"), max_digits=10, decimal_places=2, default=Decimal("0"),
        help_text=_("Average Daily Rate = выручка / занятые номера"),
    )
    revpar = models.DecimalField(
        _("RevPAR"), max_digits=10, decimal_places=2, default=Decimal("0"),
        help_text=_("Revenue Per Available Room = выручка / все номера"),
    )

    # ---- Bookings ----
    new_bookings = models.PositiveSmallIntegerField(_("новых броней"), default=0)
    confirmed_bookings = models.PositiveSmallIntegerField(_("подтверждено"), default=0)
    cancelled_bookings = models.PositiveSmallIntegerField(_("отменено"), default=0)
    checkins = models.PositiveSmallIntegerField(_("заездов"), default=0)
    checkouts = models.PositiveSmallIntegerField(_("выездов"), default=0)
    no_shows = models.PositiveSmallIntegerField(_("не явились"), default=0)

    # ---- Guests ----
    total_guests = models.PositiveSmallIntegerField(_("гостей"), default=0)
    new_guests = models.PositiveSmallIntegerField(_("новых гостей"), default=0)

    # ---- Meta ----
    calculated_at = models.DateTimeField(_("рассчитано в"), auto_now=True)

    class Meta:
        verbose_name = _("метрики за день")
        verbose_name_plural = _("метрики по дням")
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"Метрики {self.date}: загрузка {self.occupancy_rate}%"

    def calculate_kpis(self):
        """Recalculate ADR and RevPAR from raw data."""
        if self.occupied_rooms > 0:
            self.adr = self.total_revenue / self.occupied_rooms
        if self.total_rooms > 0:
            self.revpar = self.total_revenue / self.total_rooms
        if self.total_rooms > 0:
            self.occupancy_rate = Decimal(self.occupied_rooms) / self.total_rooms * 100
        self.save(update_fields=["adr", "revpar", "occupancy_rate", "calculated_at"])


# ---------------------------------------------------------------------------
# PageView
# ---------------------------------------------------------------------------

class PageView(models.Model):
    """
    Lightweight page view log for internal analytics.
    Not a replacement for Google Analytics — used for booking funnel analysis.
    """

    class PageType(models.TextChoices):
        HOME = "home", _("Главная")
        ROOM_LIST = "room_list", _("Список номеров")
        ROOM_DETAIL = "room_detail", _("Страница номера")
        BOOKING_FORM = "booking_form", _("Форма бронирования")
        BOOKING_SUCCESS = "booking_success", _("Успешное бронирование")
        ABOUT = "about", _("О нас")
        CONTACTS = "contacts", _("Контакты")
        OTHER = "other", _("Другое")

    # ---- Request info ----
    page_type = models.CharField(
        _("тип страницы"), max_length=20,
        choices=PageType.choices, default=PageType.OTHER,
        db_index=True,
    )
    path = models.CharField(_("URL"), max_length=500)
    referrer = models.CharField(_("реферер"), max_length=500, blank=True)

    # ---- User ----
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="page_views",
        verbose_name=_("пользователь"),
    )
    session_key = models.CharField(
        _("сессия"), max_length=40, blank=True, db_index=True
    )
    ip_address = models.GenericIPAddressField(
        _("IP адрес"), null=True, blank=True
    )
    user_agent = models.CharField(_("User-Agent"), max_length=500, blank=True)

    # ---- Context ----
    room_category = models.ForeignKey(
        "hotel.RoomCategory",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="page_views",
        verbose_name=_("категория номера"),
    )

    # ---- Timestamp ----
    viewed_at = models.DateTimeField(_("просмотрено"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("просмотр страницы")
        verbose_name_plural = _("просмотры страниц")
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["page_type", "viewed_at"]),
            models.Index(fields=["session_key", "viewed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.page_type} — {self.path} ({self.viewed_at:%d.%m.%Y %H:%M})"


# ---------------------------------------------------------------------------
# BookingFunnel
# ---------------------------------------------------------------------------

class BookingFunnel(models.Model):
    """
    Tracks a single user's journey through the booking funnel.
    One record per session — updated as the user progresses.

    Stages: search → room_view → form_open → form_submit → success
    """

    class FunnelStage(models.TextChoices):
        SEARCH = "search", _("Поиск")
        ROOM_VIEW = "room_view", _("Просмотр номера")
        FORM_OPEN = "form_open", _("Открыл форму")
        FORM_SUBMIT = "form_submit", _("Отправил форму")
        SUCCESS = "success", _("Успешное бронирование")
        ABANDONED = "abandoned", _("Брошено")

    session_key = models.CharField(
        _("сессия"), max_length=40, db_index=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="funnel_events",
        verbose_name=_("пользователь"),
    )
    stage = models.CharField(
        _("этап"), max_length=20,
        choices=FunnelStage.choices, default=FunnelStage.SEARCH,
        db_index=True,
    )
    room_category = models.ForeignKey(
        "hotel.RoomCategory",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="funnel_events",
        verbose_name=_("категория номера"),
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="funnel_events",
        verbose_name=_("бронирование"),
    )
    # Search params at the time of the event
    search_check_in = models.DateField(_("искал заезд"), null=True, blank=True)
    search_check_out = models.DateField(_("искал выезд"), null=True, blank=True)
    search_guests = models.PositiveSmallIntegerField(_("гостей"), null=True, blank=True)

    started_at = models.DateTimeField(_("начало"), auto_now_add=True)
    updated_at = models.DateTimeField(_("обновлено"), auto_now=True)

    class Meta:
        verbose_name = _("воронка бронирования")
        verbose_name_plural = _("воронки бронирования")
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Воронка {self.session_key[:8]}… — {self.get_stage_display()}"


# ---------------------------------------------------------------------------
# RevenueSnapshot
# ---------------------------------------------------------------------------

class RevenueSnapshot(models.Model):
    """
    Monthly revenue snapshot for charts and year-over-year comparison.
    Populated by a monthly Celery Beat task on the 1st of each month.
    """

    year = models.PositiveSmallIntegerField(_("год"), db_index=True)
    month = models.PositiveSmallIntegerField(
        _("месяц"),
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    total_revenue = models.DecimalField(
        _("выручка"), max_digits=14, decimal_places=2, default=Decimal("0")
    )
    total_bookings = models.PositiveIntegerField(_("броней"), default=0)
    total_nights = models.PositiveIntegerField(_("ночей"), default=0)
    avg_occupancy = models.DecimalField(
        _("средняя загрузка (%)"), max_digits=5, decimal_places=2, default=Decimal("0")
    )
    avg_adr = models.DecimalField(
        _("средний ADR"), max_digits=10, decimal_places=2, default=Decimal("0")
    )
    calculated_at = models.DateTimeField(_("рассчитано"), auto_now=True)

    class Meta:
        verbose_name = _("снимок выручки")
        verbose_name_plural = _("снимки выручки")
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["year", "month"],
                name="unique_revenue_snapshot_per_month",
            )
        ]

    def __str__(self) -> str:
        return f"Выручка {self.month:02d}/{self.year}: {self.total_revenue:,.0f} ₽"
