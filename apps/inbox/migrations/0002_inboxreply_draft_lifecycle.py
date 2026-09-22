"""Give ``InboxReply`` a draft → sent/failed lifecycle.

Before this, an ``InboxReply`` row was written only *after* the platform
accepted the reply, so ``sent_at`` could be ``auto_now_add`` and every
row implicitly meant "delivered". Draft replies (created by an agent, or
saved from the composer for later) need a row that exists before any
send, so we add an explicit ``status`` plus ``created_at`` / ``updated_at``
and make ``sent_at`` nullable.

Schema only, deliberately: every pre-existing row still has to be
backfilled to ``sent``, but that runs in ``0003`` so it lands in its own
transaction. ``status`` is indexed, and Django defers a new field's
``CREATE INDEX`` to the end of the migration — so a backfill living here
would leave pending FK trigger events on ``inbox_reply`` and Postgres
would refuse to build the index. See ``0003`` for the full story.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inbox", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="inboxreply",
            name="status",
            field=models.CharField(
                choices=[("draft", "Draft"), ("sent", "Sent"), ("failed", "Failed")],
                db_index=True,
                default="draft",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="inboxreply",
            name="send_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="inboxreply",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="inboxreply",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="inboxreply",
            name="sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="inboxreply",
            options={"ordering": ["created_at"]},
        ),
    ]
