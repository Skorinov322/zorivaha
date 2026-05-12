"""
reviews/models.py

Система отзывов гостей с модерацией.

Модели:
  Review          — отзыв гостя о проживании
  ReviewResponse  — ответ администрации на отзыв
  ReviewModeration — история модерации отзыва

Правила:
  - Отзыв можно оставить только на завершенное бронирование (checked_out)
  - Один отзыв на одно бронирование
  - Модерация: pending → approved / rejected
  - Админы и ресепшн могут модерировать отзывы
  - Администрация может отвечать на отзывы
"""

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel, UUIDModel
from apps.bookings.models import Booking


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class ReviewStatus(models.TextChoices):
    PENDING   = "pending",   _("На модерации")
    APPROVED  = "approved",  _("Одобрен")
    REJECTED  = "rejected",  _("Отклонен")


class ReviewRating(models.IntegerChoices):
    """Оценка от 1 до 5 звезд"""
    ONE   = 1, _("1 — Ужасно")
    TWO   = 2, _("2 — Плохо")
    THREE = 3, _("3 — Нормально")
    FOUR  = 4, _("4 — Хорошо")
    FIVE  = 5, _("5 — Отлично")


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

class Review(UUIDModel, TimeStampedModel):
    """
    Отзыв гостя о проживании.
    
    Связан с конкретным бронированием (один отзыв на бронь).
    Требует модерации перед публикацией.
    """

    # ---- Relations ----
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="review",
        verbose_name=_("бронирование"),
        help_text=_("Отзыв привязан к конкретному бронированию"),
    )
    room_category = models.ForeignKey(
        "hotel.RoomCategory",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviews_for_category",
        verbose_name=_("категория номера"),
        help_text=_("Категория номера, о которой вы оставляете отзыв"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("автор"),
    )

    # ---- Ratings (1-5) ----
    overall_rating = models.PositiveSmallIntegerField(
        _("общая оценка"),
        choices=ReviewRating.choices,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Общее впечатление от проживания"),
    )
    cleanliness_rating = models.PositiveSmallIntegerField(
        _("чистота"),
        choices=ReviewRating.choices,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comfort_rating = models.PositiveSmallIntegerField(
        _("комфорт"),
        choices=ReviewRating.choices,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    staff_rating = models.PositiveSmallIntegerField(
        _("персонал"),
        choices=ReviewRating.choices,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    value_rating = models.PositiveSmallIntegerField(
        _("соотношение цена/качество"),
        choices=ReviewRating.choices,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    location_rating = models.PositiveSmallIntegerField(
        _("расположение"),
        choices=ReviewRating.choices,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    # ---- Content ----
    title = models.CharField(
        _("заголовок"),
        max_length=200,
        help_text=_("Краткое описание впечатления"),
    )
    text = models.TextField(
        _("текст отзыва"),
        help_text=_("Подробный отзыв о проживании"),
    )
    pros = models.TextField(
        _("достоинства"),
        blank=True,
        help_text=_("Что понравилось"),
    )
    cons = models.TextField(
        _("недостатки"),
        blank=True,
        help_text=_("Что не понравилось"),
    )

    # ---- Moderation ----
    status = models.CharField(
        _("статус"),
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        db_index=True,
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_reviews",
        verbose_name=_("модератор"),
    )
    moderated_at = models.DateTimeField(
        _("дата модерации"),
        null=True,
        blank=True,
    )
    moderation_comment = models.TextField(
        _("комментарий модератора"),
        blank=True,
        help_text=_("Причина отклонения или заметки"),
    )

    # ---- Publication ----
    is_featured = models.BooleanField(
        _("избранный"),
        default=False,
        help_text=_("Показывать на главной странице"),
    )
    published_at = models.DateTimeField(
        _("дата публикации"),
        null=True,
        blank=True,
    )

    # ---- Guest info snapshot ----
    guest_name = models.CharField(
        _("имя гостя"),
        max_length=200,
        help_text=_("Имя на момент написания отзыва"),
    )

    # ---- Metadata ----
    ip_address = models.GenericIPAddressField(
        _("IP адрес"),
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        _("User Agent"),
        blank=True,
    )

    class Meta:
        verbose_name = _("отзыв")
        verbose_name_plural = _("отзывы")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["is_featured", "status"]),
            models.Index(fields=["-overall_rating", "status"]),
        ]

    def __str__(self) -> str:
        return f"Отзыв от {self.guest_name} — {self.get_overall_rating_display()}"

    def get_absolute_url(self):
        return reverse("reviews:detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        # Автоматически заполняем имя гостя при создании
        if not self.guest_name and self.author:
            self.guest_name = self.author.get_full_name() or self.author.email
        super().save(*args, **kwargs)

    # ---- Computed properties ----

    @property
    def average_rating(self) -> float:
        """Средняя оценка по всем категориям"""
        ratings = [
            self.overall_rating,
            self.cleanliness_rating,
            self.comfort_rating,
            self.staff_rating,
            self.value_rating,
            self.location_rating,
        ]
        return sum(ratings) / len(ratings)

    @property
    def is_pending(self) -> bool:
        return self.status == ReviewStatus.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == ReviewStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == ReviewStatus.REJECTED

    @property
    def is_published(self) -> bool:
        """Опубликован = одобрен и есть дата публикации"""
        return self.is_approved and self.published_at is not None

    @property
    def can_be_moderated(self) -> bool:
        """Можно модерировать только отзывы на модерации"""
        return self.is_pending

    @property
    def has_response(self) -> bool:
        """Есть ли ответ администрации"""
        return hasattr(self, 'response') and self.response is not None

    # ---- Moderation actions ----

    def approve(self, moderator=None, comment: str = ""):
        """Одобрить отзыв"""
        if not self.can_be_moderated:
            raise ValueError("Этот отзыв уже прошел модерацию")
        
        self.status = ReviewStatus.APPROVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.published_at = timezone.now()
        self.moderation_comment = comment
        self.save(update_fields=[
            "status", "moderated_by", "moderated_at",
            "published_at", "moderation_comment", "updated_at"
        ])
        
        # Логируем модерацию
        ReviewModeration.objects.create(
            review=self,
            action=ReviewModeration.Action.APPROVED,
            moderator=moderator,
            comment=comment,
        )

    def reject(self, moderator=None, reason: str = ""):
        """Отклонить отзыв"""
        if not self.can_be_moderated:
            raise ValueError("Этот отзыв уже прошел модерацию")
        
        self.status = ReviewStatus.REJECTED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.moderation_comment = reason
        self.save(update_fields=[
            "status", "moderated_by", "moderated_at",
            "moderation_comment", "updated_at"
        ])
        
        # Логируем модерацию
        ReviewModeration.objects.create(
            review=self,
            action=ReviewModeration.Action.REJECTED,
            moderator=moderator,
            comment=reason,
        )

    def toggle_featured(self):
        """Переключить статус избранного"""
        if not self.is_approved:
            raise ValueError("Только одобренные отзывы могут быть избранными")
        
        self.is_featured = not self.is_featured
        self.save(update_fields=["is_featured", "updated_at"])


# ---------------------------------------------------------------------------
# ReviewResponse
# ---------------------------------------------------------------------------

class ReviewResponse(UUIDModel, TimeStampedModel):
    """
    Ответ администрации на отзыв гостя.
    """

    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name="response",
        verbose_name=_("отзыв"),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="review_responses",
        verbose_name=_("автор ответа"),
        help_text=_("Сотрудник, написавший ответ"),
    )
    text = models.TextField(
        _("текст ответа"),
        help_text=_("Ответ администрации на отзыв"),
    )
    author_name = models.CharField(
        _("имя автора"),
        max_length=200,
        help_text=_("Имя сотрудника для отображения"),
    )
    author_position = models.CharField(
        _("должность"),
        max_length=100,
        blank=True,
        help_text=_("Например: Администратор, Менеджер"),
    )

    class Meta:
        verbose_name = _("ответ на отзыв")
        verbose_name_plural = _("ответы на отзывы")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Ответ на отзыв от {self.review.guest_name}"

    def save(self, *args, **kwargs):
        # Автоматически заполняем имя автора при создании
        if not self.author_name and self.author:
            self.author_name = self.author.get_full_name() or self.author.email
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# ReviewModeration
# ---------------------------------------------------------------------------

class ReviewModeration(TimeStampedModel):
    """
    История модерации отзывов (аудит-лог).
    Иммутабельная запись — только добавление, без изменений.
    """

    class Action(models.TextChoices):
        APPROVED = "approved", _("Одобрен")
        REJECTED = "rejected", _("Отклонен")
        EDITED   = "edited",   _("Отредактирован")
        DELETED  = "deleted",  _("Удален")

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="moderation_history",
        verbose_name=_("отзыв"),
    )
    action = models.CharField(
        _("действие"),
        max_length=20,
        choices=Action.choices,
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="review_moderation_actions",
        verbose_name=_("модератор"),
    )
    comment = models.TextField(
        _("комментарий"),
        blank=True,
    )
    snapshot = models.JSONField(
        _("снимок данных"),
        default=dict,
        blank=True,
        help_text=_("Состояние отзыва на момент действия"),
    )

    class Meta:
        verbose_name = _("история модерации")
        verbose_name_plural = _("история модерации")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_action_display()} — {self.review}"
