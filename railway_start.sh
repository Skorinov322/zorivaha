#!/usr/bin/env bash
# Railway startup script - runs migrations before starting the server
set -o errexit

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.prod}

echo "Running database migrations..."
python manage.py migrate --no-input

echo "Creating cache table..."
python manage.py createcachetable || echo "Cache table already exists or not needed"

echo "Starting Gunicorn server..."
exec gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
