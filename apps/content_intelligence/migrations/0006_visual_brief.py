import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("composer", "0020_platformpost_first_comment_state"),
        ("content_intelligence", "0005_ai_provider_configuration_and_usage"),
        ("media_library", "0003_pendingupload"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="VisualBrief",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(choices=[("openai", "OpenAI"), ("agnes", "Agnes AI")], max_length=20)),
                ("model", models.CharField(blank=True, default="", max_length=120)),
                ("objective", models.TextField()),
                ("style", models.CharField(blank=True, default="", max_length=120)),
                ("format", models.CharField(default="square", max_length=40)),
                ("colors", models.JSONField(blank=True, default=list)),
                ("constraints", models.TextField(blank=True, default="")),
                ("prompt", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")], db_index=True, default="pending", max_length=12)),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("brand", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="visual_briefs", to="brands.brandprofile")),
                ("generated_content", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visual_briefs", to="content_intelligence.generatedcontent")),
                ("generation_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visual_briefs", to="content_intelligence.generationrequest")),
                ("media_asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visual_briefs", to="media_library.mediaasset")),
                ("post", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visual_briefs", to="composer.post")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visual_briefs", to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="visual_briefs", to="workspaces.workspace")),
            ],
            options={"db_table": "content_intelligence_visual_brief", "ordering": ["-created_at"]},
        )
    ]
