"""
apps/dashboard/views.py — Admin dashboard views.
"""

import json
from decimal import Decimal
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView

from apps.core.permissions import (
    ManagerRequiredMixin,
    ReceptionistRequiredMixin,
    AdminRequiredMixin,
    SuperAdminRequiredMixin,
)
from apps.bookings.selectors import get_today_arrivals, get_today_departures
from apps.bookings.services import (
    confirm_booking, perform_check_in, perform_check_out,
    BookingUnavailableError, BookingStateError,
)
from apps.bookings.models import BookingStatus
from .selectors import (
    get_dashboard_metrics,
    get_revenue_chart_data,
    get_occupancy_calendar,
    get_booking_status_breakdown,
    get_room_status_grid,
    get_recent_activity,
    get_unread_messages,
    get_recent_messages,
    get_all_bookings_for_management,
)

# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------

class DashboardView(ReceptionistRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        today = timezone.localdate()
        chart = get_revenue_chart_data()

        metrics = get_dashboard_metrics()
        breakdown = get_booking_status_breakdown()
        user = self.request.user
        show_analytics = (
            user.is_manager or user.is_admin or user.is_super_admin or user.is_superuser
        )

        ctx.update({
            "metrics":          metrics,
            "today_arrivals":   get_today_arrivals(),
            "today_departures": get_today_departures(),
            "recent_activity":  get_recent_activity(limit=12),
            "status_breakdown": breakdown,
            "unread_messages":  get_unread_messages(self.request.user),
            "recent_messages":  get_recent_messages(self.request.user),
            "today":            today,
            "show_analytics":   show_analytics,
            "room_bars": [
                ("available",   metrics["rooms"]["available"],   "#28a745", "Свободных"),
                ("occupied",    metrics["rooms"]["occupied"],    "#6ea8fe", "Занятых"),
                ("cleaning",    metrics["rooms"]["cleaning"],    "#ffc107", "Уборка"),
                ("maintenance", metrics["rooms"]["maintenance"], "#dc3545", "Обслуживание"),
            ] if show_analytics else [],

            # Chart.js data — serialised to JSON for the template
            "chart_labels":   json.dumps(chart["labels"], cls=DjangoJSONEncoder),
            "chart_revenues": json.dumps(chart["revenues"], cls=DjangoJSONEncoder),
            "chart_counts":   json.dumps(chart["counts"], cls=DjangoJSONEncoder),

            # Donut chart
            "donut_labels": json.dumps([s["label"] for s in breakdown], cls=DjangoJSONEncoder),
            "donut_data":   json.dumps([s["count"] for s in breakdown], cls=DjangoJSONEncoder),
            "donut_colors": json.dumps([s["color"]  for s in breakdown], cls=DjangoJSONEncoder),

            "quick_nav": [
                ("Брони",       "/bookings/staff/",          "bi-calendar-check",  "#6ea8fe"),
                ("Новая бронь", "/bookings/staff/create/",   "bi-plus-circle",     "#28a745"),
                ("Номера",      "/rooms/manage/rooms/",      "bi-building",        "var(--gold)"),
                ("Галерея",     "/dashboard/gallery/",       "bi-images",          "#d9376e"),
                ("Отчёты",      "/reports/",                 "bi-bar-chart",       "#ffc107"),
                ("Пользователи","/cabinet/users/",           "bi-person-gear",     "#adb5bd"),
            ],
        })
        return ctx


# ---------------------------------------------------------------------------
# Occupancy calendar
# ---------------------------------------------------------------------------

class OccupancyCalendarView(ReceptionistRequiredMixin, TemplateView):
    template_name = "dashboard/calendar.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()

        try:
            year  = int(self.request.GET.get("year",  today.year))
            month = int(self.request.GET.get("month", today.month))
        except ValueError:
            year, month = today.year, today.month

        # Clamp
        if month < 1:  month = 12; year -= 1
        if month > 12: month = 1;  year += 1

        import calendar
        month_name = calendar.month_name[month]
        _, days_in_month = calendar.monthrange(year, month)
        first_weekday = calendar.monthrange(year, month)[0]  # 0=Mon

        prev_month = month - 1 or 12
        prev_year  = year - (1 if month == 1 else 0)
        next_month = month % 12 + 1
        next_year  = year + (1 if month == 12 else 0)

        ctx.update({
            "calendar_days": get_occupancy_calendar(year, month),
            "year":          year,
            "month":         month,
            "month_name":    month_name,
            "first_weekday": first_weekday,
            "days_in_month": days_in_month,
            "prev_year":     prev_year,
            "prev_month":    prev_month,
            "next_year":     next_year,
            "next_month":    next_month,
            "today":         today,
            "room_grid":     get_room_status_grid(),
            "weekdays":      ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "empty_cells":   range(first_weekday),
            "legend": [
                (0,  "Свободно",    "#6ea8fe"),
                (40, "40%+ занято", "#28a745"),
                (70, "70%+ занято", "#ffc107"),
                (90, "90%+ занято", "#dc3545"),
            ],
            "room_legend": [
                ("#28a745", "Свободен"),
                ("#6ea8fe", "Занят"),
                ("#ffc107", "Уборка"),
                ("#dc3545", "Обслуживание"),
                ("#6c757d", "Заблокирован"),
            ],
        })
        return ctx


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class StatisticsView(ManagerRequiredMixin, View):
    """Legacy URL — merged into the main dashboard."""

    def get(self, request):
        return redirect("dashboard:index")


# ---------------------------------------------------------------------------
# Booking management
# ---------------------------------------------------------------------------

class BookingManagementView(ReceptionistRequiredMixin, ListView):
    template_name       = "dashboard/bookings.html"
    context_object_name = "bookings"
    paginate_by         = 20

    def get_queryset(self):
        return get_all_bookings_for_management(
            status=self.request.GET.get("status", ""),
            search=self.request.GET.get("q", ""),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"]  = self.request.GET.get("status", "")
        ctx["search_query"]   = self.request.GET.get("q", "")
        ctx["status_choices"] = BookingStatus.choices
        return ctx

    def post(self, request, *args, **kwargs):
        booking_id = request.POST.get("booking_id")
        action     = request.POST.get("action")
        if action == "confirm" and booking_id:
            try:
                booking = confirm_booking(booking_id, actor=request.user)
                messages.success(request, f"Бронь #{booking.confirmation_number} подтверждена.")
            except Exception as e:
                messages.error(request, str(e))
        return redirect("dashboard:bookings")


# ---------------------------------------------------------------------------
# Check-in / Check-out
# ---------------------------------------------------------------------------

class CheckInView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        try:
            booking = perform_check_in(pk, actor=request.user)
            messages.success(request, f"Гость заселён в номер {booking.room.number}.")
        except (BookingUnavailableError, BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class CheckOutView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        try:
            booking = perform_check_out(pk, actor=request.user)
            messages.success(request, f"Гость выселен. Бронь #{booking.confirmation_number} закрыта.")
        except (BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


# ---------------------------------------------------------------------------
# Room management
# ---------------------------------------------------------------------------

class RoomManagementView(ReceptionistRequiredMixin, TemplateView):
    template_name = "dashboard/rooms.html"

    def get_context_data(self, **kwargs):
        from apps.hotel.models import Room
        ctx = super().get_context_data(**kwargs)
        ctx["rooms"]      = Room.objects.select_related("category").order_by("floor", "number")
        ctx["room_grid"]  = get_room_status_grid()
        return ctx


# ---------------------------------------------------------------------------
# Metrics (analytics)
# ---------------------------------------------------------------------------

class MetricsView(ManagerRequiredMixin, TemplateView):
    """
    Full analytics metrics page.
    Sections: visitors, bookings trend, conversion funnel,
              occupancy, popular rooms.
    """
    template_name = "dashboard/metrics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        from apps.analytics.selectors import (
            get_metrics_summary,
            get_visitor_stats,
            get_page_type_breakdown,
            get_conversion_funnel,
            get_occupancy_trend,
            get_occupancy_by_category,
            get_popular_room_categories,
            get_room_revenue_chart,
            get_bookings_trend,
        )

        # Period selector
        try:
            days = int(self.request.GET.get("days", 30))
            if days not in (7, 14, 30, 90):
                days = 30
        except ValueError:
            days = 30

        summary    = get_metrics_summary(days)
        visitors   = get_visitor_stats(days)
        bookings_t = get_bookings_trend(days)
        funnel     = get_conversion_funnel(days)
        occupancy  = get_occupancy_trend(days)
        room_rev   = get_room_revenue_chart()
        page_types = get_page_type_breakdown(days)

        ctx.update({
            "days":    days,
            "summary": summary,
            "funnel":  funnel,
            "popular_rooms":       get_popular_room_categories(),
            "occupancy_by_cat":    get_occupancy_by_category(),
            "page_types":          get_page_type_breakdown(days),
            "today":               timezone.localdate(),
            "period_choices": [
                (7,  "7 дней"),
                (14, "14 дней"),
                (30, "30 дней"),
                (90, "90 дней"),
            ],

            # Chart data — JSON
            "visitors_labels":     json.dumps(visitors["labels"], cls=DjangoJSONEncoder),
            "visitors_views":      json.dumps(visitors["views"], cls=DjangoJSONEncoder),
            "visitors_unique":     json.dumps(visitors["unique"], cls=DjangoJSONEncoder),

            "bookings_labels":     json.dumps(bookings_t["labels"], cls=DjangoJSONEncoder),
            "bookings_total":      json.dumps(bookings_t["total"], cls=DjangoJSONEncoder),
            "bookings_confirmed":  json.dumps(bookings_t["confirmed"], cls=DjangoJSONEncoder),
            "bookings_cancelled":  json.dumps(bookings_t["cancelled"], cls=DjangoJSONEncoder),

            "occupancy_labels":    json.dumps(occupancy["labels"], cls=DjangoJSONEncoder),
            "occupancy_data":      json.dumps(occupancy["occupancy"], cls=DjangoJSONEncoder),
            "avg_occupancy":       occupancy["avg_occupancy"],

            "room_rev_labels":     json.dumps(room_rev["labels"], cls=DjangoJSONEncoder),
            "room_rev_revenues":   json.dumps(room_rev["revenues"], cls=DjangoJSONEncoder),
            "room_rev_counts":     json.dumps(room_rev["counts"], cls=DjangoJSONEncoder),

            "page_type_labels":    json.dumps([p["label"] for p in page_types], cls=DjangoJSONEncoder),
            "page_type_data":      json.dumps([p["count"] for p in page_types], cls=DjangoJSONEncoder),
            "page_type_colors":    json.dumps([p["color"] for p in page_types], cls=DjangoJSONEncoder),

            "funnel_labels":       json.dumps([s["label"] for s in funnel["steps"]], cls=DjangoJSONEncoder),
            "funnel_values":       json.dumps([s["value"] for s in funnel["steps"]], cls=DjangoJSONEncoder),
            "funnel_colors":       json.dumps([s["color"] for s in funnel["steps"]], cls=DjangoJSONEncoder),
        })
        return ctx


# ---------------------------------------------------------------------------
# Gallery management
# ---------------------------------------------------------------------------

class GalleryManagementView(ReceptionistRequiredMixin, View):
    """
    Dashboard gallery management: list, upload, delete, reorder photos.
    """
    template_name = "dashboard/gallery.html"

    ABOUT_BLOCK_FIELDS = {
        "about": "about_gallery_photo",
        "rooms": "rooms_gallery_photo",
        "services": "services_gallery_photo",
        "contacts": "contacts_gallery_photo",
    }

    def _about_blocks_context(self, about_page):
        blocks = [
            ("about", "about_gallery_photo", about_page.about_title or "О нас"),
            ("rooms", "rooms_gallery_photo", about_page.rooms_title or "Номера"),
            (
                "services",
                "services_gallery_photo",
                about_page.services_title or "Сервис и инфраструктура",
            ),
            (
                "contacts",
                "contacts_gallery_photo",
                about_page.contacts_title or "Важная информация и контакты",
            ),
        ]
        result = []
        for key, field_name, label in blocks:
            photo = getattr(about_page, field_name, None)
            url = None
            if photo and photo.image:
                url = photo.image.url
            result.append({
                "key": key,
                "label": label,
                "photo": photo,
                "photo_url": url,
            })
        return result

    def get(self, request):
        from apps.content.models import AboutPage, HotelGallery

        section_filter = request.GET.get("section", "")
        qs = HotelGallery.objects.all()
        if section_filter:
            qs = qs.filter(section=section_filter)

        about_page = (
            AboutPage.objects.select_related(
                "about_gallery_photo",
                "rooms_gallery_photo",
                "services_gallery_photo",
                "contacts_gallery_photo",
            )
            .filter(pk=1)
            .first()
            or AboutPage.get_instance()
        )

        return render(request, self.template_name, {
            "photos":          qs.order_by("section", "sort_order"),
            "picker_photos":   HotelGallery.objects.all().order_by(
                "section", "sort_order"
            ),
            "section_choices": HotelGallery.GallerySection.choices,
            "active_section":  section_filter,
            "total_count":     HotelGallery.objects.count(),
            "active_count":    HotelGallery.objects.filter(is_active=True).count(),
            "about_page":      about_page,
            "about_blocks":    self._about_blocks_context(about_page),
        })

    def post(self, request):
        from apps.content.models import AboutPage, HotelGallery
        action = request.POST.get("action")

        if action in ("assign_about_photo", "clear_about_photo"):
            block = request.POST.get("block", "")
            photo_pk = request.POST.get("photo_pk", "").strip()
            field_name = self.ABOUT_BLOCK_FIELDS.get(block)
            if not field_name:
                messages.error(request, "Неизвестный блок страницы «О нас».")
                return redirect("dashboard:gallery")

            about_page = AboutPage.get_instance()
            if action == "clear_about_photo":
                setattr(about_page, field_name, None)
                about_page.save(update_fields=[field_name, "updated_at"])
                messages.success(request, "Фото для блока снято.")
                return redirect("dashboard:gallery")

            if not photo_pk:
                messages.error(request, "Выберите фото из списка.")
                return redirect("dashboard:gallery")

            photo = get_object_or_404(HotelGallery, pk=photo_pk)
            setattr(about_page, field_name, photo)
            if photo.section != HotelGallery.GallerySection.ABOUT:
                photo.section = HotelGallery.GallerySection.ABOUT
                photo.save(update_fields=["section", "updated_at"])
            block_label = block
            for b in self._about_blocks_context(about_page):
                if b["key"] == block:
                    block_label = b["label"]
                    break
            about_page.save(update_fields=[field_name, "updated_at"])
            messages.success(
                request,
                f"Фото назначено для блока «{block_label}» на странице «О нас».",
            )
            return redirect("dashboard:gallery")

        if action == "upload":
            from apps.core.media import media_upload_error_message

            images = request.FILES.getlist("images")
            section = request.POST.get("section", "other")
            title   = request.POST.get("title", "")
            is_featured = request.POST.get("is_featured") == "on"
            count = 0
            errors = 0
            for img in images:
                try:
                    HotelGallery.objects.create(
                        image=img,
                        section=section,
                        title=title,
                        alt_text=title,
                        is_featured=is_featured,
                        is_active=True,
                    )
                    count += 1
                except Exception as exc:
                    errors += 1
                    messages.error(request, media_upload_error_message(exc))
            if count:
                messages.success(request, f"Загружено фото: {count}.")
            elif not errors:
                messages.warning(request, "Файлы не выбраны.")

        elif action == "delete":
            pk = request.POST.get("pk")
            photo = get_object_or_404(HotelGallery, pk=pk)
            if photo.image:
                photo.image.delete(save=False)
            photo.delete()
            messages.success(request, "Фото удалено.")

        elif action == "toggle_active":
            pk = request.POST.get("pk")
            photo = get_object_or_404(HotelGallery, pk=pk)
            photo.is_active = not photo.is_active
            photo.save(update_fields=["is_active", "updated_at"])

        elif action == "toggle_featured":
            pk = request.POST.get("pk")
            photo = get_object_or_404(HotelGallery, pk=pk)
            photo.is_featured = not photo.is_featured
            photo.save(update_fields=["is_featured", "updated_at"])

        elif action == "update":
            pk      = request.POST.get("pk")
            photo   = get_object_or_404(HotelGallery, pk=pk)
            photo.title      = request.POST.get("title", photo.title)
            photo.alt_text   = request.POST.get("alt_text", photo.alt_text)
            photo.section    = request.POST.get("section", photo.section)
            photo.sort_order = int(request.POST.get("sort_order", photo.sort_order) or 0)
            photo.save(update_fields=["title", "alt_text", "section", "sort_order", "updated_at"])
            messages.success(request, "Фото обновлено.")

        return redirect(request.get_full_path())


# ---------------------------------------------------------------------------
# Review moderation
# ---------------------------------------------------------------------------

class ReviewModerationView(ReceptionistRequiredMixin, TemplateView):
    template_name = "dashboard/reviews.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.reviews.models import Review, ReviewStatus

        status = self.request.GET.get("status", "pending")
        reviews = Review.objects.select_related("author", "room_category", "moderated_by")

        if status == "approved":
            reviews = reviews.filter(status=ReviewStatus.APPROVED)
        elif status == "all":
            reviews = reviews.order_by("-created_at")
        else:
            reviews = reviews.filter(status=ReviewStatus.PENDING)

        ctx.update({
            "reviews": reviews.order_by("-created_at"),
            "review_status": status,
            "review_counts": {
                "pending": Review.objects.filter(status=ReviewStatus.PENDING).count(),
                "approved": Review.objects.filter(status=ReviewStatus.APPROVED).count(),
                "all": Review.objects.count(),
            },
        })
        return ctx

    def post(self, request, *args, **kwargs):
        from apps.reviews.models import Review, ReviewStatus

        pk = request.POST.get("pk")
        action = request.POST.get("action")
        review = get_object_or_404(Review, pk=pk)

        if action == "approve":
            review.approve(moderator=request.user)
            messages.success(request, "Отзыв одобрен.")
        elif action == "unapprove":
            review.status = ReviewStatus.PENDING
            review.moderated_by = None
            review.moderated_at = None
            review.published_at = None
            review.save(update_fields=["status", "moderated_by", "moderated_at", "published_at", "updated_at"])
            messages.success(request, "Отзыв снят с публикации.")
        else:
            messages.error(request, "Неподдерживаемое действие.")

        return redirect("dashboard:reviews")


# ---------------------------------------------------------------------------
# FAQ management
# ---------------------------------------------------------------------------

class FAQManagementView(SuperAdminRequiredMixin, TemplateView):
    template_name = "dashboard/faq.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.content.models import FAQ

        ctx["faqs"] = FAQ.objects.order_by("category", "sort_order")
        ctx["category_choices"] = FAQ.FAQCategory.choices
        return ctx

    def post(self, request, *args, **kwargs):
        from apps.content.models import FAQ

        action = request.POST.get("action")
        if action == "create":
            question = request.POST.get("question", "").strip()
            answer = request.POST.get("answer", "").strip()
            category = request.POST.get("category", FAQ.FAQCategory.GENERAL)
            is_active = request.POST.get("is_active") == "on"
            try:
                sort_order = int(request.POST.get("sort_order") or 0)
            except (TypeError, ValueError):
                sort_order = 0

            if not question or not answer:
                messages.error(request, "Вопрос и ответ обязаостиницаны для создания FAQ.")
            else:
                FAQ.objects.create(
                    question=question,
                    answer=answer,
                    category=category,
                    is_active=is_active,
                    sort_order=sort_order,
                )
                messages.success(request, "FAQ создан.")

        elif action in {"save", "delete"}:
            faq = get_object_or_404(FAQ, pk=request.POST.get("faq_pk"))

            if action == "save":
                faq.question = request.POST.get("question", faq.question).strip()
                faq.answer = request.POST.get("answer", faq.answer).strip()
                faq.category = request.POST.get("category", faq.category)
                faq.is_active = request.POST.get("is_active") == "on"
                try:
                    faq.sort_order = int(request.POST.get("sort_order") or faq.sort_order)
                except (TypeError, ValueError):
                    pass
                faq.save()
                messages.success(request, "FAQ обновлён.")
            else:
                faq.delete()
                messages.success(request, "FAQ удалён.")

        else:
            messages.error(request, "Неподдерживаемое действие.")

        return redirect("dashboard:faq")


# ---------------------------------------------------------------------------
# About page content
# ---------------------------------------------------------------------------

class AboutContentView(AdminRequiredMixin, TemplateView):
    template_name = "dashboard/about_content.html"

    TEXT_FIELDS = [
        "hero_title",
        "hero_subtitle",
        "about_title",
        "about_text",
        "rooms_title",
        "rooms_text",
        "services_title",
        "services_text",
        "contacts_title",
        "contacts_text",
        "stat1_number",
        "stat1_label",
        "stat2_number",
        "stat2_label",
        "stat3_number",
        "stat3_label",
        "stat4_number",
        "stat4_label",
    ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.content.models import AboutPage
        ctx["about_page"] = AboutPage.get_instance()
        return ctx

    def post(self, request, *args, **kwargs):
        from apps.content.models import AboutPage
        about_page = AboutPage.get_instance()
        for field in self.TEXT_FIELDS:
            setattr(about_page, field, request.POST.get(field, ""))
        about_page.save(update_fields=[*self.TEXT_FIELDS, "updated_at"])
        messages.success(request, "Страница «О нас» обновлена.")
        return redirect("dashboard:about_content")


# ---------------------------------------------------------------------------
# Site content policies
# ---------------------------------------------------------------------------

class SiteContentPolicyView(AdminRequiredMixin, TemplateView):
    template_name = "dashboard/site_content.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.content.models import LegalPage

        ctx["legal_pages"] = list(LegalPage.objects.filter(is_active=True).order_by("page_type"))
        return ctx

    def post(self, request, *args, **kwargs):
        from apps.content.models import LegalPage

        action = request.POST.get("action", "")

        if action == "save_legal_pages":
            for page in LegalPage.objects.filter(is_active=True):
                title_field = f"title_{page.page_type}"
                content_field = f"content_{page.page_type}"
                
                if title_field in request.POST:
                    page.title = request.POST[title_field]
                if content_field in request.POST:
                    page.content = request.POST[content_field]
                page.save(update_fields=["title", "content", "updated_at"])

            messages.success(request, "Изменения сохранены.")
        else:
            messages.error(request, "Неподдерживаемое действие.")

        return redirect("dashboard:site_content")

# ---------------------------------------------------------------------------
# End of views
# ---------------------------------------------------------------------------
