from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
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


@admin.register(Organization, site=role_admin_site)
class OrganizationAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"

    list_display  = ["name", "org_type", "inn", "contact_person", "approval_status", "created_by_user", "corporate_discount_pct", "is_active", "is_approved"]
    list_filter   = ["org_type", "is_active", "is_approved", "created_at"]
    search_fields = ["name", "inn", "contact_person", "email", "phone"]
    list_editable = ["is_active", "is_approved", "corporate_discount_pct"]
    readonly_fields = ["created_by_user", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["is_approved", "name"]
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "short_name", "org_type", "is_active", "is_approved")
        }),
        ("Юридические данные", {
            "fields": ("inn", "kpp", "ogrn", "legal_address", "actual_address")
        }),
        ("Контакты", {
            "fields": ("phone", "email", "website", "contact_person")
        }),
        ("Коммерческие условия", {
            "fields": ("corporate_discount_pct", "credit_limit", "payment_terms_days")
        }),
        ("CRM", {
            "fields": ("assigned_manager", "notes")
        }),
        ("Системная информация", {
            "fields": ("created_by_user", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span class="badge bg-success">Подтверждена</span>')
        else:
            return format_html('<span class="badge bg-warning">Ожидает подтверждения</span>')
    approval_status.short_description = "Статус подтверждения"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Show pending organizations first
        return qs.order_by("is_approved", "name")

    actions = ["approve_organizations", "reject_organizations", "activate_organizations", "deactivate_organizations", "set_discount_5", "set_discount_10", "delete_selected"]

    @admin.action(description="Подтвердить выбранные организации")
    def approve_organizations(self, request, queryset):
        updated = queryset.update(is_approved=True, is_active=True)
        self.message_user(request, f"Подтверждено организаций: {updated}")

    @admin.action(description="Отклонить выбранные организации")
    def reject_organizations(self, request, queryset):
        updated = queryset.update(is_approved=False, is_active=False)
        self.message_user(request, f"Отклонено организаций: {updated}")
    
    @admin.action(description="Активировать выбранные организации")
    def activate_organizations(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано организаций: {updated}")
    
    @admin.action(description="Деактивировать выбранные организации")
    def deactivate_organizations(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано организаций: {updated}")
    
    @admin.action(description="Установить скидку 5%")
    def set_discount_5(self, request, queryset):
        updated = queryset.update(corporate_discount_pct=5)
        self.message_user(request, f"Установлена скидка 5% для {updated} организаций")
    
    @admin.action(description="Установить скидку 10%")
    def set_discount_10(self, request, queryset):
        updated = queryset.update(corporate_discount_pct=10)
        self.message_user(request, f"Установлена скидка 10% для {updated} организаций")
    
    @admin.action(description="Удалить выбранные организации")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено организаций: {count}")


@admin.register(ClientProfile, site=role_admin_site)
class ClientProfileAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"

    list_display  = ["user", "client_type", "status_badge", "status", "total_stays", "total_spent", "assigned_manager", "is_blacklisted"]
    list_filter   = ["status", "client_type", "is_blacklisted", "assigned_manager"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "user__phone"]
    raw_id_fields = ["user", "assigned_manager", "organization"]
    readonly_fields = ["total_stays", "total_nights", "total_spent", "first_stay_date", "last_stay_date"]
    inlines = [AdminCommentInline, InteractionInline]
    list_editable = ["status"]
    
    actions = ["set_vip_status", "set_active_status", "set_inactive_status", "blacklist_clients", "unblacklist_clients", "delete_selected"]

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
    
    @admin.action(description="Установить VIP статус")
    def set_vip_status(self, request, queryset):
        updated = queryset.update(status="vip")
        self.message_user(request, f"Установлен VIP статус для {updated} клиентов")
    
    @admin.action(description="Установить активный статус")
    def set_active_status(self, request, queryset):
        updated = queryset.update(status="active")
        self.message_user(request, f"Установлен активный статус для {updated} клиентов")
    
    @admin.action(description="Установить неактивный статус")
    def set_inactive_status(self, request, queryset):
        updated = queryset.update(status="inactive")
        self.message_user(request, f"Установлен неактивный статус для {updated} клиентов")
    
    @admin.action(description="Добавить в черный список")
    def blacklist_clients(self, request, queryset):
        updated = queryset.update(status="blacklisted", is_blacklisted=True)
        self.message_user(request, f"Добавлено в черный список: {updated} клиентов")
    
    @admin.action(description="Убрать из черного списка")
    def unblacklist_clients(self, request, queryset):
        updated = queryset.update(is_blacklisted=False)
        # Также меняем статус на активный если был blacklisted
        queryset.filter(status="blacklisted").update(status="active")
        self.message_user(request, f"Убрано из черного списка: {updated} клиентов")
    
    @admin.action(description="Удалить выбранные профили")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено профилей: {count}")


@admin.register(Task, site=role_admin_site)
class TaskAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "manager"
    min_add_role    = "manager"

    list_display  = ["title", "assigned_to", "priority", "status", "due_date", "client", "created_at"]
    list_filter   = ["status", "priority", "assigned_to", "due_date", "created_at"]
    search_fields = ["title", "description", "assigned_to__email", "client__user__email"]
    raw_id_fields = ["assigned_to", "created_by", "client", "booking"]
    list_editable = ["status", "priority"]
    date_hierarchy = "due_date"
    ordering = ["due_date", "priority"]
    
    actions = ["mark_completed", "mark_in_progress", "mark_pending", "set_high_priority", "set_low_priority", "delete_selected"]
    
    @admin.action(description="Отметить как выполненные")
    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"Отмечено как выполненные: {updated} задач")
    
    @admin.action(description="Отметить как в работе")
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status="in_progress")
        self.message_user(request, f"Отмечено как в работе: {updated} задач")
    
    @admin.action(description="Отметить как ожидающие")
    def mark_pending(self, request, queryset):
        updated = queryset.update(status="pending")
        self.message_user(request, f"Отмечено как ожидающие: {updated} задач")
    
    @admin.action(description="Установить высокий приоритет")
    def set_high_priority(self, request, queryset):
        updated = queryset.update(priority="high")
        self.message_user(request, f"Установлен высокий приоритет для {updated} задач")
    
    @admin.action(description="Установить низкий приоритет")
    def set_low_priority(self, request, queryset):
        updated = queryset.update(priority="low")
        self.message_user(request, f"Установлен низкий приоритет для {updated} задач")
    
    @admin.action(description="Удалить выбранные задачи")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено задач: {count}")


@admin.register(Interaction, site=role_admin_site)
class InteractionAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"

    list_display  = ["interaction_type", "subject", "client", "staff", "is_resolved", "created_at"]
    list_filter   = ["interaction_type", "is_resolved", "staff", "created_at"]
    search_fields = ["subject", "notes", "client__user__email", "staff__email"]
    raw_id_fields = ["client", "staff", "booking"]
    list_editable = ["is_resolved"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    
    actions = ["mark_resolved", "mark_unresolved", "delete_selected"]
    
    @admin.action(description="Отметить как решенные")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f"Отмечено как решенные: {updated} взаимодействий")
    
    @admin.action(description="Отметить как нерешенные")
    def mark_unresolved(self, request, queryset):
        updated = queryset.update(is_resolved=False)
        self.message_user(request, f"Отмечено как нерешенные: {updated} взаимодействий")
    
    @admin.action(description="Удалить выбранные взаимодействия")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено взаимодействий: {count}")
