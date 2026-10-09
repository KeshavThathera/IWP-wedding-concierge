FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Static assets (CSS, htmx) are committed pre-built, so Node is not needed in the image.
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --no-input

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --no-input && python manage.py seed_demo && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
