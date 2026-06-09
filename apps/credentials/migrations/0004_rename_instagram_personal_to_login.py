from django.db import migrations, models


def rename_instagram_personal(apps, schema_editor):
    PlatformCredential = apps.get_model("credentials", "PlatformCredential")
    PlatformCredential.objects.filter(platform="instagram_personal").update(platform="instagram_login")


def revert_instagram_login(apps, schema_editor):
    PlatformCredential = apps.get_model("credentials", "PlatformCredential")
    PlatformCredential.objects.filter(platform="instagram_login").update(platform="instagram_personal")


class Migration(migrations.Migration):
    dependencies = [
        ("credentials", "0003_add_instagram_personal_platform"),
    ]

    operations = [
        migrations.RunPython(rename_instagram_personal, revert_instagram_login),
        migrations.AlterField(
            model_name="platformcredential",
            name="platform",
            field=models.CharField(
                choices=[
                    ("facebook", "Facebook"),
                    ("instagram", "Instagram"),
                    ("instagram_login", "Instagram (Direct)"),
                    ("linkedin_personal", "LinkedIn (Personal Profile)"),
                    ("linkedin_company", "LinkedIn (Company Page)"),
                    ("tiktok", "TikTok"),
                    ("youtube", "YouTube"),
                    ("pinterest", "Pinterest"),
                    ("threads", "Threads"),
                    ("bluesky", "Bluesky"),
                    ("google_business", "Google Business Profile"),
                    ("mastodon", "Mastodon"),
                ],
                max_length=30,
            ),
        ),
    ]
