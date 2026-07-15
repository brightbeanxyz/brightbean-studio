from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountinsightssnapshot",
            name="errors",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="accountinsightssnapshot",
            name="raw",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="postinsightssnapshot",
            name="errors",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="postinsightssnapshot",
            name="raw",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
