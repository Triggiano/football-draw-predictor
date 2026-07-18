#!/usr/bin/env bash
set -e

# Load .env if present
if [ -f /app/.env ]; then
  export $(grep -v '^#' /app/.env | xargs)
fi

echo "Running alembic upgrade head (if migrations exist)"
if command -v alembic >/dev/null 2>&1; then
  alembic -c /app/alembic.ini upgrade head || echo "alembic upgrade failed or no migrations"
else
  echo "alembic not installed in image"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
