# Social Marketing Read-Only Dashboard

This repo now targets a single deployment model:

- frontend UI in `design/`
- deploy on Netlify
- auth and database on Supabase
- scheduled sync from Supabase Cron to `POST /api/cron/sync-all`

The old Django and Python backend has been removed from the active architecture.

## Product scope

Supported:

- email sign up and sign in with Supabase Auth
- connect `Facebook`, `YouTube`, and `TikTok` with real OAuth
- sync channel profile, recent posts, and analytics snapshots
- show dashboard, channel analytics, content explorer, inbox-style monitoring, and settings

Disabled on purpose:

- publishing
- first comments
- media upload and processing
- scheduling and approval workflows

Those UI entry points remain visible, but they now show `Dang phat trien`.

## Stack

- `Netlify` for static hosting and the serverless API function
- `Supabase Auth` for authentication
- `Supabase Postgres` for application data
- `Supabase Vault` for cron secrets
- `Supabase Cron` plus `pg_net` for scheduled sync
- `Vite + React + TypeScript` for the existing UI

## Main directories

- `design/`: frontend and Netlify function source
- `supabase/`: SQL migrations
- `docs/netlify-supabase-readonly.md`: deployment and environment setup

## Local development

```powershell
npm run install:frontend
npm run lint
npm run build
```

To run the UI locally:

```powershell
npm run dev
```

If you want local Netlify Functions too:

```powershell
cd design
netlify dev
```

## Required environment variables

See:

- [.env](</c:/Users/cuong/OneDrive/Documents/GitHub/Social Marketing/.env>)

## Database setup

Run these migrations in order:

```sql
\i supabase/migrations/20260425_readonly_dashboard.sql
\i supabase/migrations/20260425_schedule_sync_cron.sql
```

Then create Supabase Vault secrets:

```sql
select vault.create_secret('https://your-site.netlify.app', 'netlify_app_url');
select vault.create_secret('your-cron-secret', 'netlify_cron_secret');
```

## OAuth callbacks

- `https://your-site.netlify.app/api/oauth/callback/facebook`
- `https://your-site.netlify.app/api/oauth/callback/youtube`
- `https://your-site.netlify.app/api/oauth/callback/tiktok`

## CI

The repository CI now only validates the frontend application:

- type check
- production build

## Deployment guide

Use:

- [docs/netlify-supabase-readonly.md](/c:/Users/cuong/OneDrive/Documents/GitHub/Social%20Marketing/docs/netlify-supabase-readonly.md)
