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
        ("credentials", "0004_rename_instagram_personal_to_login"),
    ]

    operations = [
        migrations.AlterField(
            model_name="platformcredential",
            name="platform",
            field=models.CharField(choices=PLATFORM_CHOICES, max_length=30),
        ),
    ]
