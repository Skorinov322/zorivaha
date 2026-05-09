"""
apps/core/permissions.py

Central RBAC module for the Зори Ваха project.

Provides three layers of access control — use whichever fits the context:

  1. Decorators          — for function-based views
  2. Mixins              — for class-based views
  3. Permission classes  — for programmatic checks in services/templates

────────────────────────────────────────────────────────────────────────────
ROLE HIERARCHY  (ascending privilege)
────────────────────────────────────────────────────────────────────────────
  USER  <  RECEPTIONIST  <  MANAGER  <  ADMIN  <  SUPER_ADMIN
                                                       │
                                              is_superuser always passes

────────────────────────────────────────────────────────────────────────────
QUICK REFERENCE
────────────────────────────────────────────────────────────────────────────

  # Function-based view
  @login_required
  @role_required(UserRole.MANAGER)
  def my_view(request): ...

  # Class-based view
  class MyView(ManagerRequiredMixin, View): ...

  # Programmatic check
  if has_permission(request.user, Permission.MANAGE_BOOKINGS):
      ...

  # Template
  {% if perms_ctx.can_manage_bookings %}
      <a href="...">Управление бронями</a>
  {% endif %}
"""

from __future__ import annotations

import functools
import logging
from enum import Enum
from typing import Callable

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Import role constants (avoid circular imports by importing lazily where needed)
# ---------------------------------------------------------------------------

def _get_role():
    from apps.accounts.models import UserRole
    return UserRole


# ---------------------------------------------------------------------------
# Permission enum
# ---------------------------------------------------------------------------

class Permission(str, Enum):
    """
    Fine-grained permission constants.
    Map to minimum required roles in PERMISSION_ROLE_MAP below.
    """

    # Bookings
    VIEW_OWN_BOOKINGS    = "view_own_bookings"
    CREATE_BOOKING       = "create_booking"
    CANCEL_OWN_BOOKING   = "cancel_own_booking"
    MANAGE_BOOKINGS      = "manage_bookings"      # confirm, check-in, check-out
    VIEW_ALL_BOOKINGS    = "view_all_bookings"

    # Rooms
    VIEW_ROOMS           = "view_rooms"
    MANAGE_ROOMS         = "manage_rooms"

    # CRM
    VIEW_CRM             = "view_crm"
    MANAGE_CRM           = "manage_crm"

    # Reports
    VIEW_REPORTS         = "view_reports"
    EXPORT_REPORTS       = "export_reports"

    # Dashboard
    VIEW_DASHBOARD       = "view_dashboard"

    # Users
    VIEW_USERS           = "view_users"
    MANAGE_USERS         = "manage_users"
    ASSIGN_ROLES         = "assign_roles"         # SUPER_ADMIN only

    # Content
    MANAGE_CONTENT       = "manage_content"

    # Analytics
    VIEW_ANALYTICS       = "view_analytics"


# Minimum role required for each permission
# (user.has_role(min_role) must return True)
PERMISSION_ROLE_MAP: dict[Permission, str] = {
    # Any authenticated user
    Permission.VIEW_OWN_BOOKINGS:  "user",
    Permission.CREATE_BOOKING:     "user",
    Permission.CANCEL_OWN_BOOKING: "user",

    # Receptionist+
    Permission.VIEW_ROOMS:         "receptionist",
    Permission.MANAGE_BOOKINGS:    "receptionist",

    # Manager+
    Permission.VIEW_ALL_BOOKINGS:  "manager",
    Permission.VIEW_CRM:           "manager",
    Permission.MANAGE_CRM:         "manager",
    Permission.VIEW_REPORTS:       "manager",
    Permission.EXPORT_REPORTS:     "manager",
    Permission.VIEW_DASHBOARD:     "manager",
    Permission.VIEW_ANALYTICS:     "manager",

    # Admin+
    Permission.MANAGE_ROOMS:       "admin",
    Permission.MANAGE_USERS:       "admin",
    Permission.VIEW_USERS:         "admin",
    Permission.MANAGE_CONTENT:     "admin",

    # Super-admin only
    Permission.ASSIGN_ROLES:       "super_admin",
}


def has_permission(user, permission: Permission) -> bool:
    """
    Core permission check.

    Usage:
        from apps.core.permissions import has_permission, Permission
        if has_permission(request.user, Permission.MANAGE_BOOKINGS):
            ...
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    min_role = PERMISSION_ROLE_MAP.get(permission)
    if min_role is None:
        return False
    return user.has_role(min_role)


def get_user_permissions(user) -> set[Permission]:
    """Return the full set of permissions for a user."""
    if not user or not user.is_authenticated:
        return set()
    return {p for p in Permission if has_permission(user, p)}


# ---------------------------------------------------------------------------
# Decorators  (function-based views)
# ---------------------------------------------------------------------------

def role_required(
    minimum_role: str,
    redirect_url: str | None = None,
    raise_exception: bool = False,
):
    """
    Decorator: require user to have at least `minimum_role`.

    Args:
        minimum_role:   Minimum role string from UserRole (e.g. UserRole.MANAGER)
        redirect_url:   Where to redirect on failure (default: login page)
        raise_exception: Raise PermissionDenied instead of redirecting

    Usage:
        @login_required
        @role_required(UserRole.MANAGER)
        def my_view(request): ...

        @login_required
        @role_required("admin", raise_exception=True)
        def admin_view(request): ...
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                from django.conf import settings
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if request.user.has_role(minimum_role):
                return view_func(request, *args, **kwargs)

            logger.warning(
                "Access denied: user=%s role=%s required=%s path=%s",
                request.user.email, request.user.role, minimum_role, request.path,
            )

            if raise_exception:
                raise PermissionDenied

            messages.error(request, "У вас недостаточно прав для этого действия.")
            return redirect(redirect_url or "hotel:index")

        return wrapper
    return decorator


def permission_required(
    permission: Permission,
    redirect_url: str | None = None,
    raise_exception: bool = False,
):
    """
    Decorator: require a specific Permission enum value.

    Usage:
        @login_required
        @permission_required(Permission.MANAGE_BOOKINGS)
        def confirm_booking(request, pk): ...
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                from django.conf import settings
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if has_permission(request.user, permission):
                return view_func(request, *args, **kwargs)

            logger.warning(
                "Permission denied: user=%s permission=%s path=%s",
                request.user.email, permission.value, request.path,
            )

            if raise_exception:
                raise PermissionDenied

            messages.error(request, "У вас недостаточно прав для этого действия.")
            return redirect(redirect_url or "hotel:index")

        return wrapper
    return decorator


def super_admin_required(raise_exception: bool = False):
    """
    Shortcut decorator for SUPER_ADMIN-only views.

    Usage:
        @login_required
        @super_admin_required()
        def assign_role_view(request): ...
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                from django.conf import settings
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if request.user.is_super_admin:
                return view_func(request, *args, **kwargs)

            if raise_exception:
                raise PermissionDenied

            messages.error(request, "Эта страница доступна только супер-администраторам.")
            return redirect("hotel:index")

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Mixins  (class-based views)
# ---------------------------------------------------------------------------

class _BaseRoleMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Internal base for all role mixins.
    Subclasses must implement test_func().
    """

    login_url = "/auth/login/"
    permission_denied_message = "У вас недостаточно прав для этого действия."

    def handle_no_permission(self) -> HttpResponse:
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, self.permission_denied_message)
        return redirect(getattr(self, "redirect_url", "hotel:index"))


class LoginRequiredMixin(_BaseRoleMixin):
    """
    Drop-in replacement for Django's LoginRequiredMixin.
    Redirects to /auth/login/ instead of /accounts/login/.
    """

    def test_func(self) -> bool:
        return self.request.user.is_authenticated


class UserRequiredMixin(_BaseRoleMixin):
    """Any authenticated user (USER role or higher)."""

    def test_func(self) -> bool:
        return self.request.user.is_authenticated


class ReceptionistRequiredMixin(_BaseRoleMixin):
    """Receptionist, Manager, Admin, Super-Admin."""

    def test_func(self) -> bool:
        return self.request.user.is_authenticated and \
               self.request.user.has_role("receptionist")


class ManagerRequiredMixin(_BaseRoleMixin):
    """Manager, Admin, Super-Admin."""

    def test_func(self) -> bool:
        return self.request.user.is_authenticated and \
               self.request.user.has_role("manager")


class AdminRequiredMixin(_BaseRoleMixin):
    """Admin and Super-Admin."""

    def test_func(self) -> bool:
        return self.request.user.is_authenticated and \
               self.request.user.has_role("admin")


class SuperAdminRequiredMixin(_BaseRoleMixin):
    """Super-Admin only (or Django superuser)."""

    permission_denied_message = "Эта страница доступна только супер-администраторам."

    def test_func(self) -> bool:
        return self.request.user.is_authenticated and \
               self.request.user.is_super_admin


class PermissionRequiredMixin(_BaseRoleMixin):
    """
    CBV mixin for fine-grained permission checks.

    Usage:
        class MyView(PermissionRequiredMixin, View):
            required_permission = Permission.MANAGE_BOOKINGS
    """

    required_permission: Permission | None = None

    def test_func(self) -> bool:
        if self.required_permission is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} must define required_permission"
            )
        return has_permission(self.request.user, self.required_permission)


class RoleRequiredMixin(_BaseRoleMixin):
    """
    Generic mixin: set allowed_roles list on the view.

    Usage:
        class MyView(RoleRequiredMixin, View):
            allowed_roles = [UserRole.MANAGER, UserRole.ADMIN]
    """

    allowed_roles: list[str] = []

    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role in self.allowed_roles


# ---------------------------------------------------------------------------
# Context processor  (injects permissions into every template)
# ---------------------------------------------------------------------------

def permissions_context(request) -> dict:
    """
    Injects a `perms_ctx` object into every template context.

    Usage in templates:
        {% if perms_ctx.can_manage_bookings %}
        {% if perms_ctx.can_assign_roles %}
        {% if perms_ctx.is_super_admin %}
    """
    user = request.user

    class _Ctx:
        pass

    ctx = _Ctx()

    if user.is_authenticated:
        ctx.is_authenticated    = True
        ctx.is_plain_user       = user.is_plain_user
        ctx.is_receptionist     = user.has_role("receptionist")
        ctx.is_manager          = user.has_role("manager")
        ctx.is_admin            = user.has_role("admin")
        ctx.is_super_admin      = user.is_super_admin

        ctx.can_view_dashboard      = has_permission(user, Permission.VIEW_DASHBOARD)
        ctx.can_manage_bookings     = has_permission(user, Permission.MANAGE_BOOKINGS)
        ctx.can_view_all_bookings   = has_permission(user, Permission.VIEW_ALL_BOOKINGS)
        ctx.can_view_crm            = has_permission(user, Permission.VIEW_CRM)
        ctx.can_view_reports        = has_permission(user, Permission.VIEW_REPORTS)
        ctx.can_export_reports      = has_permission(user, Permission.EXPORT_REPORTS)
        ctx.can_manage_rooms        = has_permission(user, Permission.MANAGE_ROOMS)
        ctx.can_manage_users        = has_permission(user, Permission.MANAGE_USERS)
        ctx.can_assign_roles        = has_permission(user, Permission.ASSIGN_ROLES)
        ctx.can_manage_content      = has_permission(user, Permission.MANAGE_CONTENT)
        ctx.can_view_analytics      = has_permission(user, Permission.VIEW_ANALYTICS)
    else:
        ctx.is_authenticated    = False
        ctx.is_plain_user       = False
        ctx.is_receptionist     = False
        ctx.is_manager          = False
        ctx.is_admin            = False
        ctx.is_super_admin      = False
        for attr in [
            "can_view_dashboard", "can_manage_bookings", "can_view_all_bookings",
            "can_view_crm", "can_view_reports", "can_export_reports",
            "can_manage_rooms", "can_manage_users", "can_assign_roles",
            "can_manage_content", "can_view_analytics",
        ]:
            setattr(ctx, attr, False)

    return {"perms_ctx": ctx}
