from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
from .models import User


@admin.register(User, site=role_admin_site)
class UserAdmin(RoleRestrictedMixin, BaseUserAdmin):
    """
    ADMIN  — просмотр + редактирование профиля (без смены ролей)
    SUPER_ADMIN — полный доступ включая роли
    """
    min_view_role   = "admin"
    min_change_role = "admin"
    min_delete_role = "super_admin"
    min_add_role    = "admin"

    ordering      = ["-created_at"]
    list_display  = ["email", "get_full_name", "role", "is_active", "is_staff", "last_login", "created_at"]
    list_filter   = ["role", "is_active", "is_staff", "is_superuser", "marketing_consent", "created_at"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    list_editable = ["is_active"]
    date_hierarchy = "created_at"
    
    actions = ["activate_users", "deactivate_users", "make_staff", "remove_staff", "delete_selected"]

    def get_fieldsets(self, request, obj=None):
        base = (
            (None, {"fields": ("email", "password")}),
            (_("Личные данные"), {"fields": ("first_name", "last_name", "phone", "date_of_birth", "avatar")}),
            (_("Документы"), {"fields": ("passport_series", "passport_number")}),
            (_("Настройки"), {"fields": ("preferred_language", "marketing_consent")}),
            (_("Даты"), {"fields": ("last_login", "created_at", "updated_at")}),
        )
        # Только SUPER_ADMIN видит поля ролей и прав
        if request.user.is_superuser or request.user.has_role("super_admin"):
            return base + (
                (_("Роль и доступ"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
            )
        # ADMIN видит только is_active (без смены роли)
        return base + (
            (_("Доступ"), {"fields": ("is_active",)}),
        )

    readonly_fields = ["created_at", "updated_at", "last_login"]

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )
    
    @admin.action(description="Активировать выбранных пользователей")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано пользователей: {updated}")
    
    @admin.action(description="Деактивировать выбранных пользователей")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано пользователей: {updated}")
    
    @admin.action(description="Сделать сотрудниками")
    def make_staff(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав для изменения статуса сотрудника", level="error")
            return
        updated = queryset.update(is_staff=True)
        self.message_user(request, f"Сделано сотрудниками: {updated}")
    
    @admin.action(description="Убрать статус сотрудника")
    def remove_staff(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав для изменения статуса сотрудника", level="error")
            return
        updated = queryset.update(is_staff=False)
        self.message_user(request, f"Убран статус сотрудника у: {updated}")
    
    @admin.action(description="Удалить выбранных пользователей")
    def delete_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав для удаления пользователей", level="error")
            return
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено пользователей: {count}")
