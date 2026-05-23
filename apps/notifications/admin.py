from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
from .models import EmailLog, NotificationTemplate, PushNotification, ContactMessage, ContactReply


# ---------------------------------------------------------------------------
# EmailLog — только ADMIN+
# ---------------------------------------------------------------------------

@admin.register(EmailLog, site=role_admin_site)
class EmailLogAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "admin"
    min_change_role = "super_admin"
    min_delete_role = "admin"
    min_add_role    = "super_admin"

    list_display  = ["created_at_short", "email_type_badge", "subject_short", "recipient_email", "status_badge", "retry_count"]
    list_filter   = ["status", "email_type", "created_at"]
    search_fields = ["recipient_email", "subject", "booking__confirmation_number"]
    readonly_fields = [
        "created_at", "updated_at", "sent_at",
        "recipient_email", "recipient_name", "recipient_user",
        "email_type", "subject", "status", "error_message",
        "retry_count", "task_id", "booking", "body_html_preview", "body_text",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    actions = ["resend_emails", "mark_as_sent", "delete_selected"]

    fieldsets = (
        ("Получаостиница", {"fields": ("recipient_email", "recipient_name", "recipient_user", "booking")}),
        ("Письмо",     {"fields": ("email_type", "subject", "body_html_preview", "body_text")}),
        ("Доставка",   {"fields": ("status", "sent_at", "error_message", "retry_count", "task_id")}),
        ("Мета",       {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

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
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">{} {}</span>',
            bg, color, icon, obj.get_status_display(),
        )
    status_badge.short_description = "Статус"

    def email_type_badge(self, obj):
        return format_html('<span style="font-size:11px;color:#888">{}</span>', obj.get_email_type_display())
    email_type_badge.short_description = "Тип"

    def body_html_preview(self, obj):
        if not obj.body_html:
            return "—"
        return mark_safe(
            f'<details><summary style="cursor:pointer;color:#c9a84c">Показать HTML</summary>'
            f'<div style="border:1px solid #ddd;border-radius:4px;padding:8px;margin-top:8px;max-height:400px;overflow:auto">'
            f'{obj.body_html}</div></details>'
        )
    body_html_preview.short_description = "HTML тело"

    @admin.action(description="Повторно отправить выбранные письма")
    def resend_emails(self, request, queryset):
        from apps.notifications.tasks import (
            send_booking_created_email, send_booking_cancelled_email, send_checkin_reminder_email,
        )
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
    
    @admin.action(description="Отметить как отправленные")
    def mark_as_sent(self, request, queryset):
        updated = queryset.update(status="sent", sent_at=timezone.now())
        self.message_user(request, f"Отмечено как отправленные: {updated} писем")
    
    @admin.action(description="Удалить выбранные логи")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено логов: {count}")


# ---------------------------------------------------------------------------
# NotificationTemplate — только SUPER_ADMIN
# ---------------------------------------------------------------------------

@admin.register(NotificationTemplate, site=role_admin_site)
class NotificationTemplateAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "super_admin"
    min_change_role = "super_admin"
    min_delete_role = "super_admin"
    min_add_role    = "super_admin"

    list_display  = ["name", "email_type", "is_active", "updated_at"]
    list_filter   = ["is_active", "email_type"]
    search_fields = ["name", "subject"]
    readonly_fields = ["updated_at"]
    raw_id_fields   = ["updated_by"]


# ---------------------------------------------------------------------------
# PushNotification — MANAGER+
# ---------------------------------------------------------------------------

@admin.register(PushNotification, site=role_admin_site)
class PushNotificationAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "admin"

    list_display  = ["recipient", "notification_type", "title", "is_read", "created_at"]
    list_filter   = ["notification_type", "is_read"]
    search_fields = ["recipient__email", "title"]
    raw_id_fields = ["recipient", "booking"]
    readonly_fields = ["created_at", "read_at"]
    actions = ["mark_read", "mark_unread", "delete_selected"]

    @admin.action(description="Отметить как прочитанные")
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"Отмечено как прочитанные: {updated} уведомлений")

    @admin.action(description="Отметить как непрочитанные")
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"Отмечено как непрочитанные: {updated} уведомлений")
    
    @admin.action(description="Удалить выбранные уведомления")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено уведомлений: {count}")


# ---------------------------------------------------------------------------
# ContactMessage — RECEPTIONIST+
# ---------------------------------------------------------------------------

class ContactReplyInline(admin.TabularInline):
    model = ContactReply
    extra = 0
    readonly_fields = ["author", "created_at", "is_staff_reply", "is_read_by_guest"]
    fields = ["body", "author", "is_staff_reply", "is_read_by_guest", "created_at"]
    ordering = ["created_at"]


@admin.register(ContactMessage, site=role_admin_site)
class ContactMessageAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "receptionist"
    min_change_role = "receptionist"
    min_delete_role = "admin"
    min_add_role    = "manager"

    list_display  = ["id", "sender_name", "sender_email", "subject_short", "status_badge", "assigned_to", "created_at"]
    list_filter   = ["status", "created_at"]
    search_fields = ["sender_name", "sender_email", "sender_phone", "subject", "message"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["sender_user", "assigned_to"]
    inlines = [ContactReplyInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    actions = ["mark_closed", "mark_new", "assign_to_me", "delete_selected"]

    fieldsets = (
        ("Отправиостиница", {"fields": ("sender_user", "sender_name", "sender_email", "sender_phone")}),
        ("Сообщение",   {"fields": ("subject", "message")}),
        ("Статус",      {"fields": ("status", "assigned_to")}),
        ("Мета",        {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def subject_short(self, obj):
        s = obj.subject or obj.message[:40]
        return s[:50] + "…" if len(s) > 50 else s
    subject_short.short_description = "Тема"

    def status_badge(self, obj):
        colors = {
            "new":      ("#fff3cd", "#856404"),
            "in_work":  ("#cfe2ff", "#084298"),
            "answered": ("#d1e7dd", "#0a3622"),
            "closed":   ("#e2e3e5", "#41464b"),
        }
        bg, color = colors.get(obj.status, ("#e2e3e5", "#41464b"))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">{}</span>',
            bg, color, obj.get_status_display(),
        )
    status_badge.short_description = "Статус"

    @admin.action(description="Закрыть выбранные обращения")
    def mark_closed(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.CLOSED)
        self.message_user(request, f"Закрыто обращений: {updated}")

    @admin.action(description="Вернуть в статус «Новое»")
    def mark_new(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.NEW)
        self.message_user(request, f"Возвращено в статус 'Новое': {updated} обращений")
    
    @admin.action(description="Назначить на меня")
    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user, status=ContactMessage.Status.IN_WORK)
        self.message_user(request, f"Назначено на вас: {updated} обращений")
    
    @admin.action(description="Удалить выбранные обращения")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено обращений: {count}")


@admin.register(ContactReply, site=role_admin_site)
class ContactReplyAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"

    list_display  = ["message", "author", "is_staff_reply", "is_read_by_guest", "created_at"]
    list_filter   = ["is_staff_reply", "is_read_by_guest"]
    search_fields = ["body", "author__email", "message__sender_email"]
    raw_id_fields = ["message", "author"]
    readonly_fields = ["created_at"]
