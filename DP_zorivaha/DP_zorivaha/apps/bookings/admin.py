from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, BookingHistory, Payment


class BookingHistoryInline(admin.TabularInline):
    model = BookingHistory
    extra = 0
    readonly_fields = ["action", "status_after", "changed_by", "note", "created_at"]
    can_delete = False
    ordering = ["created_at"]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ["created_at"]
    fields = ["amount", "method", "payment_type", "is_confirmed", "processed_by", "created_at"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "confirmation_number", "guest_full_name_display",
        "room_category", "check_in", "check_out",
        "nights_display", "status_badge", "payment_status", "final_price_display",
    ]
    list_filter  = ["status", "payment_status", "source", "room_category", "check_in"]
    search_fields = [
        "confirmation_number",
        "guest_last_name", "guest_first_name",
        "guest_email", "guest_phone",
        "guest__email",
    ]
    readonly_fields = [
        "confirmation_number", "created_at", "updated_at",
        "cancelled_at", "auto_cancel_at",
    ]
    raw_id_fields  = ["guest", "room", "room_category", "cancelled_by", "created_by", "organization"]
    inlines        = [BookingHistoryInline, PaymentInline]
    date_hierarchy = "check_in"

    fieldsets = (
        ("Бронь", {
            "fields": ("confirmation_number", "guest", "room_category", "room", "organization", "source")
        }),
        ("Гость (снимок)", {
            "fields": ("guest_last_name", "guest_first_name", "guest_patronymic", "guest_phone", "guest_email")
        }),
        ("Даты", {
            "fields": ("check_in", "check_out", "arrival_time", "departure_time", "auto_cancel_at")
        }),
        ("Гости", {"fields": ("adults", "children")}),
        ("Цены", {
            "fields": ("price_per_night", "total_price", "discount_amount", "discount_reason", "payment_status")
        }),
        ("Статус", {"fields": ("status",)}),
        ("Пожелания", {"fields": ("special_requests", "internal_notes")}),
        ("Отмена", {
            "fields": ("cancelled_at", "cancellation_reason", "cancelled_by"),
            "classes": ("collapse",),
        }),
        ("Мета", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def guest_full_name_display(self, obj):
        return obj.guest_full_name
    guest_full_name_display.short_description = "Гость"

    def nights_display(self, obj):
        return f"{obj.nights} н."
    nights_display.short_description = "Ночей"

    def final_price_display(self, obj):
        return f"{obj.final_price:,.0f} ₽"
    final_price_display.short_description = "Итого"

    def status_badge(self, obj):
        colors = {
            "pending":    "warning",
            "confirmed":  "success",
            "checked_in": "primary",
            "checked_out":"info",
            "cancelled":  "danger",
            "no_show":    "secondary",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Статус"
