#!/bin/sh
# Healthy when the last successful backup is less than 26 hours old.
set -eu
marker="${BACKUP_DIR:-/backups}/.last-success"
[ -f "$marker" ] || exit 1
last="$(cat "$marker")"
[ $(( $(date -u +%s) - last )) -lt 93600 ]
