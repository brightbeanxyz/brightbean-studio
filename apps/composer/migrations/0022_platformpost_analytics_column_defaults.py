"""Re-assert the database-level default on the column ``0021`` added.

``0021`` now uses Django's ``db_default`` and therefore retains the default
during the add. This follow-up remains for databases that already applied an
earlier version of ``0021`` before that fix landed.

``Procfile`` runs ``release: manage.py migrate`` while the *previous* slug is
still serving traffic. That release's ``PlatformPost`` model has no
``analytics_failure_count``, so every row it writes — and the composer autosave
writes them constantly — INSERTs without it and fails::

    null value in column "analytics_failure_count" of relation
    "composer_platform_post" violates not-null constraint

Putting the default back closes that window. ``analytics_attempted_at`` needs
nothing: it is nullable.

This runs as its own migration so a database which has already applied the
earlier ``0021`` still receives the repair, and so the schema change and the
data-affecting statement never share a migration, which is what makes an
indexed ``AddField`` blow up on a populated Postgres table.

The default is harmless to keep afterwards: the new code always writes the
column explicitly.
"""

from django.db import migrations

_COLUMN_DEFAULTS = {
    "analytics_failure_count": "0",
}


def _set_column_defaults(apps, schema_editor):
    # Postgres-only: sqlite (the dev server) has no ALTER COLUMN ... SET
    # DEFAULT, and it does not have the release-phase overlap either.
    if schema_editor.connection.vendor != "postgresql":
        return
    for column, default in _COLUMN_DEFAULTS.items():
        schema_editor.execute(f'ALTER TABLE "composer_platform_post" ALTER COLUMN "{column}" SET DEFAULT {default}')


def _restore_column_defaults(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for column, default in _COLUMN_DEFAULTS.items():
        schema_editor.execute(f'ALTER TABLE "composer_platform_post" ALTER COLUMN "{column}" SET DEFAULT {default}')


class Migration(migrations.Migration):
    dependencies = [
        ("composer", "0021_platformpost_analytics_sync_state"),
    ]

    operations = [
        migrations.RunPython(_set_column_defaults, _restore_column_defaults),
    ]
