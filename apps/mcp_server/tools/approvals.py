"""list_approval_queue, approve, request_changes."""

from __future__ import annotations

from typing import Any

from apps.approvals import services as approvals_services
from apps.composer.models import PlatformPost, Post


def _post_brief(post: Post) -> dict[str, Any]:
    return {
        "id": str(post.id),
        "title": post.title,
        "caption": post.caption[:280],
        "author_id": str(post.author_id) if post.author_id else None,
        "status": post.status,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "platform_posts": [
            {
                "id": str(pp.id),
                "platform": pp.social_account.platform,
                "social_account_id": str(pp.social_account_id),
                "status": pp.status,
            }
            for pp in post.platform_posts.select_related("social_account").all()
        ],
    }


def _resolve_target(ctx, target_id: str):
    """target_id may be a Post id or a PlatformPost id."""
    ws = ctx.require_workspace()
    post = Post.objects.for_workspace(ws.id).filter(pk=target_id).first()
    if post is not None:
        return post
    pp = (
        PlatformPost.objects.filter(pk=target_id, post__workspace_id=ws.id)
        .select_related("post", "social_account")
        .first()
    )
    if pp is not None:
        return pp
    raise ValueError(f"Post or PlatformPost {target_id} not found in current workspace.")


def register(mcp, ctx):
    @mcp.tool()
    def list_approval_queue(role: str = "internal") -> list[dict[str, Any]]:
        """List posts pending approval.

        role: 'internal' (pending_review) or 'client' (pending_client).
        """
        ctx.require_permission("approve_posts")
        ws = ctx.require_workspace()
        target_status = PlatformPost.Status.PENDING_CLIENT if role == "client" else PlatformPost.Status.PENDING_REVIEW
        qs = (
            Post.objects.for_workspace(ws.id)
            .filter(platform_posts__status=target_status)
            .distinct()
            .select_related("author")
            .prefetch_related("platform_posts__social_account")
            .order_by("scheduled_at", "-created_at")
        )
        return [_post_brief(p) for p in qs]

    @mcp.tool()
    def approve(target_id: str, comment: str = "") -> dict[str, Any]:
        """Approve a post or one platform variant. Accepts a post_id or platform_post_id."""
        ctx.require_permission("approve_posts")
        target = _resolve_target(ctx, target_id)
        post = approvals_services.approve_post(target, ctx.user, ctx.require_workspace(), comment=comment)
        return _post_brief(post)

    @mcp.tool()
    def request_changes(target_id: str, comment: str) -> dict[str, Any]:
        """Send a post (or one platform variant) back to the author with a comment."""
        ctx.require_permission("approve_posts")
        if not comment.strip():
            raise ValueError("A comment is required when requesting changes.")
        target = _resolve_target(ctx, target_id)
        post = approvals_services.request_changes(target, ctx.user, ctx.require_workspace(), comment)
        return _post_brief(post)
