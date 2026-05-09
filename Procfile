web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --log-level debug
release: python manage.py migrate --noinput
