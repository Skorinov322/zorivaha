"""Global template context processors."""

from django.conf import settings


def site_settings(request):
    """Inject common site-wide variables into every template context."""
    from django.urls import reverse
    return {
        "SITE_NAME": "Зори Ваха",
        "SITE_TAGLINE": "Уютный отдых в тихом посёлке",
        "CONTACT_PHONE": "+7 (928) 000-00-00",
        "CONTACT_EMAIL": "info@zorivaha.ru",
        "DEBUG": settings.DEBUG,
        "footer_links_hotel": [
            ("Номера", "/rooms/"),
            ("О гостинице", "/about/"),
            ("Контакты", "/contacts/"),
        ],
    }
