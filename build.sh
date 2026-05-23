#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings.prod}

echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

echo "Build completed successfully!"

