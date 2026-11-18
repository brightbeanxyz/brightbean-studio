import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("brands", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="EditorialStrategy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("reach_percentage", models.PositiveSmallIntegerField(default=35)),
                ("authority_percentage", models.PositiveSmallIntegerField(default=50)),
                ("conversion_percentage", models.PositiveSmallIntegerField(default=15)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("brand", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="editorial_strategy", to="brands.brandprofile")),
            ],
            options={"db_table": "brands_editorial_strategy"},
        ),
        migrations.CreateModel(
            name="EditorialStrategyVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("version", models.PositiveIntegerField()),
                ("reach_percentage", models.PositiveSmallIntegerField()),
                ("authority_percentage", models.PositiveSmallIntegerField()),
                ("conversion_percentage", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="editorial_strategy_versions", to=settings.AUTH_USER_MODEL)),
                ("strategy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="brands.editorialstrategy")),
            ],
            options={"db_table": "brands_editorial_strategy_version", "ordering": ["-version"]},
        ),
        migrations.AddConstraint(
            model_name="editorialstrategyversion",
            constraint=models.UniqueConstraint(fields=("strategy", "version"), name="unique_editorial_strategy_version"),
        ),
    ]
