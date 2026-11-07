import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [("workspaces", "0003_alter_workspace_primary_color_and_more")]

    operations = [
        migrations.CreateModel(
            name="BrandProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                ("industry", models.CharField(blank=True, default="", max_length=150)),
                ("target_audience", models.TextField(blank=True, default="")),
                ("brand_voice", models.TextField(blank=True, default="")),
                ("tone", models.CharField(blank=True, default="", max_length=255)),
                ("vocabulary", models.JSONField(blank=True, default=list)),
                ("prohibited_terms", models.JSONField(blank=True, default=list)),
                ("preferred_terminology", models.JSONField(blank=True, default=list)),
                ("primary_language", models.CharField(default="English", max_length=35)),
                ("secondary_language", models.CharField(blank=True, default="", max_length=35)),
                ("brand_colors", models.JSONField(blank=True, default=list)),
                ("positioning", models.TextField(blank=True, default="")),
                ("value_proposition", models.TextField(blank=True, default="")),
                ("content_pillars", models.JSONField(blank=True, default=list)),
                ("cta_strategy", models.TextField(blank=True, default="")),
                ("posting_frequency", models.CharField(blank=True, default="", max_length=255)),
                ("target_geographies", models.JSONField(blank=True, default=list)),
                ("target_personas", models.JSONField(blank=True, default=list)),
                ("recruiting_objective", models.TextField(blank=True, default="")),
                ("business_objective", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="brand_profiles",
                        to="workspaces.workspace",
                    ),
                ),
            ],
            options={
                "db_table": "brands_brand_profile",
                "ordering": ["name"],
                "indexes": [models.Index(fields=["workspace", "is_active", "name"], name="brands_bran_workspa_dde665_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("workspace", "name"), name="unique_brand_name_per_workspace")
                ],
            },
        )
    ]
