"""
accounts/services.py

Business logic for user account operations.
All write operations go through here — never directly in views.
"""

from django.db import transaction
from django.core.exceptions import PermissionDenied

from .models import User, UserRole, ROLE_HIERARCHY


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@transaction.atomic
def update_profile(user: User, cleaned_data: dict) -> User:
    """Update user profile fields from validated form data."""
    allowed_fields = [
        "email", "first_name", "last_name", "patronymic", "phone",
        "date_of_birth",
        "preferred_language",
    ]
    for field in allowed_fields:
        if field in cleaned_data:
            setattr(user, field, cleaned_data[field])

    if cleaned_data.get("avatar"):
        user.avatar = cleaned_data["avatar"]

    user.save()
    return user


@transaction.atomic
def update_user_profile_snapshot(user: User, data: dict, overwrite: bool = True) -> User:
    """
    Store contact data entered in public forms back to the user's profile.

    Only known profile fields are accepted. Empty values are ignored so an
    incomplete form submission does not erase previously saved data.
    """
    if not user or not user.is_authenticated:
        return user

    allowed_fields = [
        "first_name", "last_name", "patronymic", "phone",
    ]
    update_fields = []

    for field in allowed_fields:
        value = data.get(field)
        if value in (None, ""):
            continue
        if overwrite or not getattr(user, field):
            setattr(user, field, value)
            update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        user.save(update_fields=update_fields)

    return user


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------

class RoleAssignmentError(Exception):
    """Raised when a role assignment is not permitted."""


@transaction.atomic
def assign_role(actor: User, target: User, new_role: str) -> User:
    """
    Assign a new role to `target` user.

    Rules:
      - Only SUPER_ADMIN (or is_superuser) can assign SUPER_ADMIN role
      - ADMIN can assign roles up to MANAGER
      - A user cannot demote themselves
      - Cannot assign a role that doesn't exist in UserRole

    Args:
        actor:    The user performing the assignment
        target:   The user whose role is being changed
        new_role: The new role string (from UserRole)

    Returns:
        Updated target user

    Raises:
        RoleAssignmentError: if the assignment is not permitted
    """
    # Validate role value
    valid_roles = [r.value for r in UserRole]
    if new_role not in valid_roles:
        raise RoleAssignmentError(f"Неизвестная роль: {new_role}")

    # Actor must be able to assign this role
    if not actor.can_assign_role(new_role):
        raise RoleAssignmentError(
            f"У вас нет прав назначать роль «{UserRole(new_role).label}»."
        )

    # Cannot self-demote (safety guard)
    if actor.pk == target.pk and new_role != target.role:
        if ROLE_HIERARCHY.index(new_role) < ROLE_HIERARCHY.index(target.role):
            raise RoleAssignmentError("Вы не можете понизить собственную роль.")

    old_role = target.role
    target.role = new_role

    # Sync Django staff flag
    target.is_staff = new_role in (
        UserRole.RECEPTIONIST, UserRole.MANAGER,
        UserRole.ADMIN, UserRole.SUPER_ADMIN,
    )

    target.save(update_fields=["role", "is_staff", "updated_at"])

    import logging
    logging.getLogger(__name__).info(
        "Role changed: target=%s %s→%s by actor=%s",
        target.email, old_role, new_role, actor.email,
    )

    return target


def get_assignable_roles(actor: User) -> list[tuple[str, str]]:
    """
    Return the list of (value, label) role choices that `actor` can assign.
    Used to populate the role dropdown in the user management form.
    """
    if actor.is_super_admin:
        return UserRole.choices

    if actor.has_role(UserRole.ADMIN):
        # Admin can assign up to MANAGER
        cutoff = ROLE_HIERARCHY.index(UserRole.ADMIN)
        return [
            (r, UserRole(r).label)
            for r in ROLE_HIERARCHY[:cutoff]
        ]

    return []
