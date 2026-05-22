"""
Base settings for Зори Ваха hotel project.
All environment-specific settings inherit from this file.
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost", cast=Csv())

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "django_filters",
    # Temporarily disabled Celery apps
    # "django_celery_beat",
    # "django_celery_results",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
]

LOCAL_APPS = [
    "apps.core",
    "apps.setup",
    "apps.accounts",
    "apps.hotel",
    "apps.bookings",
    "apps.crm",
    "apps.notifications",
    "apps.analytics",
    "apps.content",
    "apps.reports",
    "apps.dashboard",
    "apps.reviews",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # First-run setup guard — must be AFTER auth middleware
    "apps.setup.middleware.SetupMiddleware",
    # Page view tracking for analytics
    "apps.analytics.middleware.PageViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
                "apps.core.context_processors.contact_messages_count",
                # Injects perms_ctx into every template
                "apps.core.permissions.permissions_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# For production, use MySQL (uncomment below and comment SQLite above)
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.mysql",
#         "NAME": config("DB_NAME", default="zori_vaha"),
#         "USER": config("DB_USER", default="root"),
#         "PASSWORD": config("DB_PASSWORD", default=""),
#         "HOST": config("DB_HOST", default="localhost"),
#         "PORT": config("DB_PORT", default="3306"),
#         "CONN_MAX_AGE": 60,
#         "OPTIONS": {
#             "connect_timeout": 10,
#             "charset": "utf8mb4",
#         },
#     }
# }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/cabinet/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Allauth
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Allauth
# ---------------------------------------------------------------------------

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED        = True
ACCOUNT_USERNAME_REQUIRED      = False
ACCOUNT_EMAIL_VERIFICATION     = "none"   # отключаем обязаостиницаное подтверждение email
ACCOUNT_UNIQUE_EMAIL           = True

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------------

STATIC_URL = config("STATIC_URL", default="/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Email — SMTP configuration
# ---------------------------------------------------------------------------
#
# Supported providers:
#   Gmail:   EMAIL_HOST=smtp.gmail.com  PORT=587  TLS=True
#   Yandex:  EMAIL_HOST=smtp.yandex.ru  PORT=587  TLS=True
#   Mail.ru: EMAIL_HOST=smtp.mail.ru    PORT=587  TLS=True
#   Custom:  Set EMAIL_HOST / EMAIL_PORT / EMAIL_USE_SSL as needed
#
# For Gmail you MUST use an App Password (not your account password):
#   Google Account → Security → 2-Step Verification → App passwords
#
# ---------------------------------------------------------------------------

EMAIL_BACKEND     = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST        = config("EMAIL_HOST",        default="smtp.gmail.com")
EMAIL_PORT        = config("EMAIL_PORT",        default=587, cast=int)
EMAIL_USE_TLS     = config("EMAIL_USE_TLS",     default=True,  cast=bool)
EMAIL_HOST_USER   = config("EMAIL_HOST_USER",   default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# Email addresses
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@zorivaha.ru")
CONTACT_EMAIL = config("CONTACT_EMAIL", default="info@zorivaha.ru")
CONTACT_PHONE = config("CONTACT_PHONE", default="+7 (928) 000-00-00")
EMAIL_USE_SSL     = config("EMAIL_USE_SSL",     default=False, cast=bool)
EMAIL_HOST_USER   = config("EMAIL_HOST_USER",   default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT     = config("EMAIL_TIMEOUT",     default=10, cast=int)  # seconds

# "From" address shown to recipients
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="Зори Ваха <noreply@zorivaha.ru>",
)
# Address for Django system emails (500 errors, etc.)
SERVER_EMAIL = config("SERVER_EMAIL", default="errors@zorivaha.ru")

# Admins who receive error emails in production
ADMINS = [
    ("Admin", config("ADMIN_EMAIL", default="admin@zorivaha.ru")),
]

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL            = config("CELERY_BROKER_URL",    default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND        = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT        = ["json"]
CELERY_TASK_SERIALIZER       = "json"
CELERY_RESULT_SERIALIZER     = "json"
CELERY_TIMEZONE              = TIME_ZONE
CELERY_ENABLE_UTC            = True
CELERY_BEAT_SCHEDULER        = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_TRACK_STARTED    = True
CELERY_TASK_TIME_LIMIT       = 30 * 60          # hard limit: 30 min
CELERY_TASK_SOFT_TIME_LIMIT  = 25 * 60          # soft limit: 25 min (raises SoftTimeLimitExceeded)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1           # fair dispatch — important for long tasks
CELERY_TASK_ACKS_LATE        = True             # ack after task completes, not before
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200         # restart worker after 200 tasks (memory leak guard)

# Store task results in DB (django_celery_results)
CELERY_RESULT_EXTENDED        = True
DJANGO_CELERY_RESULTS_TASK_ID_MAX_LENGTH = 191

# Retry policy defaults
CELERY_TASK_MAX_RETRIES      = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60            # seconds

# Beat: sync schedule to DB on startup
CELERY_BEAT_SYNC_EVERY       = 1

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "max_connections": 50,
        },
        "KEY_PREFIX": "zv",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

SESSION_ENGINE      = "django.contrib.sessions.backends.db"
SESSION_SAVE_EVERY_REQUEST = True

# Redis connection for Celery broker (separate from cache)
# db0 = broker, db1 = results, db2 = cache (via REDIS_URL)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 3600,          # 1 hour — tasks invisible to other workers
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.5,
}

# ---------------------------------------------------------------------------
# Crispy Forms
# ---------------------------------------------------------------------------

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ---------------------------------------------------------------------------
# Security headers (overridden in prod)
# ---------------------------------------------------------------------------

SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
