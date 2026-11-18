# Deploying Brown Creative Studio

Production runs with Docker Compose on one VPS, with media in S3-compatible storage.
At the expected scale (5 clients, 3 studio users) a 2 vCPU / 4 GB server is plenty.

Containers: `app` (Gunicorn), `worker` (publishing and background jobs), `postgres`,
`caddy` (HTTPS), a one-shot `migrate`, and `backup` (nightly database backups).
Only Caddy listens on the internet, on ports 80 and 443.

## 1. Before the first deploy

- A domain or subdomain for the app, e.g. `studio.example.com`, with an A record
  pointing at the server.
- Docker with Compose 2.24 or newer (`docker compose version`).
- An S3-compatible bucket for media (Cloudflare R2, Backblaze B2, AWS S3...). Keep it
  private: the app hands out short-lived signed links.
- A second private bucket (or a prefix with its own key) for database backups, with
  a lifecycle rule that deletes objects after 30 days and versioning switched on.
- An SMTP provider for email (Resend, Postmark, Amazon SES...), with SPF and DKIM set
  up for the sending domain.
- A Sentry project for error reports, and an uptime monitor pointed at `https://<domain>/health/`.
- The public fork on GitHub, so the Source code link has somewhere to point.

## 2. Configure

```bash
git clone https://github.com/<owner>/<fork>.git brown-creative-studio
cd brown-creative-studio
cp .env.example .env
```

Edit `.env`. The values that must change for production:

| Variable | Value |
|---|---|
| `SECRET_KEY`, `ENCRYPTION_KEY_SALT` | Long random strings (`openssl rand -hex 32`). They encrypt stored platform tokens; keep a copy somewhere safe, because a database backup cannot decrypt tokens without them. |
| `DEBUG` | `false` |
| `ALLOWED_HOSTS`, `APP_URL`, `APP_DOMAIN` | `studio.example.com`, `https://studio.example.com`, `studio.example.com` |
| `POSTGRES_PASSWORD` | A long random string |
| `DATABASE_URL` | `postgres://postgres:<POSTGRES_PASSWORD>@postgres:5432/brightbean` |
| `SIGNUP_MODE` | `invite` (production refuses `open`) |
| `STORAGE_BACKEND`, `S3_*` | `s3` and the media bucket's endpoint, keys and name |
| `CADDY_MEDIA_ROOT` | `/var/empty` once storage is `s3` |
| `EMAIL_BACKEND_TYPE`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | `smtp` and the provider's settings; the from address on the studio's domain |
| `SENTRY_DSN` | The Sentry project's DSN |
| `SITE_NAME`, `SUPPORT_EMAIL`, `TERMS_URL`, `PRIVACY_URL` | The studio's name, support address and published policies |
| `SOURCE_CODE_URL` | `https://github.com/<owner>/<fork>` |
| `BACKUP_S3_*` | The backup bucket. Without it, backups stay on the server only. |
| `INTELLIGENCE_*`, `STUDIO_*` | Leave blank |

Do not set `SOURCE_COMMIT` in `.env`. The deploy script bakes it into the image, and
a value in `.env` would override it.

## 3. Deploy

```bash
deploy/deploy.sh
```

The script refuses to deploy uncommitted changes, or a commit that is not on the
public fork yet, because users could not get that source. It builds the images with
the commit baked in, then runs `python manage.py check --deploy --fail-level ERROR`
inside the new image. Errors stop the deploy and warnings are printed. Only then does
it replace the running containers.

| Check | Level | Meaning |
|---|---|---|
| `about.E001` | Error | `SOURCE_CODE_URL` missing or not https |
| `about.E002` | Error | The running commit is unknown |
| `about.W001` | Warning | `SIGNUP_MODE=open` |
| `about.W002` | Warning | Media on local disk instead of S3 |
| `about.W003` | Warning | No `SENTRY_DSN` |
| `about.W004` | Warning | No `SUPPORT_EMAIL` |
| `about.W005` | Warning | `TERMS_URL` or `PRIVACY_URL` missing |
| `about.W006` | Warning | The Intelligence add-on is enabled |
| `about.W007` | Warning | Email would be printed to the log, or is unconfigured |

## 4. First account

Sign-up is invite-only, so create the studio owner from the command line, then sign
in and create the organization:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.studio.yml \
  exec app python manage.py createsuperuser
```

Everyone else joins by invitation from the app.

## 5. Updating

```bash
git pull
deploy/deploy.sh
```

Migrations run automatically in the `migrate` container before `app` and `worker` start.

## 6. Backups

The `backup` container runs `pg_dump` every day at `BACKUP_TIME_UTC` (default
08:30 UTC, which is 02:30 studio time). It keeps 7 days on the server and uploads
each dump to `BACKUP_S3_BUCKET`. Media needs no separate backup when it lives in S3
with versioning on. The container turns unhealthy when the last success is more than
26 hours old (`docker compose ... ps`). Set `BACKUP_HEALTHCHECK_URL` to a
dead-man's-switch service to be alerted.

```bash
# alias for the commands below
dc="docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.studio.yml"

$dc exec backup studio-backup                 # take a backup now
$dc exec backup ls -lh /backups               # list local backups

# restore one (downloads it from the bucket if it is not on the server)
$dc stop app worker
$dc exec backup studio-restore db-2026-11-18T083000Z.dump
$dc start app worker
```

Restore a backup into a scratch server every quarter to confirm the backups work.
`.env` is not in the backup. Keep it, especially `SECRET_KEY` and
`ENCRYPTION_KEY_SALT`, in the studio's password manager.

## What has been verified

| Part | Status |
|---|---|
| Production image build with `SOURCE_COMMIT`, `.dockerignore` | Tested locally with Docker |
| Stack start, migrations, `/health/`, source page naming the built commit | Tested locally with Docker |
| Postgres and Gunicorn not published on the host | Tested locally with Docker |
| `check --deploy` errors and warnings | Tested (unit tests and in the image) |
| `pg_dump` backup, file permissions (600), healthcheck, restore of a chosen backup | Tested locally with Docker |
| Deletion of local backups older than 7 days | Not exercised (no old files existed) |
| Upload of backups to S3 | **Not tested** against a real bucket |
| S3 media storage | Upstream code path, **not tested** here |
| SMTP delivery, Sentry reporting, Caddy certificates for a real domain | **Not tested**: they need real accounts and a public server |
