# Technical Architecture

Companion to: Feature Specification v2

---

## 1. Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0, Django REST Framework |
| Frontend | Django templates, HTMX, Alpine.js |
| CSS | Tailwind CSS 4 via django-tailwind |
| Database | PostgreSQL 16+ (also serves as job queue) |
| Background jobs | django-background-tasks (PostgreSQL-backed, no Redis/Celery) |
| Caching | Redis (optional - not required at launch, add later for real-time features) |
| Media storage | Local filesystem (default) or S3-compatible (Cloudflare R2, AWS S3, MinIO, Backblaze B2) |
| Media processing | FFmpeg (video), Pillow (images) |
| Email | Resend (cloud), SMTP-configurable (self-hosted) |
| Web server | Gunicorn behind Caddy (auto-HTTPS) |

---

## 2. Project Structure

```
project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/               # F-5.1: Auth, registration, 2FA
│   ├── organizations/          # F-1.1: Org management
│   ├── workspaces/             # F-1.2: Workspace CRUD
│   ├── members/                # F-1.3: RBAC, invitations
│   ├── client_portal/          # F-1.4: Client views, magic links
│   ├── credentials/            # F-1.5: Platform API credentials
│   ├── settings_manager/       # F-1.6: Configurable defaults
│   ├── onboarding/             # F-1.7: Client onboarding, checklist
│   ├── composer/               # F-2.1: Post composer
│   ├── approvals/              # F-2.2: Approval workflows
│   ├── calendar/               # F-2.3: Calendar, scheduling, queues
│   ├── publisher/              # F-2.4: Publishing engine
│   ├── social_accounts/        # F-2.5: OAuth connection flows
│   ├── inbox/                  # F-3.1: Unified social inbox
│   ├── analytics/              # F-4.1, F-4.2: Analytics
│   ├── reports/                # F-4.3: Report builder
│   ├── whitelabel/             # F-5.2: White-label config
│   ├── integrations/           # F-5.3: Canva, stock media, Slack, AI, API, webhooks
│   ├── media_library/          # F-6.1: Media assets
│   └── notifications/          # F-7.1: Notification engine
├── providers/                  # Social platform provider modules
│   ├── base.py                 # Abstract SocialProvider interface
│   ├── facebook.py
│   ├── instagram.py
│   ├── linkedin.py
│   ├── tiktok.py
│   ├── youtube.py
│   ├── pinterest.py
│   ├── threads.py
│   ├── bluesky.py
│   ├── google_business.py
│   └── mastodon.py
├── theme/                      # django-tailwind theme app
│   └── static_src/
│       ├── src/
│       │   └── styles.css      # Tailwind directives + custom CSS
│       └── tailwind.config.js
├── templates/
│   ├── base.html
│   └── components/             # Reusable HTMX partials
├── static/                     # Compiled CSS, vendored JS (HTMX, Alpine.js)
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── railway.toml
├── render.yaml
├── Procfile                    # Heroku
├── app.json                    # Heroku "Deploy" button manifest
└── README.md
```

---

## 3. Frontend Architecture

Server-rendered HTML. No JavaScript build step for the application. Only Tailwind CSS requires a build step (handled by django-tailwind).

**Tailwind CSS:**
- Managed via `django-tailwind`, which wraps Tailwind CLI in a Django app.
- Development: `python manage.py tailwind start` watches templates and recompiles.
- Production: `python manage.py tailwind build` in the Dockerfile produces minified CSS.
- `tailwind.config.js` content paths include all template directories for correct purging.
- White-label theming (F-5.2): agency brand colors are injected as CSS custom properties on the `<html>` element at runtime, overriding Tailwind's default color tokens. This allows per-org color customization without rebuilding CSS.

**HTMX handles:**
- Page partials, form submissions, view switching without full reloads.
- Composer live preview: debounced (500ms) `hx-post` returns rendered preview HTML.
- Approval actions: inline status updates via `hx-post` + `hx-swap`.
- Inbox infinite scroll: `hx-get` with `hx-trigger="revealed"`.
- Calendar view switching: swap calendar container via `hx-get`.
- Notification badge: polled every 30 seconds (upgrade to WebSocket with Redis later).

**Alpine.js handles (client-side only):**
- Drag-and-drop: calendar rescheduling, media reordering, report section reordering. Fires `hx-post` on drop.
- UI interactions: dropdowns, modals, tabs, toggles, emoji picker.
- Character counter: calculated client-side from platform limits in data attributes.

**Known limits:**
- Composer preview requires server round-trips. Mitigated by keeping the preview endpoint stateless (no DB queries).
- Calendar drag-and-drop uses optimistic UI (Alpine moves the card immediately, HTMX posts update, reverts on failure).
- Real-time inbox requires Redis + django-channels. Launch with 30-second polling.

---

## 4. Social Provider Architecture

Each platform has a dedicated module implementing an abstract base class. No third-party unified API providers.

```
SocialProvider (abstract):

  get_auth_url(redirect_uri, state) → str
  exchange_code(code, redirect_uri) → OAuthTokens
  refresh_token(refresh_token) → OAuthTokens
  get_profile(access_token) → AccountProfile
  publish_post(access_token, content) → PublishResult
  publish_comment(access_token, post_id, text) → CommentResult
  get_post_metrics(access_token, post_id) → PostMetrics
  get_account_metrics(access_token, date_range) → AccountMetrics
  get_audience_demographics(access_token) → Demographics
  get_messages(access_token, since) → list[InboxMessage]
  reply_to_message(access_token, message_id, text) → ReplyResult
  revoke_token(access_token) → bool

  platform_name → str
  max_caption_length → int
  supported_post_types → list[PostType]
  supported_media_types → list[MediaType]
  rate_limits → RateLimitConfig
```

**Adding a new platform:** Create one file in `providers/`, register in provider registry, add to `Platform` enum. No changes to publisher, inbox, analytics, or any other system.

---

## 5. Database

PostgreSQL as data store + job queue. django-background-tasks stores jobs in a PostgreSQL table polled by the worker. Eliminates Redis as a hard dependency.

**Background jobs:**

| Job | Frequency |
|-----|-----------|
| Publish scheduled posts | Every 15 seconds |
| Sync inbox messages | Every 5 minutes per account |
| Collect post analytics | Hourly (<48h old), daily (older) |
| Collect account metrics | Daily |
| Collect audience demographics | Weekly |
| Refresh OAuth tokens | Hourly (tokens expiring within 24h) |
| Generate recurring posts | Daily (90-day lookahead) |
| Generate scheduled reports | Per schedule config |
| Process media for upcoming posts | Posts within 60 minutes of publish |
| Send notifications | On event trigger |
| Health check accounts | Every 6 hours |
| Cleanup expired data | Daily |

All intervals configurable via F-1.6.

**Data isolation:** Custom Django model manager auto-filters all queries by `organization_id`/`workspace_id`. Applied at ORM layer. Cloud version adds PostgreSQL Row-Level Security as defense-in-depth.

**Encryption:** OAuth tokens, API keys, credentials encrypted with AES-256-GCM via custom model fields. Key derived from `SECRET_KEY` env var via HKDF. Rotation supported via management command.

---

## 6. Deployment

### 6.1 Docker Compose (all deployments)

**Development - 3 containers:**

```
app:      Django runserver + volume mount
worker:   python manage.py process_tasks
postgres: postgres:16-alpine

Tailwind: `python manage.py tailwind start` on host (watches + recompiles)
```

**Production - 4 containers:**

```
app:      Gunicorn (4 workers, 2 threads)
worker:   python manage.py process_tasks
postgres: postgres:16-alpine
caddy:    Reverse proxy + auto-TLS

Tailwind: built during Docker image build
```

### 6.2 Cloud (Hetzner VPS)

Production Docker Compose on a single VPS.

| Resource | Spec | Cost |
|----------|------|------|
| VPS | Hetzner CX32 (4 vCPU, 8GB RAM) | €7.59/month |
| Media | Cloudflare R2 (10GB free) | ~€0 |
| Email | Resend (3,000/month free, $20/month for 50k) | ~€0 |
| Monitoring | Sentry + UptimeRobot free tiers | €0 |
| **Total** | | **~€10/month** |

Automated deploy: GitHub Actions → SSH → pull + restart. Backups: daily `pg_dump` to R2.

**Scaling path:**

| Action | Added cost |
|--------|-----------|
| Managed PostgreSQL | +€18/month |
| Second VPS for workers | +€7.59/month |
| Load balancer + second web VPS | +€13/month |

### 6.3 Self-Hosted: Railway

Config: `railway.toml` in repo. Three services: web, worker, managed PostgreSQL.

Ephemeral filesystem - `STORAGE_BACKEND` must be `s3`. App detects Railway via `RAILWAY_ENVIRONMENT` and warns on misconfiguration.

**Cost:** ~$15-30/month.

### 6.4 Self-Hosted: Render

Config: `render.yaml` blueprint in repo. Three services: web ($7), worker ($7), PostgreSQL ($7).

Free tier sleeps (breaks worker) - must use paid. Ephemeral disk - requires S3.

**Cost:** $21/month minimum.

### 6.5 Self-Hosted: Heroku

Config: `Procfile` + `app.json` (enables "Deploy to Heroku" button).

**Procfile:**
```
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 2
worker: python manage.py process_tasks
```

**app.json** pre-configures: Basic dynos, PostgreSQL Essential-0, auto-generated SECRET_KEY, post-deploy migration, env var prompts. README includes deploy button linking to `https://heroku.com/deploy?template=https://github.com/yourorg/social-platform` - running app in ~5 minutes.

| Component | Plan | Cost |
|-----------|------|------|
| Web dyno | Basic | $7/month |
| Worker dyno | Basic | $7/month |
| PostgreSQL | Essential-0 (1GB, 20 conn) | $5/month |
| **Total** | | **$19/month** |

**Critical warnings:**
- **Eco dynos break the app.** They sleep after 30 minutes - worker stops, nothing publishes. Must use Basic+.
- **Ephemeral filesystem.** `STORAGE_BACKEND` must be `s3`. App detects Heroku via `DYNO` env var and warns.
- **20 connection limit.** Upgrade to Essential-1 ($15/month, 40 conn) if scaling beyond 2 web dynos.
- **White-label custom domains** require manual `heroku domains:add` per domain. No on-demand TLS.
- **Static files** served via `whitenoise` (no separate hosting needed).

### 6.6 Self-Hosted: Bare VPS (Docker Compose)

Primary documented path. Any Linux VPS with Docker.

```
1. Provision VPS (min 2 vCPU, 4GB RAM)
2. Install Docker: curl -fsSL https://get.docker.com | sh
3. Clone repo, cp .env.example .env, fill in secrets
4. docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
5. docker compose exec app python manage.py migrate
6. Open browser, complete first-run setup wizard
```

Upgrade: `git pull && docker compose up -d --build && docker compose exec app python manage.py migrate`

Media: local filesystem by default (Docker volume). Switch to S3 via env var.

---

## 7. Media Storage

Single env var switches backend:

```
STORAGE_BACKEND=local  →  FileSystemStorage (Docker volume)
STORAGE_BACKEND=s3     →  S3Boto3Storage via django-storages
```

**Processing pipeline:**
- *On upload:* save, extract metadata, generate thumbnail (Pillow/FFmpeg).
- *Before publish:* background job processes media for posts within 60 minutes. Resizes images, converts formats, transcodes video (H.264/AAC/MP4). Processed versions stored alongside originals.
- *FFmpeg limits:* max 2 concurrent transcodes (configurable), 5-minute timeout per video.

---

## 8. Security

| Concern | Approach |
|---------|----------|
| Passwords | bcrypt, cost factor 12 |
| Sessions | DB-backed, HTTP-only/Secure/SameSite=Lax, 30-day sliding |
| OAuth login | django-allauth (Google, GitHub) |
| 2FA | TOTP via django-otp, encrypted secret, bcrypt-hashed recovery codes |
| Magic links | 32-byte token, stored as SHA-256 hash |
| API keys | 40-byte token, stored as SHA-256 hash, scoped per org |
| Encryption at rest | AES-256-GCM for tokens/keys/credentials, key from env var |
| Data isolation | Custom ORM manager auto-filters by org_id/workspace_id |
| CSRF | Django middleware, HTMX auto-includes token |
| CSP | Restrictive policy via Django's built-in CSP middleware |
| Rate limiting | django-ratelimit on login, API, OAuth endpoints |
| Audit log | Append-only, destructive actions, retained 1 year |
| GDPR | Export + deletion per workspace/org |

---

## 9. Backup & Restore

### Cloud Version

Daily automated `pg_dump` to Cloudflare R2 via cron on the VPS. Retain 30 daily backups. Media is already on R2 (inherently durable).

### Self-Hosted

The repo includes a backup management command and documented restore procedure.

**What to back up:**
- PostgreSQL database (all application data).
- Media storage: the Docker volume (`media_data`) if using local filesystem, or nothing additional if using S3 (already durable).

**Backup command:**

```
# Included management command - dumps database + lists media volume location
python manage.py backup --output /path/to/backup/

# Produces:
#   /path/to/backup/db_2026-03-25.sql.gz    (gzipped pg_dump)
#   /path/to/backup/manifest.json            (backup metadata: timestamp, app version, storage backend, media path)
```

Via Docker:
```
docker compose exec app python manage.py backup --output /backups/
```

The backup command:
1. Runs `pg_dump` against the configured `DATABASE_URL`, compresses with gzip.
2. If `STORAGE_BACKEND=local`, records the media volume path in the manifest so the user knows to also back up that Docker volume.
3. If `STORAGE_BACKEND=s3`, records the bucket name - no media backup needed.
4. Writes a `manifest.json` with: timestamp, application version, database size, storage backend, media path or bucket name.

**Restore command:**

```
python manage.py restore /path/to/backup/db_2026-03-25.sql.gz
```

The restore command:
1. Confirms with the user that this will overwrite all current data.
2. Drops and recreates the database.
3. Loads the gzipped SQL dump.
4. Runs any pending migrations (in case the backup is from an older version).
5. If `STORAGE_BACKEND=local`, prints a reminder to restore the media Docker volume from the user's own volume backup.

**Automated backups (documented, not built-in):**

The README documents a cron job pattern for automated backups:
```
# Daily backup at 2:00 AM, retain 30 days
0 2 * * * docker compose exec -T app python manage.py backup --output /backups/ && find /backups/ -name "db_*.sql.gz" -mtime +30 -delete
```

For offsite backups, the README documents piping the backup to S3-compatible storage:
```
docker compose exec -T app python manage.py backup --stdout | aws s3 cp - s3://my-backups/db_$(date +%F).sql.gz
```

---

## 10. Inbound Webhooks (Platform → Application)

The publishing engine sends content out to platforms (outbound). For real-time inbox updates, some platforms push data back to the application via webhooks (inbound). This is separate from the outbound webhook system in F-5.3.

### Supported Platforms

| Platform | Webhook Support | What It Delivers |
|----------|----------------|-----------------|
| Facebook | Yes (Graph API Webhooks) | Page comments, mentions, messages, post reactions |
| Instagram | Yes (via Facebook Graph API Webhooks) | Comments on media, mentions, story replies, messages |
| LinkedIn | No | - (polling only) |
| TikTok | No | - (polling only) |
| YouTube | Yes (YouTube Data API push notifications via PubSubHubbub) | New comments on videos |
| Pinterest | No | - (polling only) |
| Threads | No | - (polling only) |
| Bluesky | No (AT Protocol firehose exists but is not per-account) | - (polling only) |
| Google Business Profile | No | - (polling only) |
| Mastodon | Yes (Streaming API via WebSocket, not HTTP webhooks) | Notifications, mentions, new followers |

In practice, Facebook and Instagram are the only platforms where HTTP-based inbound webhooks meaningfully replace polling for inbox sync.

### Webhook Endpoint Architecture

The application exposes platform-specific webhook receiver endpoints:

```
POST /webhooks/facebook/     ← Facebook & Instagram webhook events
POST /webhooks/youtube/      ← YouTube PubSubHubbub notifications
```

Each endpoint:
1. **Verifies the request signature** before processing. Unsigned or incorrectly signed requests are rejected with 403.
2. Parses the platform-specific payload.
3. Maps the payload to the internal `InboxMessage` model.
4. Enqueues a background job to process the message (deduplication, sentiment tagging, notification dispatch).
5. Returns 200 immediately (platforms require fast responses - typically within 5 seconds or they retry/disable the webhook).

### Signature Verification

| Platform | Verification Method |
|----------|-------------------|
| Facebook / Instagram | HMAC-SHA256. Facebook signs the payload with the App Secret. The receiver computes `HMAC-SHA256(app_secret, raw_request_body)` and compares it to the `X-Hub-Signature-256` header. Reject if mismatch. |
| YouTube | PubSubHubbub verification: on subscription, YouTube sends a `GET` challenge with a `hub.challenge` parameter. The endpoint must echo back the challenge. On notification, payloads are Atom XML - verify the `hub.secret` HMAC if configured during subscription. |

The App Secret used for Facebook/Instagram signature verification is the same credential stored in F-1.5 (Platform API Credentials). The verification function reads it from the `PlatformCredential` model.

### Webhook Registration

**Facebook / Instagram:**
- Webhooks are configured in the Facebook App Dashboard (developer console) by the platform developer (cloud) or self-hoster.
- Required configuration: Callback URL, Verify Token, and subscribed fields.
- **Cloud version:** Callback URL is `https://app.yourdomain.com/webhooks/facebook/`. Configured once by the developer in the Facebook App Dashboard.
- **Self-hosted:** Callback URL is `https://<self-hosted-domain>/webhooks/facebook/`. The self-hoster configures this in their own Facebook App Dashboard. The setup wizard (first-run) provides the exact URL to copy and step-by-step instructions.
- Verify Token: a random string stored as an environment variable (`FACEBOOK_WEBHOOK_VERIFY_TOKEN`). Used during Facebook's initial GET verification handshake.
- Subscribed fields: `feed`, `mention`, `messages` (for Pages), `comments`, `mentions` (for Instagram).

**YouTube:**
- PubSubHubbub subscriptions are created programmatically when a YouTube account is connected (F-2.5).
- The application sends a subscription request to YouTube's PubSubHubbub hub for the connected channel's activity feed.
- Subscriptions expire (typically 10 days) and must be renewed by a background job.
- Callback URL follows the same pattern: `https://<domain>/webhooks/youtube/`.

### Self-Hosted Considerations

- **HTTPS required.** Facebook and YouTube reject webhook callbacks to HTTP endpoints. Self-hosters must have TLS configured (Caddy handles this automatically).
- **Public URL required.** The webhook endpoint must be reachable from the internet. Self-hosters behind NAT or firewalls must configure port forwarding or use a tunnel.
- **Different callback URLs per deployment.** Each self-hosted instance has its own domain, so each must register its own webhook callback URL with Facebook/YouTube. The setup wizard generates the correct URLs and provides copy-paste-ready instructions.
- **Fallback to polling.** If a self-hoster cannot configure inbound webhooks (e.g., their server is not publicly accessible), the platform falls back to the polling-based inbox sync (every 5 minutes). Webhook configuration is optional - polling is always active as a baseline.

### Data Flow

```
Platform (Facebook/Instagram) → POST /webhooks/facebook/
  → Verify signature (HMAC-SHA256 with App Secret)
  → Parse payload (identify event type, page/account, message content)
  → Match to workspace (lookup SocialAccount by platform account ID)
  → Deduplicate (check platform_message_id against existing InboxMessages)
  → Create InboxMessage record
  → Enqueue notification job (in-app badge, email, Slack per F-7.1)
  → Return 200
```

---

## 11. Environment Variables

```
# CORE
SECRET_KEY=
DEBUG=false
ALLOWED_HOSTS=app.yourdomain.com
APP_URL=https://app.yourdomain.com

# DATABASE
DATABASE_URL=postgres://user:pass@postgres:5432/socialapp

# STORAGE
STORAGE_BACKEND=local
MEDIA_ROOT=/app/media
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=
S3_CUSTOM_DOMAIN=
S3_REGION_NAME=auto

# EMAIL
# Self-hosted uses SMTP (any provider: Resend SMTP, Mailgun, SES, own server):
EMAIL_BACKEND=smtp                   # "resend" (API) or "smtp" (generic SMTP)
EMAIL_HOST=                          # SMTP only
EMAIL_PORT=587                       # SMTP only
EMAIL_HOST_USER=                     # SMTP only
EMAIL_HOST_PASSWORD=                 # SMTP only
EMAIL_USE_TLS=true                   # SMTP only
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# PLATFORM CREDENTIALS (cloud - self-hosted uses admin UI)
PLATFORM_FACEBOOK_APP_ID=
PLATFORM_FACEBOOK_APP_SECRET=
PLATFORM_LINKEDIN_CLIENT_ID=
PLATFORM_LINKEDIN_CLIENT_SECRET=
PLATFORM_TIKTOK_CLIENT_KEY=
PLATFORM_TIKTOK_CLIENT_SECRET=
PLATFORM_GOOGLE_CLIENT_ID=
PLATFORM_GOOGLE_CLIENT_SECRET=
PLATFORM_PINTEREST_APP_ID=
PLATFORM_PINTEREST_APP_SECRET=

# REDIS (optional)
REDIS_URL=

# INBOUND WEBHOOKS
FACEBOOK_WEBHOOK_VERIFY_TOKEN=       # Random string for Facebook webhook verification handshake
YOUTUBE_WEBHOOK_SECRET=              # Optional HMAC secret for YouTube PubSubHubbub

# SENTRY (optional)
SENTRY_DSN=
```

---

## 12. Development

```bash
git clone https://github.com/yourorg/social-platform.git && cd social-platform
cp .env.example .env  # set DEBUG=true, DATABASE_URL

docker compose up postgres -d

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python manage.py tailwind install   # one-time
python manage.py tailwind start     # watches + recompiles CSS

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver           # terminal 1
python manage.py process_tasks       # terminal 2
```

Or: `docker compose up` (Tailwind builds inside Dockerfile).

**CI (GitHub Actions):** lint (ruff) → type check (mypy) → tests (pytest) → E2E (Playwright) → build image → deploy on merge to main.

---

## 13. Cost Summary

**Cloud (Hetzner):**

| Scale | Monthly |
|-------|---------|
| Launch (1–100 orgs) | ~€10 |
| Growth (100–500 orgs) | ~€28 |
| Scale (500–2,000 orgs) | ~€45 |

**Self-hosted:**

| Path | Monthly |
|------|---------|
| Bare VPS (Hetzner/DO/Linode) | €5–7 |
| Heroku (Basic + Essential-0) | $19 |
| Railway | $15–30 |
| Render | $21+ |
| Home server | $0 |
