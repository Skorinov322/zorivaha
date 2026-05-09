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
        try:
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
                children=d["children"],
                room=d.get("room"),
                organization=d.get("organization"),
                special_requests=d.get("special_requests", ""),
                arrival_time=d.get("arrival_time"),
                source="website",
            )
        except BookingUnavailableError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {"form": form}, status=400)

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


class BookingCreateStaffView(ManagerRequiredMixin, View):
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
                children=d["children"],
                room=d.get("room"),
                organization=d.get("organization"),
                special_requests=d.get("special_requests", ""),
                arrival_time=d.get("arrival_time"),
                source=d.get("source", "walk_in"),
                internal_notes=d.get("internal_notes", ""),
                discount_amount=d.get("discount_amount") or 0,
                discount_reason=d.get("discount_reason", ""),
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
