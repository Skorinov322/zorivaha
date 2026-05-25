"""
crm/services.py — all write operations for the CRM module.
"""

from django.db import transaction

from .models import ClientProfile, AdminComment, Interaction, Task, Organization


# ---------------------------------------------------------------------------
# ClientProfile
# ---------------------------------------------------------------------------

@transaction.atomic
def update_client_profile(profile: ClientProfile, cleaned_data: dict, actor=None) -> ClientProfile:
    """Update CRM profile fields from validated form data."""
    allowed = [
        "client_type", "guest_type", "status",
        "organization", "assigned_manager",
        "preferred_room_category", "preferred_floor",
        "dietary_requirements", "special_needs",
        "vip_notes", "is_blacklisted", "blacklist_reason",
    ]
    for field in allowed:
        if field in cleaned_data:
            setattr(profile, field, cleaned_data[field])
    profile.save()
    return profile


@transaction.atomic
def set_client_status(profile: ClientProfile, new_status: str, actor=None) -> ClientProfile:
    """Change client CRM status."""
    profile.status = new_status
    if new_status == ClientProfile.ClientStatus.BLACKLISTED:
        profile.is_blacklisted = True
    elif new_status != ClientProfile.ClientStatus.BLACKLISTED:
        profile.is_blacklisted = False
    profile.save(update_fields=["status", "is_blacklisted", "updated_at"])
    return profile


# ---------------------------------------------------------------------------
# AdminComment
# ---------------------------------------------------------------------------

@transaction.atomic
def add_admin_comment(profile: ClientProfile, author, body: str, is_pinned: bool = False) -> AdminComment:
    """Add a staff comment to a client profile."""
    return AdminComment.objects.create(
        client=profile,
        author=author,
        body=body,
        is_pinned=is_pinned,
    )


@transaction.atomic
def delete_admin_comment(comment_id: int, actor=None) -> None:
    """Delete a comment (only author or admin can delete)."""
    comment = AdminComment.objects.get(pk=comment_id)
    comment.delete()


@transaction.atomic
def toggle_pin_comment(comment_id: int) -> AdminComment:
    comment = AdminComment.objects.get(pk=comment_id)
    comment.is_pinned = not comment.is_pinned
    comment.save(update_fields=["is_pinned"])
    return comment


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------

@transaction.atomic
def create_interaction(
    client: ClientProfile,
    staff,
    interaction_type: str,
    subject: str,
    body: str,
    booking=None,
    outcome: str = "",
    follow_up_date=None,
) -> Interaction:
    return Interaction.objects.create(
        client=client,
        staff=staff,
        interaction_type=interaction_type,
        subject=subject,
        body=body,
        booking=booking,
        outcome=outcome,
        follow_up_date=follow_up_date,
    )


@transaction.atomic
def resolve_interaction(interaction_id: int) -> Interaction:
    interaction = Interaction.objects.get(pk=interaction_id)
    interaction.is_resolved = True
    interaction.save(update_fields=["is_resolved", "updated_at"])
    return interaction


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@transaction.atomic
def create_task(
    title: str,
    assigned_to,
    created_by=None,
    client: ClientProfile = None,
    booking=None,
    priority: str = "medium",
    due_date=None,
    description: str = "",
) -> Task:
    return Task.objects.create(
        title=title,
        description=description,
        assigned_to=assigned_to,
        created_by=created_by,
        client=client,
        booking=booking,
        priority=priority,
        due_date=due_date,
    )


@transaction.atomic
def complete_task(task_id: int, actor=None) -> Task:
    task = Task.objects.get(pk=task_id)
    task.complete(actor=actor)
    return task


@transaction.atomic
def cancel_task(task_id: int, actor=None) -> Task:
    task = Task.objects.get(pk=task_id)
    task.status = Task.TaskStatus.CANCELLED
    task.save(update_fields=["status", "updated_at"])
    return task


@transaction.atomic
def delete_task(task_id: int, actor=None) -> None:
    """Permanently delete a task."""
    Task.objects.get(pk=task_id).delete()


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

@transaction.atomic
def create_organization(cleaned_data: dict, actor=None) -> Organization:
    data = dict(cleaned_data)
    if actor is not None:
        data["created_by_user"] = actor
        data["is_approved"] = True
    return Organization.objects.create(**data)


@transaction.atomic
def update_organization(org: Organization, cleaned_data: dict, actor=None) -> Organization:
    for field, value in cleaned_data.items():
        setattr(org, field, value)
    org.save()
    return org
