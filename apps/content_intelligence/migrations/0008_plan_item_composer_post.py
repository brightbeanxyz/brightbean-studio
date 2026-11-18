from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("content_intelligence", "0007_campaign_and_library_fields")]

    operations = [
        migrations.AddField(
            model_name="contentplanitem",
            name="composer_post",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="content_plan_item",
                to="composer.post",
            ),
        ),
    ]
