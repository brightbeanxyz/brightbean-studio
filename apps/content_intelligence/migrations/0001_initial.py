import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("brands", "0002_editorial_strategy"), ("workspaces", "0003_alter_workspace_primary_color_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="ContentPlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("cadence", models.CharField(choices=[("weekly", "Weekly"), ("monthly", "Monthly")], max_length=10)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(choices=[("draft", "Draft"), ("archived", "Archived")], default="draft", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("brand", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_plans", to="brands.brandprofile")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_content_plans", to=settings.AUTH_USER_MODEL)),
                ("strategy_version", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="content_plans", to="brands.editorialstrategyversion")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_plans", to="workspaces.workspace")),
            ],
            options={"db_table": "content_intelligence_content_plan", "ordering": ["-start_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="ContentPlanItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("position", models.PositiveIntegerField()),
                ("planned_for", models.DateField()),
                ("objective", models.CharField(choices=[("reach", "Reach"), ("authority", "Authority"), ("conversion", "Conversion")], max_length=12)),
                ("topic", models.CharField(max_length=255)),
                ("hook", models.TextField()),
                ("cta", models.TextField(blank=True, default="")),
                ("keywords", models.JSONField(blank=True, default=list)),
                ("hashtags", models.JSONField(blank=True, default=list)),
                ("recommended_format", models.CharField(max_length=50)),
                ("recommended_platform", models.CharField(choices=[("linkedin", "LinkedIn"), ("instagram", "Instagram")], max_length=20)),
                ("content_pillar", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="content_intelligence.contentplan")),
            ],
            options={"db_table": "content_intelligence_content_plan_item", "ordering": ["position"]},
        ),
        migrations.AddIndex(model_name="contentplan", index=models.Index(fields=["workspace", "brand", "start_date"], name="content_int_workspa_4d31e8_idx")),
        migrations.AddConstraint(model_name="contentplanitem", constraint=models.UniqueConstraint(fields=("plan", "position"), name="unique_content_plan_item_position")),
    ]
