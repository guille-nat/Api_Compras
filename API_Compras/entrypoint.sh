#!/usr/bin/env bash
set -e

DB_HOST="${MYSQL_HOST:-db}"
DB_PORT="${MYSQL_PORT:-3306}"

echo "Esperando a la base de datos en ${DB_HOST}:${DB_PORT}..."
until mysqladmin ping -h"${DB_HOST}" -P"${DB_PORT}" --silent; do
  sleep 1
done

echo "Base de datos lista. Migrando..."
python manage.py migrate --noinput

if [ "${CREATE_SUPERUSER:-false}" = "true" ]; then
  echo "Creando superusuario (si no existe)..."
  python manage.py shell <<'PYCODE'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(
    username=os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"),
    defaults={
        "email": os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com"),
        "is_staff": True,
        "is_superuser": True
    }
)
if created:
    u.set_password(os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin"))
    u.save()
    print("Superusuario creado.")
else:
    print("Superusuario ya existía.")
PYCODE
fi

echo "Levantando runserver..."
exec python manage.py runserver 0.0.0.0:8000