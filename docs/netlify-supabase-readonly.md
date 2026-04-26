# Netlify + Supabase Read-Only Deployment

This repo is now wired for a read-only analytics deployment:

- Frontend: `design/` Vite app on Netlify
- Auth: Supabase Auth
- Database: Supabase Postgres
- Backend API: Netlify Function at `/api/*`
- Sync jobs: manual sync from UI, or scheduled sync by calling `/api/cron/sync-all`

## Scope kept

- Sign up / sign in
- Connect channels with OAuth
- Store tokens securely in Supabase
- Sync channel profile, recent content, and analytics snapshots
- Render dashboard, channel analytics, content explorer, inbox view

## Scope intentionally disabled

- Publishing
- Comment replies
- Media upload / processing
- Scheduled posting workflows

The UI keeps those entry points, but they now show `Dang phat trien`.

## 1. Supabase setup

1. Create a Supabase project.
2. Run the SQL migrations:

```sql
\i supabase/migrations/20260425_readonly_dashboard.sql
\i supabase/migrations/20260425_schedule_sync_cron.sql
```

3. In Supabase Auth:
   - enable Email sign-in
   - configure your Site URL to the Netlify domain
   - add Redirect URLs:
     - `https://your-site.netlify.app`
     - `https://your-site.netlify.app/login`
     - `https://your-site.netlify.app/register`

## 2. Netlify environment variables

Set these in your local `.env` and in Netlify:

```dotenv
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

APP_URL=https://your-site.netlify.app
APP_STATE_SECRET=
CRON_SECRET=

PLATFORM_FACEBOOK_APP_ID=
PLATFORM_FACEBOOK_APP_SECRET=

PLATFORM_GOOGLE_CLIENT_ID=
PLATFORM_GOOGLE_CLIENT_SECRET=

PLATFORM_TIKTOK_CLIENT_KEY=
PLATFORM_TIKTOK_CLIENT_SECRET=
```

Use a long random value for:

- `APP_STATE_SECRET`
- `CRON_SECRET`

## 3. OAuth redirect URIs

Register these exact callback URLs in each provider dashboard:

- Facebook:
  `https://your-site.netlify.app/api/oauth/callback/facebook`
- YouTube / Google:
  `https://your-site.netlify.app/api/oauth/callback/youtube`
- TikTok:
  `https://your-site.netlify.app/api/oauth/callback/tiktok`

## 4. Netlify build config

The repo already includes:

- [netlify.toml](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/netlify.toml)
- build base: `design`
- publish dir: `design/dist`
- function entry: `design/netlify/functions/api.ts`

## 5. Supabase Cron sync

This repo now includes a Supabase Cron migration that schedules sync every `30 minutes`.

Before the scheduled job can call Netlify, create these secrets in Supabase Vault:

```sql
select vault.create_secret('https://your-site.netlify.app', 'netlify_app_url');
select vault.create_secret('your-cron-secret', 'netlify_cron_secret');
```

The migration creates:

- extension setup for `pg_cron`, `pg_net`, and `vault`
- a helper function `private.invoke_netlify_sync_all()`
- a cron job named `netlify-sync-all-every-30-minutes`

Manual endpoint, used by the cron job:

Endpoint:

```text
POST https://your-site.netlify.app/api/cron/sync-all
```

Header:

```text
X-Cron-Secret: <CRON_SECRET>
```

If you want a different cadence, update the cron expression in:

- [20260425_schedule_sync_cron.sql](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/supabase/migrations/20260425_schedule_sync_cron.sql)

## 6. Local development

In `design/`:

```powershell
npm install
npm run build
npm run lint
```

For local frontend testing:

```powershell
npm run dev
```

If you also want to test Netlify Functions locally, use Netlify CLI:

```powershell
netlify dev
```

## 7. Main files

- Frontend app: [design/src/App.tsx](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/design/src/App.tsx)
- Auth + state store: [design/src/store/AppContext.tsx](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/design/src/store/AppContext.tsx)
- Supabase client: [design/src/lib/supabase.ts](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/design/src/lib/supabase.ts)
- Netlify API: [design/netlify/functions/api.ts](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/design/netlify/functions/api.ts)
- Supabase schema: [supabase/migrations/20260425_readonly_dashboard.sql](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/supabase/migrations/20260425_readonly_dashboard.sql)
- Supabase cron: [supabase/migrations/20260425_schedule_sync_cron.sql](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/supabase/migrations/20260425_schedule_sync_cron.sql)
