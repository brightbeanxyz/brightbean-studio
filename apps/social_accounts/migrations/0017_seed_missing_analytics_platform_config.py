"""Backfill AnalyticsPlatformConfig rows for platforms added after 0010.

``0010_seed_analytics_platform_config`` enumerated the platform choices as they
stood at that migration, so every slug added later (``devto`` was the first)
has no row and never appears in the admin's Analytics platforms list — leaving
no way to see, let alone change, its analytics state. ``enabled_platforms()``
now reads a missing row as enabled, so this is cosmetic rather than
load-bearing, but the admin list should show every platform.

Idempotent, same as 0010: re-running touches nothing.
"""

from django.db import migrations


def seed_missing_analytics_platform_config(apps, schema_editor):
    AnalyticsPlatformConfig = apps.get_model("social_accounts", "AnalyticsPlatformConfig")
    PlatformCredential = apps.get_model("credentials", "PlatformCredential")
    for value, _label in PlatformCredential._meta.get_field("platform").choices:
        AnalyticsPlatformConfig.objects.get_or_create(platform=value, defaults={"is_enabled": True})


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0016_socialaccount_webhook_error_detail_and_more"),
        ("credentials", "0005_add_devto_platform"),
    ]

    operations = [
        migrations.RunPython(seed_missing_analytics_platform_config, migrations.RunPython.noop),
    ]
