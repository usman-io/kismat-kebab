#!/usr/bin/env bash

set -e

echo "==> Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Running Django system checks..."
python manage.py check --deploy

echo "==> Creating database migrations..."
python manage.py makemigrations --noinput

echo "==> Applying database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

python manage.py create_superuser

echo "==> Deployment build completed successfully!"
