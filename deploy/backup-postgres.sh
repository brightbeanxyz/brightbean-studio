#!/usr/bin/env bash
set -Eeuo pipefail

backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
filename="$backup_dir/brightbean-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-brightbean}" | gzip > "$filename"
chmod 600 "$filename"
echo "Backup written to $filename"
