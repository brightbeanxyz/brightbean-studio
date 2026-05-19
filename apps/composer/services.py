"""Composer service helpers."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.social_accounts.models import SocialAccount

from .models import PlatformPost, Post, PostMedia


class ComposerError(Exception):
    """Raised on invalid composer inputs (unknown accounts, non-editable post, etc.)."""


def sync_post_scheduled_at(post):
    """Set ``post.scheduled_at`` to ``min(children scheduled_at)``.

    Keeps the legacy ``Post.scheduled_at`` column in sync with the earliest
    per-platform scheduled time so listings, grouping and Coalesce fallbacks
    remain consistent. No-op when no PlatformPost has a scheduled_at set.
    """
    times = list(post.platform_posts.exclude(scheduled_at__isnull=True).values_list("scheduled_at", flat=True))
    if not times:
        return
    earliest = min(times)
    if post.scheduled_at != earliest:
        post.scheduled_at = earliest
        post.save(update_fields=["scheduled_at", "updated_at"])


def create_post(
    *,
    workspace,
    author,
    caption: str = "",
    social_account_ids: list,
    scheduled_at=None,
    title: str = "",
    first_comment: str = "",
    category=None,
    tags: list | None = None,
    media_asset_ids: list | None = None,
    initial_status: str = PlatformPost.Status.DRAFT,
) -> Post:
    """Create a Post + one PlatformPost per social account, plus optional media attachments."""
    accounts = list(SocialAccount.objects.for_workspace(workspace.id).filter(id__in=social_account_ids))
    if len(accounts) != len(set(social_account_ids)):
        raise ComposerError("One or more social_account_ids are not valid for this workspace.")
    if not accounts:
        raise ComposerError("At least one social_account_id is required.")

    with transaction.atomic():
        post = Post.objects.create(
            workspace=workspace,
            author=author,
            title=title,
            caption=caption,
            first_comment=first_comment,
            category=category,
            tags=list(tags or []),
            scheduled_at=scheduled_at,
        )
        PlatformPost.objects.bulk_create(
            [
                PlatformPost(
                    post=post,
                    social_account=account,
                    status=initial_status,
                    scheduled_at=scheduled_at,
                )
                for account in accounts
            ]
        )
        if media_asset_ids:
            PostMedia.objects.bulk_create(
                [PostMedia(post=post, media_asset_id=mid, position=idx) for idx, mid in enumerate(media_asset_ids)]
            )
    return post


def update_post(
    post: Post,
    *,
    caption=None,
    title=None,
    first_comment=None,
    category=None,
    tags=None,
    scheduled_at=None,
) -> Post:
    """Update editable fields on a Post. Leaves PlatformPosts untouched."""
    if not post.is_editable:
        raise ComposerError(f"Post is not editable in status '{post.status}'.")

    fields = []
    if caption is not None:
        post.caption = caption
        fields.append("caption")
    if title is not None:
        post.title = title
        fields.append("title")
    if first_comment is not None:
        post.first_comment = first_comment
        fields.append("first_comment")
    if category is not None:
        post.category = category
        fields.append("category")
    if tags is not None:
        post.tags = list(tags)
        fields.append("tags")
    if scheduled_at is not None:
        post.scheduled_at = scheduled_at
        fields.append("scheduled_at")

    if fields:
        fields.append("updated_at")
        post.save(update_fields=fields)
    return post


_RESCHEDULABLE_STATES = {
    PlatformPost.Status.DRAFT,
    PlatformPost.Status.APPROVED,
    PlatformPost.Status.CHANGES_REQUESTED,
    PlatformPost.Status.REJECTED,
    PlatformPost.Status.FAILED,
    PlatformPost.Status.SCHEDULED,
}


def schedule_post(post: Post, scheduled_at) -> Post:
    """Schedule (or reschedule) every eligible child PlatformPost at ``scheduled_at``.

    Children already in SCHEDULED keep that status; their scheduled_at is updated.
    Children in DRAFT/APPROVED/etc. transition to SCHEDULED.
    """
    if scheduled_at <= timezone.now():
        raise ComposerError("scheduled_at must be in the future.")

    with transaction.atomic():
        children = list(post.platform_posts.select_for_update())
        if not children:
            raise ComposerError("Post has no platform_posts to schedule.")
        for child in children:
            if child.status not in _RESCHEDULABLE_STATES:
                raise ComposerError(f"Child {child.id} in status '{child.status}' cannot be scheduled.")
            child.scheduled_at = scheduled_at
            if child.status != PlatformPost.Status.SCHEDULED:
                child.transition_to(PlatformPost.Status.SCHEDULED)
            child.save(update_fields=["scheduled_at", "status", "updated_at"])
        post.scheduled_at = scheduled_at
        post.save(update_fields=["scheduled_at", "updated_at"])
    return post


def delete_post(post: Post) -> None:
    """Delete a Post; cascades to PlatformPosts, PostMedia, PostVersion."""
    post.delete()
