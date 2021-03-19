web: gunicorn bhr_site.wsgi --workers=8 --timeout=45 --max-requests=500 --log-file -
release: python manage.py migrate --noinput
