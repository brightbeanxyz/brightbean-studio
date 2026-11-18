#!/bin/sh
# Take one database backup now.
#
#   1. pg_dump (custom format) into /backups, written under a temporary name and
#      renamed only when complete, so a half-written file is never mistaken for
#      a backup
#   2. copy it to S3-compatible storage when BACKUP_S3_BUCKET is set
#   3. delete local copies older than BACKUP_KEEP_LOCAL_DAYS (default 7);
#      retention in the bucket is a lifecycle rule on the bucket itself
#   4. record the success time for the container healthcheck, and ping
#      BACKUP_HEALTHCHECK_URL if set (e.g. a healthchecks.io check)
#
# Run by hand with:  docker compose ... exec backup studio-backup
set -eu
# Dumps hold client data: readable by this container's user only, however it is invoked.
umask 077

: "${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_LOCAL_DAYS:-7}"

stamp="$(date -u +%Y-%m-%dT%H%M%SZ)"
file="$BACKUP_DIR/db-$stamp.dump"

mkdir -p "$BACKUP_DIR"
pg_dump --format=custom --no-owner --no-privileges --file="$file.partial" "$DATABASE_URL"
mv "$file.partial" "$file"
echo "backup: wrote $file ($(du -h "$file" | cut -f1))"

if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    # Dedicated BACKUP_S3_* credentials win; otherwise reuse the media storage ones.
    AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID:-${S3_ACCESS_KEY_ID:-}}"
    AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY:-${S3_SECRET_ACCESS_KEY:-}}"
    AWS_DEFAULT_REGION="${BACKUP_S3_REGION:-${S3_REGION_NAME:-auto}}"
    export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION
    endpoint="${BACKUP_S3_ENDPOINT_URL:-${S3_ENDPOINT_URL:-}}"
    key="${BACKUP_S3_PREFIX:-database}/$(basename "$file")"
    if [ -n "$endpoint" ]; then
        aws s3 cp --only-show-errors --endpoint-url "$endpoint" "$file" "s3://$BACKUP_S3_BUCKET/$key"
    else
        aws s3 cp --only-show-errors "$file" "s3://$BACKUP_S3_BUCKET/$key"
    fi
    echo "backup: uploaded s3://$BACKUP_S3_BUCKET/$key"
else
    echo "backup: BACKUP_S3_BUCKET is not set; this backup exists only on this server" >&2
fi

find "$BACKUP_DIR" -name 'db-*.dump' -type f -mtime +"$KEEP_DAYS" -delete
date -u +%s > "$BACKUP_DIR/.last-success"

if [ -n "${BACKUP_HEALTHCHECK_URL:-}" ]; then
    wget -q -O /dev/null -T 10 "$BACKUP_HEALTHCHECK_URL" || echo "backup: healthcheck ping failed" >&2
fi
