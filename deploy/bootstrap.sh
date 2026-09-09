#!/usr/bin/env bash
# Provision/refresh the app host. Idempotent — safe to re-run on every deploy.
# Run from the repo checkout on the server, with .env already in place.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo ".env missing — copy .env.example and fill it in first" >&2; exit 1; }
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
compose() { docker compose -f docker-compose.yml -f docker-compose.prod.yml "$@"; }
compose up -d --build
compose exec -T app python manage.py check --deploy
