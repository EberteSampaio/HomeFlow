web: gunicorn config.wsgi:application --bind 0.0.0.0:8000
release: python manage.py migrate --settings=config.settings.prod
