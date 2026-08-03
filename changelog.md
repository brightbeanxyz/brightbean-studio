# Changelog

Historic detail lives here rather than in source comments (rule 3): comments
describe what is alive, this file records how it got that way.

Entries are newest-first. Each carries the commit the change was applied on
top of, and that commit's own date.

The date is the BASELINE COMMIT's, not the moment of generation, and it is
labelled as such. Derived output that stamps the current time differs on every
run, so regenerating this file produced a diff that meant nothing. If you want
to know when a change landed, read the git history of this file; the stamp
below tells you what it was applied to.

## Django 5.1 -> 6.0.7

- **Base commit:** `e4da3a2c2b717f9140af54a7a03a34b90ae4cf59`
- **Baseline dated:** 2026-07-02T22:16:40+02:00

### python-floor

- `Dockerfile` - python 3.12-slim -> 3.13-slim
  - *Why:* Conform to .python-version, which already declared 3.13.
- `pyproject.toml` - ruff target-version and mypy python_version -> 3.13
  - *Why:* Static analysis must target the version actually deployed, or it reports on syntax the runtime never sees.
- `.github/workflows/ci.yml` - all 3 setup-python jobs 3.12 -> 3.13
  - *Why:* CI installed and tested on an interpreter the application no longer ships on. The file was absent from the plan, so the requirement this step generates was contradicted by the tree it was generated from.
- `.pre-commit-config.yaml` - default_language_version python3.12 -> python3.13
  - *Why:* Hooks ran ruff and mypy under a different interpreter than the one the project declares, so a contributor's pre-commit run and CI could disagree with the deployed runtime.

### csp

- `config/settings/base.py` - django-csp flat CSP_* settings -> core SECURE_CSP dict; form-action named
  - *Why:* Django 6.0 provides CSP in core. Removes a dependency and the settings/decorator API divergence django-csp 4.0 would have forced.
- `config/settings/development.py` - CSP_REPORT_ONLY flag -> SECURE_CSP_REPORT_ONLY setting
  - *Why:* Core CSP expresses report-only as a separate policy, not a flag on one.
- `config/settings/test.py` - CSP_REPORT_ONLY flag -> SECURE_CSP_REPORT_ONLY setting
  - *Why:* Core CSP expresses report-only as a separate policy, not a flag on one.
- `3 modules` - @csp_update -> @csp_override, splatting the named form-action base
  - *Why:* csp_update appends to a directive; csp_override replaces it. Restating the base at each site would be four copies that drift, so each splats one named list instead.
- `apps/onboarding/views.py` - DELETED the @csp_update on connection_oauth_start instead of converting it
  - *Why:* It appended ten form-action hosts that the base list already contains, so under django-csp's append semantics the policy it served WAS the base policy - settled by set membership against the two lists, not by judgement. Converting it would have shipped a decorator claiming an effect it does not have. Called out on its own line because a CSP decorator disappearing from an OAuth start view must be visible in the record even when it is provably a no-op.
- `templates/ + apps/api/api.py` - 27 template sites, plus the comment in apps/api/api.py: {{ request.csp_nonce }} -> {{ csp_nonce }}
  - *Why:* Core Django stores the nonce privately as request._csp_nonce and publishes it as csp_nonce via the context processor. The old spelling renders empty and blocks every inline script - silently, in production.
- `tests/test_csp_overrides.py` - new unit test: every @csp_override site must widen the base policy, not replace it
  - *Why:* The e2e test covers the one override site reachable without auth; the account-connection sites were argued correct and never executed, and a site added later was covered by nothing. This discovers the sites from the URLconf, so the property holds for all of them and for future ones.

### comment-truth

- `apps/approvals/tasks.py` - corrected a comment claiming a settings_manager override that does not exist
  - *Why:* No call site in this module calls get_setting(); the override path was aspirational.
- `3 files` - reads name encoding="utf-8" instead of inheriting the platform's
  - *Why:* Python falls back to the locale encoding, so these behaved one way on CI and another on a German Windows shell - one of them silently changing whether the test suite passed. apps/calendar/holidays.py is application code and would raise in production on such a host.
- `README.md, development_specs/architecture.md` - the shipped docs state Django 6.0, Python 3.13 and core CSP
  - *Why:* The repository front page and the architecture spec still declared Django 5.x, Python 3.12+ and a CSP provided by django-csp - the dependency this same run deletes. Nothing gates markdown, so all of it survived every check; and a contributor following the front page installs 3.12, whereupon pre-commit fails looking for python3.13.
- *Note:* scanned every module; no comment names removed machinery

### requirements

- `requirements.txt` - Django 5.1 -> 6.0.7
  - *Why:* Migration target.
- `requirements.txt` - removed django-csp
  - *Why:* Django 6.0 ships Content Security Policy in core (django.middleware.csp.ContentSecurityPolicyMiddleware).
- *Note:* django-background-tasks RETAINED - measured to run clean on 6.0.7 (migrations apply, a @background call enqueues, and `process_tasks` executed all eleven recurring jobs with zero failures), and replacing it is out of scope for a framework migration
- *Note:* `mcp` pin is imported by NOTHING - flagged as removable, but left in place because dependency removal is out of scope for a Django migration. Recorded as a design note instead.

### e2e

- `tests/e2e/ + config/settings/e2e.py` - new end-to-end suite: 9 files
  - *Why:* Rule 6. The first test pins the empty-nonce regression, which no existing gate in this repository could see.
- `pyproject.toml` - registered the e2e marker and deselected it by default (-m "not e2e")
  - *Why:* The unit suite must stay as fast as it was. An e2e run is a separate command because it also needs a different settings module.
- `requirements.txt` - added pytest-playwright
  - *Why:* Supplies the browser the e2e suite drives. Postgres is NOT added as a dependency: the suite uses the server's own binaries directly and psycopg is already required.
- `Makefile` - added a test-e2e target
  - *Why:* The e2e run needs --ds=config.settings.e2e and a browser binary; putting that in one target stops it being rediscovered each time.
- `.github/workflows/ci.yml` - added an e2e job, so the end-to-end suite actually runs on push and PR
  - *Why:* CI ran a bare `pytest`, which inherits `-m 'not e2e'` from addopts, so EVERY e2e test was deselected on every run. The only detectors for the two silent CSP defects were therefore never executed by anything automated. UNVERIFIED: this job has not been run - it needs GitHub's runner - so its first push is its first execution.
- `apps/publisher/engine.py` - publisher pool threads now release their database connection
  - *Why:* Django opens a connection per thread and frees it only on garbage collection; a worker process fires none of the signals that call close_old_connections(), and both pools are rebuilt every tick. Surfaced by the new publish-path e2e test, which could not drop its database afterwards.

### docs

- `requirements/python-version.md` - generated requirement entry
  - *Why:* Rule 4.
- `requirements/content-security-policy.md` - generated requirement entry
  - *Why:* Rule 4.
- `design/csp-provider.md` - generated design entry
  - *Why:* Rule 4.
- `design/settings-manager-is-unwired.md` - generated design entry
  - *Why:* Rule 4.
- `design/unused-mcp-dependency.md` - generated design entry
  - *Why:* Rule 4.
- `requirements/dependency-currency.md` - generated requirement entry
  - *Why:* Rule 4.
- `design/no-lockfile.md` - generated design entry
  - *Why:* Rule 4.
- `requirements/end-to-end-testing.md` - generated requirement entry
  - *Why:* Rule 4.
- `design/e2e-ephemeral-postgres.md` - generated design entry
  - *Why:* Rule 4.
- `design/django-6-0-not-5-2-lts.md` - generated design entry
  - *Why:* Rule 4.
- `design/keep-django-background-tasks.md` - generated design entry
  - *Why:* Rule 4.
- `requirements/background-work.md` - generated requirement entry
  - *Why:* Rule 4.
- `changelog.md` - recorded this migration
  - *Why:* Rule 3.
