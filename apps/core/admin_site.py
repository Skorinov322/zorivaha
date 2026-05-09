"""
apps/core/admin_site.py

Кастомный AdminSite с ролевым доступом.

Матрица доступа:
  RECEPTIONIST — Booking (только просмотр + смена статуса), ContactMessage
  MANAGER      — + CRM (ClientProfile, Organization, Task, Interaction), ContactReply, PushNotification
  ADMIN        — + Room, RoomCategory, Amenity, User (без смены ролей), EmailLog
  SUPER_ADMIN  — полный доступ (все модели + NotificationTemplate)
"""

from django.contrib import admin
from django.contrib.admin import AdminSite


class RoleBasedAdminSite(AdminSite):
    """
    Переопределяет has_permission чтобы пускать в /admin/
    пользователей с ролью RECEPTIONIST и выше (без is_staff).
    """
    site_header = "Зори Ваха — Управление"
    site_title  = "Зори Ваха Admin"
    index_title = "Панель управления"

    def has_permission(self, request):
        if not request.user.is_active or not request.user.is_authenticated:
            return False
        # Superuser всегда имеет доступ
        if request.user.is_superuser:
            return True
        # Пускаем всех кто RECEPTIONIST и выше
        from apps.accounts.models import UserRole
        return request.user.has_role(UserRole.RECEPTIONIST)
    
    def index(self, request, extra_context=None):
        """
        Переопределяем главную страницу админки для добавления статистики
        """
        extra_context = extra_context or {}
        
        # Добавляем статистику
        try:
            from .admin_views import admin_dashboard_stats
            stats = admin_dashboard_stats(request)
            extra_context.update(stats)
        except Exception:
            # Если что-то пошло не так, используем заглушки
            extra_context.update({
                'total_bookings': 0,
                'active_bookings': 0,
                'total_users': 0,
                'total_rooms': 0,
                'occupancy_rate': 0,
                'pending_orgs': 0,
            })
        
        return super().index(request, extra_context)


# Единственный экземпляр — заменяет стандартный admin.site
role_admin_site = RoleBasedAdminSite(name="role_admin")


# ---------------------------------------------------------------------------
# Базовый миксин для ролевых ограничений в ModelAdmin
# ---------------------------------------------------------------------------

class RoleRestrictedMixin:
    """
    Миксин для ModelAdmin.
    Подклассы задают:
      min_view_role   — минимальная роль для просмотра
      min_change_role — минимальная роль для редактирования
      min_delete_role — минимальная роль для удаления
      min_add_role    — минимальная роль для создания
    """
    min_view_role   = "receptionist"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"

    def _has_role(self, request, role):
        if request.user.is_superuser:
            return True
        return request.user.has_role(role)

    def has_view_permission(self, request, obj=None):
        return self._has_role(request, self.min_view_role)

    def has_change_permission(self, request, obj=None):
        return self._has_role(request, self.min_change_role)

    def has_delete_permission(self, request, obj=None):
        return self._has_role(request, self.min_delete_role)

    def has_add_permission(self, request):
        return self._has_role(request, self.min_add_role)

    def has_module_perms(self, request, app_label):
        return self._has_role(request, self.min_view_role)
