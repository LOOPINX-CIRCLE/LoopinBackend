#!/bin/sh
set -e

echo "🚀 Starting Loopin Backend container"

# Derive database host/port from DATABASE_URL when available
if [ -z "$DATABASE_HOST" ] && [ -n "$DATABASE_URL" ]; then
  export DATABASE_HOST="$(python3 -c "import os, urllib.parse as up; url = up.urlparse(os.environ['DATABASE_URL']); print(url.hostname or '')")"
  export DATABASE_PORT="$(python3 -c "import os, urllib.parse as up; url = up.urlparse(os.environ['DATABASE_URL']); print(url.port or 5432)")"
fi

DB_HOST="${DATABASE_HOST:-}"
DB_PORT="${DATABASE_PORT:-5432}"

if [ -n "$DB_HOST" ]; then
  echo "⏳ Waiting for database at ${DB_HOST}:${DB_PORT}"
  until nc -z "$DB_HOST" "$DB_PORT"; do
    echo "   Database not ready, retrying in 2s..."
    sleep 2
  done
fi

echo "✅ Database is reachable, running migrations (fake initial enabled)"
python3 manage.py migrate --noinput --fake-initial

if [ "${COLLECT_STATIC:-true}" = "true" ]; then
  echo "📦 Collecting static assets"
  python3 manage.py collectstatic --noinput
fi

if [ -f "/app/setup_data.py" ] && [ "${RUN_SETUP_DATA:-false}" = "true" ]; then
  echo "🛠  Running setup data script"
  python3 setup_data.py
fi

echo "🚀 Launching application: $*"
exec "$@"


