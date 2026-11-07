import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("composer", "0020_platformpost_first_comment_state"),
        ("content_intelligence", "0003_alter_generatedcontent_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="generatedcontent",
            name="composer_post",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="generated_source",
                to="composer.post",
            ),
        ),
    ]
