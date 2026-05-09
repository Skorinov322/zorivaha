from django.contrib import admin
from django.utils.html import format_html

from .models import Organization, ClientProfile, AdminComment, Interaction, Task, Message


class AdminCommentInline(admin.TabularInline):
    model = AdminComment
    extra = 0
    readonly_fields = ["author", "created_at"]
    fields = ["body", "is_pinned", "author", "created_at"]


class InteractionInline(admin.TabularInline):
    model = Interaction
    extra = 0
    readonly_fields = ["created_at"]
    fields = ["interaction_type", "subject", "staff", "is_resolved", "created_at"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display  = ["name", "org_type", "inn", "contact_person", "corporate_discount_pct", "is_active"]
    list_filter   = ["org_type", "is_active"]
    search_fields = ["name", "inn", "contact_person", "email"]
    list_editable = ["is_active"]


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display  = [
        "user", "client_type", "status_badge", "loyalty_tier",
        "total_stays", "total_spent", "assigned_manager",
    ]
    list_filter   = ["status", "client_type", "loyalty_tier", "is_blacklisted"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user", "assigned_manager", "organization"]
    readonly_fields = ["total_stays", "total_nights", "total_spent", "first_stay_date", "last_stay_date"]
    inlines       = [AdminCommentInline, InteractionInline]

    def status_badge(self, obj):
        colors = {
            "active":      "success",
            "vip":         "warning",
            "inactive":    "secondary",
            "blacklisted": "danger",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Статус"


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display  = ["title", "assigned_to", "priority", "status", "due_date", "client"]
    list_filter   = ["status", "priority"]
    search_fields = ["title", "assigned_to__email"]
    raw_id_fields = ["assigned_to", "created_by", "client", "booking"]
    list_editable = ["status"]


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display  = ["interaction_type", "subject", "client", "staff", "is_resolved", "created_at"]
    list_filter   = ["interaction_type", "is_resolved"]
    search_fields = ["subject", "client__user__email"]
    raw_id_fields = ["client", "staff", "booking"]
