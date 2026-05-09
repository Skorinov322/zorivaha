from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
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


@admin.register(Booking, site=role_admin_site)
class BookingAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    """
    RECEPTIONIST — просмотр + смена статуса (только readonly поля)
    MANAGER+     — полное редактирование
    ADMIN+       — удаление
    """
    min_view_role   = "receptionist"
    min_change_role = "receptionist"   # ресепшн может менять статус
    min_delete_role = "admin"
    min_add_role    = "manager"

    list_display = [
        "confirmation_number", "guest_full_name_display",
        "room_category", "check_in", "check_out",
        "nights_display", "status_badge", "status", "payment_status", "final_price_display",
    ]
    list_filter  = ["status", "payment_status", "source", "room_category", "check_in", "created_at"]
    search_fields = [
        "confirmation_number",
        "guest_last_name", "guest_first_name",
        "guest_email", "guest_phone",
        "guest__email",
    ]
    date_hierarchy = "check_in"
    list_editable = ["status"]
    ordering = ["-created_at"]
    
    actions = ["cancel_bookings", "confirm_bookings", "checkin_bookings", "checkout_bookings", "set_paid", "set_unpaid", "delete_selected"]

    def get_readonly_fields(self, request, obj=None):
        base = ["confirmation_number", "created_at", "updated_at", "cancelled_at", "auto_cancel_at"]
        # Ресепшн может менять только статус, всё остальное readonly
        if not request.user.has_role("manager") and not request.user.is_superuser:
            all_fields = [f.name for f in Booking._meta.get_fields() if hasattr(f, 'name')]
            return [f for f in all_fields if f != "status"]
        return base

    def get_inlines(self, request, obj):
        inlines = [BookingHistoryInline]
        if request.user.has_role("manager") or request.user.is_superuser:
            inlines.append(PaymentInline)
        return inlines

    raw_id_fields  = ["guest", "room", "room_category", "cancelled_by", "created_by", "organization"]

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
            "checked_out": "info",
            "cancelled":  "danger",
            "no_show":    "secondary",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Статус"

    @admin.action(description="Отменить выбранные брони")
    def cancel_bookings(self, request, queryset):
        if not request.user.has_role("manager") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав.", level="error")
            return
        from django.utils import timezone
        count = queryset.filter(status__in=["pending", "confirmed"]).update(
            status="cancelled",
            cancelled_at=timezone.now(),
            cancellation_reason="Отменено администратором через admin-панель.",
            cancelled_by=request.user,
        )
        self.message_user(request, f"Отменено {count} броней.")

    @admin.action(description="Подтвердить выбранные брони")
    def confirm_bookings(self, request, queryset):
        if not request.user.has_role("receptionist") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав.", level="error")
            return
        count = queryset.filter(status="pending").update(status="confirmed", auto_cancel_at=None)
        self.message_user(request, f"Подтверждено {count} броней.")
    
    @admin.action(description="Заселить гостей")
    def checkin_bookings(self, request, queryset):
        if not request.user.has_role("receptionist") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав.", level="error")
            return
        count = queryset.filter(status="confirmed").update(status="checked_in")
        self.message_user(request, f"Заселено гостей по {count} броням.")
    
    @admin.action(description="Выселить гостей")
    def checkout_bookings(self, request, queryset):
        if not request.user.has_role("receptionist") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав.", level="error")
            return
        count = queryset.filter(status="checked_in").update(status="checked_out")
        self.message_user(request, f"Выселено гостей по {count} броням.")
    
    @admin.action(description="Отметить как оплаченные")
    def set_paid(self, request, queryset):
        if not request.user.has_role("manager") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав.", level="error")
            return
        count = queryset.update(payment_status="paid")
        self.message_user(request, f"Отмечено как оплаченные: {count} броней.")
    
    @admin.action(description="Отметить как неоплаченные")
    def set_unpaid(self, request, queryset):
        if not request.user.has_role("manager") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав.", level="error")
            return
        count = queryset.update(payment_status="unpaid")
        self.message_user(request, f"Отмечено как неоплаченные: {count} броней.")
    
    @admin.action(description="Удалить выбранные брони")
    def delete_selected(self, request, queryset):
        if not request.user.has_role("admin") and not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав для удаления броней.", level="error")
            return
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено броней: {count}")
