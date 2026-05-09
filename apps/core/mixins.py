"""
apps/core/mixins.py

Re-exports all mixins from apps.core.permissions for backward compatibility.
Import from here in views — the actual implementation lives in permissions.py.
"""

# Re-export everything so existing imports don't break
from apps.core.permissions import (  # noqa: F401
    LoginRequiredMixin,
    UserRequiredMixin,
    ReceptionistRequiredMixin,
    ManagerRequiredMixin,
    AdminRequiredMixin,
    SuperAdminRequiredMixin,
    PermissionRequiredMixin,
    RoleRequiredMixin,
)

# Legacy alias
StaffRequiredMixin = ManagerRequiredMixin

__all__ = [
    "LoginRequiredMixin",
    "UserRequiredMixin",
    "ReceptionistRequiredMixin",
    "ManagerRequiredMixin",
    "AdminRequiredMixin",
    "SuperAdminRequiredMixin",
    "PermissionRequiredMixin",
    "RoleRequiredMixin",
    "StaffRequiredMixin",
]
