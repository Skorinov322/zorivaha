#!/usr/bin/env bash
set -o errexit

echo "==> Running database migrations..."
python manage.py migrate --noinput --run-syncdb

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
