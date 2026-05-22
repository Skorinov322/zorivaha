"""
bookings/views.py

Guest views:
  BookingCreateView   — форма бронирования (только авторизованные)
  BookingDetailView   — детали своей брони
  BookingSuccessView  — страница успеха после создания
  BookingCancelView   — отмена своей брони

Staff views:
  BookingListStaffView    — список всех броней с фильтром
  BookingDetailStaffView  — детали любой брони
  BookingConfirmView      — подтвердить бронь
  BookingCheckInView      — заселить гостя
  BookingCheckOutView     — выселить гостя
  BookingNoShowView       — отметить незаезд
  BookingCancelStaffView  — отменить бронь (staff)
  BookingUndoCheckInView  — отменить заселение
  BookingUndoCheckOutView — отменить выселение
  BookingCreateStaffView  — создать бронь вручную
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, TemplateView

from apps.core.permissions import ManagerRequiredMixin, ReceptionistRequiredMixin
from .forms import BookingCreateForm, BookingCancelForm, BookingStaffForm, BookingFilterForm
from .models import Booking, BookingStatus
from .selectors import (
    get_booking_by_id,
    get_booking_for_guest,
    get_guest_bookings,
    get_bookings_filtered,
)
from .services import (
    create_booking,
    create_booking_group,
    confirm_booking,
    cancel_booking,
    perform_check_in,
    perform_check_out,
    perform_no_show,
    BookingUnavailableError,
    BookingStateError,
)

logger = logging.getLogger(__name__)


# ===========================================================================
# GUEST VIEWS
# ===========================================================================

class BookingCreateView(LoginRequiredMixin, View):
    """
    Full booking form — only for authenticated users.
    Pre-fills contact fields from the user's profile.
    """
    template_name = "bookings/create.html"
    login_url     = "/auth/login/"

    def get(self, request):
        category_id = request.GET.get("category")
        form = BookingCreateForm(user=request.user, category_id=category_id)
        return render(request, self.template_name, {
            "form": form,
            "category_id": category_id,
        })

    def post(self, request):
        form = BookingCreateForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        d = form.cleaned_data
        from apps.accounts.services import update_user_profile_snapshot
        update_user_profile_snapshot(
            request.user,
            {
                "first_name": d["guest_first_name"],
                "last_name": d["guest_last_name"],
                "patronymic": d.get("guest_patronymic", ""),
                "phone": d["guest_phone"],
            },
            overwrite=True,
        )
        
        # Handle organization creation
        organization = None
        if d.get("client_type") == "organization":
            if d.get("create_new_organization"):
                # Create new organization (pending approval)
                from apps.crm.models import Organization
                organization = Organization.objects.create(
                    name=d["new_org_name"],
                    inn=d["new_org_inn"],
                    kpp=d.get("new_org_kpp", ""),
                    legal_address=d["new_org_legal_address"],
                    phone=d.get("new_org_phone", ""),
                    email=d.get("new_org_email", ""),
                    contact_person=d["new_org_contact_person"],
                    is_approved=False,  # Requires admin approval
                    created_by_user=request.user,
                )
                messages.info(request, 
                    _("Организация «{}» создана и отправлена на модерацию администратору.").format(organization.name)
                )
            else:
                organization = d.get("organization")
        
        total_persons = d["adults"] + d.get("children", 0)
        category = d["room_category"]
        needs_group = total_persons > category.max_guests

        try:
            if needs_group:
                bookings = create_booking_group(
                    guest=request.user,
                    room_category=category,
                    check_in=d["check_in"],
                    check_out=d["check_out"],
                    guest_first_name=d["guest_first_name"],
                    guest_last_name=d["guest_last_name"],
                    guest_patronymic=d.get("guest_patronymic", ""),
                    guest_phone=d["guest_phone"],
                    guest_email=d["guest_email"],
                    adults=d["adults"],
                    children=d.get("children", 0),
                    early_check_in=d.get("early_check_in", False),
                    organization=organization,
                    special_requests=d.get("special_requests", ""),
                    arrival_time=d.get("arrival_time"),
                    source="website",
                    accommodation_policy_agreed=d.get("accommodation_policy_agreed", False),
                )
            else:
                booking = create_booking(
                    guest=request.user,
                    room_category=category,
                    check_in=d["check_in"],
                    check_out=d["check_out"],
                    guest_first_name=d["guest_first_name"],
                    guest_last_name=d["guest_last_name"],
                    guest_patronymic=d.get("guest_patronymic", ""),
                    guest_phone=d["guest_phone"],
                    guest_email=d["guest_email"],
                    adults=d["adults"],
                    children=d.get("children", 0),
                    occupancy_type=d.get("occupancy_type", "solo"),
                    early_check_in=d.get("early_check_in", False),
                    room=None,
                    organization=organization,
                    special_requests=d.get("special_requests", ""),
                    arrival_time=d.get("arrival_time"),
                    source="website",
                    accommodation_policy_agreed=d.get("accommodation_policy_agreed", False),
                )
        except BookingUnavailableError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {
                "form": form,
                "alternatives": e.alternatives,
                "contact_phone": e.contact_phone,
            }, status=400)

        if needs_group:
            logger.info(
                "Group booking created: group_id=%s (%d rooms) by user %s",
                bookings[0].group_id, len(bookings), request.user.email,
            )
            messages.success(request, f"Групповая бронь на {len(bookings)} номера создана. Ожидайте подтверждения.")
            return redirect("bookings:group_success", group_id=str(bookings[0].group_id))
        else:
            logger.info("Booking created: %s by user %s", booking.confirmation_number, request.user.email)
            messages.success(request, f"Бронь #{booking.confirmation_number} создана. Ожидайте подтверждения.")
            return redirect("bookings:success", pk=booking.pk)


class BookingDetailView(LoginRequiredMixin, DetailView):
    """Guest's own booking detail."""
    template_name       = "bookings/detail.html"
    context_object_name = "booking"
    login_url           = "/auth/login/"

    def get_object(self, queryset=None):
        return get_booking_for_guest(self.kwargs["pk"], self.request.user)


class BookingSuccessView(LoginRequiredMixin, DetailView):
    """Shown once after successful booking creation."""
    template_name       = "bookings/success.html"
    context_object_name = "booking"
    login_url           = "/auth/login/"

    def get_object(self, queryset=None):
        return get_booking_for_guest(self.kwargs["pk"], self.request.user)


class BookingGroupSuccessView(LoginRequiredMixin, View):
    """Страница успеха для групповой брони."""
    template_name = "bookings/group_success.html"
    login_url = "/auth/login/"

    def get(self, request, group_id):
        from django.http import Http404
        bookings = Booking.objects.filter(
            group_id=group_id, guest=request.user
        ).select_related("room_category").order_by("created_at")

        if not bookings.exists():
            raise Http404

        total_price = sum(b.total_price for b in bookings)
        return render(request, self.template_name, {
            "bookings": bookings,
            "total_price": total_price,
            "group_id": group_id,
        })


class BookingCancelView(LoginRequiredMixin, View):
    """Guest cancels their own booking."""
    template_name = "bookings/cancel_confirm.html"
    login_url     = "/auth/login/"

    def _get_booking(self, pk, user):
        return get_booking_for_guest(pk, user)

    def get(self, request, pk):
        booking = self._get_booking(pk, request.user)
        if not booking.can_be_cancelled:
            messages.error(request, "Эту бронь нельзя отменить.")
            return redirect("bookings:detail", pk=pk)
        return render(request, self.template_name, {
            "booking": booking,
            "form":    BookingCancelForm(),
        })

    def post(self, request, pk):
        booking = self._get_booking(pk, request.user)
        form = BookingCancelForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"booking": booking, "form": form})
        try:
            booking = cancel_booking(
                booking_id=pk,
                reason=form.cleaned_data.get("reason", ""),
                actor=request.user,
            )
            messages.info(request, f"Бронь #{booking.confirmation_number} отменена.")
        except BookingStateError as e:
            messages.error(request, str(e))
        return redirect("accounts:my_bookings")


# ===========================================================================
# STAFF VIEWS
# ===========================================================================

class BookingListStaffView(ReceptionistRequiredMixin, View):
    """Staff: filterable list of all bookings."""
    template_name = "bookings/staff/list.html"

    def get(self, request):
        filter_form = BookingFilterForm(request.GET or None)
        bookings = get_bookings_filtered(
            search=request.GET.get("q", ""),
            status=request.GET.get("status", ""),
            check_in_from=_parse_date(request.GET.get("check_in_from")),
            check_in_to=_parse_date(request.GET.get("check_in_to")),
            category_id=request.GET.get("category") or None,
        )
        return render(request, self.template_name, {
            "bookings":    bookings,
            "filter_form": filter_form,
            "status_choices": BookingStatus.choices,
            "total": bookings.count(),
        })


class BookingDetailStaffView(ReceptionistRequiredMixin, View):
    """Staff: full booking detail with action buttons."""
    template_name = "bookings/staff/detail.html"

    def get(self, request, pk):
        booking = get_booking_by_id(pk)
        
        # Get available rooms for check-in if booking is confirmed
        available_rooms = []
        if booking.status == 'confirmed':
            from apps.hotel.selectors import get_available_rooms_for_category
            available_rooms = get_available_rooms_for_category(
                booking.room_category_id, 
                booking.check_in, 
                booking.check_out
            )
            # Add current occupancy info
            for room in available_rooms:
                room.current_occupancy = room.get_current_occupancy_count()
        
        return render(request, self.template_name, {
            "booking": booking,
            "available_rooms": available_rooms
        })


class BookingConfirmView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        try:
            booking = confirm_booking(pk, actor=request.user)
            messages.success(request, f"Бронь #{booking.confirmation_number} подтверждена.")
        except (ValueError, BookingStateError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class BookingCheckInView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        room_id = request.POST.get('room_id')
        try:
            booking = perform_check_in(pk, room_id=room_id, actor=request.user)
            messages.success(request, f"Гость заселён в номер {booking.room.full_number}.")
        except (BookingUnavailableError, BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class BookingCheckOutView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        try:
            booking = perform_check_out(pk, actor=request.user)
            messages.success(request, f"Гость выселен. Бронь #{booking.confirmation_number} завершена.")
        except (BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class BookingNoShowView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        try:
            booking = perform_no_show(pk, actor=request.user)
            messages.warning(request, f"Бронь #{booking.confirmation_number} отмечена как незаезд.")
        except (BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class BookingCancelStaffView(ReceptionistRequiredMixin, View):
    def post(self, request, pk):
        reason = request.POST.get("reason", "Отменено сотрудником.")
        try:
            booking = cancel_booking(pk, reason=reason, actor=request.user)
            messages.info(request, f"Бронь #{booking.confirmation_number} отменена.")
        except (BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_list")


class BookingUndoCheckInView(ReceptionistRequiredMixin, View):
    """Отменить заселение: checked_in → confirmed."""
    def post(self, request, pk):
        from .services import undo_check_in
        try:
            booking = undo_check_in(pk, actor=request.user)
            messages.success(request, f"Заселение отменено. Бронь #{booking.confirmation_number} возвращена в статус «Подтверждена».")
        except (BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class BookingUndoCheckOutView(ReceptionistRequiredMixin, View):
    """Отменить выселение: checked_out → checked_in."""
    def post(self, request, pk):
        from .services import undo_check_out
        try:
            booking = undo_check_out(pk, actor=request.user)
            messages.success(request, f"Выселение отменено. Гость возвращён в номер.")
        except (BookingStateError, ValueError) as e:
            messages.error(request, str(e))
        return redirect("bookings:staff_detail", pk=pk)


class BookingCreateStaffView(ReceptionistRequiredMixin, View):
    """Staff: manually create a booking for any guest."""
    template_name = "bookings/staff/create.html"

    def get(self, request):
        return render(request, self.template_name, {"form": BookingStaffForm()})

    def post(self, request):
        form = BookingStaffForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        d = form.cleaned_data
        # Staff bookings are linked to the currently logged-in user as guest
        # unless a guest lookup is implemented — use request.user as fallback
        try:
            # Calculate discount from percent if apply_discount is checked
            from decimal import Decimal
            discount_amount = d.get("discount_amount") or Decimal("0")
            discount_reason = d.get("discount_reason", "")
            if d.get("apply_discount") and d.get("discount_percent"):
                # We'll calculate the actual amount after price calculation in create_booking
                # Pass percent as a special marker via discount_reason for now,
                # actual calculation happens in service
                discount_reason = discount_reason or "Скидка администратора"

            booking = create_booking(
                guest=request.user,
                room_category=d["room_category"],
                check_in=d["check_in"],
                check_out=d["check_out"],
                guest_first_name=d["guest_first_name"],
                guest_last_name=d["guest_last_name"],
                guest_patronymic=d.get("guest_patronymic", ""),
                guest_phone=d["guest_phone"],
                guest_email=d["guest_email"],
                adults=d["adults"],
                children=d.get("children", 0),
                occupancy_type=d.get("occupancy_type", "solo"),
                room=d.get("room"),
                organization=d.get("organization"),
                special_requests=d.get("special_requests", ""),
                arrival_time=d.get("arrival_time"),
                early_check_in=d.get("early_check_in", False),
                source=d.get("source", "walk_in"),
                internal_notes=d.get("internal_notes", ""),
                discount_amount=discount_amount,
                discount_reason=discount_reason,
                discount_percent=d.get("discount_percent") if d.get("apply_discount") else None,
                created_by=request.user,
            )
            messages.success(request, f"Бронь #{booking.confirmation_number} создана.")
            return redirect("bookings:staff_detail", pk=booking.pk)
        except BookingUnavailableError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {"form": form}, status=400)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value):
    if not value:
        return None
    try:
        from datetime import date
        return date.fromisoformat(value)
    except ValueError:
        return None
