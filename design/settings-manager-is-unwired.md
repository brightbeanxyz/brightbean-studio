# apps.settings_manager is declared but largely unconsulted

`apps/settings_manager` implements a three-tier cascade (workspace -> org -> `APP_DEFAULTS`) and declares roughly forty keys. Almost nothing reads it.

Concrete examples found at migration time:

- `APP_DEFAULTS['publishing.first_comment_delay_seconds']` exists, while   the publisher reads `settings.PUBLISHER_FIRST_COMMENT_DELAY` - a name   that is not defined in `config/settings/base.py` either, so the   hardcoded fallback is what actually runs.
- `apps/approvals/tasks.py` carried a comment claiming its thresholds   were overridable through the cascade. No `get_setting()` call exists   in that module.

Decision: **not resolved in this migration.** Either wiring the cascade up or deleting the app is a behavioural change unrelated to Django 6, and mixing it in would make the migration unreviewable. The false comment is corrected; the underlying duplication is recorded here so the next reader does not mistake the layer for a live one.
