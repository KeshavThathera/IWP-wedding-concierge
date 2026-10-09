#!/usr/bin/env bash
# Production build used by Render (and handy anywhere else).
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py seed_demo
