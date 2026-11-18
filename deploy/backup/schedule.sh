#!/bin/sh
# Run studio-backup once a day at BACKUP_TIME_UTC (HH:MM, default 08:30 UTC,
# which is 02:30 in America/Guatemala and America/Belize). A failed run is
# logged and retried the next day; the healthcheck turns the container
# unhealthy after 26 hours without a success.
set -eu

BACKUP_TIME_UTC="${BACKUP_TIME_UTC:-08:30}"
case "$BACKUP_TIME_UTC" in
    [0-2][0-9]:[0-5][0-9]) ;;
    *) echo "backup: BACKUP_TIME_UTC must be HH:MM, got '$BACKUP_TIME_UTC'" >&2; exit 1 ;;
esac

if [ "${BACKUP_ON_START:-false}" = "true" ]; then
    studio-backup || echo "backup: run on start failed" >&2
fi

while true; do
    now="$(date -u +%s)"
    target="$(date -u -d "$(date -u +%Y-%m-%d) $BACKUP_TIME_UTC" +%s)"
    if [ "$target" -le "$now" ]; then
        target=$((target + 86400))
    fi
    echo "backup: next run at $(date -u -d "@$target" '+%Y-%m-%d %H:%M UTC')"
    sleep $((target - now))
    studio-backup || echo "backup: scheduled run failed" >&2
done
