#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Creating cache table..."
python manage.py createcachetable || true

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Build completed successfully!"
