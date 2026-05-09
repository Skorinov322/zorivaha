"""
notifications/admin.py

Django Admin для EmailLog, NotificationTemplate, PushNotification.
Позволяет:
  - просматривать все отправленные письма
  - фильтровать по статусу, типу, дате
  - повторно отправить письмо (resend action)
  - просматривать HTML-тело прямо в admin
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import EmailLog, NotificationTemplate, PushNotification


# ---------------------------------------------------------------------------
# EmailLog
# ---------------------------------------------------------------------------

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        "created_at_short", "email_type_badge", "subject_short",
        "recipient_email", "status_badge", "retry_count",
    ]
    list_filter  = ["status", "email_type", "created_at"]
    search_fields = ["recipient_email", "subject", "booking__confirmation_number"]
    readonly_fields = [
        "created_at", "updated_at", "sent_at",
        "recipient_email", "recipient_name", "recipient_user",
        "email_type", "subject", "status", "error_message",
        "retry_count", "task_id", "booking",
        "body_html_preview", "body_text",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    actions = ["resend_emails"]

    fieldsets = (
        ("Получатель", {
            "fields": ("recipient_email", "recipient_name", "recipient_user", "booking"),
        }),
        ("Письмо", {
            "fields": ("email_type", "subject", "body_html_preview", "body_text"),
        }),
        ("Доставка", {
            "fields": ("status", "sent_at", "error_message", "retry_count", "task_id"),
        }),
        ("Мета", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # ---- Custom columns ----

    def created_at_short(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")
    created_at_short.short_description = "Дата"
    created_at_short.admin_order_field = "created_at"

    def subject_short(self, obj):
        return obj.subject[:60] + "…" if len(obj.subject) > 60 else obj.subject
    subject_short.short_description = "Тема"

    def status_badge(self, obj):
        colors = {
            "pending": ("#fff8e8", "#b8860b", "⏳"),
            "sent":    ("#e8f8ee", "#1a7a3a", "✅"),
            "failed":  ("#fef0f0", "#c0392b", "❌"),
            "bounced": ("#f5f5f5", "#666",    "↩"),
        }
        bg, color, icon = colors.get(obj.status, ("#f5f5f5", "#666", "?"))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;'
            'font-size:12px;font-weight:600;">{} {}</span>',
            bg, color, icon, obj.get_status_display(),
        )
    status_badge.short_description = "Статус"

    def email_type_badge(self, obj):
        return format_html(
            '<span style="font-size:11px;color:#888;">{}</span>',
            obj.get_email_type_display(),
        )
    email_type_badge.short_description = "Тип"

    def body_html_preview(self, obj):
        if not obj.body_html:
            return "—"
        return mark_safe(
            f'<details><summary style="cursor:pointer;color:#c9a84c;">Показать HTML</summary>'
            f'<div style="border:1px solid #ddd;border-radius:4px;padding:8px;margin-top:8px;'
            f'max-height:400px;overflow:auto;">{obj.body_html}</div></details>'
        )
    body_html_preview.short_description = "HTML тело"

    # ---- Actions ----

    @admin.action(description="Повторно отправить выбранные письма")
    def resend_emails(self, request, queryset):
        from apps.notifications.tasks import (
            send_booking_created_email,
            send_booking_confirmed_email,
            send_booking_cancelled_email,
            send_booking_auto_cancelled_email,
            send_checkin_reminder_email,
            send_no_show_email,
        )
        from .models import EmailLog

        task_map = {
            EmailLog.EmailType.BOOKING_CONFIRMATION: send_booking_created_email,
            EmailLog.EmailType.BOOKING_CANCELLED:    send_booking_cancelled_email,
            EmailLog.EmailType.BOOKING_REMINDER:     send_checkin_reminder_email,
        }

        sent = 0
        for log in queryset.filter(booking__isnull=False):
            task = task_map.get(log.email_type)
            if task:
                task.delay(str(log.booking_id))
                sent += 1

        self.message_user(request, f"Поставлено в очередь {sent} писем.")


# ---------------------------------------------------------------------------
# NotificationTemplate
# ---------------------------------------------------------------------------

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display  = ["name", "email_type", "is_active", "updated_at"]
    list_filter   = ["is_active", "email_type"]
    search_fields = ["name", "subject"]
    readonly_fields = ["updated_at"]
    raw_id_fields   = ["updated_by"]


# ---------------------------------------------------------------------------
# PushNotification
# ---------------------------------------------------------------------------

@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display  = ["recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter   = ["notification_type", "is_read"]
    search_fields = ["recipient__email", "title"]
    raw_id_fields = ["recipient", "booking"]
    readonly_fields = ["created_at", "read_at"]
