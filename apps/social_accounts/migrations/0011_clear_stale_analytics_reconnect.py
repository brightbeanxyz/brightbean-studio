from django.db import migrations

NO_ANALYTICS_PLATFORMS = ("linkedin_personal", "bluesky", "mastodon")


def clear_stale_flags(apps, schema_editor):
    SocialAccount = apps.get_model("social_accounts", "SocialAccount")
    SocialAccount.objects.filter(
        platform__in=NO_ANALYTICS_PLATFORMS,
        analytics_needs_reconnect=True,
    ).update(analytics_needs_reconnect=False)


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0010_seed_analytics_platform_config"),
    ]

    operations = [
        migrations.RunPython(clear_stale_flags, migrations.RunPython.noop),
    ]
