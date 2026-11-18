# Changes to upstream files

Brown Creative Studio is a fork of [BrightBean Studio](https://github.com/brightbeanxyz/brightbean-studio)
(AGPL-3.0), forked at upstream commit `14b92fc` on 2026-11-18.

Every change to a file that came from upstream is recorded here with its date and
reason, so each upstream merge can be reviewed against a known list. New features
live in new Django apps and new files; those are listed per entry but need no
merge care. See [docs/fork/README.md](docs/fork/README.md) for the working rules
and the upstream merge procedure.

## 2026-11-18 · Phase 0: fork and baseline

### Upstream files changed

| File | Change | Reason |
|---|---|---|
| `config/settings/base.py` | Added `apps.about` to `LOCAL_APPS` and `apps.about.context_processors.site_identity` to the context processors; `SIGNUP_MODE` now defaults to `invite`; star-imports `config/settings/studio.py` on its last line. | Fork settings live in their own module. Sign-up must fail closed: upstream's default lets anyone on the internet create an account. |
| `config/settings/production.py` | Raises `ImproperlyConfigured` when `SIGNUP_MODE=open`. | Production must never accept public sign-ups. |
| `config/urls.py` | Includes `apps.about.urls` (`/about/source/`, `/legal/terms/`, `/legal/privacy/`). | AGPL source page and the studio's own legal pages. |
| `apps/accounts/middleware.py` | Added `/legal/` and `/about/` to `TosAcceptanceMiddleware`'s exempt prefixes. | A user asked to accept the terms must be able to read them, and the source page must reach everyone. |
| `templates/base.html` | Includes the sidebar "Source code" link above the organization footer; the signed-out `<main>` became a flex column and includes the public footer. | AGPL-3.0 §13: every user sees a link to the running source. |
| `templates/client_portal/portal_base.html` | Includes the public footer after `<main>`. | Same, for portal users. |
| `templates/client_portal/magic_link_confirm.html`, `templates/client_portal/magic_link_expired.html` | Include the public footer; `<body>` became `flex-col` so it sits under the card. | Same, for clients arriving from a link. |
| `templates/account/accept_terms.html` | Includes the public footer; Terms and Privacy links use `TERMS_URL` / `PRIVACY_URL` instead of brightbean.xyz. | AGPL link; the studio's policies, not BrightBean's. |
| `templates/account/signup.html` | Terms and Privacy links use `TERMS_URL` / `PRIVACY_URL`. | The studio's policies, not BrightBean's. |
| `templates/members/accept_invite.html`, `templates/members/invite_expired.html`, `templates/notifications/unsubscribe.html`, `templates/notifications/unsubscribed.html`, `templates/oauth2_provider/base.html`, `templates/ninja/swagger_cdn.html` | Include the public footer before `</body>`. | These pages render their own `<html>` shell; each must carry the source link. A test (`apps/about/tests/test_pages.py`) fails if a new standalone shell lacks it. |
| `Dockerfile` | `ARG SOURCE_COMMIT` / `ENV SOURCE_COMMIT`, declared after the dependency layers. | The image records the commit it was built from, for the source link. |
| `.env.example` | `SIGNUP_MODE=invite`; added `SENTRY_DSN=` (read by settings but missing from the example); appended a Brown Creative Studio section. | Safe defaults and the new settings. |
| `README.md` | Short fork notice at the top. | Says what this repository is and points to the fork docs. |
| `.pre-commit-config.yaml` | `check-yaml` excludes `docker-compose.studio.yml`. | That file uses Compose's `!reset` tag, which a plain YAML loader rejects; `docker compose config` validates it instead. |

### New files

- `apps/about/`: source page, legal fallback pages, the `site_identity` context
  processor, running-commit resolution, production deploy checks
  (`manage.py check --deploy`), and a post-migrate sync of the
  `django.contrib.sites` record (upstream migration `accounts.0004` names it
  "Brightbean", which allauth puts into email subjects).
- `config/settings/studio.py`: the fork's settings.
- `.dockerignore`: upstream had none, so `COPY . .` baked `.env` (secrets) and
  local uploads into the image.
- `docker-compose.studio.yml`: production overlay. Stops publishing Postgres
  (5432, password `postgres`) and Gunicorn (8000, plain HTTP) on the host, takes
  the database password from `.env`, passes `APP_DOMAIN` to Caddy, adds backups.
- `deploy/deploy.sh`, `deploy/backup/`: deploy script and nightly backup service.
- `docs/fork/`: fork rules, baseline report, deployment guide.

### Changed test expectations

None. All 2,793 upstream tests pass unchanged (`config/settings/test.py` already
pins `SIGNUP_MODE=open` for its own signup tests).
