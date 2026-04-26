from django.db import migrations


def seed_platform_visibility(apps, schema_editor):
    PlatformVisibility = apps.get_model("social_accounts", "PlatformVisibility")
    PlatformCredential = apps.get_model("credentials", "PlatformCredential")
    for value, _label in PlatformCredential._meta.get_field("platform").choices:
        PlatformVisibility.objects.get_or_create(platform=value, defaults={"is_visible": True})


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0004_platformvisibility"),
        ("credentials", "0003_add_instagram_personal_platform"),
    ]

    operations = [
        migrations.RunPython(seed_platform_visibility, migrations.RunPython.noop),
    ]
