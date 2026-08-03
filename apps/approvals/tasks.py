"""Background tasks for approval workflow reminders."""

import logging
from datetime import timedelta

from background_task import background
from django.utils import timezone

from apps.composer.models import Post
from apps.members.models import WorkspaceMembership
from apps.notifications.engine import notify
from apps.notifications.models import EventType

from .models import ApprovalReminder

logger = logging.getLogger(__name__)

# Reminder thresholds. These are module constants and are NOT read
# through apps.settings_manager - nothing in this module calls
# get_setting(). Change them here, or wire the cascade in deliberately.
PENDING_REVIEW_HOURS = 24
PENDING_CLIENT_HOURS = 48
MAX_REMINDERS = 2


def check_approval_reminders():
    """Check for stalled approvals and send reminders.

    Should be run periodically (every hour).
    """
    now = timezone.now()

    # 1. Posts stuck in pending_review
    _process_stage(
        stage="pending_review",
        status="pending_review",
        threshold_hours=PENDING_REVIEW_HOURS,
        now=now,
    )

    # 2. Posts stuck in pending_client
    _process_stage(
        stage="pending_client",
        status="pending_client",
        threshold_hours=PENDING_CLIENT_HOURS,
        now=now,
    )


def _process_stage(stage, status, threshold_hours, now):
    """Process reminders for a specific approval stage."""
    threshold = now - timedelta(hours=threshold_hours)

    stalled_posts = (
        Post.objects.filter(
            platform_posts__status=status,
            updated_at__lte=threshold,
        )
        .distinct()
        .select_related("workspace", "author")
    )

    for post in stalled_posts:
        reminder, created = ApprovalReminder.objects.get_or_create(
            post=post,
            stage=stage,
            defaults={"reminder_count": 0},
        )

        # Check if we should send a reminder
        if reminder.reminder_count >= MAX_REMINDERS:
            # Already sent max reminders - escalate if not already done
            if not reminder.escalated:
                _escalate(post, stage)
                reminder.escalated = True
                reminder.save(update_fields=["escalated"])
            continue

        # Check cooldown (don't spam - wait at least threshold_hours between reminders)
        if reminder.last_reminder_at:
            cooldown = reminder.last_reminder_at + timedelta(hours=threshold_hours)
            if now < cooldown:
                continue

        # Send reminder
        if stage == "pending_review":
            _remind_reviewers(post)
        elif stage == "pending_client":
            _remind_clients(post)

        reminder.reminder_count += 1
        reminder.last_reminder_at = now
        reminder.save(update_fields=["reminder_count", "last_reminder_at"])

        logger.info(
            "Sent reminder #%d for post %s (stage: %s)",
            reminder.reminder_count,
            post.id,
            stage,
        )


def _remind_reviewers(post):
    """Send reminder to workspace members with approve_posts permission."""
    workspace = post.workspace
    memberships = WorkspaceMembership.objects.filter(
        workspace=workspace,
    ).select_related("user", "custom_role")

    for membership in memberships:
        perms = membership.effective_permissions
        if perms.get("approve_posts", False):
            notify(
                user=membership.user,
                event_type=EventType.APPROVAL_REMINDER,
                title="Post awaiting your review",
                body=f'A post in {workspace.name} has been waiting for review: "{post.caption_snippet}"',
                data={
                    "post_id": str(post.id),
                    "workspace_id": str(workspace.id),
                },
            )


def _remind_clients(post):
    """Send reminder to client members."""
    workspace = post.workspace
    client_memberships = WorkspaceMembership.objects.filter(
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
    ).select_related("user")

    for membership in client_memberships:
        notify(
            user=membership.user,
            event_type=EventType.APPROVAL_REMINDER,
            title="Posts waiting for your approval",
            body=f"Content in {workspace.name} is waiting for your review.",
            data={
                "post_id": str(post.id),
                "workspace_id": str(workspace.id),
            },
        )


def _escalate(post, stage):
    """Notify workspace managers that a post is stalled."""
    workspace = post.workspace
    manager_memberships = WorkspaceMembership.objects.filter(
        workspace=workspace,
        workspace_role__in=[
            WorkspaceMembership.WorkspaceRole.OWNER,
            WorkspaceMembership.WorkspaceRole.MANAGER,
        ],
    ).select_related("user")

    stage_label = "internal review" if stage == "pending_review" else "client approval"

    for membership in manager_memberships:
        notify(
            user=membership.user,
            event_type=EventType.APPROVAL_STALLED,
            title="Stalled post needs attention",
            body=f'A post in {workspace.name} has been stuck in {stage_label} after multiple reminders: "{post.caption_snippet}"',
            data={
                "post_id": str(post.id),
                "workspace_id": str(workspace.id),
                "stage": stage,
            },
        )


# How often the recurring approval-reminder check runs; registered on a repeating
# schedule by apps.approvals.apps.ApprovalsConfig.
APPROVAL_REMINDER_INTERVAL_SECONDS = 60 * 60  # hourly


@background(schedule=0)
def run_approval_reminders_cycle():
    """Send reminders/escalations for stalled approvals (registered hourly).

    Wraps ``check_approval_reminders`` so the plain function stays callable
    synchronously from the ``run_approval_reminders`` command and from tests.
    """
    check_approval_reminders()
