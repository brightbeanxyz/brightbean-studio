<p align="center">
  <a href="https://github.com/brightbeanxyz/brightbean-studio">
    <img src=".github/assets/brightbean-studio-logo.webp" alt="BrightBean Studio" width="280">
  </a>
</p>

<p align="center">
  <strong>Open-source social media management for creators, agencies, and SMBs.</strong>
</p>

<p align="center">
  <a href="https://github.com/brightbeanxyz/brightbean-studio/actions/workflows/ci.yml"><img src="https://github.com/brightbeanxyz/brightbean-studio/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg" alt="Python 3.12+"></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-5.x-green.svg" alt="Django 5.x"></a>
</p>

<p align="center">
  <a href="https://brightbean.xyz/studio/"><img src="https://img.shields.io/badge/Free%20hosted%20version-brightbean.xyz%2Fstudio-FFB300?style=for-the-badge" alt="Free hosted version at brightbean.xyz/studio"></a>
</p>

---

## About BrightBean Studio

BrightBean Studio is an open-source, self-hostable social media management platform built for creators, agencies and SMBs. It does what Sendible, SocialPilot, or ContentStudio do, but free and without per-seat, per-channel, or per-workspace limits. Plan, compose, schedule, approve, publish, and monitor content across Facebook, Instagram, LinkedIn, TikTok, YouTube, Pinterest, Threads, Bluesky, Google Business Profile, and Mastodon from a single multi-workspace dashboard.

It's for people managing many client accounts under one roof who'd rather own their social stack than pay $100–300/month to a SaaS vendor. Every feature is available to every user. No paid tier, no feature gate, no upsell.

A free hosted version is available at [brightbean.xyz/studio](https://brightbean.xyz/studio/). You can also deploy it yourself with a one-click button on Heroku, Render, or Railway, run it on your own VPS via Docker, or run it locally. All platform integrations talk directly to the official first-party APIs using your own developer credentials, so there's no aggregator middleman, no vendor lock-in, and no third party sitting between you and your data.

## Features

| | |
|---|---|
| **Multi-workspace & teams** | Unlimited orgs → workspaces → members. Granular RBAC with custom roles, invitations, and a separate Client role for external collaborators. |
| **Content composer** | Rich editor with per-platform caption/media overrides, version history, reusable templates, content categories & tags, a Kanban idea board. |
| **Calendar & scheduling** | Visual calendar with recurring weekly posting slots per account and named queues that auto-assign posts to the next available slot. |
| **Publishing engine** | Direct first-party API integrations (no aggregator), automatic retries, per-account rate-limit tracking, and a 90-day publish audit log. |
| **Approval workflows** | Configurable stages (none / optional / internal / internal + client), threaded internal & external comments, reminders, and a full audit trail. |
| **Unified social inbox** | Comments, mentions, DMs, and reviews from every connected platform in one place, with sentiment analysis, assignments, threaded replies, and historical backfill. |
| **Analytics** | Per-post and channel-level performance from every connected platform's native API, with KPI cards, 7/30/90-day trend charts, and a sortable all-posts table for views, engagement, follower growth, reach, and watch time. |
| **Media library** | Org- and workspace-scoped libraries with nested folders, auto-generated platform-optimized variants, alt text, and built-in Unsplash stock-photo search in the composer. |
| **Client portal** | Passwordless 30-day magic-link access so clients can approve or reject posts without creating an account. |
| **Notifications** | In-app, email, and webhook delivery with per-user preferences for every event type. |
| **Security & ops** | Encrypted token & credential storage, Google SSO, Sentry support, and a 14-day reversible org-deletion grace period. 2FA (TOTP) is on the roadmap. |
| **White-label friendly** | Per-workspace branding (logo, colors) and workspace defaults for hashtags, first comments, and posting templates. |

### A quick look

<table>
  <tr>
    <td colspan="2"><img src=".github/assets/BrightBean%20Studio%20Calendar.webp" alt="Calendar view"><br><sub><b>Visual calendar</b> - drag-and-drop scheduling with recurring slots and queues.</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src=".github/assets/BrightBean%20Studio%20Post%20Editor.webp" alt="Post editor"><br><sub><b>Post editor</b> - composer with per-platform overrides and previews.</sub></td>
    <td width="50%"><img src=".github/assets/BrightBean%20Studio%20Idea%20Kanban%20Board.webp" alt="Idea kanban board"><br><sub><b>Idea board</b> - Kanban workflow to keep track of all your post ideas.</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src=".github/assets/BrightBean%20Social%20Media%20Platforms.webp" alt="Connected platforms"><br><sub><b>Connect anything</b> - 10+ first-party integrations, no aggregator.</sub></td>
    <td width="50%"><img src=".github/assets/BrightBean%20Studio%20Analytics.webp" alt="Analytics dashboard"><br><sub><b>Performance analytics</b> - per-post and channel-level metrics with KPI cards and trend charts.</sub></td>
  </tr>
</table>

## Supported Platforms

| Platform | Publish | Comments | DMs | Insights |
|---|:---:|:---:|:---:|:---:|
| <img src="https://cdn.simpleicons.org/facebook" width="16" height="16"> Facebook | ✓ | ✓ | ✓ | ✓ |
| <img src="https://cdn.simpleicons.org/instagram" width="16" height="16"> Instagram | ✓ | ✓ | ✓ | ✓ |
| <img src="https://cdn.simpleicons.org/instagram" width="16" height="16"> Instagram (Direct) | ✓ | ✓ | ✓ | ✓ |
| <img src="https://api.iconify.design/logos/linkedin-icon.svg" width="16" height="16"> LinkedIn (Personal) | ✓ | ✓ | — | ✓ |
| <img src="https://api.iconify.design/logos/linkedin-icon.svg" width="16" height="16"> LinkedIn (Company) | ✓ | ✓ | — | ✓ |
| <img src="https://cdn.simpleicons.org/tiktok" width="16" height="16"> TikTok | ✓ | — | — | ✓ |
| <img src="https://cdn.simpleicons.org/youtube" width="16" height="16"> YouTube | ✓ | ✓ | — | ✓ |
| <img src="https://cdn.simpleicons.org/pinterest" width="16" height="16"> Pinterest | ✓ | — | — | ✓ |
| <img src="https://cdn.simpleicons.org/threads" width="16" height="16"> Threads | ✓ | ✓ | — | ✓ |
| <img src="https://cdn.simpleicons.org/bluesky" width="16" height="16"> Bluesky | ✓ | ✓ | — | — |
| <img src="https://api.iconify.design/logos/google-icon.svg" width="16" height="16"> Google Business Profile | ✓ | — | — | ✓ |
| <img src="https://cdn.simpleicons.org/mastodon" width="16" height="16"> Mastodon | ✓ | ✓ | — | — |

---

### Hosted Version

A free hosted version of Brightbean Studio is available at [brightbean.xyz/studio](https://brightbean.xyz/studio/). It runs the same codebase as this repository, with no setup or maintenance required.

If you'd rather self-host, choose one of the options below.

### One-Click Deploy

| Heroku | Render | Railway |
|:------:|:------:|:-------:|
| [![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/brightbeanxyz/brightbean-studio) | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/brightbeanxyz/brightbean-studio) | [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/brightbean-studio?referralCode=brightbean) |

After deploying, set these environment variables in your platform's dashboard:

| Variable | Required | Description |
|----------|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | Auto-set | `config.settings.production`. Set if deployment config has not placed it. |
| `SECRET_KEY` | Auto-generated | Django secret key. Set automatically by the deploy button. |
| `ENCRYPTION_KEY_SALT` | Auto-generated | Encryption salt. Set automatically by the deploy button. |
| `DATABASE_URL` | Auto-provisioned | PostgreSQL connection string. Set automatically. |
| `ALLOWED_HOSTS` | Yes | Your app's domain, e.g. `your-app.herokuapp.com` |
| `APP_URL` | Yes | Full public URL, e.g. `https://your-app.herokuapp.com` |
| `STORAGE_BACKEND` | No | Set to `s3` for S3/R2 storage. Default: `local`. Heroku, Render, and Railway have ephemeral filesystems, so uploaded files are lost on redeploy without S3. |
| `S3_ENDPOINT_URL` | If using S3 | S3-compatible endpoint URL |
| `S3_ACCESS_KEY_ID` | If using S3 | S3 access key |
| `S3_SECRET_ACCESS_KEY` | If using S3 | S3 secret key |
| `S3_BUCKET_NAME` | If using S3 | S3 bucket name |
| `EMAIL_HOST` | No | SMTP server for sending invitations and password resets |
| `EMAIL_PORT` | No | SMTP port (default: `587`) |
| `EMAIL_HOST_USER` | No | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | SMTP password |
| `GOOGLE_AUTH_CLIENT_ID` | No | For Google OAuth login. Get from [Google Cloud Console](https://console.cloud.google.com/) → Credentials. |
| `GOOGLE_AUTH_CLIENT_SECRET` | No | Google OAuth secret |
| `UNSPLASH_ACCESS_KEY` | No | Enables Unsplash stock-photo search in the composer. Create a free app at [unsplash.com/developers](https://unsplash.com/developers). |

For social media API keys, see [Platform Credentials](#platform-credentials). Full variable reference: `.env.example`.

## Quick Start (Docker)

```bash
git clone https://github.com/brightbeanxyz/brightbean-studio.git
cd brightbean-studio
cp .env.example .env
```

Edit `.env` - change `DATABASE_URL` to point to the Docker service name:

```
DATABASE_URL=postgres://postgres:postgres@postgres:5432/brightbean
```

Then start everything:

```bash
docker compose up -d --build
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
```

Tailwind compiles automatically via the `tailwind` Compose service. First build
takes ~60–90 seconds (running `npm install` in a fresh container); subsequent
starts are instant. Watch progress with `docker compose logs -f tailwind`.

Open http://localhost:8000 - you're running.


## Fully Local Development (without Docker)

Run everything natively - no Docker, no PostgreSQL install. Uses SQLite for the database.

### Prerequisites

- Python 3.12+
- Node.js 20+

### Setup

**1. Clone and configure**

```bash
git clone https://github.com/brightbeanxyz/brightbean-studio.git
cd brightbean-studio
cp .env.example .env
```

**2. Switch to SQLite**

Open `.env` and replace the `DATABASE_URL` line:

```
DATABASE_URL=sqlite:///db.sqlite3
```

That's it - no database server to install or manage.

**3. Set up Python**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**4. Set up Tailwind CSS**

```bash
cd theme/static_src
npm install
cd ../..
```

**5. Run database migrations**

```bash
python manage.py migrate
```

**6. Create your admin account**

```bash
python manage.py createsuperuser
```

**7. Start the app (3 terminal tabs)**

Tab 1 - Tailwind watcher:
```bash
cd theme/static_src && npm run start
```

Tab 2 - Django dev server:
```bash
source .venv/bin/activate
python manage.py runserver
```

Tab 3 - Background worker:
```bash
source .venv/bin/activate
python manage.py process_tasks
```

Open http://localhost:8000 and log in with the superuser you created.

### Daily workflow (Docker-free)

```bash
source .venv/bin/activate                # activate Python env
python manage.py runserver               # start web server
# (open another tab)
python manage.py process_tasks           # start worker
```

> **Note:** SQLite is fine for local development and small deployments. For production or heavy concurrent usage, switch to PostgreSQL.

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=apps --cov-report=term-missing
```

## Linting & Type Checking

```bash
ruff check .                             # lint
ruff format --check .                    # format check
mypy apps/ config/ --ignore-missing-imports  # type check
```

Auto-fix lint issues:

```bash
ruff check --fix .
ruff format .
```

## Production Deployment

### Docker Compose on a VPS (recommended)

```bash
# On your server:
git clone https://github.com/brightbeanxyz/brightbean-studio.git
cd brightbean-studio
cp .env.example .env
# Edit .env:
#   SECRET_KEY=<generate a random 50+ char string>
#   DEBUG=false
#   ALLOWED_HOSTS=yourdomain.com
#   APP_URL=https://yourdomain.com
#   DATABASE_URL=postgres://postgres:<strong-password>@postgres:5432/brightbean

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec app python manage.py createsuperuser
```

This starts 5 containers: app (Gunicorn), worker, PostgreSQL, Caddy (auto-HTTPS), and a one-shot migrate container that runs database migrations automatically on startup. Edit the `Caddyfile` with your domain.

To update:

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Other Platforms

| Platform | Config file | Notes |
|----------|-------------|-------|
| **Heroku** | `Procfile` + `app.json` | Deploy-button ready. Must use Basic+ dynos (Eco dynos break the worker). |
| **Railway** | `railway.toml` | The [one-click template](https://railway.com/deploy/brightbean-studio) provisions three services: web (Gunicorn, runs `migrate` on startup), worker (`python manage.py process_tasks`), and managed PostgreSQL. The web service's startup `migrate` fires the `post_migrate` hooks that register the recurring tasks, so scheduling works out of the box. |
| **Render** | `render.yaml` | Blueprint with web, worker, PostgreSQL. Must use paid tier. |

All platforms with ephemeral filesystems require `STORAGE_BACKEND=s3` - see `.env.example` for S3 configuration.

See `architecture.md` for detailed per-platform instructions and cost breakdowns.

## Project Structure

```
brightbean-studio/
├── config/
│   ├── settings/
│   │   ├── base.py            # Shared settings
│   │   ├── development.py     # Local dev overrides
│   │   ├── production.py      # Production hardening
│   │   └── test.py            # Test overrides
│   ├── urls.py                # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/              # Custom User model, auth, OAuth, sessions
│   ├── organizations/         # Organization management
│   ├── workspaces/            # Workspace CRUD
│   ├── members/               # RBAC, invitations, middleware, decorators
│   ├── settings_manager/      # Configurable defaults with cascade logic
│   ├── credentials/           # Platform API credential storage (encrypted)
│   └── common/                # Shared: encrypted fields, scoped model managers
├── providers/                 # Social platform API modules (one file per platform)
├── templates/                 # Django templates
│   ├── base.html              # Layout with sidebar + nav
│   └── components/            # Reusable HTMX partials
├── static/
│   └── js/                    # Vendored HTMX + Alpine.js
├── theme/                     # django-tailwind theme app
│   └── static_src/
│       ├── src/styles.css     # Tailwind directives
│       └── tailwind.config.js
├── Dockerfile
├── docker-compose.yml         # Dev: app + worker + postgres
├── docker-compose.prod.yml    # Prod override: adds Caddy, uses Gunicorn
├── Caddyfile                  # Reverse proxy + auto-HTTPS config
├── .env.example               # All environment variables
├── Procfile                   # Heroku
├── app.json                   # Heroku deploy button
├── railway.toml               # Railway config
└── render.yaml                # Render blueprint
```

> **Settings selection:** The `DJANGO_SETTINGS_MODULE` environment variable controls which settings file Django uses. The defaults are already wired for each context: `manage.py` uses `development`, `wsgi.py`/`asgi.py` use `production`, and `pytest` uses `test` (via `pyproject.toml`). Docker Compose files and platform deploy configs (Heroku, Render) also set it explicitly. You only need to override it manually if you want a non-default module for a specific command, e.g. `DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy`.

## Platform Credentials

To connect social media accounts, you need API credentials from each platform's developer portal. You can set these via environment variables in `.env` (see `.env.example`) or, per organization, through the Django admin at `{APP_URL}/admin/` → **Credentials → Platform credentials** (superuser only). If a platform is configured in both places, the `.env` value takes precedence.

**Admin UI access (superuser only):** The Django admin at `{APP_URL}/admin/` (for example `https://brightbean.example.com/admin/`) is restricted to superuser accounts — only a superuser can view or edit platform credentials there. If you don't already have one, create a superuser, then sign in and open **Credentials → Platform credentials**:

```bash
python manage.py createsuperuser
# Docker: docker compose exec app python manage.py createsuperuser
```

**Redirect URI:** When registering your app on any platform, set the OAuth redirect URI to:

```
{APP_URL}/social-accounts/callback/{platform}/
```

For example, if your `APP_URL` is `https://brightbean.example.com`, the Facebook redirect URI would be `https://brightbean.example.com/social-accounts/callback/facebook/`.

> **TikTok:** use the slug `social1` instead of `tiktok` — TikTok rejects redirect URIs containing their brand name. See the [TikTok](#tiktok) section.

### Meta (Facebook, Instagram, Threads)

Facebook, Instagram, and Threads all use the same Meta app credentials.

1. Go to [Meta for Developers](https://developers.facebook.com/) and create a new app (type: **Business**)
2. Under **App Settings → Basic**, copy your **App ID** and **App Secret**
3. In the App Dashboard, go to **Use cases** and add the following four use cases. For each use case, click into it and go to **Permissions and features** to add the required optional permissions:

   **Use case: "Manage everything on your Page"** (Facebook)
   - This use case auto-includes `business_management`, `pages_show_list`, and `public_profile`
   - Add these optional permissions: `pages_manage_posts`, `pages_manage_engagement`, `pages_read_engagement`, `pages_read_user_content`, `pages_manage_metadata`, `read_insights`

   **Use case: "Messenger from Meta"** (Facebook Messaging)
   - Required to enable the `pages_messaging` permission, which is not available under the "Manage Pages" use case
   - Add the optional permission: `pages_messaging`

   **Use case: "Manage messaging & content on Instagram"** (Instagram)
   - Add these permissions: `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `instagram_manage_insights`

   **Use case: "Access the Threads API"** (Threads)
   - This use case auto-includes `threads_basic`
   - Add these optional permissions: `threads_content_publish`, `threads_manage_insights`, `threads_manage_replies`

4. Under **Facebook Login → Settings → Valid OAuth Redirect URIs**, add the following redirect URIs:
   ```
   {APP_URL}/social-accounts/callback/facebook/
   {APP_URL}/social-accounts/callback/instagram/
   {APP_URL}/social-accounts/callback/threads/
   ```
5. Set the environment variables:
   ```
   PLATFORM_FACEBOOK_APP_ID=your-app-id
   PLATFORM_FACEBOOK_APP_SECRET=your-app-secret
   ```

### Instagram (Direct, via Instagram Login)

The Instagram (Direct) connector uses the **Instagram API with Instagram Login** - a separate OAuth flow from the Facebook Login-based Instagram connector above. It works with **Professional** Instagram accounts (Business or Creator) **without** requiring a linked Facebook Page.

> **Account-type requirement:** Personal Instagram accounts have no API access since the Instagram Basic Display API was retired on 2024-12-04. Users must convert their account to Professional first (free, in IG Settings → *Account type and tools* → *Switch to professional account*).

1. In the same Meta app, go to **Use cases** and add the **"Instagram API"** use case
2. Under **API setup with Instagram Login**, note your **Instagram App ID** and **Instagram App Secret** (these are different from your Facebook App ID/Secret)
3. Go to **Permissions and features** and add the required permissions:
   - `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_comments`, `instagram_business_manage_messages`, `instagram_business_manage_insights`
4. Under **API setup with Instagram Login → Step 4: Set up Instagram business login**, click **Set up** and add the redirect URI (must match exactly, including the trailing slash):
   ```
   {APP_URL}/social-accounts/callback/instagram_login/
   ```
5. Under **API setup with Instagram Login → Step 3: Configure webhooks**, set:
   - **Callback URL:** `{APP_URL}/webhooks/instagram_login/`
   - **Verify token:** the value of `INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN` from your `.env` (any random string; generate one and set the env var before clicking Verify and save). After verification, subscribe to the `messages`, `comments`, and `mentions` fields.
6. Set the environment variables:
   ```
   PLATFORM_INSTAGRAM_APP_ID=your-instagram-app-id
   PLATFORM_INSTAGRAM_APP_SECRET=your-instagram-app-secret
   INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN=your-random-verify-token
   ```

### LinkedIn

Brightbean Studio supports two LinkedIn paths. Pick whichever your LinkedIn dev app can obtain - or both, on separate apps.

**Path A - Personal-only (any individual developer can do this):**

1. Go to the [LinkedIn Developer Portal](https://developer.linkedin.com/) and create a new app (no Company Page verification required).
2. Under **Products**, request access to (both auto-approved):
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
3. Under **Auth**, add the redirect URI:
   ```
   {APP_URL}/social-accounts/callback/linkedin_personal/
   ```
4. Scopes: `openid`, `profile`, `email`, `w_member_social`.
5. Set the environment variables:
   ```
   PLATFORM_LINKEDIN_PERSONAL_CLIENT_ID=your-client-id
   PLATFORM_LINKEDIN_PERSONAL_CLIENT_SECRET=your-client-secret
   ```

> **Limitations of Path A:** access tokens last ~60 days and LinkedIn does not issue refresh tokens for these scopes - users must manually reconnect every ~60 days. Inbox / comment-reading is not available for personal accounts on this path.

**Path B - Company Pages (also enables full Personal features):**

1. Go to the [LinkedIn Developer Portal](https://developer.linkedin.com/) and create a new app.
2. Verify the app's association with a LinkedIn Company Page.
3. Under **Products**, request access to:
   - **Community Management API** *(restricted - requires LinkedIn review)*
4. Under **Auth**, add **both** redirect URIs:
   ```
   {APP_URL}/social-accounts/callback/linkedin_personal/
   {APP_URL}/social-accounts/callback/linkedin_company/
   ```
5. Scopes:
   - **Personal:** `r_basicprofile`, `w_member_social`, `r_member_social`
   - **Company:** `r_basicprofile`, `w_member_social`, `w_organization_social`, `r_organization_social`, `rw_organization_admin`
6. Set the environment variables:
   ```
   PLATFORM_LINKEDIN_COMPANY_CLIENT_ID=your-client-id
   PLATFORM_LINKEDIN_COMPANY_CLIENT_SECRET=your-client-secret
   ```

If you set only the Path B (Company) credentials, Brightbean Studio automatically reuses them for personal connections too - refresh tokens (365-day) and inbox both work. You only need Path A vars if you have a separate Personal-only app.

> **Note:** "Sign In with LinkedIn using OpenID Connect" / "Share on LinkedIn" and "Community Management API" are **mutually exclusive** on a single LinkedIn app. You need separate apps for Path A and Path B.

> **Backwards compatibility:** the legacy `PLATFORM_LINKEDIN_CLIENT_ID` / `PLATFORM_LINKEDIN_CLIENT_SECRET` env vars are still honored as a fallback for both `linkedin_personal` and `linkedin_company` - existing self-hosters keep working without changes. The legacy credentials are assumed to be CM-approved; if your legacy app is OIDC-only, migrate it to `PLATFORM_LINKEDIN_PERSONAL_*`.

### TikTok

1. Go to the [TikTok Developer Portal](https://developers.tiktok.com/) and create a new app
2. Add the products **Login Kit** and **Content Posting API**
3. Configure the redirect URI — use `social1`, not `tiktok` (TikTok rejects URIs containing their brand name):
   ```
   {APP_URL}/social-accounts/callback/social1/
   ```
4. Required scopes: `user.info.basic`, `video.publish`, `video.upload`, `video.list`
5. Note: TikTok uses **Client Key** (not Client ID). Copy the **Client Key** and **Client Secret** from your app dashboard
6. Set the environment variables:
   ```
   PLATFORM_TIKTOK_CLIENT_KEY=your-client-key
   PLATFORM_TIKTOK_CLIENT_SECRET=your-client-secret
   ```
7. For production review, record the demo video against a TikTok **Sandbox** showing every requested scope in use.

### Google (YouTube, Google Business Profile)

YouTube and Google Business Profile share the same Google Cloud credentials.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or select an existing one)
2. Enable the following APIs under **APIs & Services → Library**:
   - **YouTube Data API v3** (for YouTube)
   - **My Business Account Management API**, **My Business Business Information API**, and **Google My Business API** (for Google Business Profile)
3. Go to **APIs & Services → Credentials** and create an **OAuth 2.0 Client ID** (type: Web application)
4. Add the following redirect URIs under **Authorized redirect URIs**:
   ```
   {APP_URL}/social-accounts/callback/youtube/
   {APP_URL}/social-accounts/callback/google_business/
   ```
5. Copy the **Client ID** and **Client Secret**
6. Required scopes:
   - **YouTube:** `https://www.googleapis.com/auth/youtube.upload`, `https://www.googleapis.com/auth/youtube.readonly`, `https://www.googleapis.com/auth/youtube.force-ssl`, `https://www.googleapis.com/auth/yt-analytics.readonly`
   - **Google Business Profile:** `https://www.googleapis.com/auth/business.manage`
7. Set the environment variables:
   ```
   PLATFORM_GOOGLE_CLIENT_ID=your-client-id
   PLATFORM_GOOGLE_CLIENT_SECRET=your-client-secret
   ```

### Pinterest

1. Go to the [Pinterest Developer Portal](https://developers.pinterest.com/) and create a new app
2. Under your app settings, add the redirect URI:
   ```
   {APP_URL}/social-accounts/callback/pinterest/
   ```
3. Copy the **App ID** and **App Secret**
4. Required scopes: `user_accounts:read`, `boards:read`, `pins:read`, `pins:write`
5. Set the environment variables:
   ```
   PLATFORM_PINTEREST_APP_ID=your-app-id
   PLATFORM_PINTEREST_APP_SECRET=your-app-secret
   ```

### Bluesky

No developer app registration needed. Users connect by entering their Bluesky handle and an **App Password**:

1. Log in to [Bluesky](https://bsky.app/)
2. Go to **Settings → Privacy and Security → App Passwords**
3. Create a new app password and use it when connecting your account in Brightbean Studio

### Mastodon

No developer app registration needed. Brightbean Studio automatically registers an OAuth application on each Mastodon instance when a user connects their account. Users just need to enter their instance URL (e.g., `mastodon.social`).

## Inbox: Backfill Historical Messages

See the [Supported Platforms](#supported-platforms) matrix above for per-platform inbox capabilities.

To import historical messages (e.g., from the last 7 days):

```bash
python manage.py backfill_inbox --days 7
```

Options:
- `--days N` - Number of days to backfill (default: 7)
- `--platform NAME` - Only backfill a specific platform (e.g., `youtube`, `linkedin`, `tiktok`)
- `--account-id UUID` - Only backfill a specific account

## API & MCP for Agents

BrightBean Studio ships a REST API and an MCP (Model Context Protocol) server so agents and scripts can read analytics, manage media, and create or schedule posts. Both share the same authentication, permission model, rate limits, and audit log. Pick whichever protocol fits your client.

**Base URL:** `{APP_URL}/api/v1/` (e.g. `https://your-studio.example.com/api/v1/`)

### Authentication

Issue an API key from **Organization → API Keys**. Keys are workspace-scoped, can be allowlisted to specific social accounts, and inherit a subset of the issuer's workspace permissions. Revocation takes effect immediately. Send the key as a Bearer token:

```
Authorization: Bearer bb_studio_...
```

Permission keys: `create_posts`, `publish_directly`, `upload_media`, `view_analytics`. Each endpoint requires the relevant permission; missing permissions return `403`.

### Rate Limits

| Scope | Limit |
|---|---|
| Per-key writes | 120 / min |
| Per-key reads | 300 / min |
| Per-workspace aggregate | 1000 / min |

Rate-limit responses (`429`) include `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining` headers.

### REST Endpoints

| Method | Path | Purpose | Permission |
|---|---|---|---|
| `GET` | `/me` | Inspect caller scope and workspace permissions | — |
| `GET` | `/accounts` | List connected social accounts | — |
| `POST` | `/posts` | Create a draft or scheduled post | `create_posts` (+ `publish_directly` to schedule) |
| `GET` | `/posts/{post_id}` | Read a single post | — |
| `PATCH` | `/posts/{post_id}` | Update draft fields | `create_posts` |
| `POST` | `/posts/{post_id}/schedule` | Schedule a draft | `create_posts` + `publish_directly` |
| `POST` | `/posts/{post_id}/cancel` | Revert a scheduled post to draft | `create_posts` |
| `GET` | `/analytics/accounts/{account_id}` | Channel analytics summary (7/30/90-day window) | `view_analytics` |
| `GET` | `/analytics/posts/{post_id}` | Post analytics with per-platform metrics | `view_analytics` |
| `POST` | `/media` | Upload a media file (multipart) | `upload_media` |
| `GET` | `/media/{media_id}` | Retrieve a media asset | — |
| `GET` | `/media` | List media assets (filter, paginate) | — |
| `POST` | `/mcp` | JSON-RPC 2.0 endpoint for MCP clients | — |

All write endpoints accept `idempotency_key` (or `Idempotency-Key` header) for safe retries.

### MCP Tools

The MCP server lives at `POST {APP_URL}/api/v1/mcp` and speaks JSON-RPC 2.0 over Streamable HTTP. It implements the standard `initialize`, `tools/list`, `tools/call`, and `ping` methods. Tools:

| Tool | Purpose | Permission |
|---|---|---|
| `list_accounts` | List social accounts this API key can act on | — |
| `create_draft` | Create a draft post (caption, title, media, first comment, optional proposed publish time) | `create_posts` |
| `schedule_post` | Create and schedule a post in one step | `create_posts` + `publish_directly` |
| `schedule_draft` | Schedule an existing draft | `create_posts` + `publish_directly` |
| `get_post` | Retrieve a post with aggregate status and per-platform state | — |
| `cancel_post` | Revert a scheduled post back to draft | `create_posts` |
| `search_media` | Find media assets by query, type, tags, or folder | — |
| `get_media` | Retrieve a single media asset by ID | — |
| `upload_media` | Upload a small base64-encoded file (≤ 1 MB raw). For larger files, use REST `POST /media`. | `upload_media` |
| `get_account_analytics` | Channel analytics over a rolling 7–90 day window | `view_analytics` |
| `get_post_analytics` | Per-platform metrics for a single post (safe for polling drafts) | `view_analytics` |

### Connecting an MCP client

The server is at `{APP_URL}/api/v1/mcp` and supports two authentication modes — pick whichever your client uses.

**Claude Desktop (and other native OAuth connectors).** In Claude Desktop open **Settings → Connectors → Add custom connector**, name it, and enter the server URL `{APP_URL}/api/v1/mcp`. Claude registers itself (Dynamic Client Registration) and opens a browser to log in to BrightBean Studio and approve access — **no API key required**. Any Studio user can connect; the connection acts with **their own** workspace permissions (read-only roles get the read tools, while posting/scheduling/uploading require the matching permission), operating on their last-active workspace. Requires Studio to be served over a public **https** URL.

**Claude Code, Cursor, custom agents (static API key).** Point the client at the same URL and send an API key as a Bearer token (`Authorization: Bearer bb_studio_...`). For Claude Code:

```bash
claude mcp add --transport http brightbean {APP_URL}/api/v1/mcp \
  --header "Authorization: Bearer bb_studio_..."
```

### Pre-built agent skill

Don't want to wire up your own client? The companion [brightbean-studio-agent](https://github.com/brightbeanxyz/brightbean-studio-agent) repository hosts a holistic agent skill that drives BrightBean Studio end-to-end through the REST API and MCP tools documented above.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x |
| Frontend | Django templates, HTMX, Alpine.js |
| CSS | Tailwind CSS 4 via django-tailwind |
| Database | PostgreSQL 16+ |
| Background jobs | django-background-tasks (no Redis required) |
| Auth | django-allauth (email + Google OAuth) |
| Media | Pillow (images), FFmpeg (video) |
| Deployment | Docker, Gunicorn, Caddy |

---

## Troubleshooting

**Docker: `postgres` container is unhealthy**
Wait 10-15 seconds after `docker compose up` for the health check to pass, then retry your command. Check logs with `docker compose logs postgres`.

**`python manage.py migrate` fails with connection errors**
Make sure PostgreSQL is running and healthy. For Docker: `docker compose ps` should show postgres as "healthy". For local: verify the `DATABASE_URL` in `.env` matches your setup.

**Tailwind CSS changes not appearing**
Make sure the Tailwind watcher is running: `cd theme/static_src && npm run start`. If styles still don't update, try `npm run build` for a full rebuild.

**OAuth callback errors ("redirect URI mismatch")**
The redirect URI registered on the platform must exactly match `{APP_URL}/social-accounts/callback/{platform}/`. Check that `APP_URL` in `.env` matches the URL you're accessing (including `http` vs `https` and port number).

**Background tasks not running (posts not publishing)**
Make sure the worker is running: `python manage.py process_tasks`. In Docker: check `docker compose logs worker`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding guidelines, and how to submit pull requests.

## Security

To report a security vulnerability, see [SECURITY.md](SECURITY.md). Do not open a public issue.

## License

[AGPL-3.0](LICENSE) - see LICENSE for details.
