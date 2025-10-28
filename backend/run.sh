#!/usr/bin/env bash
set -e
# activate venv if exists
if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate
fi

# load environment variables from .env if present
if [ -f .env ]; then
  # set -a automatically exports all variables defined
  set -a
  . ./.env
  set +a
fi

export DATABASE_URL=${DATABASE_URL:-sqlite:///./dev.db}
export APP_HOST=${APP_HOST:-127.0.0.1}
export APP_PORT=${APP_PORT:-8000}

uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT} --reload
