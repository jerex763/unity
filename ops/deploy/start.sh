#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set to the pooled runtime database URL}"
: "${MIGRATION_DATABASE_URL:?MIGRATION_DATABASE_URL must be set to the direct migration database URL}"

cd /app/backend

DATABASE_URL="$MIGRATION_DATABASE_URL" python manage.py migrate --noinput

exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --access-logfile - \
    --error-logfile - \
    --timeout 60
