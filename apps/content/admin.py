"""
content/admin.py

Admin registration for content models.
Admins manage gallery photos, FAQ, site content, and testimonials here.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.core.admin_site import role_admin_site, RoleRestrictedMixin
from .models import HotelGallery, FAQ, SiteContent, Testimonial, LegalPage, AboutPage


@admin.register(LegalPage, site=role_admin_site)
class LegalPageAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "admin"
    min_change_role = "admin"
    min_delete_role = "super_admin"
    min_add_role    = "admin"

    list_display  = ["page_type", "title", "is_active"]
    list_filter   = ["page_type", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["title", "content"]
    ordering = ["page_type"]



@admin.register(HotelGallery, site=role_admin_site)
class HotelGalleryAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"
    
    list_display  = ["thumbnail_preview", "title", "section", "is_active", "is_featured", "sort_order"]
    list_filter   = ["section", "is_active", "is_featured"]
    list_editable = ["is_active", "is_featured", "sort_order"]
    search_fields = ["title", "alt_text"]
    ordering      = ["section", "sort_order"]
    
    actions = ["activate_photos", "deactivate_photos", "make_featured", "remove_featured", "delete_selected"]

    fieldsets = (
        ("Изображение", {
            "fields": ("image", "title", "alt_text"),
        }),
        ("Настройки", {
            "fields": ("section", "is_active", "is_featured", "sort_order"),
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:48px;width:72px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return "—"
    thumbnail_preview.short_description = "Фото"
    
    @admin.action(description="Активировать выбранные фото")
    def activate_photos(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано фото: {updated}")
    
    @admin.action(description="Деактивировать выбранные фото")
    def deactivate_photos(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано фото: {updated}")
    
    @admin.action(description="Сделать рекомендуемыми")
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"Сделано рекомендуемыми: {updated}")
    
    @admin.action(description="Убрать из рекомендуемых")
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"Убрано из рекомендуемых: {updated}")
    
    @admin.action(description="Удалить выбранные фото")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено фото: {count}")


@admin.register(FAQ, site=role_admin_site)
class FAQAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "super_admin"
    min_change_role = "super_admin"
    min_delete_role = "super_admin"
    min_add_role    = "super_admin"
    
    list_display  = ["question", "category", "is_active", "sort_order"]
    list_filter   = ["category", "is_active"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["question", "answer"]
    ordering = ["category", "sort_order"]
    
    actions = ["activate_faqs", "deactivate_faqs", "delete_selected"]
    
    @admin.action(description="Активировать выбранные FAQ")
    def activate_faqs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано FAQ: {updated}")
    
    @admin.action(description="Деактивировать выбранные FAQ")
    def deactivate_faqs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано FAQ: {updated}")
    
    @admin.action(description="Удалить выбранные FAQ")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено FAQ: {count}")


@admin.register(SiteContent, site=role_admin_site)
class SiteContentAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "admin"
    min_change_role = "admin"
    min_delete_role = "super_admin"
    min_add_role    = "admin"
    
    list_display  = ["key", "label", "content_type", "is_active", "updated_by", "updated_at"]
    list_filter   = ["content_type", "is_active", "updated_at"]
    search_fields = ["key", "label", "value_text"]
    readonly_fields = ["updated_by", "created_at", "updated_at"]
    list_editable = ["is_active"]
    
    actions = ["activate_content", "deactivate_content", "delete_selected"]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    @admin.action(description="Активировать выбранный контент")
    def activate_content(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано контента: {updated}")
    
    @admin.action(description="Деактивировать выбранный контент")
    def deactivate_content(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано контента: {updated}")
    
    @admin.action(description="Удалить выбранный контент")
    def delete_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Недостаточно прав для удаления контента", level="error")
            return
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено контента: {count}")


@admin.register(Testimonial, site=role_admin_site)
class TestimonialAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    min_view_role   = "manager"
    min_change_role = "manager"
    min_delete_role = "admin"
    min_add_role    = "manager"
    
    list_display  = ["author_name", "author_title", "rating", "is_active", "sort_order"]
    list_filter   = ["is_active", "rating"]
    list_editable = ["is_active", "sort_order"]
    search_fields = ["author_name", "text"]
    ordering = ["sort_order", "author_name"]
    
    actions = ["activate_testimonials", "deactivate_testimonials", "set_rating_5", "set_rating_4", "delete_selected"]
    
    @admin.action(description="Активировать выбранные отзывы")
    def activate_testimonials(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано отзывов: {updated}")
    
    @admin.action(description="Деактивировать выбранные отзывы")
    def deactivate_testimonials(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано отзывов: {updated}")
    
    @admin.action(description="Установить рейтинг 5 звезд")
    def set_rating_5(self, request, queryset):
        updated = queryset.update(rating=5)
        self.message_user(request, f"Установлен рейтинг 5 звезд для {updated} отзывов")
    
    @admin.action(description="Установить рейтинг 4 звезды")
    def set_rating_4(self, request, queryset):
        updated = queryset.update(rating=4)
        self.message_user(request, f"Установлен рейтинг 4 звезды для {updated} отзывов")
    
    @admin.action(description="Удалить выбранные отзывы")
    def delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Удалено отзывов: {count}")



@admin.register(AboutPage, site=role_admin_site)
class AboutPageAdmin(RoleRestrictedMixin, admin.ModelAdmin):
    """
    Админка для страницы «О нас» (singleton).
    Фото блоков выбираются из галереи гостиницы.
    """
    min_view_role   = "manager"
    min_change_role = "admin"
    min_delete_role = "super_admin"
    min_add_role    = "super_admin"

    list_display  = ["__str__", "is_active", "updated_at"]
    list_editable = ["is_active"]
    autocomplete_fields = [
        "about_gallery_photo",
        "rooms_gallery_photo",
        "services_gallery_photo",
        "contacts_gallery_photo",
    ]
    readonly_fields = [
        "about_gallery_preview",
        "rooms_gallery_preview",
        "services_gallery_preview",
        "contacts_gallery_preview",
    ]

    fieldsets = (
        ("Заголовок страницы", {
            "fields": ("hero_title", "hero_subtitle"),
        }),
        ("О нас — блок 1", {
            "fields": (
                "about_title",
                "about_text",
                "about_gallery_photo",
                "about_gallery_preview",
                "about_image",
            ),
            "description": (
                "Текст без звёздочек ** — они не отображаются на сайте. "
                "Фото: выберите из «Галерея гостиницы» или загрузите файл ниже."
            ),
        }),
        ("О нас — блок 2 (Номера)", {
            "fields": (
                "rooms_title",
                "rooms_text",
                "rooms_gallery_photo",
                "rooms_gallery_preview",
                "rooms_image",
            ),
        }),
        ("О нас — блок 3 (Сервис)", {
            "fields": (
                "services_title",
                "services_text",
                "services_gallery_photo",
                "services_gallery_preview",
                "services_image",
            ),
        }),
        ("О нас — блок 4 (Контакты)", {
            "fields": (
                "contacts_title",
                "contacts_text",
                "contacts_gallery_photo",
                "contacts_gallery_preview",
                "contacts_image",
            ),
        }),
        ("Статистика", {
            "fields": (
                ("stat1_number", "stat1_label"),
                ("stat2_number", "stat2_label"),
                ("stat3_number", "stat3_label"),
                ("stat4_number", "stat4_label"),
            ),
            "description": "Цифры под заголовком страницы",
        }),
        ("Настройки", {
            "fields": ("is_active",),
        }),
    )

    @staticmethod
    def _gallery_preview(gallery_photo):
        if gallery_photo and gallery_photo.image:
            return format_html(
                '<img src="{}" alt="" style="max-height:140px;max-width:140px;'
                'object-fit:cover;border-radius:12px;border:1px solid rgba(0,0,0,.08);" />'
                '<p style="margin:.5rem 0 0;font-size:12px;color:#666;">{}</p>',
                gallery_photo.image.url,
                gallery_photo,
            )
        return format_html(
            '<span style="color:#999;">Фото не выбрано — на сайте будет заглушка</span>'
        )

    def about_gallery_preview(self, obj):
        return self._gallery_preview(obj.about_gallery_photo)
    about_gallery_preview.short_description = "Превью (галерея)"

    def rooms_gallery_preview(self, obj):
        return self._gallery_preview(obj.rooms_gallery_photo)
    rooms_gallery_preview.short_description = "Превью (галерея)"

    def services_gallery_preview(self, obj):
        return self._gallery_preview(obj.services_gallery_photo)
    services_gallery_preview.short_description = "Превью (галерея)"

    def contacts_gallery_preview(self, obj):
        return self._gallery_preview(obj.contacts_gallery_photo)
    contacts_gallery_preview.short_description = "Превью (галерея)"
    
    def has_add_permission(self, request):
        # Разрешаем создание только если записи нет
        return not AboutPage.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Запрещаем удаление (singleton)
        return False
