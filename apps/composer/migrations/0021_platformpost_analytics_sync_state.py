"""Per-post analytics sync state: last attempt + consecutive failure count.

Schema only. Neither field is indexed and there is no ``RunPython`` here, which
is deliberate: ``AddField(db_index=True)`` in the same migration as a data pass
defers the ``CREATE INDEX`` and dies on Postgres against a table with real rows
("cannot ALTER TABLE because it has pending trigger events"). Keeping the two
apart means that failure mode cannot arise. ``analytics_failure_count`` uses
``db_default=0`` so the default remains in PostgreSQL for the whole lifetime of
this migration. That is important because the previous slug can still insert a
``PlatformPost`` while the release migration is running.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("composer", "0020_platformpost_first_comment_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformpost",
            name="analytics_attempted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="platformpost",
            name="analytics_failure_count",
            field=models.PositiveSmallIntegerField(default=0, db_default=0),
        ),
    ]
