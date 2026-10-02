import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.common.managers import WorkspaceScopedManager
from apps.common.validators import validate_hex_color


def _validate_string_list(value, field_name):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationError({field_name: "Must be a list of strings."})
    normalized = [item.strip() for item in value]
    if any(not item for item in normalized):
        raise ValidationError({field_name: "Items cannot be blank."})
    if len(normalized) != len(set(item.casefold() for item in normalized)):
        raise ValidationError({field_name: "Items must be unique."})


class BrandProfile(models.Model):
    """Workspace-scoped source of truth for content about one client brand."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="brand_profiles",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    industry = models.CharField(max_length=150, blank=True, default="")
    target_audience = models.TextField(blank=True, default="")
    brand_voice = models.TextField(blank=True, default="")
    tone = models.CharField(max_length=255, blank=True, default="")
    vocabulary = models.JSONField(default=list, blank=True)
    prohibited_terms = models.JSONField(default=list, blank=True)
    preferred_terminology = models.JSONField(default=list, blank=True)
    primary_language = models.CharField(max_length=35, default="English")
    secondary_language = models.CharField(max_length=35, blank=True, default="")
    brand_colors = models.JSONField(default=list, blank=True)
    positioning = models.TextField(blank=True, default="")
    value_proposition = models.TextField(blank=True, default="")
    content_pillars = models.JSONField(default=list, blank=True)
    cta_strategy = models.TextField(blank=True, default="")
    posting_frequency = models.CharField(max_length=255, blank=True, default="")
    target_geographies = models.JSONField(default=list, blank=True)
    target_personas = models.JSONField(default=list, blank=True)
    recruiting_objective = models.TextField(blank=True, default="")
    business_objective = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "brands_brand_profile"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_brand_name_per_workspace",
            )
        ]
        indexes = [models.Index(fields=["workspace", "is_active", "name"], name="brands_bran_workspa_dde665_idx")]

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"

    @property
    def organization(self):
        return self.workspace.organization

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Brand name is required."})

        errors = {}
        list_fields = (
            "vocabulary",
            "prohibited_terms",
            "preferred_terminology",
            "content_pillars",
            "target_geographies",
            "target_personas",
        )
        for field_name in list_fields:
            try:
                _validate_string_list(getattr(self, field_name), field_name)
            except ValidationError as exc:
                errors.update(exc.message_dict)

        try:
            _validate_string_list(self.brand_colors, "brand_colors")
            for color in self.brand_colors:
                validate_hex_color(color)
        except ValidationError as exc:
            if hasattr(exc, "error_dict"):
                errors.update(exc.message_dict)
            else:
                errors["brand_colors"] = exc.messages

        if errors:
            raise ValidationError(errors)


class EditorialStrategy(models.Model):
    """Current REACH/AUTHORITY/CONVERSION mix for a brand."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.OneToOneField(BrandProfile, on_delete=models.CASCADE, related_name="editorial_strategy")
    reach_percentage = models.PositiveSmallIntegerField(default=35)
    authority_percentage = models.PositiveSmallIntegerField(default=50)
    conversion_percentage = models.PositiveSmallIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brands_editorial_strategy"

    def __str__(self):
        return f"Editorial strategy for {self.brand.name}"

    def clean(self):
        super().clean()
        values = (self.reach_percentage, self.authority_percentage, self.conversion_percentage)
        if any(value > 100 for value in values):
            raise ValidationError("Editorial percentages must be between 0 and 100.")
        if sum(values) != 100:
            raise ValidationError("Reach, Authority and Conversion must total 100%.")


class EditorialStrategyVersion(models.Model):
    """Immutable strategy snapshot used to make generated plans reproducible."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    strategy = models.ForeignKey(EditorialStrategy, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    reach_percentage = models.PositiveSmallIntegerField()
    authority_percentage = models.PositiveSmallIntegerField()
    conversion_percentage = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="editorial_strategy_versions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brands_editorial_strategy_version"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["strategy", "version"], name="unique_editorial_strategy_version")
        ]

    def __str__(self):
        return f"{self.strategy.brand.name} v{self.version}"

    def clean(self):
        super().clean()
        values = (self.reach_percentage, self.authority_percentage, self.conversion_percentage)
        if sum(values) != 100 or any(value > 100 for value in values):
            raise ValidationError("Reach, Authority and Conversion must be between 0 and 100 and total 100%.")
