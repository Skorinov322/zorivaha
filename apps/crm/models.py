"""
crm/models.py

Models:
  Organization    — юридическое лицо / корпоративный клиент
  ClientProfile   — CRM-профиль гостя (1:1 с User)
  AdminComment    — комментарий администратора к профилю клиента
  Interaction     — лог каждого контакта с гостем
  Task            — задача для сотрудника
  Message         — внутренние сообщения

ClientProfile хранит:
  - тип клиента (физлицо / организация)
  - историю заявок (через Booking FK)
  - количество броней и ночей
  - статус (active / vip / blacklisted / inactive)
  - комментарии администратора
  - уровень лояльности
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

class Organization(TimeStampedModel):
    """Corporate client / legal entity."""

    class OrgType(models.TextChoices):
        COMPANY    = "company",    _("Компания")
        GOVERNMENT = "government", _("Государственная организация")
        NGO        = "ngo",        _("НКО")
        INDIVIDUAL = "individual", _("ИП")

    name       = models.CharField(_("название"),          max_length=255, unique=True)
    short_name = models.CharField(_("краткое название"),  max_length=100, blank=True)
    org_type   = models.CharField(
        _("тип"), max_length=20,
        choices=OrgType.choices, default=OrgType.COMPANY, db_index=True,
    )

    # Legal
    inn  = models.CharField(_("ИНН"),  max_length=12, blank=True, db_index=True)
    kpp  = models.CharField(_("КПП"),  max_length=9,  blank=True)
    ogrn = models.CharField(_("ОГРН"), max_length=15, blank=True)
    legal_address  = models.TextField(_("юридический адрес"), blank=True)
    actual_address = models.TextField(_("фактический адрес"), blank=True)

    # Contacts
    phone          = models.CharField(_("телефон"),        max_length=20,  blank=True)
    email          = models.EmailField(_("email"),                          blank=True)
    website        = models.URLField(_("сайт"),                             blank=True)
    contact_person = models.CharField(_("контактное лицо"), max_length=200, blank=True)

    # Commercial
    corporate_discount_pct = models.DecimalField(
        _("корпоративная скидка (%)"), max_digits=5, decimal_places=2, default=0,
    )
    credit_limit       = models.DecimalField(_("кредитный лимит"), max_digits=12, decimal_places=2, default=0)
    payment_terms_days = models.PositiveSmallIntegerField(_("отсрочка платежа (дней)"), default=0)

    # CRM
    assigned_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="managed_organizations",
        verbose_name=_("менеджер"),
    )
    notes     = models.TextField(_("заметки"), blank=True)
    is_active = models.BooleanField(_("активна"), default=True, db_index=True)
    is_approved = models.BooleanField(_("подтверждена"), default=False, db_index=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_organizations",
        verbose_name=_("создана пользователем"),
    )

    class Meta:
        verbose_name        = _("организация")
        verbose_name_plural = _("организации")
        ordering            = ["name"]

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# ClientProfile
# ---------------------------------------------------------------------------

class ClientProfile(TimeStampedModel):
    """
    Extended CRM profile for every guest.
    Auto-created via signal on User registration.

    client_type distinguishes физлицо vs организация.
    status tracks the overall CRM state of the client.
    """

    class LoyaltyTier(models.TextChoices):
        STANDARD = "standard", _("Стандарт")
        SILVER   = "silver",   _("Серебро")
        GOLD     = "gold",     _("Золото")
        PLATINUM = "platinum", _("Платина")

    class GuestType(models.TextChoices):
        LEISURE   = "leisure",   _("Отдых")
        BUSINESS  = "business",  _("Бизнес")
        CORPORATE = "corporate", _("Корпоративный")
        VIP       = "vip",       _("VIP")

    class ClientType(models.TextChoices):
        INDIVIDUAL   = "individual",   _("Физическое лицо")
        ORGANIZATION = "organization", _("Организация")

    class ClientStatus(models.TextChoices):
        ACTIVE      = "active",      _("Активный")
        VIP         = "vip",         _("VIP")
        INACTIVE    = "inactive",    _("Неактивный")
        BLACKLISTED = "blacklisted", _("Чёрный список")

    # ---- Core ----
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="crm_profile", verbose_name=_("пользоваостиница"),
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="clients",
        verbose_name=_("организация"),
    )

    # ---- Classification ----
    client_type = models.CharField(
        _("тип клиента"), max_length=20,
        choices=ClientType.choices, default=ClientType.INDIVIDUAL,
        db_index=True,
    )
    guest_type = models.CharField(
        _("тип гостя"), max_length=20,
        choices=GuestType.choices, default=GuestType.LEISURE,
        db_index=True,
    )
    status = models.CharField(
        _("статус клиента"), max_length=20,
        choices=ClientStatus.choices, default=ClientStatus.ACTIVE,
        db_index=True,
    )

    # ---- Loyalty ----
    loyalty_tier   = models.CharField(
        _("уровень лояльности"), max_length=20,
        choices=LoyaltyTier.choices, default=LoyaltyTier.STANDARD,
        db_index=True,
    )
    loyalty_points = models.PositiveIntegerField(_("баллы лояльности"), default=0)

    # ---- Aggregated stats (updated on checkout) ----
    total_stays  = models.PositiveIntegerField(_("всего заездов"),  default=0)
    total_nights = models.PositiveIntegerField(_("всего ночей"),    default=0)
    total_spent  = models.DecimalField(
        _("всего потрачено"), max_digits=14, decimal_places=2, default=0
    )
    first_stay_date = models.DateField(_("первый заезд"),    null=True, blank=True)
    last_stay_date  = models.DateField(_("последний заезд"), null=True, blank=True)

    # ---- Preferences ----
    preferred_room_category = models.ForeignKey(
        "hotel.RoomCategory", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="preferred_by",
        verbose_name=_("предпочитаемая категория"),
    )
    preferred_floor       = models.PositiveSmallIntegerField(_("предпочитаемый этаж"), null=True, blank=True)
    dietary_requirements  = models.CharField(_("диетические требования"), max_length=200, blank=True)
    special_needs         = models.TextField(_("особые потребности"), blank=True)

    # ---- CRM ----
    assigned_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="managed_clients",
        verbose_name=_("менеджер"),
    )
    vip_notes        = models.TextField(_("VIP заметки"), blank=True)
    is_blacklisted   = models.BooleanField(_("в чёрном списке"), default=False, db_index=True)
    blacklist_reason = models.TextField(_("причина блокировки"), blank=True)

    class Meta:
        verbose_name        = _("профиль клиента")
        verbose_name_plural = _("профили клиентов")
        ordering            = ["-total_spent"]

    def __str__(self) -> str:
        return f"CRM: {self.user}"

    # ---- Loyalty ----

    TIER_THRESHOLDS = {
        LoyaltyTier.PLATINUM: 20,
        LoyaltyTier.GOLD:     10,
        LoyaltyTier.SILVER:    5,
    }

    def recalculate_tier(self):
        new_tier = self.LoyaltyTier.STANDARD
        for tier, threshold in self.TIER_THRESHOLDS.items():
            if self.total_stays >= threshold:
                new_tier = tier
                break
        if self.loyalty_tier != new_tier:
            self.loyalty_tier = new_tier
            self.save(update_fields=["loyalty_tier", "updated_at"])

    def add_loyalty_points(self, points: int):
        self.loyalty_points += points
        self.save(update_fields=["loyalty_points", "updated_at"])

    def update_status_from_tier(self):
        """Auto-promote to VIP status when tier reaches GOLD+."""
        if self.loyalty_tier in (self.LoyaltyTier.GOLD, self.LoyaltyTier.PLATINUM):
            if self.status == self.ClientStatus.ACTIVE:
                self.status = self.ClientStatus.VIP
                self.save(update_fields=["status", "updated_at"])

    @property
    def booking_count(self) -> int:
        return self.user.bookings.count()

    @property
    def active_booking_count(self) -> int:
        from apps.bookings.models import BookingStatus
        return self.user.bookings.filter(
            status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]
        ).count()


# ---------------------------------------------------------------------------
# AdminComment
# ---------------------------------------------------------------------------

class AdminComment(TimeStampedModel):
    """
    Staff comment attached to a ClientProfile.
    Visible only to staff — never shown to the guest.
    Immutable after creation (append-only audit trail).
    """

    client = models.ForeignKey(
        ClientProfile, on_delete=models.CASCADE,
        related_name="admin_comments", verbose_name=_("клиент"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="crm_comments",
        verbose_name=_("автор"),
    )
    body = models.TextField(_("комментарий"))
    is_pinned = models.BooleanField(
        _("закреплён"), default=False,
        help_text=_("Закреплённые комментарии показываются первыми"),
    )

    class Meta:
        verbose_name        = _("комментарий администратора")
        verbose_name_plural = _("комментарии администраторов")
        ordering            = ["-is_pinned", "-created_at"]

    def __str__(self) -> str:
        return f"Комментарий {self.author} → {self.client.user}"


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------

class Interaction(TimeStampedModel):
    """
    ⚠️ DEPRECATED: This model will be removed in v2.0
    
    Use bookings.BookingHistory for booking-related interactions.
    Use crm.AdminComment for general client notes.
    
    Reason: Duplicates functionality of BookingHistory + AdminComment.
    Migration guide: docs/DEPRECATION_PLAN.md
    
    ---
    
    Immutable log of every contact with a guest — append only.
    """

    class InteractionType(models.TextChoices):
        CALL      = "call",      _("Звонок")
        EMAIL     = "email",     _("Email")
        IN_PERSON = "in_person", _("Личная встреча")
        CHAT      = "chat",      _("Чат")
        NOTE      = "note",      _("Заметка")
        COMPLAINT = "complaint", _("Жалоба")

    client = models.ForeignKey(
        ClientProfile, on_delete=models.CASCADE,
        related_name="interactions", verbose_name=_("клиент"),
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="crm_interactions",
        verbose_name=_("сотрудник"),
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="interactions",
        verbose_name=_("бронирование"),
    )
    interaction_type = models.CharField(
        _("тип"), max_length=20, choices=InteractionType.choices, db_index=True
    )
    subject        = models.CharField(_("тема"),       max_length=200)
    body           = models.TextField(_("содержание"))
    outcome        = models.CharField(_("результат"),  max_length=200, blank=True)
    is_resolved    = models.BooleanField(_("решено"),  default=False, db_index=True)
    follow_up_date = models.DateField(_("дата повторного контакта"), null=True, blank=True)

    class Meta:
        verbose_name        = _("взаимодействие")
        verbose_name_plural = _("взаимодействия")
        ordering            = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_interaction_type_display()} — {self.client.user}"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class Task(TimeStampedModel):
    """
    ⚠️ DEPRECATED: This model will be removed in v2.0
    
    Use external task management tools instead:
    - Trello (https://trello.com)
    - Asana (https://asana.com)
    - Notion (https://notion.so)
    - Microsoft To Do
    
    Reason: Redundant - external tools provide better task management.
    Migration guide: docs/DEPRECATION_PLAN.md
    Export script: python manage.py export_tasks_to_csv
    
    ---
    
    CRM task assigned to a staff member.
    """

    class Priority(models.TextChoices):
        LOW    = "low",    _("Низкий")
        MEDIUM = "medium", _("Средний")
        HIGH   = "high",   _("Высокий")
        URGENT = "urgent", _("Срочный")

    class TaskStatus(models.TextChoices):
        OPEN        = "open",        _("Открыта")
        IN_PROGRESS = "in_progress", _("В работе")
        DONE        = "done",        _("Выполнена")
        CANCELLED   = "cancelled",   _("Отменена")

    title       = models.CharField(_("заголовок"),  max_length=200)
    description = models.TextField(_("описание"),   blank=True)

    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="created_tasks", verbose_name=_("создал"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="assigned_tasks", verbose_name=_("исполниостиница"),
    )
    client = models.ForeignKey(
        ClientProfile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tasks", verbose_name=_("клиент"),
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="tasks", verbose_name=_("бронирование"),
    )

    priority     = models.CharField(
        _("приоритет"), max_length=10,
        choices=Priority.choices, default=Priority.MEDIUM, db_index=True,
    )
    status       = models.CharField(
        _("статус"), max_length=20,
        choices=TaskStatus.choices, default=TaskStatus.OPEN, db_index=True,
    )
    due_date     = models.DateField(_("срок"), null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(_("выполнена в"), null=True, blank=True)

    class Meta:
        verbose_name        = _("задача")
        verbose_name_plural = _("задачи")
        ordering            = ["-priority", "due_date"]
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["due_date", "status"]),
        ]

    def __str__(self) -> str:
        return self.title

    def complete(self, actor=None):
        from django.utils import timezone
        self.status      = self.TaskStatus.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class Message(TimeStampedModel):
    """
    ⚠️ DEPRECATED: This model will be removed in v2.0
    
    Use notifications.ContactMessage instead - it has better features:
    - Thread support (replies)
    - Staff/guest distinction
    - Read status tracking
    - Better integration with notifications
    
    Reason: Duplicates ContactMessage functionality.
    Migration guide: docs/DEPRECATION_PLAN.md
    Migration script: python manage.py migrate_crm_messages
    
    ---
    
    Internal messaging between staff and guests.
    """

    class MessageStatus(models.TextChoices):
        UNREAD   = "unread",   _("Не прочитано")
        READ     = "read",     _("Прочитано")
        REPLIED  = "replied",  _("Отвечено")
        ARCHIVED = "archived", _("В архиве")

    class MessageType(models.TextChoices):
        INQUIRY   = "inquiry",   _("Запрос")
        COMPLAINT = "complaint", _("Жалоба")
        REQUEST   = "request",   _("Просьба")
        FEEDBACK  = "feedback",  _("Отзыв")
        INTERNAL  = "internal",  _("Внутреннее")

    sender    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="sent_messages", verbose_name=_("отправиостиница"),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="received_messages",
        verbose_name=_("получаостиница"),
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="messages", verbose_name=_("бронирование"),
    )
    client_profile = models.ForeignKey(
        ClientProfile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="messages", verbose_name=_("профиль клиента"),
    )
    message_type = models.CharField(
        _("тип"), max_length=20,
        choices=MessageType.choices, default=MessageType.INQUIRY, db_index=True,
    )
    subject    = models.CharField(_("тема"),  max_length=255)
    body       = models.TextField(_("текст"))
    attachment = models.FileField(
        _("вложение"), upload_to="messages/attachments/%Y/%m/",
        null=True, blank=True,
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="replies", verbose_name=_("ответ на"),
    )
    status    = models.CharField(
        _("статус"), max_length=20,
        choices=MessageStatus.choices, default=MessageStatus.UNREAD, db_index=True,
    )
    read_at   = models.DateTimeField(_("прочитано в"), null=True, blank=True)
    is_urgent = models.BooleanField(_("срочное"), default=False, db_index=True)

    class Meta:
        verbose_name        = _("сообщение")
        verbose_name_plural = _("сообщения")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "status"]),
            models.Index(fields=["booking", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_message_type_display()}: {self.subject}"

    def mark_read(self):
        from django.utils import timezone
        if self.status == self.MessageStatus.UNREAD:
            self.status  = self.MessageStatus.READ
            self.read_at = timezone.now()
            self.save(update_fields=["status", "read_at", "updated_at"])
