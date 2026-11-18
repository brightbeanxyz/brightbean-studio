# Nightly PostgreSQL backups for Brown Creative Studio. See docs/fork/deployment.md.
FROM postgres:16-alpine

RUN apk add --no-cache aws-cli

COPY backup.sh /usr/local/bin/studio-backup
COPY schedule.sh /usr/local/bin/studio-backup-schedule
COPY healthy.sh /usr/local/bin/studio-backup-healthy
COPY restore.sh /usr/local/bin/studio-restore
RUN chmod 0755 /usr/local/bin/studio-backup /usr/local/bin/studio-backup-schedule /usr/local/bin/studio-backup-healthy /usr/local/bin/studio-restore

ENTRYPOINT ["/usr/local/bin/studio-backup-schedule"]
