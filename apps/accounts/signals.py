"""
Account signals.
Kept minimal — only side-effects that must happen synchronously.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def create_crm_profile(sender, instance: User, created: bool, **kwargs):
    """Automatically create a CRM ClientProfile when a new user registers."""
    if created and instance.is_plain_user:
        from apps.crm.models import ClientProfile
        ClientProfile.objects.get_or_create(user=instance)
