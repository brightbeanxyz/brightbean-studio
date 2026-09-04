import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import WorkspaceScopedManager


class ContentPlan(models.Model):
    class Cadence(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="content_plans")
    brand = models.ForeignKey("brands.BrandProfile", on_delete=models.CASCADE, related_name="content_plans")
    strategy_version = models.ForeignKey(
        "brands.EditorialStrategyVersion", on_delete=models.PROTECT, related_name="content_plans"
    )
    cadence = models.CharField(max_length=10, choices=Cadence.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_content_plans"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "content_intelligence_content_plan"
        ordering = ["-start_date", "-created_at"]
        indexes = [models.Index(fields=["workspace", "brand", "start_date"], name="content_int_workspa_4d31e8_idx")]

    def __str__(self):
        return f"{self.brand.name} {self.get_cadence_display()} plan ({self.start_date})"

    def clean(self):
        super().clean()
        if self.brand_id and self.workspace_id and self.brand.workspace_id != self.workspace_id:
            from django.core.exceptions import ValidationError

            raise ValidationError({"brand": "Brand must belong to the plan workspace."})
        if self.end_date < self.start_date:
            from django.core.exceptions import ValidationError

            raise ValidationError({"end_date": "End date must not precede start date."})


class ContentPlanItem(models.Model):
    class Objective(models.TextChoices):
        REACH = "reach", "Reach"
        AUTHORITY = "authority", "Authority"
        CONVERSION = "conversion", "Conversion"

    class Platform(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        INSTAGRAM = "instagram", "Instagram"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(ContentPlan, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveIntegerField()
    planned_for = models.DateField()
    objective = models.CharField(max_length=12, choices=Objective.choices)
    topic = models.CharField(max_length=255)
    hook = models.TextField()
    cta = models.TextField(blank=True, default="")
    keywords = models.JSONField(default=list, blank=True)
    hashtags = models.JSONField(default=list, blank=True)
    recommended_format = models.CharField(max_length=50)
    recommended_platform = models.CharField(max_length=20, choices=Platform.choices)
    content_pillar = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_intelligence_content_plan_item"
        ordering = ["position"]
        constraints = [models.UniqueConstraint(fields=["plan", "position"], name="unique_content_plan_item_position")]

    def __str__(self):
        return f"{self.plan}: {self.position} - {self.topic}"


class GenerationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        GEMINI = "gemini", "Gemini"
        OPENROUTER = "openrouter", "OpenRouter"
        OLLAMA = "ollama", "Ollama"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="generation_requests")
    brand = models.ForeignKey("brands.BrandProfile", on_delete=models.CASCADE, related_name="generation_requests")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    model = models.CharField(max_length=120, blank=True, default="")
    platform = models.CharField(max_length=20)
    content_type = models.CharField(max_length=50)
    audience = models.TextField(blank=True, default="")
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    error_message = models.TextField(blank=True, default="")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_generation_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "content_intelligence_generation_request"
        ordering = ["-created_at"]


class GeneratedContent(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(GenerationRequest, on_delete=models.CASCADE, related_name="outputs")
    workspace = models.ForeignKey("workspaces.Workspace", on_delete=models.CASCADE, related_name="generated_content")
    brand = models.ForeignKey("brands.BrandProfile", on_delete=models.CASCADE, related_name="generated_content")
    composer_post = models.OneToOneField(
        "composer.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_source",
    )
    platform = models.CharField(max_length=20)
    content_type = models.CharField(max_length=50)
    variant = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "content_intelligence_generated_content"
        ordering = ["-created_at", "variant"]
        constraints = [models.UniqueConstraint(fields=["request", "variant"], name="unique_generation_output_variant")]
