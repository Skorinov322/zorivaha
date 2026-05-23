"""Root URL configuration for Зори Ваха."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from apps.core.health import HealthCheckView
from apps.core.admin_site import role_admin_site

urlpatterns = [
    # Yandex Webmaster verification
    path(
        "yandex_26cd3036c0f3861a.html",
        TemplateView.as_view(
            template_name="yandex_26cd3036c0f3861a.html",
            content_type="text/html",
        ),
        name="yandex_verification",
    ),

    # Health check (no auth, used by Docker/Nginx/monitoring)
    path("health/", HealthCheckView.as_view(), name="health"),

    # Django admin — стандартный (только is_superuser)
    path("admin/", admin.site.urls),

    # Role-based admin — для персонала по ролям
    path("staff-admin/", role_admin_site.urls),

    # First-run setup wizard
    path("setup/", include("apps.setup.urls", namespace="setup")),

    # Auth: register / login / logout
    path("auth/", include("apps.accounts.auth_urls")),

    # Personal cabinet
    path("cabinet/", include("apps.accounts.urls", namespace="accounts")),

    # Booking flow
    path("bookings/", include("apps.bookings.urls", namespace="bookings")),

    # CRM (staff only)
    path("crm/", include("apps.crm.urls", namespace="crm")),

    # Dashboard / admin panel
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),

    # Reports
    path("reports/", include("apps.reports.urls", namespace="reports")),

    # Email log (staff)
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),

    # Reviews
    path("reviews/", include("apps.reviews.urls", namespace="reviews")),

    # Content pages (FAQ, legal docs) — before hotel catch-all
    path("", include("apps.content.urls", namespace="content")),

    # Public hotel site (catch-all index last)
    path("", include("apps.hotel.urls", namespace="hotel")),
]

# Uploaded media: Cloudinary URLs are external; local fallback needs /media/ serving on Railway.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # import debug_toolbar
    # urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns

    # Test error pages in development
    urlpatterns += [
        path("test-errors/", include("apps.core.test_urls")),
    ]

# Custom error handlers
handler403 = "apps.core.views.custom_403"
handler404 = "apps.core.views.custom_404"
handler500 = "apps.core.views.custom_500"
