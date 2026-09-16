#!/bin/sh
set -e

python manage.py wait_for_db
python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn secret_santa.wsgi:application --bind 0.0.0.0:8000