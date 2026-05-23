"""
reviews/admin.py

Админ-панель для управления отзывами.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Review, ReviewResponse, ReviewModeration


# ---------------------------------------------------------------------------
# Inline для ответов на отзывы
# ---------------------------------------------------------------------------

class ReviewResponseInline(admin.StackedInline):
    model = ReviewResponse
    extra = 0
    max_num = 1
    fields = ("text", "author_name", "author_position", "created_at")
    readonly_fields = ("created_at",)


# ---------------------------------------------------------------------------
# Review Admin
# ---------------------------------------------------------------------------

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "guest_name",
        "booking_number",
        "overall_rating_stars",
        "status_badge",
        "is_featured",
        "created_at",
        "moderated_by",
    )
    list_filter = (
        "status",
        "is_featured",
        "overall_rating",
        "created_at",
        "moderated_at",
    )
    search_fields = (
        "guest_name",
        "title",
        "text",
        "booking__confirmation_number",
        "author__email",
    )
    readonly_fields = (
        "id",
        "booking",
        "author",
        "guest_name",
        "average_rating_display",
        "created_at",
        "updated_at",
        "moderated_at",
        "published_at",
        "ip_address",
        "user_agent",
    )
    fieldsets = (
        (_("Основная информация"), {
            "fields": (
                "id",
                "booking",
                "author",
                "guest_name",
                "status",
                "is_featured",
            )
        }),
        (_("Оценки"), {
            "fields": (
                "overall_rating",
                "cleanliness_rating",
                "comfort_rating",
                "staff_rating",
                "value_rating",
                "location_rating",
                "average_rating_display",
            )
        }),
        (_("Содержание"), {
            "fields": (
                "title",
                "text",
                "pros",
                "cons",
            )
        }),
        (_("Модерация"), {
            "fields": (
                "moderated_by",
                "moderated_at",
                "moderation_comment",
            )
        }),
        (_("Метаданные"), {
            "fields": (
                "created_at",
                "updated_at",
                "published_at",
                "ip_address",
                "user_agent",
            ),
            "classes": ("collapse",),
        }),
    )
    inlines = [ReviewResponseInline]
    actions = ["approve_reviews", "reject_reviews", "toggle_featured"]

    def booking_number(self, obj):
        return obj.booking.confirmation_number
    booking_number.short_description = _("Номер брони")

    def overall_rating_stars(self, obj):
        stars = "⭐" * obj.overall_rating
        return format_html(f'<span style="font-size: 16px;">{stars}</span>')
    overall_rating_stars.short_description = _("Оценка")

    def status_badge(self, obj):
        colors = {
            "pending": "orange",
            "approved": "green",
            "rejected": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _("Статус")

    def average_rating_display(self, obj):
        return f"{obj.average_rating:.1f} / 5.0"
    average_rating_display.short_description = _("Средняя оценка")

    # ---- Actions ----

    @admin.action(description=_("Одобрить выбранные отзывы"))
    def approve_reviews(self, request, queryset):
        count = 0
        for review in queryset.filter(status="pending"):
            review.approve(moderator=request.user)
            count += 1
        self.message_user(request, f"Одобрено отзывов: {count}")

    @admin.action(description=_("Отклонить выбранные отзывы"))
    def reject_reviews(self, request, queryset):
        count = 0
        for review in queryset.filter(status="pending"):
            review.reject(moderator=request.user, reason="Отклонено администратором")
            count += 1
        self.message_user(request, f"Отклонено отзывов: {count}")

    @admin.action(description=_("Переключить статус 'Избранный'"))
    def toggle_featured(self, request, queryset):
        count = 0
        for review in queryset.filter(status="approved"):
            review.toggle_featured()
            count += 1
        self.message_user(request, f"Обновлено отзывов: {count}")


# ---------------------------------------------------------------------------
# ReviewResponse Admin
# ---------------------------------------------------------------------------

@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    list_display = (
        "review",
        "author_name",
        "author_position",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "text",
        "author_name",
        "review__guest_name",
    )
    readonly_fields = ("id", "review", "author", "created_at", "updated_at")
    fieldsets = (
        (_("Основная информация"), {
            "fields": ("id", "review", "author")
        }),
        (_("Ответ"), {
            "fields": ("text", "author_name", "author_position")
        }),
        (_("Метаданные"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------------
# ReviewModeration Admin
# ---------------------------------------------------------------------------

@admin.register(ReviewModeration)
class ReviewModerationAdmin(admin.ModelAdmin):
    list_display = (
        "review",
        "action",
        "moderator",
        "created_at",
    )
    list_filter = ("action", "created_at")
    search_fields = (
        "review__guest_name",
        "moderator__email",
        "comment",
    )
    readonly_fields = (
        "review",
        "action",
        "moderator",
        "comment",
        "snapshot",
        "created_at",
    )
    fieldsets = (
        (_("Информация"), {
            "fields": (
                "review",
                "action",
                "moderator",
                "comment",
                "created_at",
            )
        }),
        (_("Снимок данных"), {
            "fields": ("snapshot",),
            "classes": ("collapse",),
        }),
    )

    def has_add_permission(self, request):
        # История модерации создается автоматически
        return False

    def has_change_permission(self, request, obj=None):
        # История иммутабельна
        return False

    def has_delete_permission(self, request, obj=None):
        # Не удаляем историю
        return False
