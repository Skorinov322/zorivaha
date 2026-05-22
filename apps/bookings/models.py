"""
bookings/models.py

Lifecycle:
  pending → confirmed → checked_in → checked_out
      ↓           ↓
  cancelled    cancelled        no_show

Models:
  BookingStatus   — 6 статусов жизненного цикла
  PaymentStatus   — статусы оплаты
  BookingSource   — источник брони
  Booking         — основная запись (UUID PK)
  BookingHistory  — иммутабельный аудит-лог
  Payment         — платёж к брони
"""

import random
import string
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, UUIDModel
from apps.hotel.models import Room, RoomCategory


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class BookingStatus(models.TextChoices):
    PENDING    = "pending",    _("Новая")
    CONFIRMED  = "confirmed",  _("Подтверждена")
    CHECKED_IN = "checked_in", _("Заселён")
    CHECKED_OUT= "checked_out",_("Завершена")
    CANCELLED  = "cancelled",  _("Отменена")
    NO_SHOW    = "no_show",    _("Незаезд")


class OccupancyType(models.TextChoices):
    SOLO        = "solo",        _("Один гость")
    NEWLYWEDS   = "newlyweds",   _("Молодожёны (одна кровать, +50%)")
    FRIENDS     = "friends",     _("Друзья (две кровати, ×2)")
    TWO_GUESTS  = "two_guests",  _("Двое гостей (×2)")


class PaymentStatus(models.TextChoices):
    UNPAID   = "unpaid",   _("Не оплачено")
    PARTIAL  = "partial",  _("Частично оплачено")
    PAID     = "paid",     _("Оплачено")
    REFUNDED = "refunded", _("Возврат")
    FAILED   = "failed",   _("Ошибка оплаты")


class BookingSource(models.TextChoices):
    WEBSITE   = "website",   _("Сайт")
    PHONE     = "phone",     _("Телефон")
    WALK_IN   = "walk_in",   _("Стойка регистрации")
    OTA       = "ota",       _("OTA (Booking.com и др.)")
    CORPORATE = "corporate", _("Корпоративный клиент")


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------

phone_validator = RegexValidator(
    regex=r"^\+?[\d\s\-\(\)]{7,20}$",
    message=_("Введите корректный номер телефона."),
)


class Booking(UUIDModel, TimeStampedModel):
    """
    Core booking record.

    UUID PK — safe to expose in URLs and emails.
    confirmation_number — short human-readable code: ZV-XXXXXXXX.

    Guest contact fields (first_name, last_name, phone, email) are stored
    as a snapshot at booking time — independent of the User profile,
    which may change later.
    """

    # ---- Confirmation ----
    confirmation_number = models.CharField(
        _("номер брони"), max_length=12, unique=True,
        editable=False, db_index=True,
    )

    # ---- Relations ----
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("гость"),
    )
    room_category = models.ForeignKey(
        RoomCategory,
        on_delete=models.PROTECT,
        related_name="bookings",
        verbose_name=_("категория номера"),
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
        verbose_name=_("номер"),
        help_text=_("Назначается при заселении"),
    )
    group_id = models.UUIDField(
        _("ID группы"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("UUID группы броней, созданных в рамках одного запроса"),
    )
    organization = models.ForeignKey(
        "crm.Organization",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
        verbose_name=_("организация"),
        help_text=_("Для корпоративных броней"),
    )

    # ---- Guest contact snapshot (frozen at booking time) ----
    guest_first_name = models.CharField(_("имя"), max_length=150)
    guest_last_name  = models.CharField(_("фамилия"), max_length=150)
    guest_patronymic = models.CharField(_("отчество"), max_length=150, blank=True)
    guest_phone      = models.CharField(
        _("телефон"), max_length=20, validators=[phone_validator]
    )
    guest_email      = models.EmailField(_("email"))

    # ---- Dates ----
    check_in  = models.DateField(_("дата заезда"),  db_index=True)
    check_out = models.DateField(_("дата выезда"), db_index=True)

    # ---- Guests count ----
    adults   = models.PositiveSmallIntegerField(_("взрослых"), default=1)
    children = models.PositiveSmallIntegerField(_("детей"),    default=0)
    occupancy_type = models.CharField(
        _("тип размещения"), max_length=20,
        choices=OccupancyType.choices, default=OccupancyType.SOLO,
        db_index=True,
    )

    # ---- Pricing snapshot (frozen at booking time) ----
    price_per_night = models.DecimalField(
        _("цена за ночь"), max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    total_price = models.DecimalField(
        _("итого"), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    discount_amount = models.DecimalField(
        _("скидка"), max_digits=10, decimal_places=2, default=Decimal("0"),
    )
    discount_reason = models.CharField(_("причина скидки"), max_length=200, blank=True)

    # ---- Status ----
    status = models.CharField(
        _("статус"), max_length=20,
        choices=BookingStatus.choices, default=BookingStatus.PENDING,
        db_index=True,
    )
    payment_status = models.CharField(
        _("статус оплаты"), max_length=20,
        choices=PaymentStatus.choices, default=PaymentStatus.UNPAID,
        db_index=True,
    )
    source = models.CharField(
        _("источник"), max_length=20,
        choices=BookingSource.choices, default=BookingSource.WEBSITE,
        db_index=True,
    )

    # ---- Auto-cancel ----
    auto_cancel_at = models.DateTimeField(
        _("автоотмена в"), null=True, blank=True, db_index=True,
        help_text=_("Если бронь не подтверждена до этого времени — отменяется автоматически"),
    )

    # ---- Guest requests ----
    special_requests = models.TextField(_("особые пожелания"), blank=True)
    arrival_time     = models.TimeField(_("примерное время прибытия"), null=True, blank=True)
    departure_time   = models.TimeField(_("примерное время отъезда"),  null=True, blank=True)
    early_check_in   = models.BooleanField(
        _("ранний заезд (до 12:00)"), default=False,
        help_text=_("Заезд до 12:00 считается ранним и будет взиматься доплата 50% от стоимости одних суток"),
    )

    # ---- Internal ----
    internal_notes = models.TextField(_("внутренние заметки"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_bookings",
        verbose_name=_("создал"),
        help_text=_("Если бронь создана сотрудником"),
    )

    # ---- Policy Agreement ----
    accommodation_policy_agreed = models.BooleanField(
        _("согласие с политикой проживания"), default=False
    )
    accommodation_policy_agreed_at = models.DateTimeField(
        _("дата и время согласия"), null=True, blank=True
    )

    # ---- Cancellation ----
    cancelled_at        = models.DateTimeField(_("отменено в"),    null=True, blank=True)
    cancellation_reason = models.TextField(_("причина отмены"),    blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cancelled_bookings",
        verbose_name=_("отменил"),
    )

    class Meta:
        verbose_name         = _("бронирование")
        verbose_name_plural  = _("бронирования")
        ordering             = ["-created_at"]
        indexes = [
            models.Index(fields=["check_in", "check_out"]),
            models.Index(fields=["status", "check_in"]),
            models.Index(fields=["guest", "status"]),
            models.Index(fields=["auto_cancel_at", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(check_out__gt=models.F("check_in")),
                name="booking_checkout_after_checkin",
            ),
            models.CheckConstraint(
                check=models.Q(adults__gte=1) | models.Q(children__gte=1),
                name="booking_at_least_one_guest",
            ),
        ]

    def __str__(self) -> str:
        return f"Бронь #{self.confirmation_number} — {self.guest_full_name}"

    def get_absolute_url(self):
        return reverse("bookings:detail", kwargs={"pk": self.pk})

    # ---- Save hook ----

    def save(self, *args, **kwargs):
        if not self.confirmation_number:
            self.confirmation_number = self._generate_confirmation_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_confirmation_number() -> str:
        chars = string.ascii_uppercase + string.digits
        suffix = "".join(random.choices(chars, k=8))
        return f"ZV-{suffix}"

    # ---- Computed properties ----

    @property
    def guest_full_name(self) -> str:
        parts = [self.guest_last_name, self.guest_first_name, self.guest_patronymic]
        return " ".join(p for p in parts if p)

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    @property
    def total_guests(self) -> int:
        return self.adults + self.children

    @property
    def is_group_booking(self) -> bool:
        return bool(self.group_id)

    @property
    def group_total_guests(self) -> int:
        if not self.group_id:
            return self.total_guests
        totals = Booking.objects.filter(group_id=self.group_id).aggregate(
            adults=models.Sum("adults"),
            children=models.Sum("children"),
        )
        return (totals["adults"] or 0) + (totals["children"] or 0)

    @property
    def group_final_price(self) -> Decimal:
        if not self.group_id:
            return self.final_price
        totals = Booking.objects.filter(group_id=self.group_id).aggregate(
            total=models.Sum("total_price"),
            discount=models.Sum("discount_amount"),
        )
        return (totals["total"] or Decimal("0")) - (totals["discount"] or Decimal("0"))

    @property
    def group_rooms_count(self) -> int:
        if not self.group_id:
            return 1
        return Booking.objects.filter(group_id=self.group_id).count()

    @property
    def final_price(self) -> Decimal:
        return self.total_price - self.discount_amount

    @property
    def is_active(self) -> bool:
        return self.status in (
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
            BookingStatus.CHECKED_IN,
        )

    @property
    def can_be_cancelled(self) -> bool:
        return self.status in (BookingStatus.PENDING, BookingStatus.CONFIRMED)

    # ---- State transitions ----

    def confirm(self, actor=None):
        if self.status != BookingStatus.PENDING:
            raise ValueError("Только новые брони можно подтвердить.")
        self.status = BookingStatus.CONFIRMED
        self.auto_cancel_at = None
        self.save(update_fields=["status", "auto_cancel_at", "updated_at"])
        self._log("Бронь подтверждена.", actor, BookingHistory.Action.CONFIRMED)

    def cancel(self, reason: str = "", actor=None):
        if not self.can_be_cancelled:
            raise ValueError("Эту бронь нельзя отменить.")
        self.status = BookingStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.cancelled_by = actor
        self.save(update_fields=[
            "status", "cancelled_at", "cancellation_reason",
            "cancelled_by", "updated_at",
        ])
        self._log(f"Отменено: {reason}", actor, BookingHistory.Action.CANCELLED)

    def check_in_guest(self, room: Room, actor=None):
        if self.status != BookingStatus.CONFIRMED:
            raise ValueError("Только подтверждённые брони можно заселить.")
        self.status = BookingStatus.CHECKED_IN
        self.room = room
        self.save(update_fields=["status", "room", "updated_at"])
        
        # Update room status based on occupancy
        current_occupancy = room.get_current_occupancy_count()
        if current_occupancy >= room.max_guests_per_room:
            room.status = Room.RoomStatus.OCCUPIED
        else:
            # Room is partially occupied but can still accept more guests
            room.status = Room.RoomStatus.AVAILABLE
        room.save(update_fields=["status", "updated_at"])
        
        self._log(f"Заселён в номер {room.full_number}.", actor, BookingHistory.Action.CHECKED_IN)

    def check_out_guest(self, actor=None):
        if self.status != BookingStatus.CHECKED_IN:
            raise ValueError("Гость не заселён.")
        self.status = BookingStatus.CHECKED_OUT
        self.save(update_fields=["status", "updated_at"])
        
        if self.room:
            # Check remaining occupancy after checkout
            remaining_occupancy = self.room.get_current_occupancy_count() - 1  # -1 for current checkout
            if remaining_occupancy <= 0:
                self.room.status = Room.RoomStatus.CLEANING
            else:
                # Still has other guests, keep as available for new bookings
                self.room.status = Room.RoomStatus.AVAILABLE
            self.room.save(update_fields=["status", "updated_at"])
            
        self._log("Гость выселился.", actor, BookingHistory.Action.CHECKED_OUT)

    def mark_no_show(self, actor=None):
        if self.status != BookingStatus.CONFIRMED:
            raise ValueError("Только подтверждённые брони можно отметить как незаезд.")
        self.status = BookingStatus.NO_SHOW
        self.save(update_fields=["status", "updated_at"])
        self._log("Гость не явился (незаезд).", actor, BookingHistory.Action.NO_SHOW)

    def undo_check_in(self, actor=None):
        """Отменить заселение: checked_in → confirmed."""
        if self.status != BookingStatus.CHECKED_IN:
            raise ValueError("Отменить заселение можно только для заселённой брони.")
        prev_room = self.room

        # Освобождаем номер перед сменой статуса
        if prev_room:
            # После отмены заселения этой брони считаем оставшуюся занятость
            remaining = prev_room.bookings.filter(
                status=BookingStatus.CHECKED_IN
            ).exclude(pk=self.pk).count()
            if remaining <= 0:
                prev_room.status = Room.RoomStatus.AVAILABLE
            prev_room.save(update_fields=["status", "updated_at"])

        self.status = BookingStatus.CONFIRMED
        self.room = None
        self.save(update_fields=["status", "room", "updated_at"])
        self._log(
            f"Заселение отменено (номер {prev_room.full_number if prev_room else '—'}).",
            actor,
            BookingHistory.Action.UNDO_CHECK_IN,
        )

    def undo_check_out(self, actor=None):
        """Отменить выселение: checked_out → checked_in."""
        if self.status != BookingStatus.CHECKED_OUT:
            raise ValueError("Отменить выселение можно только для завершённой брони.")
        if not self.room:
            raise ValueError("Невозможно отменить выселение: номер не назначен.")
        self.status = BookingStatus.CHECKED_IN
        self.save(update_fields=["status", "updated_at"])

        # Возвращаем номер в занятый статус
        room = self.room
        current_occupancy = room.get_current_occupancy_count()
        if current_occupancy >= room.max_guests_per_room:
            room.status = Room.RoomStatus.OCCUPIED
        else:
            room.status = Room.RoomStatus.AVAILABLE
        room.save(update_fields=["status", "updated_at"])

        self._log(
            f"Выселение отменено, гость возвращён в номер {room.full_number}.",
            actor,
            BookingHistory.Action.UNDO_CHECK_OUT,
        )

    def _log(self, note: str, actor, action: str):
        BookingHistory.objects.create(
            booking=self,
            action=action,
            status_after=self.status,
            changed_by=actor,
            note=note,
            snapshot={
                "status": self.status,
                "room": str(self.room) if self.room else None,
                "total_price": str(self.total_price),
            },
        )


# ---------------------------------------------------------------------------
# BookingHistory
# ---------------------------------------------------------------------------

class BookingHistory(TimeStampedModel):
    """Immutable audit trail — append only, never update."""

    class Action(models.TextChoices):
        CREATED         = "created",         _("Создана")
        CONFIRMED       = "confirmed",        _("Подтверждена")
        CHECKED_IN      = "checked_in",       _("Заселён")
        CHECKED_OUT     = "checked_out",      _("Выселился")
        CANCELLED       = "cancelled",        _("Отменена")
        NO_SHOW         = "no_show",          _("Незаезд")
        PAYMENT         = "payment",          _("Оплата")
        NOTE_ADDED      = "note_added",       _("Заметка")
        MODIFIED        = "modified",         _("Изменена")
        UNDO_CHECK_IN   = "undo_check_in",    _("Заселение отменено")
        UNDO_CHECK_OUT  = "undo_check_out",   _("Выселение отменено")

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE,
        related_name="history", verbose_name=_("бронирование"),
    )
    action = models.CharField(
        _("действие"), max_length=20, choices=Action.choices, db_index=True
    )
    status_after = models.CharField(
        _("статус после"), max_length=20,
        choices=BookingStatus.choices, blank=True,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="booking_history_entries",
        verbose_name=_("кто изменил"),
    )
    note     = models.TextField(_("заметка"), blank=True)
    snapshot = models.JSONField(_("снимок данных"), default=dict, blank=True)

    class Meta:
        verbose_name        = _("история брони")
        verbose_name_plural = _("история броней")
        ordering            = ["created_at"]

    def __str__(self) -> str:
        return f"{self.booking.confirmation_number} → {self.get_action_display()}"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class Payment(UUIDModel, TimeStampedModel):
    """Payment record — supports multiple partial payments per booking."""

    class PaymentMethod(models.TextChoices):
        CASH     = "cash",     _("Наличные")
        CARD     = "card",     _("Банковская карта")
        TRANSFER = "transfer", _("Банковский перевод")
        ONLINE   = "online",   _("Онлайн-оплата")

    class PaymentType(models.TextChoices):
        CHARGE = "charge", _("Оплата")
        REFUND = "refund", _("Возврат")

    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT,
        related_name="payments", verbose_name=_("бронирование"),
    )
    amount = models.DecimalField(
        _("сумма"), max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    method = models.CharField(
        _("способ оплаты"), max_length=20,
        choices=PaymentMethod.choices, default=PaymentMethod.CARD,
    )
    payment_type = models.CharField(
        _("тип"), max_length=10,
        choices=PaymentType.choices, default=PaymentType.CHARGE,
    )
    transaction_id = models.CharField(
        _("ID транзакции"), max_length=200, blank=True, db_index=True
    )
    is_confirmed = models.BooleanField(_("подтверждён"), default=False)
    confirmed_at = models.DateTimeField(_("подтверждён в"), null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processed_payments",
        verbose_name=_("принял оплату"),
    )
    notes = models.TextField(_("заметки"), blank=True)

    class Meta:
        verbose_name        = _("платёж")
        verbose_name_plural = _("платежи")
        ordering            = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_payment_type_display()} {self.amount} ₽ — {self.booking.confirmation_number}"
