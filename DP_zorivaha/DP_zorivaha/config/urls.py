"""Root URL configuration for Зори Ваха."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from apps.core.health import HealthCheckView

urlpatterns = [
    # Health check (no auth, used by Docker/Nginx/monitoring)
    path("health/", HealthCheckView.as_view(), name="health"),

    # Django admin
    path("admin/", admin.site.urls),

    # ----------------------------------------------------------------
    # First-run setup wizard
    # Accessible only when no superuser exists (enforced by middleware
    # + Http404 guard inside the views themselves).
    # ----------------------------------------------------------------
    path("setup/", include("apps.setup.urls", namespace="setup")),

    # Public hotel site
    path("", include("apps.hotel.urls", namespace="hotel")),

    # Booking flow
    path("bookings/", include("apps.bookings.urls", namespace="bookings")),

    # Auth: register / login / logout  →  /auth/…
    path("auth/", include("apps.accounts.auth_urls")),

    # Personal cabinet  →  /cabinet/…
    path("cabinet/", include("apps.accounts.urls", namespace="accounts")),

    # CRM (staff only)
    path("crm/", include("apps.crm.urls", namespace="crm")),

    # Dashboard / admin panel
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),

    # Reports
    path("reports/", include("apps.reports.urls", namespace="reports")),

    # Email log (staff)
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
