"""Global template context processors."""

from django.conf import settings


def site_settings(request):
    """Inject common site-wide variables into every template context."""
    return {
        "SITE_NAME": "Зори Ваха",
        "SITE_TAGLINE": "Уютный отдых в тихом посёлке",
        "CONTACT_PHONE": "+7 (3466) 28-70-03",
        "CONTACT_PHONE_SECOND": "+7 (3466) 28-23-61",
        "CONTACT_EMAIL": "zorivaha@mail.ru",
        "DEBUG": settings.DEBUG,
        "footer_links_hotel": [
            ("Номера", "/rooms/"),
            ("О гостинице", "/about/"),
            ("Контакты", "/contacts/"),
        ],
    }


def contact_messages_count(request):
    """Inject unread contact messages count for staff sidebar badge."""
    if not request.user.is_authenticated:
        return {"contact_messages_new_count": 0}
    try:
        from apps.accounts.models import UserRole
        if not request.user.has_role(UserRole.RECEPTIONIST):
            return {"contact_messages_new_count": 0}
        from apps.notifications.models import ContactMessage
        count = ContactMessage.objects.filter(status=ContactMessage.Status.NEW).count()
        return {"contact_messages_new_count": count}
    except Exception:
        return {"contact_messages_new_count": 0}
