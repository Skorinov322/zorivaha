"""
accounts/models.py

Role hierarchy (ascending privilege):
  USER (guest)  <  ADMIN  <  SUPER_ADMIN

Full set stored in UserRole:
  USER         — обычный гость, может бронировать
  RECEPTIONIST — стойка регистрации, заселение/выселение
  MANAGER      — менеджер, CRM + брони + отчёты
  ADMIN        — администратор гостиницы, всё кроме смены ролей
  SUPER_ADMIN  — полный доступ, может менять роли любых пользователей

is_superuser (Django built-in) = технический суперпользоваостиница БД,
всегда имеет все права независимо от role.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# UserRole
# ---------------------------------------------------------------------------

class UserRole(models.TextChoices):
    USER         = "user",         _("Пользователь")
    RECEPTIONIST = "receptionist", _("Ресепшн")
    MANAGER      = "manager",      _("Менеджер")
    ADMIN        = "admin",        _("Администратор")
    SUPER_ADMIN  = "super_admin",  _("Супер-администратор")


# Role hierarchy: higher index = more privileges
ROLE_HIERARCHY: list[str] = [
    UserRole.USER,
    UserRole.RECEPTIONIST,
    UserRole.MANAGER,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
]


def role_gte(role_a: str, role_b: str) -> bool:
    """Return True if role_a has equal or higher privileges than role_b."""
    try:
        return ROLE_HIERARCHY.index(role_a) >= ROLE_HIERARCHY.index(role_b)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class UserManager(BaseUserManager):
    """Custom manager — email is the unique identifier instead of username."""

    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.USER)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

phone_validator = RegexValidator(
    regex=r"^\+?[\d\s\-\(\)]{7,20}$",
    message=_("Введите корректный номер телефона."),
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(AbstractUser, TimeStampedModel):
    """
    Extended user model.

    Auth:     email + password (no username)
    Access:   role field + is_superuser flag
    Profile:  phone, date_of_birth, avatar
    Prefs:    preferred_language, marketing_consent, email_notifications
    """

    # ---- Auth ----
    username = None
    email = models.EmailField(_("email"), unique=True)

    # ---- Role ----
    role = models.CharField(
        _("роль"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        db_index=True,
    )

    # ---- Personal info ----
    phone = models.CharField(
        _("телефон"), max_length=20, blank=True, validators=[phone_validator]
    )
    patronymic = models.CharField(_("отчество"), max_length=150, blank=True)
    date_of_birth = models.DateField(_("дата рождения"), null=True, blank=True)
    avatar = models.ImageField(
        _("аватар"), upload_to="avatars/%Y/%m/", null=True, blank=True
    )

    # ---- Preferences ----
    preferred_language = models.CharField(
        _("язык интерфейса"), max_length=10, default="ru", blank=True,
        choices=[("ru", "Русский"), ("en", "English")],
    )
    marketing_consent    = models.BooleanField(_("согласие на рассылку"), default=False)
    email_notifications  = models.BooleanField(_("email-уведомления"),    default=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name         = _("пользоваостиница")
        verbose_name_plural  = _("пользователи")
        ordering             = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.email

    # ------------------------------------------------------------------
    # Role predicates  (use these everywhere — never compare role strings)
    # ------------------------------------------------------------------

    @property
    def is_plain_user(self) -> bool:
        """Regular guest — lowest privilege."""
        return self.role == UserRole.USER and not self.is_superuser

    @property
    def is_receptionist(self) -> bool:
        return self.has_role(UserRole.RECEPTIONIST)

    @property
    def is_manager(self) -> bool:
        return self.has_role(UserRole.MANAGER)

    @property
    def is_admin(self) -> bool:
        return self.has_role(UserRole.ADMIN)

    @property
    def is_super_admin(self) -> bool:
        """Can manage roles and has full system access."""
        return self.is_superuser or self.role == UserRole.SUPER_ADMIN

    # Legacy alias used in existing views
    @property
    def is_hotel_admin(self) -> bool:
        return self.is_admin

    def has_role(self, minimum_role: str) -> bool:
        """
        Return True if the user's role is >= minimum_role in the hierarchy,
        OR if the user is a Django superuser (always passes).

        Usage:
            user.has_role(UserRole.MANAGER)   # True for manager, admin, super_admin
        """
        if self.is_superuser:
            return True
        return role_gte(self.role, minimum_role)

    def can_assign_role(self, target_role: str) -> bool:
        """
        Only SUPER_ADMIN can assign any role.
        An ADMIN can assign roles below their own level.
        """
        if self.is_super_admin:
            return True
        if self.has_role(UserRole.ADMIN):
            # Admin can assign roles strictly below ADMIN
            return role_gte(UserRole.MANAGER, target_role)
        return False

    # ------------------------------------------------------------------
    # Name helpers
    # ------------------------------------------------------------------

    def get_full_name(self) -> str:
        return " ".join(
            part for part in [self.last_name, self.first_name, self.patronymic] if part
        )

    def get_short_name(self) -> str:
        return self.first_name or self.email.split("@")[0]

    def get_initials(self) -> str:
        parts = [self.first_name[:1], self.last_name[:1]]
        return "".join(p for p in parts if p).upper() or self.email[:2].upper()

    @property
    def push_notifications_unread_count(self) -> int:
        return self.push_notifications.filter(is_read=False).count()

    @property
    def contact_messages_unread_replies_count(self) -> int:
        """Количество непрочитанных ответов персонала по всем обращениям гостя."""
        from apps.notifications.models import ContactReply
        return ContactReply.objects.filter(
            message__sender_user=self,
            is_staff_reply=True,
            is_read_by_guest=False,
        ).count()
