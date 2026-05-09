from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
from .models import PageView, DailyMetrics, BookingFunnel, RevenueSnapshot


@admin.register(PageView, site=role_admin_site)
class PageViewAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "super_admin"

    list_display  = ["viewed_at", "user_display", "page_type", "path", "ip_address", "user_agent_short"]
    list_filter   = ["page_type", "viewed_at"]
    search_fields = ["path", "ip_address", "user__email", "user_agent"]
    readonly_fields = ["viewed_at", "user", "session_key", "path", "page_type", "ip_address", "user_agent", "referrer"]
    date_hierarchy = "viewed_at"
    ordering = ["-viewed_at"]
    
    actions = ["delete_selected", "delete_old_records"]

    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.email}"
        return f"Анонимный ({obj.ip_address})"
    user_display.short_description = "Пользователь"

    def user_agent_short(self, obj):
        if not obj.user_agent:
            return "—"
        ua = obj.user_agent
        if len(ua) > 50:
            return ua[:47] + "..."
        return ua
    user_agent_short.short_description = "User Agent"
    
    @admin.action(description="Удалить записи старше 30 дней")
    def delete_old_records(self, request, queryset):
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)
        count = PageView.objects.filter(viewed_at__lt=cutoff_date).count()
        PageView.objects.filter(viewed_at__lt=cutoff_date).delete()
        self.message_user(request, f"Удалено старых записей: {count}")
    
    @admin.action(description="Удалить выбранные записи")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено записей: {count}")


@admin.register(DailyMetrics, site=role_admin_site)
class DailyMetricsAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "admin"

    list_display  = ["date", "occupancy_rate", "total_revenue", "adr", "revpar", "new_bookings", "calculated_at"]
    list_filter   = ["date", "calculated_at"]
    search_fields = ["date"]
    readonly_fields = ["calculated_at"]
    date_hierarchy = "date"
    ordering = ["-date"]
    
    actions = ["recalculate_kpis", "delete_selected"]
    
    @admin.action(description="Пересчитать KPI для выбранных записей")
    def recalculate_kpis(self, request, queryset):
        count = 0
        for metric in queryset:
            metric.calculate_kpis()
            count += 1
        self.message_user(request, f"Пересчитано KPI для {count} записей")
    
    @admin.action(description="Удалить выбранные записи")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено записей: {count}")


@admin.register(BookingFunnel, site=role_admin_site)
class BookingFunnelAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "super_admin"

    list_display  = ["session_key_short", "user_display", "stage", "room_category", "started_at", "updated_at"]
    list_filter   = ["stage", "started_at", "updated_at"]
    search_fields = ["session_key", "user__email"]
    readonly_fields = ["session_key", "user", "started_at", "updated_at"]
    date_hierarchy = "started_at"
    ordering = ["-updated_at"]
    
    actions = ["mark_abandoned", "delete_selected"]

    def session_key_short(self, obj):
        return obj.session_key[:8] + "..." if obj.session_key else "—"
    session_key_short.short_description = "Сессия"

    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.email}"
        return f"Анонимный"
    user_display.short_description = "Пользователь"
    
    @admin.action(description="Отметить как брошенные")
    def mark_abandoned(self, request, queryset):
        updated = queryset.update(stage="abandoned")
        self.message_user(request, f"Отмечено как брошенные: {updated} воронок")
    
    @admin.action(description="Удалить выбранные воронки")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено воронок: {count}")


@admin.register(RevenueSnapshot, site=role_admin_site)
class RevenueSnapshotAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "admin"

    list_display  = ["year", "month", "total_revenue", "total_bookings", "avg_occupancy", "avg_adr", "calculated_at"]
    list_filter   = ["year", "month", "calculated_at"]
    search_fields = ["year", "month"]
    readonly_fields = ["calculated_at"]
    ordering = ["-year", "-month"]
    
    actions = ["delete_selected"]
    
    @admin.action(description="Удалить выбранные снимки")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено снимков: {count}")