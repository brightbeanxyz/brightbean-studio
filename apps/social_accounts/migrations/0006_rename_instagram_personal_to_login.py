from django.db import migrations, models


def rename_instagram_personal(apps, schema_editor):
    SocialAccount = apps.get_model("social_accounts", "SocialAccount")
    SocialAccount.objects.filter(platform="instagram_personal").update(platform="instagram_login")
    PlatformVisibility = apps.get_model("social_accounts", "PlatformVisibility")
    PlatformVisibility.objects.filter(platform="instagram_personal").update(platform="instagram_login")


def revert_instagram_login(apps, schema_editor):
    SocialAccount = apps.get_model("social_accounts", "SocialAccount")
    SocialAccount.objects.filter(platform="instagram_login").update(platform="instagram_personal")
    PlatformVisibility = apps.get_model("social_accounts", "PlatformVisibility")
    PlatformVisibility.objects.filter(platform="instagram_login").update(platform="instagram_personal")


CHOICES = [
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
]


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0005_seed_platform_visibility"),
        ("credentials", "0004_rename_instagram_personal_to_login"),
    ]

    operations = [
        migrations.RunPython(rename_instagram_personal, revert_instagram_login),
        migrations.AlterField(
            model_name="socialaccount",
            name="platform",
            field=models.CharField(choices=CHOICES, max_length=30),
        ),
        migrations.AlterField(
            model_name="platformvisibility",
            name="platform",
            field=models.CharField(choices=CHOICES, max_length=30, unique=True),
        ),
    ]
