"""
content/models.py

Models:
  SiteContent   — редактируемые текстовые блоки сайта (CMS-lite)
  FAQ           — часто задаваемые вопросы
  HotelGallery  — общая галерея гостиницы (не номеров)
  Testimonial   — отзывы на главной странице (ручная модерация)

Управляется через Django Admin без кода.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, OrderedModel


# ---------------------------------------------------------------------------
# SiteContent
# ---------------------------------------------------------------------------

class SiteContent(TimeStampedModel):
    """
    Key-value store for editable site content blocks.
    Allows managers to update texts, contacts, descriptions
    without touching code or templates.

    Usage in templates:
        {% get_content "hero_title" as hero_title %}
        {{ hero_title }}
    """

    class ContentType(models.TextChoices):
        TEXT = "text", _("Текст")
        HTML = "html", _("HTML")
        IMAGE = "image", _("Изображение")
        URL = "url", _("Ссылка")

    key = models.SlugField(
        _("ключ"), max_length=100, unique=True,
        help_text=_("Уникальный идентификатор блока, например: hero_title"),
    )
    label = models.CharField(
        _("название"), max_length=200,
        help_text=_("Понятное название для редактора"),
    )
    content_type = models.CharField(
        _("тип контента"), max_length=10,
        choices=ContentType.choices, default=ContentType.TEXT,
    )

    # ---- Content ----
    value_text = models.TextField(_("текст"), blank=True)
    value_image = models.ImageField(
        _("изображение"), upload_to="content/%Y/%m/",
        null=True, blank=True,
    )

    # ---- Meta ----
    is_active = models.BooleanField(_("активно"), default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="content_updates",
        verbose_name=_("изменил"),
    )

    class Meta:
        verbose_name = _("контент сайта")
        verbose_name_plural = _("контент сайта")
        ordering = ["key"]

    def __str__(self) -> str:
        return f"[{self.key}] {self.label}"

    @property
    def value(self):
        """Return the appropriate value based on content_type."""
        if self.content_type == self.ContentType.IMAGE:
            return self.value_image
        return self.value_text

    @classmethod
    def get(cls, key: str, default: str = "") -> str:
        """Convenience method for templates and views."""
        try:
            obj = cls.objects.get(key=key, is_active=True)
            return obj.value or default
        except cls.DoesNotExist:
            return default


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

class FAQ(TimeStampedModel, OrderedModel):
    """Frequently asked questions displayed on the website."""

    class FAQCategory(models.TextChoices):
        BOOKING = "booking", _("Бронирование")
        CHECKIN = "checkin", _("Заезд и выезд")
        SERVICES = "services", _("Услуги")
        PAYMENT = "payment", _("Оплата")
        GENERAL = "general", _("Общее")

    question = models.CharField(_("вопрос"), max_length=500)
    answer = models.TextField(_("ответ"))
    category = models.CharField(
        _("категория"), max_length=20,
        choices=FAQCategory.choices, default=FAQCategory.GENERAL,
        db_index=True,
    )
    is_active = models.BooleanField(_("активен"), default=True, db_index=True)

    class Meta:
        verbose_name = _("FAQ")
        verbose_name_plural = _("FAQ")
        ordering = ["category", "sort_order"]

    def __str__(self) -> str:
        return self.question[:80]


# ---------------------------------------------------------------------------
# HotelGallery
# ---------------------------------------------------------------------------

class HotelGallery(TimeStampedModel, OrderedModel):
    """
    General hotel photo gallery (lobby, restaurant, pool, exterior, etc.).
    Separate from room-specific RoomImage.
    """

    class GallerySection(models.TextChoices):
        EXTERIOR = "exterior", _("Экстерьер")
        LOBBY = "lobby", _("Лобби")
        RESTAURANT = "restaurant", _("Ресторан")
        SPA = "spa", _("СПА")
        POOL = "pool", _("Бассейн")
        CONFERENCE = "conference", _("Конференц-зал")
        TERRITORY = "territory", _("Территория")
        OTHER = "other", _("Другое")

    image = models.ImageField(
        _("изображение"), upload_to="gallery/hotel/%Y/%m/"
    )
    title = models.CharField(_("заголовок"), max_length=200, blank=True)
    alt_text = models.CharField(
        _("alt текст"), max_length=200, blank=True,
        help_text=_("Для SEO и доступности"),
    )
    section = models.CharField(
        _("раздел"), max_length=20,
        choices=GallerySection.choices, default=GallerySection.OTHER,
        db_index=True,
    )
    is_active = models.BooleanField(_("активно"), default=True, db_index=True)
    is_featured = models.BooleanField(
        _("на главной"), default=False, db_index=True
    )

    class Meta:
        verbose_name = _("фото галереи")
        verbose_name_plural = _("галерея гостиницы")
        ordering = ["section", "sort_order"]

    def __str__(self) -> str:
        return f"{self.get_section_display()} — {self.title or self.pk}"


# ---------------------------------------------------------------------------
# Testimonial
# ---------------------------------------------------------------------------

class Testimonial(TimeStampedModel, OrderedModel):
    """
    Guest testimonials displayed on the homepage.
    Can be linked to a real User or entered manually.
    """

    # ---- Author ----
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="testimonials",
        verbose_name=_("пользователь"),
        help_text=_("Если оставлен реальным гостем системы"),
    )
    author_name = models.CharField(
        _("имя автора"), max_length=100,
        help_text=_("Отображается на сайте"),
    )
    author_title = models.CharField(
        _("должность / город"), max_length=100, blank=True,
        help_text=_("Например: Москва или Директор компании"),
    )
    author_avatar = models.ImageField(
        _("фото автора"), upload_to="testimonials/%Y/",
        null=True, blank=True,
    )

    # ---- Content ----
    text = models.TextField(_("текст отзыва"))
    rating = models.PositiveSmallIntegerField(
        _("оценка"), default=5,
        validators=[
            __import__("django.core.validators", fromlist=["MinValueValidator"]).MinValueValidator(1),
            __import__("django.core.validators", fromlist=["MaxValueValidator"]).MaxValueValidator(5),
        ],
    )

    # ---- Moderation ----
    is_active = models.BooleanField(_("активен"), default=True, db_index=True)
    source = models.CharField(
        _("источник"), max_length=100, blank=True,
        help_text=_("Например: Booking.com, TripAdvisor, личный визит"),
    )

    class Meta:
        verbose_name = _("отзыв")
        verbose_name_plural = _("отзывы (главная)")
        ordering = ["sort_order", "-created_at"]

    def __str__(self) -> str:
        return f"{self.author_name}: {self.text[:60]}…"


# ---------------------------------------------------------------------------
# LegalPage
# ---------------------------------------------------------------------------

class LegalPage(TimeStampedModel):
    """Editable legal pages: terms of use, privacy policy, accommodation policy."""

    class PageType(models.TextChoices):
        TERMS = "terms", _("Условия использования")
        PRIVACY = "privacy", _("Политика конфиденциальности")
        ACCOMMODATION = "accommodation", _("Политика проживания")

    page_type = models.CharField(
        _("тип страницы"), max_length=20, choices=PageType.choices, unique=True
    )
    title = models.CharField(_("заголовок"), max_length=200)
    content = models.TextField(_("содержание"), help_text=_("Поддерживается HTML"))
    is_active = models.BooleanField(_("активна"), default=True)

    class Meta:
        verbose_name = _("правовая страница")
        verbose_name_plural = _("правовые страницы")
        ordering = ["page_type"]

    def __str__(self) -> str:
        return self.get_page_type_display()
