import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_set_site_brightbean"),
        ("workspaces", "0003_alter_workspace_primary_color_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiToken",
            fields=[
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=100)),
                ("token_prefix", models.CharField(db_index=True, max_length=12)),
                ("token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "scoped_workspace",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_tokens",
                        to="workspaces.workspace",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "accounts_api_token",
                "ordering": ["-created_at"],
            },
        ),
    ]
