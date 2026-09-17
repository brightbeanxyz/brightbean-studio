"""Invitation send bookkeeping: how often, and when last.

Two AddFields. ``send_count`` has a default, so Postgres fills it in the
catalogue rather than rewriting the table (PG11+), and ``last_sent_at`` is
nullable — an existing invitation genuinely has no recorded send time, and
guessing one would hand out or withhold a cooldown that never happened. No
index and no RunPython, which is the combination that fails on this database
once the table holds rows.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_invitation_org_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='last_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='invitation',
            name='send_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
