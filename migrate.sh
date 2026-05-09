#!/usr/bin/env bash
set -o errexit

echo "Running database migrations..."
python manage.py migrate --no-input --run-syncdb
echo "Migrations completed!"
