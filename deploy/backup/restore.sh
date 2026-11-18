#!/bin/sh
# Restore the database from one backup. Stop app and worker first.
#
#   docker compose ... stop app worker
#   docker compose ... exec backup studio-restore db-2026-11-18T083000Z.dump
#   docker compose ... start app worker
#
# The file is read from /backups, or downloaded from BACKUP_S3_BUCKET when it is
# not there. --clean drops existing objects first, so the database ends up
# exactly as it was when the backup was taken.
set -eu
# Dumps hold client data: readable by this container's user only, however it is invoked.
umask 077

: "${DATABASE_URL:?DATABASE_URL is required}"
name="${1:?usage: studio-restore <db-YYYY-MM-DDTHHMMSSZ.dump>}"
name="$(basename "$name")"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
file="$BACKUP_DIR/$name"

if [ ! -f "$file" ]; then
    : "${BACKUP_S3_BUCKET:?$file not found locally and BACKUP_S3_BUCKET is not set}"
    AWS_ACCESS_KEY_ID="${BACKUP_S3_ACCESS_KEY_ID:-${S3_ACCESS_KEY_ID:-}}"
    AWS_SECRET_ACCESS_KEY="${BACKUP_S3_SECRET_ACCESS_KEY:-${S3_SECRET_ACCESS_KEY:-}}"
    AWS_DEFAULT_REGION="${BACKUP_S3_REGION:-${S3_REGION_NAME:-auto}}"
    export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION
    endpoint="${BACKUP_S3_ENDPOINT_URL:-${S3_ENDPOINT_URL:-}}"
    src="s3://$BACKUP_S3_BUCKET/${BACKUP_S3_PREFIX:-database}/$name"
    if [ -n "$endpoint" ]; then
        aws s3 cp --only-show-errors --endpoint-url "$endpoint" "$src" "$file"
    else
        aws s3 cp --only-show-errors "$src" "$file"
    fi
fi

pg_restore --clean --if-exists --no-owner --no-privileges --single-transaction --dbname "$DATABASE_URL" "$file"
echo "restore: restored $file"
