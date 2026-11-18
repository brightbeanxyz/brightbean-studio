from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("composer", "0021_content_library_fields")]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="origin",
            field=models.CharField(
                choices=[
                    ("manual", "Manual"),
                    ("ai", "AI generated"),
                    ("import", "Imported"),
                    ("template", "Template"),
                    ("plan", "Editorial plan"),
                ],
                db_index=True,
                default="manual",
                max_length=12,
            ),
        ),
    ]
