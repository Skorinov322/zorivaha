"""
apps/analytics/middleware.py

PageViewMiddleware — записывает просмотры публичных страниц в PageView.

Пишет только:
  - публичные страницы (/, /rooms/, /rooms/<slug>/, /about/, /contacts/)
  - не пишет: /admin/, /static/, /media/, /auth/, /cabinet/, /dashboard/,
    /bookings/staff/, /crm/, /reports/, /setup/

Использует session_key для анонимных пользователей.
Не блокирует запрос — запись идёт синхронно, но очень быстро (один INSERT).
Для production можно вынести в Celery task.
"""

import logging

logger = logging.getLogger(__name__)

# Префиксы, которые НЕ трекаем
_SKIP_PREFIXES = (
    "/admin/", "/static/", "/media/", "/favicon",
    "/auth/", "/cabinet/", "/dashboard/", "/setup/",
    "/bookings/staff/", "/crm/", "/reports/", "/notifications/",
    "/rooms/manage/", "__debug__",
)

# Маппинг path → PageType
_PATH_TYPE_MAP = {
    "/":          "home",
    "/rooms/":    "room_list",
    "/about/":    "about",
    "/contacts/": "contacts",
}


def _detect_page_type(path: str) -> str:
    if path in _PATH_TYPE_MAP:
        return _PATH_TYPE_MAP[path]
    if path.startswith("/rooms/") and path != "/rooms/":
        return "room_detail"
    if path.startswith("/bookings/") and "staff" not in path:
        return "booking_form"
    return "other"


class PageViewMiddleware:
    """
    WSGI middleware that records page views for analytics.
    Only tracks GET requests to public pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only track successful GET requests
        if request.method != "GET":
            return response
        if response.status_code not in (200, 301, 302):
            return response

        path = request.path_info
        if any(path.startswith(p) for p in _SKIP_PREFIXES):
            return response

        page_type = _detect_page_type(path)
        if page_type == "other" and not path.startswith("/rooms/"):
            return response  # skip unknown paths

        try:
            self._record(request, path, page_type)
        except Exception as exc:
            logger.debug("PageView record failed: %s", exc)

        return response

    @staticmethod
    def _record(request, path: str, page_type: str):
        from apps.analytics.models import PageView
        from apps.hotel.models import RoomCategory

        # Resolve room category for room_detail pages
        room_category = None
        if page_type == "room_detail":
            slug = path.rstrip("/").split("/")[-1]
            try:
                room_category = RoomCategory.objects.get(slug=slug)
            except RoomCategory.DoesNotExist:
                pass

        # Get or create session key
        if not request.session.session_key:
            request.session.create()

        user = request.user if request.user.is_authenticated else None

        PageView.objects.create(
            page_type=page_type,
            path=path,
            referrer=request.META.get("HTTP_REFERER", "")[:500],
            user=user,
            session_key=request.session.session_key or "",
            ip_address=_get_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            room_category=room_category,
        )


def _get_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
