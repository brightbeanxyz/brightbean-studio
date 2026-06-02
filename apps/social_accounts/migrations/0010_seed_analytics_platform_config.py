from django.db import migrations


def seed_analytics_platform_config(apps, schema_editor):
    AnalyticsPlatformConfig = apps.get_model("social_accounts", "AnalyticsPlatformConfig")
    PlatformCredential = apps.get_model("credentials", "PlatformCredential")
    for value, _label in PlatformCredential._meta.get_field("platform").choices:
        AnalyticsPlatformConfig.objects.get_or_create(platform=value, defaults={"is_enabled": True})


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0009_analytics_platform_config"),
        ("credentials", "0003_add_instagram_personal_platform"),
    ]

    operations = [
        migrations.RunPython(seed_analytics_platform_config, migrations.RunPython.noop),
    ]
