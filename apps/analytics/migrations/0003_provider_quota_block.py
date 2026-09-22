"""The quota circuit-breaker table. CreateModel only — no schema change to
anything that already holds rows, so nothing here can conflict with a release
running against a live database.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0002_snapshot_raw_errors"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProviderQuotaBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("platform", models.CharField(max_length=30)),
                ("credential_key", models.CharField(max_length=64)),
                ("quota_scope", models.CharField(blank=True, default="", max_length=20)),
                ("blocked_until", models.DateTimeField()),
                ("reason", models.TextField(blank=True, default="")),
                ("tripped_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "analytics_provider_quota_block",
                "unique_together": {("platform", "credential_key", "quota_scope")},
            },
        ),
    ]
