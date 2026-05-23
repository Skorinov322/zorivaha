"""
accounts/views.py

Views:
  RegisterView          — регистрация нового гостя
  LoginView             — вход по email + пароль
  LogoutView            — выход (POST only)
  CabinetDashboardView  — главная личного кабинета
  ProfileUpdateView     — редактирование профиля
  AvatarUploadView      — загрузка аватара
  PasswordChangeView    — смена пароля
  MyBookingsView        — список броней гостя
  MyBookingDetailView   — детали одной брони

Все кабинетные views защищены LoginRequiredMixin.
Регистрация и логин редиректят авторизованных пользователей.
"""

import logging

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView, UpdateView, ListView, DetailView

from apps.bookings.selectors import get_guest_bookings, get_booking_for_guest
from .forms import (
    RegisterForm,
    LoginForm,
    ProfileUpdateForm,
    AvatarUploadForm,
    CabinetPasswordChangeForm,
)
from .selectors import get_user_booking_stats, get_user_crm_profile, get_user_stay_history
from .services import update_profile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redirect_authenticated(request, default="accounts:cabinet"):
    """If user is already logged in, send them to the cabinet."""
    if request.user.is_authenticated:
        if request.user.is_manager:
            next_url = request.GET.get("next") or reverse_lazy("dashboard:index")
        else:
            next_url = request.GET.get("next") or reverse_lazy(default)
        return redirect(next_url)
    return None


def _redirect_staff_from_cabinet(request):
    """Managers/Admins/Super-admins use dashboard instead of personal cabinet."""
    if request.user.is_authenticated and request.user.is_manager:
        return redirect("dashboard:index")
    return None


# ---------------------------------------------------------------------------
# RegisterView
# ---------------------------------------------------------------------------

@method_decorator([never_cache, csrf_protect], name="dispatch")
class RegisterView(View):
    """
    Guest self-registration.

    GET  → show empty form
    POST → validate → create user → auto-login → redirect to cabinet
    """

    template_name = "accounts/register.html"

    def get(self, request):
        redir = _redirect_authenticated(request)
        if redir:
            return redir
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        redir = _redirect_authenticated(request)
        if redir:
            return redir

        form = RegisterForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)

        user = form.save()
        logger.info("New guest registered: %s (id=%s)", user.email, user.pk)

        # Auto-login after registration
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(
            request,
            f"Добро пожаловать, {user.get_short_name()}! "
            "Ваш аккаунт успешно создан.",
        )
        return redirect(request.GET.get("next") or "accounts:cabinet")


# ---------------------------------------------------------------------------
# LoginView
# ---------------------------------------------------------------------------

@method_decorator([never_cache, csrf_protect], name="dispatch")
class LoginView(View):
    """
    Email + password login with remember-me support.

    GET  → show login form
    POST → authenticate → set session expiry → redirect
    """

    template_name = "accounts/login.html"

    def get(self, request):
        redir = _redirect_authenticated(request)
        if redir:
            return redir
        return render(request, self.template_name, {
            "form": LoginForm(request),
            "next": request.GET.get("next", ""),
        })

    def post(self, request):
        redir = _redirect_authenticated(request)
        if redir:
            return redir

        form = LoginForm(request, data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form,
                "next": request.POST.get("next", ""),
            }, status=400)

        user = form.get_user()

        # Remember me: 2 weeks vs 1 day (avoid browser-session cookies that mobile browsers drop)
        if form.cleaned_data.get("remember_me"):
            request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
        else:
            request.session.set_expiry(60 * 60 * 24)  # 1 day

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        logger.info("User logged in: %s (id=%s)", user.email, user.pk)

        # Role-based redirect
        next_url = request.POST.get("next", "").strip()
        if next_url and next_url.startswith("/"):
            return redirect(next_url)

        if user.is_manager:
            return redirect("dashboard:index")
        return redirect("accounts:cabinet")


# ---------------------------------------------------------------------------
# LogoutView
# ---------------------------------------------------------------------------

class LogoutView(View):
    """
    POST-only logout for CSRF safety.
    GET requests are redirected to home (no silent logout on link click).
    """

    def post(self, request):
        if request.user.is_authenticated:
            logger.info("User logged out: %s", request.user.email)
            logout(request)
            messages.info(request, "Вы вышли из системы.")
        return redirect("hotel:index")

    def get(self, request):
        # Don't log out on GET — just redirect home
        return redirect("hotel:index")


# ---------------------------------------------------------------------------
# Cabinet: Dashboard
# ---------------------------------------------------------------------------

class CabinetDashboardView(LoginRequiredMixin, TemplateView):
    """
    Personal cabinet homepage.
    Shows booking stats and recent bookings.
    """

    template_name = "accounts/cabinet.html"
    login_url = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        redir = _redirect_staff_from_cabinet(request)
        if redir:
            return redir
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"]           = get_user_booking_stats(self.request.user)
        ctx["recent_bookings"] = get_guest_bookings(self.request.user)[:5]
        ctx["crm_profile"]     = get_user_crm_profile(self.request.user)
        return ctx


# ---------------------------------------------------------------------------
# Cabinet: Profile
# ---------------------------------------------------------------------------

class ProfileUpdateView(LoginRequiredMixin, View):
    """
    Edit personal profile.
    Handles both profile fields and avatar upload in one page.
    """

    template_name = "accounts/profile.html"
    login_url = "/auth/login/"

    def _template_name(self, request):
        if request.user.is_manager:
            return "dashboard/profile.html"
        return self.template_name

    def get(self, request):
        return render(request, self._template_name(request), {
            "form": ProfileUpdateForm(instance=request.user),
            "avatar_form": AvatarUploadForm(instance=request.user),
        })

    def post(self, request):
        # Determine which sub-form was submitted
        action = request.POST.get("action", "profile")

        if action == "avatar":
            from apps.core.media import media_upload_error_message

            avatar_form = AvatarUploadForm(
                request.POST, request.FILES, instance=request.user
            )
            if avatar_form.is_valid():
                try:
                    avatar_form.save()
                except Exception as exc:
                    messages.error(request, media_upload_error_message(exc))
                    return render(request, self._template_name(request), {
                        "form": ProfileUpdateForm(instance=request.user),
                        "avatar_form": avatar_form,
                    })
                messages.success(request, "Фото профиля обновлено.")
                return redirect("accounts:profile")
            return render(request, self._template_name(request), {
                "form": ProfileUpdateForm(instance=request.user),
                "avatar_form": avatar_form,
            })

        # Default: profile fields
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            update_profile(request.user, form.cleaned_data)
            messages.success(request, "Профиль успешно обновлён.")
            return redirect("accounts:profile")

        return render(request, self._template_name(request), {
            "form": form,
            "avatar_form": AvatarUploadForm(instance=request.user),
        })


# ---------------------------------------------------------------------------
# Cabinet: Password Change
# ---------------------------------------------------------------------------

class PasswordChangeView(LoginRequiredMixin, View):
    """Change password from inside the personal cabinet."""

    template_name = "accounts/password_change.html"
    login_url = "/auth/login/"

    def _template_name(self, request):
        if request.user.is_manager:
            return "dashboard/password_change.html"
        return self.template_name

    def get(self, request):
        return render(request, self._template_name(request), {
            "form": CabinetPasswordChangeForm(request.user),
        })

    def post(self, request):
        form = CabinetPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, "Пароль успешно изменён.")
            return redirect("accounts:profile")

        return render(request, self._template_name(request), {"form": form})


# ---------------------------------------------------------------------------
# Cabinet: Bookings
# ---------------------------------------------------------------------------

class MyBookingsView(LoginRequiredMixin, ListView):
    """List all bookings for the current user with status filter."""

    template_name = "accounts/my_bookings.html"
    context_object_name = "bookings"
    paginate_by = 10
    login_url = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        redir = _redirect_staff_from_cabinet(request)
        if redir:
            return redir
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        status = self.request.GET.get("status", "")
        return get_guest_bookings(self.request.user, status=status or None)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get("status", "")
        from apps.bookings.models import BookingStatus
        ctx["status_choices"] = BookingStatus.choices
        return ctx


class MyBookingDetailView(LoginRequiredMixin, DetailView):
    """Single booking detail in personal cabinet."""

    template_name = "accounts/booking_detail.html"
    context_object_name = "booking"
    login_url = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        redir = _redirect_staff_from_cabinet(request)
        if redir:
            return redir
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_booking_for_guest(self.kwargs["pk"], self.request.user)


# ---------------------------------------------------------------------------
# Cabinet: Stay History
# ---------------------------------------------------------------------------

class StayHistoryView(LoginRequiredMixin, ListView):
    """История завершённых проживаний гостя."""

    template_name       = "accounts/stay_history.html"
    context_object_name = "stays"
    paginate_by         = 10
    login_url           = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        redir = _redirect_staff_from_cabinet(request)
        if redir:
            return redir
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_user_stay_history(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["crm_profile"] = get_user_crm_profile(self.request.user)
        return ctx


# ---------------------------------------------------------------------------
# Cabinet: My Organizations
# ---------------------------------------------------------------------------

class MyOrganizationsView(LoginRequiredMixin, ListView):
    """Список организаций, созданных пользователем."""

    template_name       = "accounts/my_organizations.html"
    context_object_name = "organizations"
    login_url           = "/auth/login/"

    def dispatch(self, request, *args, **kwargs):
        redir = _redirect_staff_from_cabinet(request)
        if redir:
            return redir
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        from apps.crm.models import Organization
        return Organization.objects.filter(
            created_by_user=self.request.user
        ).order_by('-created_at')


# ---------------------------------------------------------------------------
# Guest contact messages (re-export from notifications views)
# ---------------------------------------------------------------------------

from apps.notifications.views import (
    GuestContactMessagesView,
    GuestContactMessageDetailView,
)
