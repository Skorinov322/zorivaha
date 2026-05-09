"""
notifications/models.py

Models:
  EmailLog          — полный лог каждого отправленного письма
  NotificationTemplate — шаблоны писем, редактируемые через Admin
  PushNotification  — in-app уведомления для личного кабинета

EmailLog пишется автоматически при каждой отправке через Celery-задачи.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# EmailLog
# ---------------------------------------------------------------------------

class EmailLog(TimeStampedModel):
    """
    Immutable log of every outgoing email.
    Written by notification tasks — never updated after creation.

    Provides:
      - Audit trail for compliance
      - Debugging failed deliveries
      - Resend capability
    """

    class EmailStatus(models.TextChoices):
        PENDING = "pending", _("В очереди")
        SENT = "sent", _("Отправлено")
        FAILED = "failed", _("Ошибка")
        BOUNCED = "bounced", _("Отклонено сервером")

    class EmailType(models.TextChoices):
        BOOKING_CONFIRMATION = "booking_confirmation", _("Подтверждение брони")
        BOOKING_CANCELLED = "booking_cancelled", _("Отмена брони")
        BOOKING_REMINDER = "booking_reminder", _("Напоминание о заезде")
        BOOKING_CHECKOUT = "booking_checkout", _("Благодарность за визит")
        PASSWORD_RESET = "password_reset", _("Сброс пароля")
        WELCOME = "welcome", _("Приветствие")
        MARKETING = "marketing", _("Маркетинговая рассылка")
        CUSTOM = "custom", _("Произвольное")

    # ---- Routing ----
    recipient_email = models.EmailField(_("получатель"), db_index=True)
    recipient_name = models.CharField(_("имя получателя"), max_length=200, blank=True)
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_logs",
        verbose_name=_("пользователь"),
    )

    # ---- Content ----
    email_type = models.CharField(
        _("тип письма"), max_length=30,
        choices=EmailType.choices, default=EmailType.CUSTOM,
        db_index=True,
    )
    subject = models.CharField(_("тема"), max_length=500)
    body_html = models.TextField(_("HTML тело"), blank=True)
    body_text = models.TextField(_("текстовое тело"), blank=True)

    # ---- Context ----
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_logs",
        verbose_name=_("бронирование"),
    )

    # ---- Delivery ----
    status = models.CharField(
        _("статус"), max_length=10,
        choices=EmailStatus.choices, default=EmailStatus.PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(_("отправлено в"), null=True, blank=True)
    error_message = models.TextField(_("ошибка"), blank=True)
    retry_count = models.PositiveSmallIntegerField(_("попыток"), default=0)

    # ---- Celery ----
    task_id = models.CharField(
        _("Celery task ID"), max_length=100, blank=True, db_index=True
    )

    class Meta:
        verbose_name = _("лог email")
        verbose_name_plural = _("лог email")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["email_type", "created_at"]),
            models.Index(fields=["recipient_email", "email_type"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_status_display()}] {self.subject} → {self.recipient_email}"

    def mark_sent(self):
        from django.utils import timezone
        self.status = self.EmailStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_failed(self, error: str):
        self.status = self.EmailStatus.FAILED
        self.error_message = error
        self.retry_count += 1
        self.save(update_fields=["status", "error_message", "retry_count", "updated_at"])


# ---------------------------------------------------------------------------
# NotificationTemplate
# ---------------------------------------------------------------------------

class NotificationTemplate(TimeStampedModel):
    """
    Editable email templates stored in the database.
    Allows managers to update email content without code changes.

    Variables in subject/body use {{ variable }} syntax (Django template).
    Available variables depend on email_type (documented in help_text).
    """

    email_type = models.CharField(
        _("тип письма"), max_length=30,
        choices=EmailLog.EmailType.choices,
        unique=True,
        help_text=_("Один шаблон на каждый тип письма"),
    )
    name = models.CharField(_("название"), max_length=200)
    subject = models.CharField(
        _("тема письма"), max_length=500,
        help_text=_("Доступные переменные: {{ booking.confirmation_number }}, {{ guest.first_name }}, …"),
    )
    body_html = models.TextField(
        _("HTML шаблон"),
        help_text=_("Django template. Наследуется от notifications/email/base_email.html"),
    )
    body_text = models.TextField(
        _("текстовый шаблон"), blank=True,
        help_text=_("Автоматически генерируется из HTML если не заполнен"),
    )
    is_active = models.BooleanField(_("активен"), default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="updated_templates",
        verbose_name=_("изменил"),
    )

    class Meta:
        verbose_name = _("шаблон письма")
        verbose_name_plural = _("шаблоны писем")
        ordering = ["email_type"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_email_type_display()})"


# ---------------------------------------------------------------------------
# PushNotification (in-app)
# ---------------------------------------------------------------------------

class PushNotification(TimeStampedModel):
    """
    In-app notification shown in the user's personal cabinet.
    Examples: "Ваша бронь подтверждена", "Напоминание о заезде завтра".
    """

    class NotificationType(models.TextChoices):
        BOOKING_CONFIRMED = "booking_confirmed", _("Бронь подтверждена")
        BOOKING_CANCELLED = "booking_cancelled", _("Бронь отменена")
        CHECKIN_REMINDER  = "checkin_reminder",  _("Напоминание о заезде")
        CHECKOUT_REMINDER = "checkout_reminder", _("Напоминание о выезде")
        LOYALTY_UPGRADE   = "loyalty_upgrade",   _("Повышение уровня лояльности")
        CONTACT_FORM      = "contact_form",      _("Обратная связь с сайта")
        SYSTEM            = "system",            _("Системное")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_notifications",
        verbose_name=_("получатель"),
    )
    notification_type = models.CharField(
        _("тип"), max_length=30,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(_("заголовок"), max_length=200)
    body = models.TextField(_("текст"))
    action_url = models.CharField(
        _("ссылка"), max_length=500, blank=True,
        help_text=_("URL для кнопки 'Подробнее'"),
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="push_notifications",
        verbose_name=_("бронирование"),
    )
    is_read = models.BooleanField(_("прочитано"), default=False, db_index=True)
    read_at = models.DateTimeField(_("прочитано в"), null=True, blank=True)

    class Meta:
        verbose_name = _("уведомление")
        verbose_name_plural = _("уведомления")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"→ {self.recipient}: {self.title}"

    def mark_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])


# ---------------------------------------------------------------------------
# ContactMessage — сообщения обратной связи с перепиской
# ---------------------------------------------------------------------------

class ContactMessage(TimeStampedModel):
    """
    Сообщение с формы обратной связи.
    Поддерживает переписку: гость → персонал → гость.
    """

    class Status(models.TextChoices):
        NEW      = "new",      _("Новое")
        IN_WORK  = "in_work",  _("В работе")
        ANSWERED = "answered", _("Отвечено")
        CLOSED   = "closed",   _("Закрыто")

    # ---- Отправитель (может быть анонимным) ----
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contact_messages_sent",
        verbose_name=_("пользователь"),
        help_text=_("Заполняется если гость авторизован"),
    )
    sender_name  = models.CharField(_("имя"),    max_length=150)
    sender_email = models.EmailField(_("email"))
    sender_phone = models.CharField(_("телефон"), max_length=20, blank=True)

    # ---- Содержание ----
    subject = models.CharField(_("тема"), max_length=200, blank=True)
    message = models.TextField(_("сообщение"))

    # ---- Статус ----
    status = models.CharField(
        _("статус"), max_length=20,
        choices=Status.choices, default=Status.NEW,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contact_messages_assigned",
        verbose_name=_("назначено"),
    )

    class Meta:
        verbose_name        = _("сообщение обратной связи")
        verbose_name_plural = _("сообщения обратной связи")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sender_name}: {self.subject or self.message[:40]}"

    @property
    def unread_replies_for_guest(self) -> int:
        """Количество непрочитанных ответов персонала для гостя."""
        return self.replies.filter(is_staff_reply=True, is_read_by_guest=False).count()


class ContactReply(TimeStampedModel):
    """Ответ в треде сообщения обратной связи."""

    message = models.ForeignKey(
        ContactMessage,
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name=_("сообщение"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contact_replies",
        verbose_name=_("автор"),
    )
    body           = models.TextField(_("текст"))
    is_staff_reply = models.BooleanField(_("ответ персонала"), default=False)
    is_read_by_guest = models.BooleanField(_("прочитано гостем"), default=False)

    class Meta:
        verbose_name        = _("ответ")
        verbose_name_plural = _("ответы")
        ordering            = ["created_at"]

    def __str__(self) -> str:
        return f"Ответ от {self.author} к #{self.message_id}"

def notify_staff_contact_form(name: str, email: str, phone: str, subject: str, message: str, contact_message_id: int = None) -> int:
    """
    Create PushNotification for all staff (RECEPTIONIST and above).
    Returns the number of notifications created.
    """
    from apps.accounts.models import CustomUser, UserRole, ROLE_HIERARCHY

    min_role_index = ROLE_HIERARCHY.index(UserRole.RECEPTIONIST)
    staff_roles = ROLE_HIERARCHY[min_role_index:]

    staff_users = CustomUser.objects.filter(
        role__in=staff_roles,
        is_active=True,
    )

    short_msg = message[:120] + ("…" if len(message) > 120 else "")
    title = f"Обратная связь: {subject or 'Без темы'}"
    body = (
        f"От: {name} ({email})"
        + (f", тел. {phone}" if phone else "")
        + f"\n{short_msg}"
    )
    action_url = f"/dashboard/messages/{contact_message_id}/" if contact_message_id else "/dashboard/messages/"

    notifications = [
        PushNotification(
            recipient=user,
            notification_type=PushNotification.NotificationType.CONTACT_FORM,
            title=title,
            body=body,
            action_url=action_url,
        )
        for user in staff_users
    ]
    PushNotification.objects.bulk_create(notifications)
    return len(notifications)
