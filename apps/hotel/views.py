"""
hotel/views.py

Public views:
  IndexView               — главная страница
  RoomListView            — каталог номеров с фильтром доступности
  RoomCategoryDetailView  — карточка категории номера

Staff views (CRUD):
  CategoryListView        — список категорий (staff)
  CategoryCreateView      — создать категорию
  CategoryUpdateView      — редактировать категорию
  CategoryDeleteView      — удалить категорию
  CategoryVisibilityView  — скрыть / показать категорию
  CategoryImageUploadView — загрузить фото
  CategoryImageDeleteView — удалить фото

  RoomListStaffView       — список физических номеров (staff)
  RoomCreateView          — создать номер
  RoomUpdateView          — редактировать номер
  RoomDeleteView          — удалить номер
  RoomStatusUpdateView    — быстрая смена статуса (AJAX-friendly POST)
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, FormView

from apps.bookings.models import BookingStatus
from apps.core.permissions import AdminRequiredMixin, ManagerRequiredMixin, ReceptionistRequiredMixin
from apps.reviews.forms import ReviewForm
from .forms import (
    AvailabilitySearchForm,
    ContactForm,
    RoomCategoryForm,
    RoomForm,
    RoomImageForm,
    RoomStatusForm,
)
from .models import RoomCategory, Room, RoomImage
from .selectors import (
    get_active_room_categories,
    get_available_categories,
    count_available_rooms_for_category,
    get_featured_room_categories,
    get_room_category_by_slug,
    get_all_room_categories_for_staff,
    get_room_category_for_edit,
    get_all_rooms_for_staff,
    get_room_for_edit,
    get_room_stats,
)
from .services import (
    create_room_category,
    update_room_category,
    delete_room_category,
    set_room_category_visibility,
    create_room,
    update_room,
    update_room_status,
    delete_room,
    add_room_image,
    delete_room_image,
)


# ===========================================================================
# PUBLIC VIEWS
# ===========================================================================

class IndexView(TemplateView):
    template_name = "hotel/index.html"

    def get_context_data(self, **kwargs):
        from apps.content.models import AboutPage
        from apps.reviews.models import Review, ReviewStatus

        ctx = super().get_context_data(**kwargs)
        ctx["about_page"]     = AboutPage.get_instance()
        ctx["search_form"]    = AvailabilitySearchForm()
        ctx["featured_rooms"] = get_featured_room_categories(limit=3)
        ctx["published_reviews"] = (
            Review.objects
            .filter(status=ReviewStatus.APPROVED)
            .select_related("author", "room_category")
            .order_by("-published_at", "-created_at")[:12]
        )
        ctx["features"] = [
            ("bi-wifi",          "Бесплатный Wi-Fi",    "Высокоскоростной интернет во всех номерах"),
            ("bi-cup-hot",       "Комфортный сервис",   "Внимаостиницаный персонал и уют на каждом шагу"),
            ("bi-stars",         "Уборка номеров",      "Регулярная уборка и свежее бельё"),
            ("bi-geo-alt",       "Центр населённого пункта", "В шаговой доступности от магазинов и инфраструктуры"),
        ]

        if self.request.user.is_authenticated:
            completed_categories = RoomCategory.objects.filter(
                bookings__guest=self.request.user,
                bookings__status=BookingStatus.CHECKED_OUT,
            ).distinct().order_by("name")
            from apps.reviews.models import Review
            ctx["user_review"] = (
                Review.objects
                .filter(author=self.request.user)
                .select_related("room_category")
                .first()
            )
            ctx["review_form"] = ReviewForm(available_categories=completed_categories) if not ctx["user_review"] else None
            ctx["review_categories"] = completed_categories
        else:
            ctx["review_form"] = None
            ctx["review_categories"] = RoomCategory.objects.none()
            ctx["user_review"] = None

        return ctx

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        from apps.reviews.models import Review
        if Review.objects.filter(author=request.user).exists():
            messages.info(request, "Вы уже оставили отзыв. Один аккаунт может оставить только один отзыв.")
            return redirect("hotel:index")

        completed_categories = RoomCategory.objects.filter(
            bookings__guest=request.user,
            bookings__status=BookingStatus.CHECKED_OUT,
        ).distinct().order_by("name")
        form = ReviewForm(request.POST, available_categories=completed_categories)

        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            review.guest_name = request.user.get_full_name() or request.user.email
            review.ip_address = self.request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0] if self.request.META.get("HTTP_X_FORWARDED_FOR") else self.request.META.get("REMOTE_ADDR")
            review.user_agent = self.request.META.get("HTTP_USER_AGENT", "")[:500]
            review.save()

            messages.success(
                request,
                "Спасибо за отзыв! Он будет опубликован после модерации."
            )
            return redirect("hotel:index")

        ctx = self.get_context_data(**kwargs)
        ctx["review_form"] = form
        return render(request, self.template_name, ctx)


class RoomListView(ListView):
    """
    Public room catalog.
    When search params are valid, availability badges are calculated from
    overlapping bookings for the selected dates.
    """
    template_name        = "hotel/room_list.html"
    context_object_name  = "categories"

    def get_queryset(self):
        self._search_form = AvailabilitySearchForm(self.request.GET or None)
        return get_active_room_categories()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self._search_form
        ctx["is_filtered"] = self._search_form.is_valid()

        if self._search_form.is_valid():
            d = self._search_form.cleaned_data
            categories = list(ctx["categories"])
            for cat in categories:
                cat.available_rooms_for_dates = count_available_rooms_for_category(
                    cat.pk,
                    d["check_in"],
                    d["check_out"],
                    d["guests"],
                )
            ctx["categories"] = categories

        return ctx


class RoomCategoryDetailView(DetailView):
    """Public room category detail page with gallery, amenities, reviews."""
    template_name       = "hotel/room_detail.html"
    context_object_name = "category"

    def get_object(self, queryset=None):
        return get_room_category_by_slug(self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["booking_form"] = AvailabilitySearchForm()
        ctx["gallery"]      = self.object.images.all()
        return ctx


class GalleryView(TemplateView):
    """Public hotel gallery page, grouped by section."""
    template_name = "hotel/gallery.html"

    def get_context_data(self, **kwargs):
        from apps.content.models import HotelGallery
        ctx = super().get_context_data(**kwargs)

        section_filter = self.request.GET.get("section", "")
        qs = HotelGallery.objects.filter(is_active=True)
        if section_filter:
            qs = qs.filter(section=section_filter)

        # Group photos by section for tab display
        sections = {}
        for photo in qs.order_by("section", "sort_order"):
            label = photo.get_section_display()
            sections.setdefault(photo.section, {"label": label, "photos": []})
            sections[photo.section]["photos"].append(photo)

        ctx["sections"]        = sections
        ctx["all_photos"]      = qs
        ctx["section_choices"] = HotelGallery.GallerySection.choices
        ctx["active_section"]  = section_filter
        return ctx


class AboutView(TemplateView):
    template_name = "hotel/about.html"

    def get_context_data(self, **kwargs):
        from apps.content.models import AboutPage
        ctx = super().get_context_data(**kwargs)
        ctx["about_page"] = (
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
        return ctx


class ContactsView(FormView):
    template_name = "hotel/contacts.html"
    form_class = ContactForm
    success_url = reverse_lazy('hotel:contacts')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        d = form.cleaned_data

        if self.request.user.is_authenticated:
            from apps.accounts.services import update_user_profile_snapshot
            name_parts = d.get("name", "").split()
            profile_data = {
                "phone": d.get("phone", ""),
            }
            if len(name_parts) >= 3:
                profile_data.update({
                    "last_name": name_parts[0],
                    "first_name": name_parts[1],
                    "patronymic": " ".join(name_parts[2:]),
                })
            elif len(name_parts) == 2:
                profile_data.update({
                    "last_name": name_parts[0],
                    "first_name": name_parts[1],
                })
            elif len(name_parts) == 1:
                profile_data["first_name"] = name_parts[0]

            update_user_profile_snapshot(
                self.request.user,
                profile_data,
                overwrite=False,
            )

        # Сохраняем сообщение в БД
        from apps.notifications.models import ContactMessage
        contact_msg = ContactMessage.objects.create(
            sender_user=self.request.user if self.request.user.is_authenticated else None,
            sender_name=d["name"],
            sender_email=d["email"],
            sender_phone=d.get("phone", ""),
            subject=d.get("subject", ""),
            message=d["message"],
        )

        # Отправляем email с обратной связью
        try:
            self._send_contact_email(d)
            messages.success(
                self.request,
                "Спасибо за ваше сообщение! Мы ответим в ближайшее время."
            )
        except Exception:
            messages.error(
                self.request,
                "Произошла ошибка при отправке сообщения. Попробуйте позже или свяжитесь с нами по телефону."
            )

        # Уведомляем персонал через in-app уведомления
        try:
            from apps.notifications.models import notify_staff_contact_form
            notify_staff_contact_form(
                name=d["name"],
                email=d["email"],
                phone=d.get("phone", ""),
                subject=d.get("subject", ""),
                message=d["message"],
                contact_message_id=contact_msg.pk,
            )
        except Exception:
            pass

        return super().form_valid(form)
    
    def _send_contact_email(self, data):
        """Отправка email с обратной связью"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f"Обратная связь с сайта: {data.get('subject', 'Без темы')}"
        
        message = f"""
Новое сообщение с сайта гостиницы "Зори Ваха"

Имя: {data['name']}
Email: {data['email']}
Телефон: {data.get('phone', 'Не указан')}
Тема: {data.get('subject', 'Без темы')}

Сообщение:
{data['message']}

---
Отправлено с сайта {self.request.get_host()}
        """.strip()
        
        # Отправляем на email администратора
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_EMAIL],
            fail_silently=False,
        )
        
        # Отправляем подтверждение пользователю
        confirmation_subject = "Ваше сообщение получено - Зори Ваха"
        confirmation_message = f"""
Здравствуйте, {data['name']}!

Спасибо за ваше обращение. Мы получили ваше сообщение и ответим в ближайшее время.

Ваше сообщение:
Тема: {data.get('subject', 'Без темы')}
{data['message']}

С уважением,
Команда гостиницы "Зори Ваха"

Телефон: {settings.CONTACT_PHONE}
Email: {settings.CONTACT_EMAIL}
        """.strip()
        
        send_mail(
            subject=confirmation_subject,
            message=confirmation_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[data['email']],
            fail_silently=True,  # Не падаем если не удалось отправить подтверждение
        )


# ===========================================================================
# STAFF: CATEGORY CRUD
# ===========================================================================

class CategoryListView(ReceptionistRequiredMixin, TemplateView):
    """Staff: list all room categories with stats."""
    template_name = "hotel/staff/category_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = get_all_room_categories_for_staff()
        ctx["room_stats"] = get_room_stats()
        return ctx


class CategoryCreateView(AdminRequiredMixin, View):
    template_name = "hotel/staff/category_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form":  RoomCategoryForm(),
            "title": "Новая категория",
            "is_create": True,
        })

    def post(self, request):
        form = RoomCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = create_room_category(form.cleaned_data.copy(), actor=request.user)
            messages.success(request, f"Категория «{category.name}» создана.")
            return redirect("hotel:staff_category_list")
        return render(request, self.template_name, {
            "form":  form,
            "title": "Новая категория",
            "is_create": True,
        })


class CategoryUpdateView(AdminRequiredMixin, View):
    template_name = "hotel/staff/category_form.html"

    def get(self, request, pk):
        category = get_room_category_for_edit(pk)
        return render(request, self.template_name, {
            "form":     RoomCategoryForm(instance=category),
            "category": category,
            "title":    f"Редактировать: {category.name}",
            "is_create": False,
        })

    def post(self, request, pk):
        category = get_room_category_for_edit(pk)
        form = RoomCategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            update_room_category(category, form.cleaned_data.copy(), actor=request.user)
            messages.success(request, f"Категория «{category.name}» обновлена.")
            return redirect("hotel:staff_category_list")
        return render(request, self.template_name, {
            "form":     form,
            "category": category,
            "title":    f"Редактировать: {category.name}",
            "is_create": False,
        })


class CategoryDeleteView(AdminRequiredMixin, View):
    """Permanently delete a category."""

    def post(self, request, pk):
        category = get_room_category_for_edit(pk)
        name = category.name
        try:
            delete_room_category(category)
            messages.success(request, f"Категория «{name}» удалена.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("hotel:staff_category_list")


class CategoryVisibilityView(AdminRequiredMixin, View):
    """Show or hide a category on the public site."""

    def post(self, request, pk):
        category = get_room_category_for_edit(pk)
        action = request.POST.get("action")
        if action == "show":
            set_room_category_visibility(category, is_active=True)
            messages.success(request, f"Категория «{category.name}» снова отображается на сайте.")
        elif action == "hide":
            set_room_category_visibility(category, is_active=False)
            messages.info(request, f"Категория «{category.name}» скрыта с сайта.")
        else:
            messages.error(request, "Неподдерживаемое действие.")
        return redirect("hotel:staff_category_list")


class CategoryImageUploadView(AdminRequiredMixin, View):
    """Upload photos for a room category."""
    template_name = "hotel/staff/category_images.html"

    def get(self, request, pk):
        category = get_room_category_for_edit(pk)
        return render(request, self.template_name, {
            "category": category,
            "images":   category.images.all(),
            "form":     RoomImageForm(),
        })

    def post(self, request, pk):
        from apps.core.media import media_upload_error_message

        category = get_room_category_for_edit(pk)
        form = RoomImageForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            try:
                add_room_image(
                    category=category,
                    image_file=d["image"],
                    caption=d.get("caption", ""),
                    alt_text=d.get("alt_text", ""),
                    is_primary=d.get("is_primary", False),
                    sort_order=d.get("sort_order", 0),
                )
            except Exception as exc:
                messages.error(request, media_upload_error_message(exc))
                return render(request, self.template_name, {
                    "category": category,
                    "images":   category.images.all(),
                    "form":     form,
                })
            messages.success(request, "Фото добавлено.")
            return redirect("hotel:staff_category_images", pk=pk)
        return render(request, self.template_name, {
            "category": category,
            "images":   category.images.all(),
            "form":     form,
        })


class CategoryImageDeleteView(AdminRequiredMixin, View):
    """Delete a single image."""

    def post(self, request, pk, image_pk):
        image = get_object_or_404(RoomImage, pk=image_pk, category_id=pk)
        delete_room_image(image)
        messages.success(request, "Фото удалено.")
        return redirect("hotel:staff_category_images", pk=pk)


# ===========================================================================
# STAFF: ROOM CRUD
# ===========================================================================

class RoomListStaffView(ReceptionistRequiredMixin, TemplateView):
    """Staff: list all physical rooms with filters."""
    template_name = "hotel/staff/room_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["rooms"] = get_all_rooms_for_staff(
            category_id=self.request.GET.get("category") or None,
            status=self.request.GET.get("status") or None,
            floor=self.request.GET.get("floor") or None,
            search=self.request.GET.get("q", ""),
        )
        ctx["categories"]    = RoomCategory.objects.filter(is_active=True).order_by("sort_order")
        ctx["status_choices"] = Room.RoomStatus.choices
        ctx["stats"]         = get_room_stats()
        ctx["filters"] = {
            "category": self.request.GET.get("category", ""),
            "status":   self.request.GET.get("status", ""),
            "floor":    self.request.GET.get("floor", ""),
            "q":        self.request.GET.get("q", ""),
        }
        return ctx


class RoomCreateView(AdminRequiredMixin, View):
    template_name = "hotel/staff/room_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form":  RoomForm(),
            "title": "Новый номер",
            "is_create": True,
        })

    def post(self, request):
        form = RoomForm(request.POST)
        if form.is_valid():
            room = create_room(form.cleaned_data.copy(), actor=request.user)
            messages.success(request, f"Номер {room.number} создан.")
            return redirect("hotel:staff_room_list")
        return render(request, self.template_name, {
            "form":  form,
            "title": "Новый номер",
            "is_create": True,
        })


class RoomUpdateView(AdminRequiredMixin, View):
    template_name = "hotel/staff/room_form.html"

    def get(self, request, pk):
        room = get_room_for_edit(pk)
        return render(request, self.template_name, {
            "form":  RoomForm(instance=room),
            "room":  room,
            "title": f"Номер {room.number}",
            "is_create": False,
        })

    def post(self, request, pk):
        room = get_room_for_edit(pk)
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            update_room(room, form.cleaned_data.copy(), actor=request.user)
            messages.success(request, f"Номер {room.number} обновлён.")
            return redirect("hotel:staff_room_list")
        return render(request, self.template_name, {
            "form":  form,
            "room":  room,
            "title": f"Номер {room.number}",
            "is_create": False,
        })


class RoomDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        room = get_room_for_edit(pk)
        number = room.number
        try:
            delete_room(room)
            messages.success(request, f"Номер {number} удалён.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("hotel:staff_room_list")


class RoomStatusUpdateView(ReceptionistRequiredMixin, View):
    """Quick status change — POST from the room list table."""

    def post(self, request, pk):
        room = get_room_for_edit(pk)
        form = RoomStatusForm(request.POST, instance=room)
        if form.is_valid():
            update_room_status(room, form.cleaned_data["status"], actor=request.user)
            messages.success(
                request,
                f"Статус номера {room.number} изменён на «{room.get_status_display()}»."
            )
        else:
            messages.error(request, "Некорректный статус.")
        return redirect("hotel:staff_room_list")
