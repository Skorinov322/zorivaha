"""
Core abstract models used across the entire project.

Hierarchy:
  TimeStampedModel  — created_at / updated_at (всегда наследуй это)
  UUIDModel         — UUID primary key (для публичных ресурсов)
  SoftDeleteModel   — мягкое удаление (deleted_at)
  OrderedModel      — sort_order для ручной сортировки
"""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# TimeStampedModel
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    """
    Abstract base: self-updating created_at / updated_at.
    Inherit this in every domain model.
    """

    created_at = models.DateTimeField(
        _("создано"), auto_now_add=True, db_index=True
    )
    updated_at = models.DateTimeField(_("обновлено"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# UUIDModel
# ---------------------------------------------------------------------------

class UUIDModel(models.Model):
    """
    Abstract model with UUID primary key.
    Use for resources whose PK is exposed in URLs (bookings, invoices).
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# SoftDelete
# ---------------------------------------------------------------------------

class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that filters out soft-deleted records by default."""

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """
    Abstract model: soft-delete via deleted_at timestamp.
    Records are never physically removed — only marked.

    Usage:
        MyModel.objects.all()          → only alive records
        MyModel.all_objects.all()      → all records including deleted
        instance.delete()              → soft-delete
        instance.hard_delete()         → physical delete
        instance.restore()             → un-delete
    """

    deleted_at = models.DateTimeField(
        _("удалено"), null=True, blank=True, db_index=True
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents=False):
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self):
        super().delete()

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# OrderedModel
# ---------------------------------------------------------------------------

class OrderedModel(models.Model):
    """
    Abstract model for manually ordered records.
    Provides sort_order field; default ordering is by sort_order.
    """

    sort_order = models.PositiveSmallIntegerField(
        _("порядок сортировки"), default=0, db_index=True
    )

    class Meta:
        abstract = True
        ordering = ["sort_order"]
