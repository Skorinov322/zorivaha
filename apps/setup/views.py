"""
Setup wizard views.

URL: /setup/
  GET  → show the setup form (or 404 if already initialized)
  POST → validate, create superuser, redirect to dashboard login

Security layers:
  1. SetupMiddleware  — redirects all traffic to /setup/ until done
  2. setup_not_complete() guard in every view — returns 404 if a
     superuser already exists (prevents re-running setup)
  3. Rate limiting via SetupRateLimitMixin — max 5 POST attempts
     per IP per hour (stored in Django cache)
  4. Honeypot field in the form — rejects bot submissions
  5. CSRF protection (Django default)
  6. No information leakage — generic error messages only
"""

import logging

from django.contrib import messages
from django.contrib.auth import login
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .forms import SetupForm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Guard helper
# ---------------------------------------------------------------------------

def _setup_is_complete() -> bool:
    """
    Return True if at least one superuser exists.
    Uses the middleware's cached flag first to avoid extra DB queries.
    """
    from apps.setup.middleware import _setup_complete
    if _setup_complete is True:
        return True

    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(is_superuser=True).exists()


def _require_setup_incomplete(func):
    """
    Decorator for view methods: raises Http404 if setup is already done.
    Applied to both GET and POST to prevent any interaction after setup.
    """
    def wrapper(self, request, *args, **kwargs):
        if _setup_is_complete():
            raise Http404("Страница настройки недоступна.")
        return func(self, request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

_RATE_LIMIT_ATTEMPTS = 5
_RATE_LIMIT_WINDOW = 60 * 60  # 1 hour in seconds


def _get_client_ip(request) -> str:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _is_rate_limited(request) -> bool:
    ip = _get_client_ip(request)
    cache_key = f"setup_attempts:{ip}"
    attempts = cache.get(cache_key, 0)
    return attempts >= _RATE_LIMIT_ATTEMPTS


def _increment_rate_limit(request):
    ip = _get_client_ip(request)
    cache_key = f"setup_attempts:{ip}"
    attempts = cache.get(cache_key, 0)
    cache.set(cache_key, attempts + 1, timeout=_RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@method_decorator([never_cache, csrf_protect], name="dispatch")
class SetupIndexView(View):
    """
    Single-page setup wizard.

    GET  → render the form
    POST → validate → create superuser → auto-login → redirect to dashboard
    """

    template_name = "setup/index.html"

    def get(self, request):
        # Setup is intentionally single-use. After completion,
        # send users to the normal app flow instead of 404.
        if _setup_is_complete():
            if request.user.is_authenticated:
                return redirect("hotel:index")
            return redirect("login")
        form = SetupForm()
        return render(request, self.template_name, {"form": form})

    @_require_setup_incomplete
    def post(self, request):
        # ---- Rate limit check ----
        if _is_rate_limited(request):
            logger.warning(
                "Setup rate limit exceeded from IP %s",
                _get_client_ip(request),
            )
            messages.error(
                request,
                "Слишком много попыток. Попробуйте через час.",
            )
            return render(request, self.template_name, {"form": SetupForm()}, status=429)

        form = SetupForm(request.POST)

        if not form.is_valid():
            _increment_rate_limit(request)
            return render(request, self.template_name, {"form": form}, status=400)

        # ---- Create superuser ----
        try:
            user = form.save()
        except Exception as exc:
            logger.exception("Failed to create initial superuser: %s", exc)
            messages.error(
                request,
                "Произошла ошибка при создании пользователя. Попробуйте ещё раз.",
            )
            return render(request, self.template_name, {"form": form}, status=500)

        logger.info(
            "Initial superuser created: %s (id=%s) from IP %s",
            user.email, user.pk, _get_client_ip(request),
        )

        # ---- Auto-login ----
        # Use the model backend explicitly — allauth is not involved here
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        messages.success(
            request,
            f"Добро пожаловать, {user.get_short_name()}! "
            "Система успешно настроена. Вы вошли как администратор.",
        )

        return redirect("setup:complete")


@method_decorator(never_cache, name="dispatch")
class SetupCompleteView(View):
    """
    Shown once after successful setup.
    Redirects to dashboard if setup is not freshly completed.
    """

    template_name = "setup/complete.html"

    def get(self, request):
        # If user somehow lands here without being logged in, send to login
        if not request.user.is_authenticated:
            return redirect("account_login")

        # If setup was already done before this session, go to dashboard
        if not request.user.is_superuser:
            return redirect("hotel:index")

        return render(request, self.template_name, {"user": request.user})
