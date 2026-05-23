"""
accounts/admin_views.py

Views for user management (ADMIN+) and role assignment (SUPER_ADMIN only).

URLs mounted at /cabinet/users/ — see accounts/urls.py
"""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.permissions import (
    AdminRequiredMixin,
    ReceptionistRequiredMixin,
    SuperAdminRequiredMixin,
    Permission,
    has_permission,
)
from .forms import AdminSetUserPasswordForm, RoleAssignForm
from .models import UserRole
from .services import assign_role, get_assignable_roles, RoleAssignmentError

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User list  (ADMIN+)
# ---------------------------------------------------------------------------

class UserListView(ReceptionistRequiredMixin, View):
    """
    List all users with search and role filter.
    Accessible to RECEPTIONIST and above.
    """

    template_name = "accounts/admin/user_list.html"

    def get(self, request):
        qs = User.objects.all().order_by("-created_at")

        # Filters
        role_filter = request.GET.get("role", "")
        search      = request.GET.get("q", "").strip()
        tab         = request.GET.get("tab", "guests")  # guests | staff

        if role_filter:
            qs = qs.filter(role=role_filter)
        if search:
            qs = qs.filter(email__icontains=search) | \
                 qs.filter(first_name__icontains=search) | \
                 qs.filter(last_name__icontains=search)

        # Split into guests and staff
        staff_roles = [UserRole.RECEPTIONIST, UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        staff_qs  = qs.filter(role__in=staff_roles)
        guests_qs = qs.filter(role=UserRole.USER)

        return render(request, self.template_name, {
            "users":        qs,
            "guests":       guests_qs,
            "staff":        staff_qs,
            "tab":          tab,
            "role_choices": UserRole.choices,
            "role_filter":  role_filter,
            "search_query": search,
            "can_assign_roles": has_permission(request.user, Permission.ASSIGN_ROLES),
        })


# ---------------------------------------------------------------------------
# User detail  (ADMIN+)
# ---------------------------------------------------------------------------

class UserDetailView(ReceptionistRequiredMixin, View):
    """View a single user's profile and role."""

    template_name = "accounts/admin/user_detail.html"

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        assignable = get_assignable_roles(request.user)
        form = RoleAssignForm(
            assignable_roles=assignable,
            initial={"role": target.role},
        ) if assignable else None

        role_hierarchy = [
            ("user",         "Пользоваостиница",      "Гость — может бронировать номера"),
            ("receptionist", "Ресепшн",            "Заселение, выселение, просмотр броней"),
            ("manager",      "Менеджер",           "CRM, все брони, отчёты, дашборд"),
            ("admin",        "Администратор",      "Управление номерами, пользоваостиницыми, контентом"),
            ("super_admin",  "Супер-администратор","Полный доступ, назначение ролей"),
        ]

        info_rows = [
            ("Телефон",    target.phone or "—"),
            ("Дата рожд.", target.date_of_birth.strftime("%d.%m.%Y") if target.date_of_birth else "—"),
            ("Язык",       target.get_preferred_language_display() if hasattr(target, "get_preferred_language_display") else target.preferred_language),
        ]

        return render(request, self.template_name, {
            "target":         target,
            "form":           form,
            "password_form":  AdminSetUserPasswordForm(target),
            "can_assign":     bool(assignable),
            "can_set_password": request.user.is_admin and (not target.is_super_admin or request.user.is_super_admin),
            "role_hierarchy": role_hierarchy,
            "info_rows":      info_rows,
        })


# ---------------------------------------------------------------------------
# Role assignment  (SUPER_ADMIN only)
# ---------------------------------------------------------------------------

class AssignRoleView(SuperAdminRequiredMixin, View):
    """
    POST endpoint: assign a new role to a user.
    Only SUPER_ADMIN can reach this view.

    POST /cabinet/users/<pk>/assign-role/
    """

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        assignable = get_assignable_roles(request.user)
        form = RoleAssignForm(request.POST, assignable_roles=assignable)

        if not form.is_valid():
            messages.error(request, "Некорректные данные формы.")
            return redirect("accounts:user_detail", pk=pk)

        new_role = form.cleaned_data["role"]

        try:
            assign_role(actor=request.user, target=target, new_role=new_role)
            messages.success(
                request,
                f"Роль пользоваостиницы {target.email} изменена на «{UserRole(new_role).label}».",
            )
        except RoleAssignmentError as e:
            messages.error(request, str(e))

        return redirect("accounts:user_detail", pk=pk)


# ---------------------------------------------------------------------------
# Password reset by admin  (ADMIN+)
# ---------------------------------------------------------------------------

class SetUserPasswordView(AdminRequiredMixin, View):
    """Allow an administrator to set a new password for a user."""

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        if target.is_super_admin and not request.user.is_super_admin:
            messages.error(request, "Пароль супер-администратора может менять только супер-администратор.")
            return redirect("accounts:user_detail", pk=pk)

        form = AdminSetUserPasswordForm(target, request.POST)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            messages.error(request, first_error)
            return redirect("accounts:user_detail", pk=pk)

        form.save()
        if target.pk == request.user.pk:
            update_session_auth_hash(request, target)

        messages.success(request, f"Пароль пользователя {target.email} изменён.")
        return redirect("accounts:user_detail", pk=pk)


# ---------------------------------------------------------------------------
# Toggle active  (ADMIN+)
# ---------------------------------------------------------------------------

class ToggleUserActiveView(AdminRequiredMixin, View):
    """
    POST endpoint: activate or deactivate a user account.
    SUPER_ADMIN cannot be deactivated by anyone except themselves.
    """

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)

        # Guard: cannot deactivate a SUPER_ADMIN unless you are one
        if target.is_super_admin and not request.user.is_super_admin:
            messages.error(request, "Нельзя деактивировать супер-администратора.")
            return redirect("accounts:user_detail", pk=pk)

        # Guard: cannot deactivate yourself
        if target.pk == request.user.pk:
            messages.error(request, "Нельзя деактивировать собственный аккаунт.")
            return redirect("accounts:user_detail", pk=pk)

        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])

        status = "активирован" if target.is_active else "деактивирован"
        messages.success(request, f"Пользоваостиница {target.email} {status}.")
        return redirect("accounts:user_list")
