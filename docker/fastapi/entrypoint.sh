#!/usr/bin/env bash
# ============================================================================
# AgroSense Cafe - FastAPI Container Entrypoint Script
# File: /docker/fastapi/entrypoint.sh
# ============================================================================
set -e

echo "[START] Starting AgroSense FastAPI Service..."

# Wait for PostgreSQL to be ready if host & port are set
if [ -n "${POSTGRES_HOST}" ]; then
  POSTGRES_PORT="${POSTGRES_PORT:-5432}"
  echo "[WAIT] Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
  while ! nc -z "${POSTGRES_HOST}" "${POSTGRES_PORT}"; do
    sleep 1
  done
  echo "[OK] PostgreSQL is reachable."
fi

# Run database migrations with Alembic before starting the application
echo "[MIGRATE] Checking and applying database migrations with Alembic..."
if [ -f "alembic.ini" ] || [ -f "apps/api/alembic.ini" ]; then
  if command -v alembic > /dev/null 2>&1; then
    alembic upgrade head
    echo "[OK] Database migrations completed successfully."
  else
    echo "[WARN] Alembic not found in PATH, skipping migrations."
  fi
else
  echo "[INFO] No alembic.ini found. Skipping automatic migration step."
fi

# Determine main app entrypoint
APP_MODULE="${APP_MODULE:-apps.api.src.agrosense_api.main:app}"
if ! python -c "import ${APP_MODULE%%:*}" > /dev/null 2>&1; then
  # Fallback for standard app.main:app structure
  APP_MODULE="${APP_MODULE:-app.main:app}"
fi

echo "[START] Launching Uvicorn server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
