"""Re-assert database-level defaults on the columns ``0002`` added.

Django manages defaults in Python, so ``add_field`` emits
``ADD COLUMN ... DEFAULT x NOT NULL`` and then immediately
``ALTER COLUMN ... DROP DEFAULT``. The column is left NOT NULL with no
database default — fine once the new code is live, but not during the
deploy itself.

Heroku's release phase runs ``manage.py migrate`` while the *previous*
slug is still serving traffic. That release's ``InboxReply`` model has no
``status`` / ``send_error`` / ``created_at`` / ``updated_at``, so every
reply it writes (``apps.inbox.services.create_reply``) INSERTs without
them and fails::

    null value in column "status" of relation "inbox_reply"
    violates not-null constraint

Putting the defaults back closes that window: old writes land with
``status='draft'`` until the new slug takes over. This runs as its own
migration rather than inside ``0002`` because staging already applied
``0002`` and would otherwise never get them — here it reaches every
database, and the gap on a fresh one is the few milliseconds between two
consecutive DDL migrations.

The defaults are harmless to keep afterwards: the new code always writes
these columns explicitly, so nothing depends on them.
"""

from django.db import migrations

_COLUMN_DEFAULTS = {
    "status": "'draft'",
    "send_error": "''",
    "created_at": "now()",
    "updated_at": "now()",
}


def _set_column_defaults(apps, schema_editor):
    # Postgres-only: sqlite (the dev server) has no ALTER COLUMN ... SET
    # DEFAULT, and it does not have the release-phase overlap either.
    if schema_editor.connection.vendor != "postgresql":
        return
    for column, default in _COLUMN_DEFAULTS.items():
        schema_editor.execute(f'ALTER TABLE "inbox_reply" ALTER COLUMN "{column}" SET DEFAULT {default}')


def _drop_column_defaults(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for column in _COLUMN_DEFAULTS:
        schema_editor.execute(f'ALTER TABLE "inbox_reply" ALTER COLUMN "{column}" DROP DEFAULT')


class Migration(migrations.Migration):
    dependencies = [
        ("inbox", "0002_inboxreply_draft_lifecycle"),
    ]

    operations = [
        migrations.RunPython(_set_column_defaults, _drop_column_defaults),
    ]
