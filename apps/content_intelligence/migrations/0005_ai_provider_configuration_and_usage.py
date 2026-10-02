import apps.common.encryption
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("content_intelligence", "0004_generatedcontent_composer_post"),
        ("organizations", "0002_organization_billing_email"),
    ]

    operations = [
        migrations.AddField(model_name="generationrequest", name="attempt_count", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="generationrequest", name="input_tokens", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="generationrequest", name="output_tokens", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="generationrequest", name="estimated_cost_usd", field=models.DecimalField(decimal_places=6, default=0, max_digits=10)),
        migrations.AlterField(model_name="generationrequest", name="provider", field=models.CharField(choices=[("openai", "OpenAI"), ("anthropic", "Anthropic"), ("gemini", "Gemini"), ("openrouter", "OpenRouter"), ("ollama", "Ollama"), ("agnes", "Agnes AI")], max_length=20)),
        migrations.CreateModel(
            name="AIProviderConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("openai", "OpenAI"), ("anthropic", "Anthropic"), ("gemini", "Gemini"), ("openrouter", "OpenRouter"), ("ollama", "Ollama"), ("agnes", "Agnes AI")], max_length=20)),
                ("api_key", apps.common.encryption.EncryptedTextField(blank=True, default="")),
                ("default_model", models.CharField(blank=True, default="", max_length=120)),
                ("base_url", models.URLField(blank=True, default="")),
                ("is_enabled", models.BooleanField(default=False)),
                ("daily_request_limit", models.PositiveIntegerField(default=100)),
                ("timeout_seconds", models.PositiveSmallIntegerField(default=60)),
                ("max_retries", models.PositiveSmallIntegerField(default=2)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_provider_configurations", to="organizations.organization")),
            ],
            options={"db_table": "content_intelligence_ai_provider_configuration", "ordering": ["provider"]},
        ),
        migrations.AddConstraint(model_name="aiproviderconfiguration", constraint=models.UniqueConstraint(fields=("organization", "provider"), name="unique_ai_provider_per_org")),
    ]
