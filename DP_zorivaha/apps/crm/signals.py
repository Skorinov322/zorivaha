"""
CRM signals for handling organization creation notifications.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.db import models

from .models import Organization

User = get_user_model()


@receiver(post_save, sender=Organization)
def notify_admin_new_organization(sender, instance, created, **kwargs):
    """
    Send notification to administrators when a new organization is created by a user.
    """
    if created and instance.created_by_user and not instance.is_approved:
        # Get all admin users
        admin_users = User.objects.filter(
            models.Q(is_superuser=True) | models.Q(role__in=['admin', 'super_admin'])
        ).values_list('email', flat=True)
        
        if admin_users:
            subject = f"Новая организация требует подтверждения: {instance.name}"
            
            context = {
                'organization': instance,
                'user': instance.created_by_user,
                'admin_url': f"{settings.SITE_URL}/admin/crm/organization/{instance.pk}/change/",
            }
            
            message = render_to_string('crm/emails/new_organization_notification.txt', context)
            html_message = render_to_string('crm/emails/new_organization_notification.html', context)
            
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=list(admin_users),
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                # Log the error but don't break the flow
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send organization notification email: {e}")