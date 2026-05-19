"""list_posts, get_post, create_post, update_post, schedule_post, delete_post."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.db.models import Q

from apps.composer import services as composer_services
from apps.composer.models import PlatformPost, Post


def _parse_dt(value: str | None):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _platform_post_summary(pp: PlatformPost) -> dict[str, Any]:
    return {
        "id": str(pp.id),
        "social_account_id": str(pp.social_account_id),
        "platform": pp.social_account.platform if pp.social_account_id else None,
        "status": pp.status,
        "scheduled_at": pp.scheduled_at.isoformat() if pp.scheduled_at else None,
        "published_at": pp.published_at.isoformat() if pp.published_at else None,
        "platform_post_id": pp.platform_post_id,
        "publish_error": pp.publish_error,
        "retry_count": pp.retry_count,
    }


def _post_summary(post: Post) -> dict[str, Any]:
    return {
        "id": str(post.id),
        "workspace_id": str(post.workspace_id),
        "title": post.title,
        "caption": post.caption,
        "first_comment": post.first_comment,
        "category_id": str(post.category_id) if post.category_id else None,
        "tags": post.tags or [],
        "author_id": str(post.author_id) if post.author_id else None,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "status": post.status,
        "is_editable": post.is_editable,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
    }


def _post_full(post: Post) -> dict[str, Any]:
    data = _post_summary(post)
    data["platform_posts"] = [
        _platform_post_summary(pp)
        for pp in post.platform_posts.select_related("social_account").order_by("social_account__platform")
    ]
    data["media"] = [
        {
            "id": str(pm.media_asset_id),
            "filename": pm.media_asset.filename,
            "position": pm.position,
            "alt_text": pm.alt_text,
        }
        for pm in post.media_attachments.select_related("media_asset").order_by("position")
    ]
    return data


def register(mcp, ctx):
    @mcp.tool()
    def list_posts(
        status: str | None = None,
        social_account_id: str | None = None,
        category_id: str | None = None,
        scheduled_from: str | None = None,
        scheduled_to: str | None = None,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List posts in the current workspace, filtered by status / account / category / date / text search.

        status values match PlatformPost.Status (draft, pending_review, approved,
        scheduled, publishing, published, failed, ...).
        """
        ws = ctx.require_workspace()
        qs = (
            Post.objects.for_workspace(ws.id)
            .select_related("author", "category")
            .prefetch_related("platform_posts__social_account")
        )
        if status:
            qs = qs.filter(platform_posts__status=status).distinct()
        if social_account_id:
            qs = qs.filter(platform_posts__social_account_id=social_account_id).distinct()
        if category_id:
            qs = qs.filter(category_id=category_id)
        if scheduled_from:
            qs = qs.filter(scheduled_at__gte=_parse_dt(scheduled_from))
        if scheduled_to:
            qs = qs.filter(scheduled_at__lte=_parse_dt(scheduled_to))
        if search:
            qs = qs.filter(Q(caption__icontains=search) | Q(title__icontains=search))
        qs = qs.order_by("-created_at")
        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
        total = qs.count()
        items = [_post_summary(p) for p in qs[offset : offset + limit]]
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    @mcp.tool()
    def get_post(post_id: str) -> dict[str, Any]:
        """Return full details of a post including per-platform variants and media."""
        ws = ctx.require_workspace()
        post = Post.objects.for_workspace(ws.id).filter(pk=post_id).first()
        if post is None:
            raise ValueError(f"Post {post_id} not found in current workspace.")
        return _post_full(post)

    @mcp.tool()
    def create_post(
        caption: str,
        social_account_ids: list[str],
        scheduled_at: str | None = None,
        title: str = "",
        first_comment: str = "",
        category_id: str | None = None,
        tags: list[str] | None = None,
        media_asset_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a draft Post with one PlatformPost per social_account_id.

        If scheduled_at is provided, every child is also marked SCHEDULED.
        """
        ctx.require_permission("create_posts")
        ws = ctx.require_workspace()

        from apps.composer.models import ContentCategory

        category = None
        if category_id:
            category = ContentCategory.objects.filter(id=category_id, workspace=ws).first()

        sched = _parse_dt(scheduled_at)
        initial_status = PlatformPost.Status.SCHEDULED if sched else PlatformPost.Status.DRAFT

        post = composer_services.create_post(
            workspace=ws,
            author=ctx.user,
            caption=caption,
            social_account_ids=social_account_ids,
            scheduled_at=sched,
            title=title,
            first_comment=first_comment,
            category=category,
            tags=tags,
            media_asset_ids=media_asset_ids,
            initial_status=initial_status,
        )
        return _post_full(post)

    @mcp.tool()
    def update_post(
        post_id: str,
        caption: str | None = None,
        title: str | None = None,
        first_comment: str | None = None,
        category_id: str | None = None,
        tags: list[str] | None = None,
        scheduled_at: str | None = None,
    ) -> dict[str, Any]:
        """Edit a Post's caption/title/etc. while it is still editable."""
        ws = ctx.require_workspace()

        post = Post.objects.for_workspace(ws.id).filter(pk=post_id).first()
        if post is None:
            raise ValueError(f"Post {post_id} not found in current workspace.")

        # Authors editing their own post need edit_own_posts; otherwise edit_others_posts.
        if post.author_id == ctx.user.id:
            ctx.require_permission("edit_own_posts")
        else:
            ctx.require_permission("edit_others_posts")

        from apps.composer.models import ContentCategory

        category = None
        if category_id:
            category = ContentCategory.objects.filter(id=category_id, workspace=ws).first()

        post = composer_services.update_post(
            post,
            caption=caption,
            title=title,
            first_comment=first_comment,
            category=category,
            tags=tags,
            scheduled_at=_parse_dt(scheduled_at),
        )
        return _post_full(post)

    @mcp.tool()
    def schedule_post(post_id: str, scheduled_at: str) -> dict[str, Any]:
        """Schedule every platform variant of a post for ``scheduled_at`` (ISO 8601)."""
        ctx.require_permission("create_posts")
        ws = ctx.require_workspace()
        post = Post.objects.for_workspace(ws.id).filter(pk=post_id).first()
        if post is None:
            raise ValueError(f"Post {post_id} not found in current workspace.")
        composer_services.schedule_post(post, _parse_dt(scheduled_at))
        post.refresh_from_db()
        return _post_full(post)

    @mcp.tool()
    def delete_post(post_id: str) -> dict[str, Any]:
        """Delete a post (cascades to all platform variants and media attachments)."""
        ws = ctx.require_workspace()
        post = Post.objects.for_workspace(ws.id).filter(pk=post_id).first()
        if post is None:
            raise ValueError(f"Post {post_id} not found in current workspace.")
        if post.author_id != ctx.user.id:
            ctx.require_permission("edit_others_posts")
        else:
            ctx.require_permission("edit_own_posts")
        composer_services.delete_post(post)
        return {"deleted": True, "id": post_id}
