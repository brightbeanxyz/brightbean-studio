# Phase 0 baseline

Recorded 2026-11-18 against upstream `main` at `14b92fc` (the commit the build brief
was written against; upstream had not moved since).

## Environment

Python 3.12.3, PostgreSQL 16, Node 22, ruff 0.15.9 (pinned to CI's version),
mypy from `requirements.txt`. Settings `config.settings.test`, as CI runs them.

## Results before any change

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check .` | Pass |
| Format | `ruff format --check .` | Pass |
| Types | `mypy apps/ config/ providers/ tests/ --ignore-missing-imports` | Pass (598 files) |
| Migrations | `python manage.py makemigrations --check --dry-run` | No changes |
| System check | `python manage.py check` (development settings) | No issues |
| Tests | `pytest --cov=apps` | **2,793 passed, 1 skipped, 0 failed** in 3 min 9 s; coverage 80% |
| App | `runserver`, `GET /health/`, `/accounts/login/`, `/accounts/signup/` | 200, 200, 200 (sign-up open to anyone) |

There were no failing tests to report. The one skip is
`apps/accounts/tests/test_invite_single_use.py` ("needs real row locks"). The 954
warnings are two upstream notices repeated: django-ninja's deprecation of tuple
returns, and whitenoise's "No directory at staticfiles/" (collectstatic is not
run for tests).

## Where the build brief no longer matches the code

Confirmed as described: PlatformPost statuses and `VALID_TRANSITIONS`, approval mode
default `none`, `ApprovalAction` without a version link, one-at-a-time portal
approval with `bulk_approve` available in `apps/approvals/services.py`, the portal
Reports placeholder, TikTok's `PUBLIC_TO_EVERYONE` default and inbox-as-failure,
Facebook's `page_total_media_view_unique` / `post_total_media_view_unique`,
Instagram on `views`, no dark theme, no translation files, no PDF library, the
Intelligence add-on off when its variables are blank, and `for_workspace()` only
filtering when called.

Differences and additions:

1. **Orange is wider than "about 75 files".** 77 templates hold 503 hard-coded
   `orange-*` / `amber-*` classes, and 120 templates hold 1,954 hard-coded
   `stone-*` / `gray-*` neutrals that also bypass the tokens. Several standalone
   pages (`notifications/unsubscribe*.html`, `members/accept_invite.html`) use inline
   hex colors and their own `<style>` blocks. `styles.css` also hard-codes the orange
   in `rgba(249,115,22,…)` shadows. Phase 1 has to cover all of it.
2. **The CSP is not strict today.** `script-src` allows `'unsafe-eval'` (Alpine's
   standard build) and `https://cdn.jsdelivr.net`, from which `base.html` loads
   flatpickr, Chart.js and SortableJS; `style-src` allows `'unsafe-inline'`.
   Self-hosting the fonts alone will not make it strict; Phase 1 should vendor those
   three libraries too.
3. **Re-approval already covers media, partly.** Attaching or removing media on an
   approved post reverts it (three call sites in `apps/composer/views.py`). The rest
   of the gap is as described: the content snapshot is title, caption, first comment
   and tags only, per-platform overrides and settings are not compared, and only
   `approved` posts are reverted.
4. **Magic links are already tied to a person and revocable in code.**
   `MagicLinkToken.user` is a required foreign key, and
   `apps.client_portal.services.revoke_magic_link()` exists, but nothing calls it:
   there is no route or button. The remaining work is the studio-facing revoke
   action, its audit entry and a test.
5. **`draft → scheduled` is a legal model transition.** The approval gate lives in
   the callers (`_require_approval_gate_passes` in composer, calendar and the API
   service layer), and `approved → scheduled` is always allowed. Phase 4's
   "every route into scheduled" tests must check the callers, not just the model.
6. **Two-factor authentication is missing.** `User` has `totp_secret`,
   `totp_recovery_codes` and `totp_enabled`, and settings have
   `org.2fa_enforcement`, but there is no enrolment or verification flow, and
   `django-otp` (named in `architecture.md`) is not installed. django-allauth 65,
   already a dependency, ships `allauth.mfa`, which is the smallest route.
7. **`architecture.md` describes things that do not exist:** `apps.reports`,
   `apps.whitelabel`, `apps.integrations`, the `backup` / `restore` management
   commands, a Resend API email backend, and an ORM manager that filters
   automatically. Phase 0 adds a backup service instead (see `deployment.md`).
8. **Email silently falls back to the console.** Any `EMAIL_BACKEND_TYPE` other
   than `smtp` selects Django's console backend, which prints mail to the log
   instead of sending it. Deploy check `about.W007` now flags it.
9. **Upstream's Docker Compose setup was unsafe for a VPS.** No `.dockerignore`, so
   `.env` was copied into the image. Postgres was published on port 5432 with
   password `postgres`, Gunicorn on port 8000 over plain HTTP, the prod overlay
   hard-coded the database password, and `APP_DOMAIN` never reached Caddy (the README
   says to edit the Caddyfile). Fixed in a fork-owned overlay; see `CHANGES.md`.
10. **Instagram's `content_publishing_limit` is never read**, so the live limit
    check is new work for Phase 6.
11. **With S3 storage the publisher hands platforms presigned URLs** valid for one
    hour (`apps/publisher/engine.py`), which fits Instagram's "create the container
    close to publish time" rule. With local storage, `/media/` must stay public for
    the same reason, so "private files through short-lived signed links" needs
    `STORAGE_BACKEND=s3`.
12. **There is no client data export, and no malware scanning of uploads.**
    Workspace archive and delete exist.
13. **Calendar events are `CustomCalendarEvent`**, alongside `PostingSlot`, `Queue`,
    `QueueEntry` and `RecurrenceRule`, all in `apps/calendar/models.py`.
14. **The pre-commit mypy hook cannot pass, even on untouched upstream code.** Its
    isolated environment has only `django-stubs` and `types-requests`, so the Django
    plugin fails to import `environ` while loading settings. CI runs mypy from the
    project's own environment and passes; so does `make typecheck`. Every other
    pre-commit hook passes on the Phase 0 changes.
15. **`manage.py check --deploy` reports seven `oauth2_provider` RFC 9700 warnings**
    (implicit and password grants enabled, plain PKCE accepted, plaintext token
    storage, no refresh-token replay detection). They concern the MCP OAuth server
    and should be settled whenever the API and MCP access rules are tightened to
    studio staff.
