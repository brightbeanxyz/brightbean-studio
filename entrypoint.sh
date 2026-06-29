#!/bin/bash
set -e
echo "Running migrations..."
python manage.py migrate --noinput
echo "Syncing media to volume..."
mkdir -p /data/media
cp -rn /app/media/* /data/media/ || true
echo "Check URL patterns for /media/:"
python3 -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from django.urls import get_resolver
resolver = get_resolver()
# Check if /media/ is in url patterns
for p in resolver.url_patterns:
    if 'media' in str(p.pattern):
        print(f'  {p.pattern} -> {p.callback}')
" 2>&1 || echo "URL CHECK FAILED"
echo "Setting up superuser..."
set +e
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@brightbean.local').exists():
    User.objects.create_superuser('admin@brightbean.local', 'BrightBean2026!')
    print('Superuser created.')
else:
    admin = User.objects.get(email='admin@brightbean.local')
    admin.set_password('BrightBean2026!')
    admin.save()
    print('Superuser password reset.')
"
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 2