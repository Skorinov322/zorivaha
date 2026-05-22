"""
Development settings.

Email backends available (set EMAIL_BACKEND_DEV in .env):
  console  — print to terminal (default)
  file     — write to EMAIL_FILE_PATH (inspect rendered HTML)
  dummy    — discard silently
  smtp     — real SMTP (set EMAIL_HOST_USER / EMAIL_HOST_PASSWORD)
"""

from .base import *  # noqa

DEBUG = True

# Temporarily disabled debug_toolbar
# INSTALLED_APPS += ["debug_toolbar"]  # noqa

# MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa

INTERNAL_IPS = ["127.0.0.1"]

# ---------------------------------------------------------------------------
# Static files — disable WhiteNoise storage in development
# ---------------------------------------------------------------------------

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa

# Add middleware to disable caching
MIDDLEWARE.insert(0, "apps.core.middleware.DisableCacheMiddleware")  # noqa

# ---------------------------------------------------------------------------
# Email — development
# ---------------------------------------------------------------------------

_EMAIL_BACKEND_DEV = config("EMAIL_BACKEND_DEV", default="console")

if _EMAIL_BACKEND_DEV == "file":
    EMAIL_BACKEND  = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = BASE_DIR / "dev_emails"   # noqa — emails saved as .eml files
elif _EMAIL_BACKEND_DEV == "dummy":
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
elif _EMAIL_BACKEND_DEV == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    # Uses EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD from .env
else:
    # Default: console — prints to runserver terminal
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Cache — use local memory cache in development
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Auth — relaxed for development
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = []

# ---------------------------------------------------------------------------
# DB — no persistent connections in dev
# ---------------------------------------------------------------------------

DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa

# ---------------------------------------------------------------------------
# Logging — show email task logs in terminal
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "format": "\033[36m[%(asctime)s]\033[0m \033[1m%(name)s\033[0m %(levelname)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
    },
    "loggers": {
        "apps.notifications": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "apps.bookings":      {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "celery":             {"handlers": ["console"], "level": "INFO",  "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
