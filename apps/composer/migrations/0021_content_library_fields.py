import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("brands", "0002_editorial_strategy"),
        ("composer", "0020_platformpost_first_comment_state"),
        ("content_intelligence", "0007_campaign_and_library_fields"),
    ]
    operations = [
        migrations.AddField(model_name="post", name="archived_at", field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="post", name="brand", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="posts", to="brands.brandprofile")),
        migrations.AddField(model_name="post", name="campaign", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="posts", to="content_intelligence.campaign")),
        migrations.AddField(model_name="post", name="origin", field=models.CharField(choices=[("manual", "Manual"), ("ai", "AI generated"), ("import", "Imported"), ("template", "Template")], db_index=True, default="manual", max_length=12)),
        migrations.AddIndex(model_name="post", index=models.Index(fields=["workspace", "origin", "archived_at"], name="composer_post_library_idx")),
    ]
