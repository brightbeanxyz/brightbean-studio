import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content_intelligence", "0006_visual_brief")]
    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("active", "Active"), ("completed", "Completed"), ("archived", "Archived")], db_index=True, default="active", max_length=12)),
                ("starts_at", models.DateField(blank=True, null=True)),
                ("ends_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("brand", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="campaigns", to="brands.brandprofile")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="campaigns", to="workspaces.workspace")),
            ],
            options={"db_table": "content_intelligence_campaign", "ordering": ["name"]},
        ),
        migrations.AddConstraint(model_name="campaign", constraint=models.UniqueConstraint(fields=("workspace", "name"), name="unique_campaign_name_workspace")),
        migrations.AddIndex(model_name="campaign", index=models.Index(fields=["workspace", "status"], name="content_campaign_ws_status")),
        migrations.AddField(model_name="contentplan", name="campaign", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_plans", to="content_intelligence.campaign")),
        migrations.AddField(model_name="generatedcontent", name="archived_at", field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="generatedcontent", name="campaign", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_content", to="content_intelligence.campaign")),
    ]
