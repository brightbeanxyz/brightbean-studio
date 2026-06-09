from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("social_accounts", "0006_rename_instagram_personal_to_login"),
    ]

    operations = [
        migrations.AlterField(
            model_name="socialaccount",
            name="avatar_url",
            field=models.URLField(blank=True, default="", max_length=2000),
        ),
    ]
