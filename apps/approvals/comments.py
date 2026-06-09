"""Post comment business logic.

Handles creation, updating, deletion, and @mention parsing for post comments.
"""

import re

from django.db.models import Prefetch
from django.utils import timezone

from apps.members.models import WorkspaceMembership
from apps.notifications.engine import notify
from apps.notifications.models import EventType

from .models import PostComment

# Match @mentions but not email addresses (require whitespace or start-of-string before @)
MENTION_REGEX = re.compile(r"(?:^|(?<=\s))@(\w[\w.]*)")
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5MB


def create_comment(post, author, body, visibility, parent_id=None, attachment=None):
    """Create a comment on a post and notify @mentioned users.

    Args:
        post: The Post instance.
        author: The User who wrote the comment.
        body: Comment text.
        visibility: "internal" or "external".
        parent_id: UUID of parent comment for threading (optional).
        attachment: UploadedFile for image attachment (optional).

    Returns:
        The created PostComment.
    """
    if attachment and attachment.size > MAX_ATTACHMENT_SIZE:
        raise ValueError("Attachment exceeds 5MB limit.")

    parent_comment = None
    if parent_id:
        parent_comment = PostComment.objects.filter(
            id=parent_id,
            post=post,
            deleted_at__isnull=True,
        ).first()

    comment = PostComment.objects.create(
        post=post,
        author=author,
        parent_comment=parent_comment,
        body=body,
        visibility=visibility,
        attachment=attachment,
    )

    # Parse @mentions and notify
    workspace = post.workspace
    mentions = MENTION_REGEX.findall(body)
    if mentions:
        _notify_mentions(mentions, post, author, workspace, body)

    return comment


def update_comment(comment_id, user, body, *, workspace=None):
    """Update a comment's body. Only the author can edit.

    When `workspace` is provided, the comment's post is required to belong to
    that workspace — defends against cross-workspace IDOR via a forged
    post_id/comment_id pair.
    """
    qs = PostComment.objects.filter(
        id=comment_id,
        deleted_at__isnull=True,
    )
    if workspace is not None:
        qs = qs.filter(post__workspace=workspace)
    comment = qs.first()

    if not comment:
        raise ValueError("Comment not found.")
    if comment.author_id != user.id:
        raise PermissionError("Only the comment author can edit.")

    comment.body = body
    comment.save(update_fields=["body", "updated_at"])
    return comment


def delete_comment(comment_id, user, workspace):
    """Soft-delete a comment. Authors and managers can delete."""
    comment = PostComment.objects.filter(
        id=comment_id,
        deleted_at__isnull=True,
    ).first()

    if not comment:
        raise ValueError("Comment not found.")

    # Check permission: author or user with approve_posts (manager+)
    membership = (
        WorkspaceMembership.objects.filter(
            user=user,
            workspace=workspace,
        )
        .select_related("custom_role")
        .first()
    )

    is_author = comment.author_id == user.id
    can_moderate = membership and membership.effective_permissions.get("approve_posts", False)

    if not is_author and not can_moderate:
        raise PermissionError("You don't have permission to delete this comment.")

    comment.deleted_at = timezone.now()
    comment.save(update_fields=["deleted_at", "updated_at"])
    return comment


def get_comments_for_post(post, user):
    """Get comments for a post, filtered by user's visibility access.

    Clients only see external comments. Team members see all.
    """
    workspace = post.workspace
    membership = WorkspaceMembership.objects.filter(
        user=user,
        workspace=workspace,
    ).first()

    active_replies = PostComment.objects.filter(
        deleted_at__isnull=True,
    ).select_related("author")

    qs = (
        PostComment.objects.filter(
            post=post,
            deleted_at__isnull=True,
            parent_comment__isnull=True,  # Top-level only; replies are prefetched
        )
        .select_related("author")
        .prefetch_related(
            Prefetch("replies", queryset=active_replies),
        )
        .order_by("created_at")
    )

    # Clients only see external comments
    if membership and membership.workspace_role == WorkspaceMembership.WorkspaceRole.CLIENT:
        qs = qs.filter(visibility=PostComment.Visibility.EXTERNAL)

    return qs


def _notify_mentions(mentions, post, author, workspace, body):
    """Send notifications to @mentioned workspace members."""
    # Build lookup of display names / email prefixes → user
    memberships = WorkspaceMembership.objects.filter(
        workspace=workspace,
    ).select_related("user")

    name_to_user = {}
    for m in memberships:
        user = m.user
        # Match by display name (spaces replaced with dots/underscores)
        display = user.display_name.lower().replace(" ", "")
        name_to_user[display] = user
        # Also match by email prefix
        email_prefix = user.email.split("@")[0].lower()
        name_to_user[email_prefix] = user

    notified = set()
    for mention in mentions:
        mention_lower = mention.lower()
        target_user = name_to_user.get(mention_lower)
        if target_user and target_user.id != author.id and target_user.id not in notified:
            notify(
                user=target_user,
                event_type=EventType.COMMENT_MENTION,
                title=f"{author.display_name} mentioned you",
                body=f'In a comment on a post: "{body[:100]}"',
                data={
                    "post_id": str(post.id),
                    "workspace_id": str(workspace.id),
                },
            )
            notified.add(target_user.id)
