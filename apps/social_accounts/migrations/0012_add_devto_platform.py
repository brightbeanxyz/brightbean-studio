from django.db import migrations, models

PLATFORM_CHOICES = [
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
    ("devto", "DEV.to"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0011_clear_stale_analytics_reconnect"),
    ]

    operations = [
        migrations.AlterField(
            model_name="socialaccount",
            name="platform",
            field=models.CharField(choices=PLATFORM_CHOICES, max_length=30),
        ),
        migrations.AlterField(
            model_name="platformvisibility",
            name="platform",
            field=models.CharField(choices=PLATFORM_CHOICES, max_length=30, unique=True),
        ),
        migrations.AlterField(
            model_name="analyticsplatformconfig",
            name="platform",
            field=models.CharField(choices=PLATFORM_CHOICES, max_length=30, unique=True),
        ),
    ]
