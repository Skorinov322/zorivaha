from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
from .models import Amenity, RoomCategory, RoomImage, Room


class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1
    fields = ["image", "caption", "is_primary", "sort_order"]


class AmenityAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "admin"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "admin"
    
    list_display  = ["name", "category", "icon", "is_highlighted", "sort_order"]
    list_filter   = ["category", "is_highlighted"]
    list_editable = ["is_highlighted", "sort_order"]
    search_fields = ["name"]
    ordering = ["category", "sort_order", "name"]
    
    actions = ["make_highlighted", "remove_highlighted", "delete_selected"]
    
    @admin.action(description="Выделить выбранные удобства")
    def make_highlighted(self, request, queryset):
        updated = queryset.update(is_highlighted=True)
        self.message_user(request, f"Выделено удобств: {updated}")
    
    @admin.action(description="Убрать выделение с выбранных удобств")
    def remove_highlighted(self, request, queryset):
        updated = queryset.update(is_highlighted=False)
        self.message_user(request, f"Убрано выделение с удобств: {updated}")
    
    @admin.action(description="Удалить выбранные удобства")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено удобств: {count}")


@admin.register(RoomCategory, site=role_admin_site)
class RoomCategoryAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "admin"

    list_display    = ["name", "bed_type", "max_guests", "base_price_per_night", "weekend_price_per_night", "is_active", "is_featured", "sort_order"]
    list_filter     = ["is_active", "is_featured", "bed_type", "max_guests"]
    list_editable   = ["is_active", "is_featured", "sort_order"]
    search_fields   = ["name", "description", "short_description"]
    filter_horizontal   = ["amenities"]
    inlines = [RoomImageInline]
    ordering = ["sort_order", "name"]
    
    actions = ["activate_categories", "deactivate_categories", "make_featured", "remove_featured", "delete_selected"]
    
    fieldsets = (
        ("Основное", {"fields": ("name", "slug", "short_description", "description", "is_active", "is_featured", "sort_order")}),
        ("Параметры", {"fields": ("max_guests", "bed_type", "area_sqm")}),
        ("Цены",      {"fields": ("base_price_per_night", "weekend_price_per_night")}),
        ("Медиа",     {"fields": ("thumbnail",)}),
        ("Удобства",  {"fields": ("amenities",)}),
    )
    
    class Media:
        js = ('admin/js/slug_autotransliterate.js',)
    
    @admin.action(description="Активировать выбранные категории")
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано категорий: {updated}")
    
    @admin.action(description="Деактивировать выбранные категории")
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано категорий: {updated}")
    
    @admin.action(description="Сделать рекомендуемыми")
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"Сделано рекомендуемыми: {updated}")
    
    @admin.action(description="Убрать из рекомендуемых")
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"Убрано из рекомендуемых: {updated}")
    
    @admin.action(description="Удалить выбранные категории")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено категорий: {count}")


@admin.register(Room, site=role_admin_site)
class RoomAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "receptionist"
    min_change_role = "admin"
    min_delete_role = "admin"
    min_add_role    = "admin"

    list_display  = ["full_number_display", "category", "floor", "status", "max_guests_per_room", "current_occupancy", "has_balcony", "has_sea_view"]
    list_filter   = ["status", "category", "floor", "max_guests_per_room", "has_balcony", "has_sea_view", "has_mountain_view"]
    list_editable = ["status"]
    search_fields = ["number", "subdivision", "category__name"]
    raw_id_fields = ["category"]
    ordering = ["floor", "number", "subdivision"]
    
    actions = ["set_available", "set_maintenance", "set_cleaning", "set_blocked", "delete_selected"]
    
    fieldsets = (
        ("Основное",    {"fields": ("category", "number", "subdivision", "floor", "status")}),
        ("Вместимость", {"fields": ("max_guests_per_room",)}),
        ("Удобства",    {"fields": ("has_balcony", "has_sea_view", "has_mountain_view", "extra_amenities")}),
        ("Служебное",   {"fields": ("notes", "last_cleaned_at")}),
    )

    def get_list_editable(self, request):
        # Ресепшн может менять статус номера прямо из списка
        if request.user.has_role("receptionist") or request.user.is_superuser:
            return ["status"]
        return []

    def full_number_display(self, obj):
        return obj.full_number
    full_number_display.short_description = "Номер"

    def current_occupancy(self, obj):
        count = obj.get_current_occupancy_count()
        return f"{count}/{obj.max_guests_per_room}"
    current_occupancy.short_description = "Заполненность"
    
    @admin.action(description="Установить статус: Свободен")
    def set_available(self, request, queryset):
        updated = queryset.update(status="available")
        self.message_user(request, f"Установлен статус 'Свободен' для {updated} номеров")
    
    @admin.action(description="Установить статус: На обслуживании")
    def set_maintenance(self, request, queryset):
        updated = queryset.update(status="maintenance")
        self.message_user(request, f"Установлен статус 'На обслуживании' для {updated} номеров")
    
    @admin.action(description="Установить статус: Уборка")
    def set_cleaning(self, request, queryset):
        updated = queryset.update(status="cleaning")
        self.message_user(request, f"Установлен статус 'Уборка' для {updated} номеров")
    
    @admin.action(description="Установить статус: Заблокирован")
    def set_blocked(self, request, queryset):
        updated = queryset.update(status="blocked")
        self.message_user(request, f"Установлен статус 'Заблокирован' для {updated} номеров")
    
    @admin.action(description="Удалить выбранные номера")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено номеров: {count}")
