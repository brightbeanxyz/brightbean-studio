"""Approval workflow business logic.

Editorial status now lives on ``PlatformPost`` so every social account flows
through the workflow independently. The functions in this module accept either
a ``Post`` (apply the action to *all* eligible children — the historical
"bundled" behaviour) or a single ``PlatformPost`` (per-account decision).

For the bundled case the resulting :class:`ApprovalAction` row stores
``platform_post=None``; for per-account decisions ``platform_post`` is set so
the audit trail remembers exactly which target was acted on.
"""

import logging

from django.db import transaction

from apps.composer.models import PlatformPost, Post
from apps.members.models import WorkspaceMembership
from apps.notifications.engine import notify
from apps.notifications.models import EventType

from .models import ApprovalAction, ApprovalReminder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_targets(target, *, eligible_from_states=None):
    """Normalise *target* into ``(post, [platform_posts], is_bundled)``.

    ``target`` may be a :class:`Post` (returns every child whose current state
    is in ``eligible_from_states``, or all children if not specified) or a
    :class:`PlatformPost` (returns just that one). Eligibility filtering keeps
    bundled actions from blowing up on already-published or already-approved
    siblings.
    """
    if isinstance(target, PlatformPost):
        return target.post, [target], False

    if not isinstance(target, Post):
        raise TypeError(f"Expected Post or PlatformPost, got {type(target).__name__}")

    children = list(target.platform_posts.select_related("social_account"))
    if eligible_from_states is not None:
        children = [pp for pp in children if pp.status in eligible_from_states]
    return target, children, True


def _transition_or_skip(pp, target_status):
    """Transition *pp* to *target_status*, returning True on success."""
    if pp.status == target_status:
        return True
    if not pp.can_transition_to(target_status):
        return False
    pp.transition_to(target_status)
    pp.save(update_fields=["status", "published_at", "updated_at"])
    return True


def _record_action(post, platform_post, user, action, comment=""):
    """Create an ApprovalAction row for either a bundled or per-PP action."""
    return ApprovalAction.objects.create(
        post=post,
        platform_post=platform_post,
        user=user,
        action=action,
        comment=comment,
    )


def _notify_reviewers(workspace, actor, *, post, event_type, title, body):
    """Notify every workspace member with ``approve_posts`` (except the actor)."""
    reviewers = WorkspaceMembership.objects.filter(workspace=workspace).select_related("user", "custom_role")
    for membership in reviewers:
        perms = membership.effective_permissions
        if perms.get("approve_posts", False) and membership.user != actor:
            notify(
                user=membership.user,
                event_type=event_type,
                title=title,
                body=body,
                data={"post_id": str(post.id), "workspace_id": str(workspace.id)},
            )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


def submit_for_review(target, user, workspace):
    """Submit a post (or single platform post) for internal review."""
    post, targets, is_bundled = _resolve_targets(
        target, eligible_from_states={"draft", "changes_requested", "rejected"}
    )

    moved = []
    with transaction.atomic():
        for pp in targets:
            if _transition_or_skip(pp, "pending_review"):
                moved.append(pp)
        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.SUBMITTED)
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.SUBMITTED)

        ApprovalReminder.objects.update_or_create(
            post=post,
            stage="pending_review",
            defaults={"reminder_count": 0, "last_reminder_at": None, "escalated": False},
        )

    # Notify all reviewers (members with approve_posts permission)
    _notify_reviewers(
        workspace,
        user,
        post=post,
        event_type=EventType.POST_SUBMITTED,
        title="Post submitted for review",
        body=f'{user.display_name} submitted a post for your review: "{post.caption_snippet}"',
    )

    return post


def approve_post(target, user, workspace, comment=""):
    """Approve a post or single platform post.

    If the workspace runs the two-stage internal+client flow and we're moving
    out of ``pending_review``, the target hops to ``approved`` and then to
    ``pending_client`` (the same behaviour as before, just per-target).
    """
    post, targets, is_bundled = _resolve_targets(
        target, eligible_from_states={"pending_review", "pending_client", "draft", "rejected", "changes_requested"}
    )

    two_stage = workspace.approval_workflow_mode == "required_internal_and_client"
    moved = []
    advanced_to_client = False
    with transaction.atomic():
        for pp in targets:
            from_pending_review = pp.status == "pending_review"
            if not _transition_or_skip(pp, "approved"):
                continue
            moved.append(pp)
            if two_stage and from_pending_review and _transition_or_skip(pp, "pending_client"):
                advanced_to_client = True

        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.APPROVED, comment)
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.APPROVED, comment)

        if advanced_to_client:
            ApprovalReminder.objects.update_or_create(
                post=post,
                stage="pending_client",
                defaults={"reminder_count": 0, "last_reminder_at": None, "escalated": False},
            )
            _notify_clients(post, workspace)

    # Only tell the author "approved" when the post actually reached approved —
    # in two-stage mode an internal approval that advances to pending_client is
    # not done yet (the client still has to sign off, which re-enters this fn).
    if post.author and post.author != user and not advanced_to_client:
        notify(
            user=post.author,
            event_type=EventType.POST_APPROVED,
            title="Post approved",
            body=f'Your post "{post.caption_snippet}" was approved by {user.display_name}.',
            data={
                "post_id": str(post.id),
                "workspace_id": str(workspace.id),
            },
        )

    return post


def request_changes(target, user, workspace, comment):
    """Request changes on a post or single platform post. Comment is required."""
    if not comment.strip():
        raise ValueError("A comment is required when requesting changes.")

    post, targets, is_bundled = _resolve_targets(target, eligible_from_states={"pending_review", "pending_client"})

    moved = []
    with transaction.atomic():
        for pp in targets:
            if _transition_or_skip(pp, "changes_requested"):
                moved.append(pp)
        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.CHANGES_REQUESTED, comment)
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.CHANGES_REQUESTED, comment)

    if post.author and post.author != user:
        notify(
            user=post.author,
            event_type=EventType.POST_CHANGES_REQUESTED,
            title="Changes requested on your post",
            body=f'{user.display_name} requested changes: "{comment[:100]}"',
            data={
                "post_id": str(post.id),
                "workspace_id": str(workspace.id),
            },
        )

    return post


def reject_post(target, user, workspace, comment):
    """Reject a post or single platform post. Comment is required."""
    if not comment.strip():
        raise ValueError("A comment is required when rejecting a post.")

    post, targets, is_bundled = _resolve_targets(target, eligible_from_states={"pending_review", "pending_client"})

    moved = []
    with transaction.atomic():
        for pp in targets:
            if _transition_or_skip(pp, "rejected"):
                moved.append(pp)
        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.REJECTED, comment)
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.REJECTED, comment)

    if post.author and post.author != user:
        notify(
            user=post.author,
            event_type=EventType.POST_REJECTED,
            title="Post rejected",
            body=f'{user.display_name} rejected your post: "{comment[:100]}"',
            data={
                "post_id": str(post.id),
                "workspace_id": str(workspace.id),
            },
        )

    return post


def request_hold(target, user, workspace, comment):
    """Client requests a hold on an already-approved post. Comment is required.

    Parks the post in ``on_hold`` — out of the publish path (the publisher only
    picks up ``scheduled`` rows, and there is no ``on_hold → scheduled`` edge) —
    and notifies the team so they can resume, rework, or drop it.
    """
    if not comment.strip():
        raise ValueError("A comment is required when requesting a hold.")

    post, targets, is_bundled = _resolve_targets(target, eligible_from_states={"approved"})

    moved = []
    with transaction.atomic():
        for pp in targets:
            if _transition_or_skip(pp, "on_hold"):
                moved.append(pp)
        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.HELD, comment)
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.HELD, comment)

    _notify_reviewers_of_hold(post, workspace, user, comment)
    return post


def resume_hold(target, user, workspace):
    """Lift a client-requested hold — move an ``on_hold`` post back to ``approved``.

    Reviewer-side counterpart to :func:`request_hold`, so a held post is never a
    dead end for the team.
    """
    post, targets, is_bundled = _resolve_targets(target, eligible_from_states={"on_hold"})

    moved = []
    with transaction.atomic():
        for pp in targets:
            if _transition_or_skip(pp, "approved"):
                moved.append(pp)
        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.APPROVED, "Hold lifted.")
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.APPROVED, "Hold lifted.")

    return moved


def resubmit_post(target, user, workspace):
    """Resubmit a post after changes/rejection — or re-review an edited approved post."""
    post, targets, is_bundled = _resolve_targets(
        target, eligible_from_states={"changes_requested", "rejected", "approved"}
    )

    moved = []
    with transaction.atomic():
        for pp in targets:
            if _transition_or_skip(pp, "pending_review"):
                moved.append(pp)
        if not moved:
            return moved

        if is_bundled:
            _record_action(post, None, user, ApprovalAction.ActionType.RESUBMITTED)
        else:
            for pp in moved:
                _record_action(post, pp, user, ApprovalAction.ActionType.RESUBMITTED)

        ApprovalReminder.objects.update_or_create(
            post=post,
            stage="pending_review",
            defaults={"reminder_count": 0, "last_reminder_at": None, "escalated": False},
        )

    _notify_reviewers(
        workspace,
        user,
        post=post,
        event_type=EventType.POST_SUBMITTED,
        title="Post resubmitted for review",
        body=f'{user.display_name} resubmitted a post: "{post.caption_snippet}"',
    )

    return post


def bulk_approve(post_ids, user, workspace):
    """Approve all eligible PlatformPosts under each post (bundled per post)."""
    results = []
    posts = Post.objects.filter(
        id__in=post_ids,
        workspace=workspace,
        platform_posts__status__in=["pending_review", "pending_client"],
    ).distinct()

    for post in posts:
        try:
            moved = approve_post(post, user, workspace)
            results.append((str(post.id), bool(moved), None))
        except ValueError as e:
            results.append((str(post.id), False, str(e)))

    return results


def bulk_reject(post_ids, user, workspace, comment):
    """Reject all eligible PlatformPosts under each post (bundled per post)."""
    if not comment.strip():
        raise ValueError("A comment is required for bulk rejection.")

    results = []
    posts = Post.objects.filter(
        id__in=post_ids,
        workspace=workspace,
        platform_posts__status__in=["pending_review", "pending_client"],
    ).distinct()

    for post in posts:
        try:
            moved = reject_post(post, user, workspace, comment)
            results.append((str(post.id), bool(moved), None))
        except ValueError as e:
            results.append((str(post.id), False, str(e)))

    return results


def _notify_reviewers_of_hold(post, workspace, user, comment):
    """Notify reviewers (approve_posts holders) that a client put a post on hold."""
    _notify_reviewers(
        workspace,
        user,
        post=post,
        event_type=EventType.APPROVAL_HOLD_REQUESTED,
        title="Client requested a hold",
        body=f'{user.display_name} put a post on hold: "{comment[:100]}"',
    )


def _notify_clients(post, workspace):
    """Send CLIENT_APPROVAL_REQUESTED notification to all client members."""
    client_memberships = WorkspaceMembership.objects.filter(
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
    ).select_related("user")

    for membership in client_memberships:
        notify(
            user=membership.user,
            event_type=EventType.CLIENT_APPROVAL_REQUESTED,
            title="Posts ready for your review",
            body=f"A post in {workspace.name} is waiting for your approval.",
            data={
                "post_id": str(post.id),
                "workspace_id": str(workspace.id),
            },
        )
