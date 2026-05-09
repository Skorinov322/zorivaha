"""
config/settings/prod.py — Production settings.

Активируется через: DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from .base import *  # noqa: F401, F403
from decouple import config

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=lambda v: [s.strip() for s in v.split(",")]) + ["healthcheck.railway.app"]

# ---------------------------------------------------------------------------
# Security — HTTPS hardening
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT             = False  # Railway handles HTTPS at proxy level
SECURE_PROXY_SSL_HEADER         = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS: 1 year, include subdomains, preload
SECURE_HSTS_SECONDS             = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS  = True
SECURE_HSTS_PRELOAD             = True

# Cookies
SESSION_COOKIE_SECURE           = True
SESSION_COOKIE_HTTPONLY         = True
SESSION_COOKIE_SAMESITE         = "Lax"
SESSION_COOKIE_AGE              = 60 * 60 * 24 * 14   # 14 days

CSRF_COOKIE_SECURE              = True
CSRF_COOKIE_HTTPONLY            = True
CSRF_COOKIE_SAMESITE            = "Lax"
CSRF_TRUSTED_ORIGINS            = config(
    "CSRF_TRUSTED_ORIGINS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# Headers
SECURE_CONTENT_TYPE_NOSNIFF     = True
SECURE_BROWSER_XSS_FILTER       = True
X_FRAME_OPTIONS                 = "DENY"
SECURE_REFERRER_POLICY          = "strict-origin-when-cross-origin"

# ---------------------------------------------------------------------------
# Static files — WhiteNoise serves compressed, cached static files
# ---------------------------------------------------------------------------

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# ---------------------------------------------------------------------------
# Database — PostgreSQL via DATABASE_URL (Railway provides this automatically)
# ---------------------------------------------------------------------------

import dj_database_url  # noqa: E402

DATABASE_URL = config("DATABASE_URL", default=None)

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    # Fallback to SQLite for local prod testing without a DB service
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# ---------------------------------------------------------------------------
# Cache — Database cache (простой вариант для начала)
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ---------------------------------------------------------------------------
# Logging — structured, to stdout
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {process:d} {thread:d} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[{asctime}] {levelname} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "include_html": True,
        },
    },
    "loggers": {
        "django":                {"handlers": ["console"],                       "level": "WARNING", "propagate": False},
        "django.request":        {"handlers": ["console", "mail_admins"],        "level": "ERROR",   "propagate": False},
        "django.security":       {"handlers": ["console", "mail_admins"],        "level": "ERROR",   "propagate": False},
        "apps.notifications":    {"handlers": ["console"],                       "level": "INFO",    "propagate": False},
        "apps.bookings":         {"handlers": ["console"],                       "level": "INFO",    "propagate": False},
        "apps.analytics":        {"handlers": ["console"],                       "level": "INFO",    "propagate": False},
        "celery":                {"handlers": ["console"],                       "level": "INFO",    "propagate": False},
        "celery.task":           {"handlers": ["console"],                       "level": "INFO",    "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
