release: python manage.py migrate
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4
worker: python manage.py process_tasks --duration 3600
