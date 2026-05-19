"""get_publish_status, publish_now, retry_failed."""

from __future__ import annotations

from typing import Any

from apps.composer.models import PlatformPost, Post
from apps.publisher import services as publisher_services


def _pp_status(pp: PlatformPost) -> dict[str, Any]:
    return {
        "id": str(pp.id),
        "post_id": str(pp.post_id),
        "social_account_id": str(pp.social_account_id),
        "status": pp.status,
        "scheduled_at": pp.scheduled_at.isoformat() if pp.scheduled_at else None,
        "published_at": pp.published_at.isoformat() if pp.published_at else None,
        "platform_post_id": pp.platform_post_id,
        "publish_error": pp.publish_error,
        "retry_count": pp.retry_count,
        "next_retry_at": pp.next_retry_at.isoformat() if pp.next_retry_at else None,
    }


def _find_platform_post(ctx, platform_post_id: str) -> PlatformPost:
    ws = ctx.require_workspace()
    pp = (
        PlatformPost.objects.select_related("social_account", "post")
        .filter(pk=platform_post_id, post__workspace_id=ws.id)
        .first()
    )
    if pp is None:
        raise ValueError(f"PlatformPost {platform_post_id} not found in current workspace.")
    return pp


def register(mcp, ctx):
    @mcp.tool()
    def get_publish_status(post_id: str) -> dict[str, Any]:
        """Return per-platform publish status for a post."""
        ws = ctx.require_workspace()
        post = Post.objects.for_workspace(ws.id).filter(pk=post_id).first()
        if post is None:
            raise ValueError(f"Post {post_id} not found in current workspace.")
        return {
            "post_id": str(post.id),
            "post_status": post.status,
            "platform_posts": [
                _pp_status(pp)
                for pp in post.platform_posts.select_related("social_account").order_by("social_account__platform")
            ],
        }

    @mcp.tool()
    def publish_now(platform_post_id: str) -> dict[str, Any]:
        """Trigger immediate publishing of a single platform variant.

        The PlatformPost is moved to SCHEDULED with scheduled_at=now; the
        publish worker picks it up on its next tick (~15s).
        """
        ctx.require_permission("publish_directly")
        pp = _find_platform_post(ctx, platform_post_id)
        publisher_services.publish_now(pp)
        pp.refresh_from_db()
        return _pp_status(pp)

    @mcp.tool()
    def retry_failed(platform_post_id: str) -> dict[str, Any]:
        """Re-queue a FAILED platform post for another publish attempt."""
        ctx.require_permission("publish_directly")
        pp = _find_platform_post(ctx, platform_post_id)
        publisher_services.retry_failed(pp)
        pp.refresh_from_db()
        return _pp_status(pp)
