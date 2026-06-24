"""Approval workflow models (F-2.2).

Models:
    ApprovalAction - Audit trail of approval decisions on a post.
    PostComment - Threaded comments with internal/external visibility.
    ApprovalReminder - Tracks reminder state per post per stage.
"""

import uuid

from django.conf import settings
from django.db import models


class ApprovalAction(models.Model):
    """Audit trail entry for an approval workflow action on a post."""

    class ActionType(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"
        REJECTED = "rejected", "Rejected"
        RESUBMITTED = "resubmitted", "Resubmitted"
        HELD = "held", "Hold Requested"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        "composer.Post",
        on_delete=models.CASCADE,
        related_name="approval_actions",
    )
    # Optional pointer to the specific PlatformPost the action targeted. Null
    # means the action was bundled at the Post level (all platforms at once).
    platform_post = models.ForeignKey(
        "composer.PlatformPost",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="approval_actions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_actions",
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approvals_approval_action"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["post", "-created_at"], name="idx_approval_post_date"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.user} on {self.post_id}"


class PostComment(models.Model):
    """Threaded comment on a post with internal/external visibility."""

    class Visibility(models.TextChoices):
        INTERNAL = "internal", "Internal"
        EXTERNAL = "external", "External"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        "composer.Post",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="post_comments",
    )
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField()
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.EXTERNAL,
    )
    attachment = models.ImageField(
        upload_to="comment_attachments/%Y/%m/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "approvals_post_comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"], name="idx_comment_post_date"),
            models.Index(fields=["post", "visibility"], name="idx_comment_post_vis"),
        ]

    def __str__(self):
        prefix = "[deleted] " if self.deleted_at else ""
        return f"{prefix}Comment by {self.author} on {self.post_id}"

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class ApprovalReminder(models.Model):
    """Tracks reminder count per post per approval stage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        "composer.Post",
        on_delete=models.CASCADE,
        related_name="approval_reminders",
    )
    stage = models.CharField(max_length=20)
    reminder_count = models.PositiveIntegerField(default=0)
    last_reminder_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)

    class Meta:
        db_table = "approvals_approval_reminder"
        unique_together = [("post", "stage")]

    def __str__(self):
        return f"Reminder({self.stage}, count={self.reminder_count}) for {self.post_id}"
