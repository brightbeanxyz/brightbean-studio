"""Adds the digest queue and claim markers to notification deliveries.

Two nullable AddFields, no index and no data migration: on Postgres those
are catalogue-only changes, so they neither rewrite the table nor block the
release running against it. Deliberately NOT ``db_index=True`` alongside a
RunPython — that combination fails on this database with "pending trigger
events" once the table holds real rows. The existing (status, next_retry_at)
index already narrows the digest query enough.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0004_alter_notification_event_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationdelivery',
            name='batch_queued_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='notificationdelivery',
            name='batch_claimed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
