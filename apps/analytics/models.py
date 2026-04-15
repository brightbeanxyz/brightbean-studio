import uuid

from django.db import models

from apps.common.managers import WorkspaceScopedManager


class PostSnapshot(models.Model):
    """Point-in-time engagement metrics for a published post.

    Upserted on refresh — keyed on (social_account, platform_post_id)
    so each post always has exactly one row with the latest metrics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="post_snapshots",
    )
    social_account = models.ForeignKey(
        "social_accounts.SocialAccount",
        on_delete=models.CASCADE,
        related_name="post_snapshots",
    )
    linked_platform_post = models.ForeignKey(
        "composer.PlatformPost",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapshots",
    )

    platform_post_id = models.CharField(max_length=255)
    post_url = models.URLField(max_length=500, blank=True, default="")
    post_text = models.TextField(blank=True, default="")
    post_type = models.CharField(max_length=30, blank=True, default="")
    posted_at = models.DateTimeField()

    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    engagements = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)

    extra = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "analytics_post_snapshot"
        unique_together = [("social_account", "platform_post_id")]
        ordering = ["-posted_at"]

    def __str__(self):
        return f"{self.social_account.account_name}: {self.post_text[:50]}"

    @property
    def engagement_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return round((self.engagements / self.impressions) * 100, 1)


class RefreshLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        ERROR = "error", "Error"
        RATE_LIMITED = "rate_limited", "Rate Limited"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="refresh_logs",
    )
    social_account = models.ForeignKey(
        "social_accounts.SocialAccount",
        on_delete=models.CASCADE,
        related_name="refresh_logs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )
    posts_fetched = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "analytics_refresh_log"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.social_account.account_name} — {self.status} ({self.started_at})"
