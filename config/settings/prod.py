"""
config/settings/prod.py — Production settings.

Активируется через: DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from .base import *  # noqa: F401, F403
from decouple import config
import dj_database_url

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

DEBUG = False

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=lambda v: [s.strip() for s in v.split(",")])

# ---------------------------------------------------------------------------
# Security — HTTPS hardening
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT             = True
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

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Database — production pool settings
# ---------------------------------------------------------------------------

# Railway provides DATABASE_URL automatically
DATABASE_URL = config("DATABASE_URL", default=None)
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    DATABASES["default"].update({  # noqa: F405
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c default_transaction_isolation=read committed",
        },
    })

# ---------------------------------------------------------------------------
# Cache — Redis with connection pool (опционально)
# ---------------------------------------------------------------------------

REDIS_URL = config("REDIS_URL", default=None)

if REDIS_URL:
    # Если Redis доступен, используем его для кеша и сессий
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "RETRY_ON_TIMEOUT": True,
                "MAX_CONNECTIONS": 100,
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            },
            "KEY_PREFIX": "zv_prod",
            "TIMEOUT": 300,
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Fallback: используем database cache и database sessions
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
# Sentry — error tracking
# ---------------------------------------------------------------------------

SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.05,
        send_default_pii=False,
        environment="production",
    )

# ---------------------------------------------------------------------------
# Logging — structured, to stdout (Docker/systemd captures it)
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
