from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0019_inbox_poll_timestamps"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialaccount",
            name="inbox_initial_backfill_cursor",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="socialaccount",
            name="inbox_initial_backfill_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="socialaccount",
            name="inbox_deep_sweep_cursor",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="socialaccount",
            name="inbox_deep_sweep_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
