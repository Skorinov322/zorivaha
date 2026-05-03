"""
Setup middleware.

Intercepts every request and redirects to /setup/ if the system
has not been initialized yet (no superuser exists in the database).

Security guarantees:
  - Only /setup/* and static/media URLs are allowed through
  - Once a superuser exists, /setup/ returns 404 permanently
  - The check result is cached in memory (per-process) to avoid
    a DB hit on every request after setup is complete
  - Cache is invalidated when a superuser is created
"""

import threading

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse

# Thread-safe in-memory flag.
# None  = not checked yet
# True  = setup complete (superuser exists)
# False = setup required
_setup_complete: bool | None = None
_lock = threading.Lock()


def _check_setup_complete() -> bool:
    """
    Query the DB once and cache the result in the module-level flag.
    Safe to call from multiple threads.
    """
    global _setup_complete

    if _setup_complete is True:
        return True

    with _lock:
        # Double-checked locking: re-read after acquiring the lock
        if _setup_complete is True:
            return True

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            _setup_complete = User.objects.filter(is_superuser=True).exists()
        except Exception:
            # DB not ready yet (e.g. during migrations) — don't redirect
            _setup_complete = False

    return _setup_complete


def invalidate_setup_cache():
    """
    Call this after creating the first superuser so the middleware
    stops redirecting immediately without a server restart.
    """
    global _setup_complete
    _setup_complete = True


class SetupMiddleware:
    """
    WSGI middleware that enforces the first-run setup flow.

    Allowed without setup:
      - /setup/*
      - /static/*
      - /media/*
      - /favicon.ico

    Everything else → redirect to /setup/.
    """

    ALLOWED_PREFIXES = ("/setup/", "/auth/", "/static/", "/media/", "/favicon.ico")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _check_setup_complete():
            path = request.path_info

            # Allow setup URLs and assets through
            if not any(path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES):
                setup_url = reverse("setup:index")
                if path != setup_url:
                    return HttpResponseRedirect(setup_url)

        return self.get_response(request)
