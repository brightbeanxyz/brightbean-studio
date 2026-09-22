#!/usr/bin/env bash
set -Eeuo pipefail

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.production.example and configure it first." >&2
  exit 1
fi

chmod 600 .env
"${COMPOSE[@]}" up -d --build
"${COMPOSE[@]}" ps
"${COMPOSE[@]}" exec -T app python manage.py check --deploy
echo "Deploy completed. Use '${COMPOSE[*]} logs -f app worker' to monitor."
