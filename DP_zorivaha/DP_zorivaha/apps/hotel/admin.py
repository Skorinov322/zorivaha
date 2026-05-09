from django.contrib import admin
from django.utils.html import format_html

from .models import Amenity, RoomCategory, RoomImage, Room


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ["name", "icon"]
    search_fields = ["name"]


class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1
    fields = ["image", "caption", "is_primary", "sort_order"]


@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "bed_type", "max_guests", "base_price_per_night", "is_active", "sort_order"]
    list_filter = ["is_active", "bed_type"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["amenities"]
    inlines = [RoomImageInline]
    fieldsets = (
        ("Основное", {"fields": ("name", "slug", "short_description", "description", "is_active", "sort_order")}),
        ("Параметры", {"fields": ("max_guests", "bed_type", "area_sqm", "floor")}),
        ("Цены", {"fields": ("base_price_per_night", "weekend_price_per_night")}),
        ("Медиа", {"fields": ("thumbnail",)}),
        ("Удобства", {"fields": ("amenities",)}),
    )


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["full_number_display", "category", "floor", "status", "max_concurrent_bookings", "current_occupancy"]
    list_filter = ["status", "category", "floor", "max_concurrent_bookings"]
    list_editable = ["status"]
    search_fields = ["number", "subdivision"]
    raw_id_fields = ["category"]
    fieldsets = (
        ("Основное", {
            "fields": ("category", "number", "subdivision", "floor", "status")
        }),
        ("Вместимость", {
            "fields": ("max_concurrent_bookings",)
        }),
        ("Удобства", {
            "fields": ("has_balcony", "has_sea_view", "has_mountain_view", "extra_amenities")
        }),
        ("Служебное", {
            "fields": ("notes", "last_cleaned_at")
        }),
    )
    
    def full_number_display(self, obj):
        return obj.full_number
    full_number_display.short_description = "Номер"
    
    def current_occupancy(self, obj):
        count = obj.get_current_occupancy_count()
        return f"{count}/{obj.max_concurrent_bookings}"
    current_occupancy.short_description = "Заполненность"
