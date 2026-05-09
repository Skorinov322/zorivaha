"""
apps/core/health.py

Health check endpoint for load balancers, Docker, and monitoring.

GET /health/
  → 200 OK  {"status": "ok", "db": "ok", "cache": "ok", "celery": "ok"}
  → 503     {"status": "error", "detail": "..."}

Used by:
  - Docker HEALTHCHECK
  - Nginx upstream health check
  - Kubernetes liveness/readiness probes
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@method_decorator(never_cache, name="dispatch")
class HealthCheckView(View):
    """
    Lightweight health check — no authentication required.
    Checks DB, cache (Redis), and Celery broker connectivity.
    """

    def get(self, request):
        checks = {}
        status_code = 200

        # ── Database ──────────────────────────────────────────────────────────
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["db"] = "ok"
        except Exception as exc:
            checks["db"] = f"error: {exc}"
            status_code = 503
            logger.error("Health check DB failed: %s", exc)

        # ── Cache (Redis) ─────────────────────────────────────────────────────
        try:
            from django.core.cache import cache
            cache.set("_health_check", "1", timeout=5)
            val = cache.get("_health_check")
            checks["cache"] = "ok" if val == "1" else "error: value mismatch"
            if val != "1":
                status_code = 503
        except Exception as exc:
            checks["cache"] = f"error: {exc}"
            status_code = 503
            logger.error("Health check cache failed: %s", exc)

        # ── Celery broker (Redis ping) ─────────────────────────────────────────
        try:
            from django.conf import settings
            import redis as redis_lib
            r = redis_lib.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
            r.ping()
            checks["celery_broker"] = "ok"
        except Exception as exc:
            checks["celery_broker"] = f"error: {exc}"
            # Don't fail health check for Celery — app still serves requests
            logger.warning("Health check Celery broker failed: %s", exc)

        overall = "ok" if status_code == 200 else "degraded"
        return JsonResponse(
            {"status": overall, **checks},
            status=status_code,
        )
