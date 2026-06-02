#!/bin/sh
set -e

if [ "$DB_ENGINE" = "postgresql" ] && [ "$POSTGRES_HOST" ]; then
  echo "Aguardando PostgreSQL em $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
