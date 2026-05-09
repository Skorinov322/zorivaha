"""
config/celery.py

Celery application for Зори Ваха.

Workers:
  celery -A config worker -l info -c 4

Beat (periodic tasks):
  celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

All periodic tasks are defined in CELERY_BEAT_SCHEDULE below and are
automatically synced to the database on first beat startup.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("zori_vaha")

# Read config from Django settings, all keys prefixed with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all INSTALLED_APPS
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Beat schedule — periodic tasks
# ---------------------------------------------------------------------------
# These are the DEFAULT schedules. They are written to the database on first
# run and can be overridden via Django Admin → Periodic Tasks.
#
# Schedule reference:
#   crontab(minute="*/15")          → every 15 minutes
#   crontab(hour=10, minute=0)      → daily at 10:00
#   crontab(hour=2, minute=0)       → daily at 02:00
#   crontab(hour=1, minute=0,
#           day_of_month=1)         → 1st of every month at 01:00
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {

    # ── Bookings ──────────────────────────────────────────────────────────

    # Cancel PENDING bookings whose auto_cancel_at has passed
    "auto-cancel-expired-bookings": {
        "task":     "apps.bookings.tasks.auto_cancel_expired_bookings",
        "schedule": crontab(minute="*/15"),
        "options":  {"expires": 14 * 60},          # task expires after 14 min
    },

    # Mark CONFIRMED bookings as NO_SHOW if guest didn't arrive within 24h
    "mark-no-show-bookings": {
        "task":     "apps.bookings.tasks.mark_no_show_bookings",
        "schedule": crontab(minute=0, hour="*/1"),  # every hour
        "options":  {"expires": 55 * 60},
    },

    # Send check-in reminder emails to guests arriving tomorrow
    "send-checkin-reminders": {
        "task":     "apps.bookings.tasks.send_checkin_reminders",
        "schedule": crontab(hour=10, minute=0),     # daily at 10:00
        "options":  {"expires": 3600},
    },

    # ── Analytics ─────────────────────────────────────────────────────────

    # Recalculate daily metrics for yesterday
    "calculate-daily-metrics": {
        "task":     "apps.analytics.tasks.calculate_daily_metrics",
        "schedule": crontab(hour=2, minute=0),      # daily at 02:00
        "options":  {"expires": 3600},
    },

    # Snapshot monthly revenue on the 1st of each month
    "snapshot-monthly-revenue": {
        "task":     "apps.analytics.tasks.snapshot_monthly_revenue",
        "schedule": crontab(hour=1, minute=0, day_of_month=1),
        "options":  {"expires": 3600},
    },
}


# ---------------------------------------------------------------------------
# Debug task (useful for testing worker connectivity)
# ---------------------------------------------------------------------------

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
