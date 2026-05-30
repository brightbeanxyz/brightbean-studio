"""Concrete MCP tool implementations.

Every tool delegates to the same service-layer functions the REST API
uses — ``apps.composer.services.create_post`` for writes, the same
allowlist + permission checks, the same platform quota — so there's no
MCP-only code path that can drift from REST validation.

Tool result envelope mirrors the spec: a list of ``content`` blocks
plus an ``isError`` flag. We serialize structured results as
``{type: "text", text: "<json>"}`` because Claude clients render JSON
in text blocks more reliably than the experimental ``json`` content
type, and agents can always ``JSON.parse`` it.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from ninja.errors import HttpError

from apps.api.limits import check_platform_quota
from apps.composer.models import PlatformPost, Post
from apps.composer.services import create_post, transition_platform_post
from apps.mcp.protocol import INVALID_PARAMS, JsonRpcError
from apps.mcp.tools import Tool, register_tool
from apps.social_accounts.models import SocialAccount


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap_text(payload: Any) -> dict:
    """Return MCP's text-content envelope around a JSON-serializable value.

    Most Claude clients render text blocks reliably; the experimental
    ``json`` content type isn't universally supported yet. Agents can
    always ``JSON.parse`` the returned text.
    """
    return {
        "content": [{"type": "text", "text": json.dumps(payload, default=str)}],
        "isError": False,
    }


def _require_perm(context: dict[str, Any], permission_key: str) -> None:
    """Re-check a workspace permission inside a tool handler.

    Mirrors REST's ``_require_perm`` so MCP can't be used to bypass
    permissions that the REST surface enforces.
    """
    membership = context["membership"]
    if not membership.effective_permissions.get(permission_key, False):
        raise JsonRpcError(INVALID_PARAMS, f"Permission denied: {permission_key}")


def _parse_uuid(value: Any, field_name: str) -> UUID:
    if not isinstance(value, str):
        raise JsonRpcError(INVALID_PARAMS, f"{field_name} must be a string UUID")
    try:
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise JsonRpcError(INVALID_PARAMS, f"{field_name} is not a valid UUID") from exc


def _resolve_allowed_account(api_key, social_account_id_str: str) -> SocialAccount:
    sa_id = _parse_uuid(social_account_id_str, "social_account_id")
    allowed = {sa.id for sa in api_key.social_accounts.all()}
    if sa_id not in allowed:
        raise JsonRpcError(
            INVALID_PARAMS, "social_account_id is not in this API key's allowlist"
        )
    return SocialAccount.objects.get(id=sa_id)


def _serialize_post(post: Post) -> dict:
    return {
        "id": str(post.id),
        "workspace_id": str(post.workspace_id),
        "title": post.title,
        "caption": post.caption,
        "first_comment": post.first_comment,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "status": post.status,
        "platform_posts": [
            {
                "id": str(pp.id),
                "social_account_id": str(pp.social_account_id),
                "platform": pp.social_account.platform,
                "status": pp.status,
                "scheduled_at": pp.scheduled_at.isoformat() if pp.scheduled_at else None,
                "published_at": pp.published_at.isoformat() if pp.published_at else None,
            }
            for pp in post.platform_posts.select_related("social_account")
        ],
    }


def _get_post_for_key(api_key, post_id_str: str) -> Post:
    """Allowlist-respecting Post fetch shared by ``get_post`` / ``cancel_post``.

    Same rule as REST's ``_get_workspace_post``: must be in the key's
    workspace AND every PlatformPost child must target an allowlisted
    account. Anything else looks like "not found" to the client, so a
    partial-scope key learns nothing about siblings.
    """
    post_id = _parse_uuid(post_id_str, "post_id")
    try:
        post = (
            Post.objects.prefetch_related("platform_posts__social_account")
            .get(id=post_id, workspace_id=api_key.workspace_id)
        )
    except Post.DoesNotExist as exc:
        raise JsonRpcError(INVALID_PARAMS, "Post not found") from exc
    allowed = {sa.id for sa in api_key.social_accounts.all()}
    pp_account_ids = {pp.social_account_id for pp in post.platform_posts.all()}
    if not pp_account_ids or not pp_account_ids.issubset(allowed):
        raise JsonRpcError(INVALID_PARAMS, "Post not found")
    return post


def _parse_iso_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise JsonRpcError(INVALID_PARAMS, f"{field_name} must be a string")
    try:
        # ``fromisoformat`` accepts trailing 'Z' starting in Python 3.11.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise JsonRpcError(INVALID_PARAMS, f"{field_name} must be ISO 8601") from exc


# ---------------------------------------------------------------------------
# Tool: list_accounts
# ---------------------------------------------------------------------------


def _list_accounts(args: dict, context: dict[str, Any]) -> dict:
    api_key = context["api_key"]
    accounts = [
        {
            "id": str(sa.id),
            "platform": sa.platform,
            "account_name": sa.account_name,
            "account_handle": getattr(sa, "account_handle", "") or "",
            "connection_status": sa.connection_status,
        }
        for sa in api_key.social_accounts.all()
    ]
    return _wrap_text({"accounts": accounts})


register_tool(
    Tool(
        name="list_accounts",
        description=(
            "List the social media accounts this API key is allowed to act on. "
            "Returns id, platform, account_name, account_handle, and connection_status. "
            "Call this first to discover which social_account_id values are valid for other tools."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        handler=_list_accounts,
    )
)


# ---------------------------------------------------------------------------
# Tool: create_draft
# ---------------------------------------------------------------------------


def _create_draft(args: dict, context: dict[str, Any]) -> dict:
    _require_perm(context, "create_posts")
    api_key = context["api_key"]
    if "social_account_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "social_account_id is required")
    if "caption" not in args:
        raise JsonRpcError(INVALID_PARAMS, "caption is required")
    sa = _resolve_allowed_account(api_key, args["social_account_id"])
    try:
        post = create_post(
            workspace=api_key.workspace,
            social_account=sa,
            caption=args["caption"],
            title=args.get("title", ""),
            first_comment=args.get("first_comment", ""),
            media_asset_ids=args.get("media_asset_ids") or [],
            author=api_key.issued_by if api_key.issued_by_id else None,
            status="draft",
        )
    except ValueError as exc:
        raise JsonRpcError(INVALID_PARAMS, str(exc)) from exc
    return _wrap_text(_serialize_post(post))


register_tool(
    Tool(
        name="create_draft",
        description=(
            "Create a draft post against a connected account. The draft is saved but not "
            "queued for publishing; call schedule_post or the schedule tool later to publish."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "social_account_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "ID of a SocialAccount in this key's allowlist (see list_accounts).",
                },
                "caption": {"type": "string", "maxLength": 10000},
                "title": {"type": "string", "default": "", "maxLength": 255},
                "first_comment": {
                    "type": "string",
                    "default": "",
                    "description": "Optional comment auto-posted after the main post.",
                },
                "media_asset_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                    "default": [],
                    "description": "MediaAsset UUIDs already uploaded to the workspace's media library.",
                },
            },
            "required": ["social_account_id", "caption"],
            "additionalProperties": False,
        },
        handler=_create_draft,
    )
)


# ---------------------------------------------------------------------------
# Tool: schedule_post — create + queue for publishing in one step
# ---------------------------------------------------------------------------


def _schedule_post(args: dict, context: dict[str, Any]) -> dict:
    # Mirrors the REST contract: scheduling sends the post into the
    # publisher's poll loop, which the composer permission model gates
    # on ``publish_directly`` (see apps/composer/views.py:797). Tools/
    # call to ``schedule_post`` requires the same.
    _require_perm(context, "create_posts")
    _require_perm(context, "publish_directly")
    api_key = context["api_key"]
    if "social_account_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "social_account_id is required")
    if "caption" not in args:
        raise JsonRpcError(INVALID_PARAMS, "caption is required")
    if "scheduled_at" not in args:
        raise JsonRpcError(INVALID_PARAMS, "scheduled_at is required (ISO 8601)")
    scheduled_at = _parse_iso_datetime(args["scheduled_at"], "scheduled_at")
    sa = _resolve_allowed_account(api_key, args["social_account_id"])
    # Platform quota is shared with REST; ``check_platform_quota``
    # raises ``HttpError(429,...)`` which we re-shape into a JSON-RPC
    # error so MCP clients see structured feedback rather than HTTP.
    try:
        check_platform_quota(sa)
    except HttpError as exc:
        raise JsonRpcError(
            INVALID_PARAMS,
            f"Per-platform daily quota reached for {sa.platform}: {exc.message}",
        ) from exc
    try:
        post = create_post(
            workspace=api_key.workspace,
            social_account=sa,
            caption=args["caption"],
            title=args.get("title", ""),
            first_comment=args.get("first_comment", ""),
            media_asset_ids=args.get("media_asset_ids") or [],
            scheduled_at=scheduled_at,
            author=api_key.issued_by if api_key.issued_by_id else None,
            status="scheduled",
        )
    except ValueError as exc:
        raise JsonRpcError(INVALID_PARAMS, str(exc)) from exc
    return _wrap_text(_serialize_post(post))


register_tool(
    Tool(
        name="schedule_post",
        description=(
            "Create a post and schedule it to publish at a specific UTC timestamp. "
            "The publisher polls every ~15s and will fire the post once the time elapses."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "social_account_id": {"type": "string", "format": "uuid"},
                "caption": {"type": "string", "maxLength": 10000},
                "scheduled_at": {
                    "type": "string",
                    "description": "ISO 8601 UTC timestamp (e.g. 2026-06-01T14:00:00Z)",
                },
                "title": {"type": "string", "default": "", "maxLength": 255},
                "first_comment": {"type": "string", "default": ""},
                "media_asset_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                    "default": [],
                },
            },
            "required": ["social_account_id", "caption", "scheduled_at"],
            "additionalProperties": False,
        },
        handler=_schedule_post,
    )
)


# ---------------------------------------------------------------------------
# Tool: get_post
# ---------------------------------------------------------------------------


def _get_post(args: dict, context: dict[str, Any]) -> dict:
    if "post_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "post_id is required")
    api_key = context["api_key"]
    post = _get_post_for_key(api_key, args["post_id"])
    return _wrap_text(_serialize_post(post))


register_tool(
    Tool(
        name="get_post",
        description=(
            "Retrieve a post by ID, including aggregate status and per-platform child state. "
            "Returns 'Post not found' for posts outside the API key's allowlist (same as for "
            "truly nonexistent IDs — the API never reveals which is which)."
        ),
        input_schema={
            "type": "object",
            "properties": {"post_id": {"type": "string", "format": "uuid"}},
            "required": ["post_id"],
            "additionalProperties": False,
        },
        handler=_get_post,
    )
)


# ---------------------------------------------------------------------------
# Tool: cancel_post
# ---------------------------------------------------------------------------


def _cancel_post(args: dict, context: dict[str, Any]) -> dict:
    _require_perm(context, "create_posts")
    if "post_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "post_id is required")
    api_key = context["api_key"]
    post = _get_post_for_key(api_key, args["post_id"])
    scheduled = [pp for pp in post.platform_posts.all() if pp.status == "scheduled"]
    if not scheduled:
        raise JsonRpcError(INVALID_PARAMS, "No scheduled platform posts to cancel")
    for pp in scheduled:
        try:
            transition_platform_post(pp, "draft")
        except ValueError as exc:
            raise JsonRpcError(INVALID_PARAMS, str(exc)) from exc
    post.refresh_from_db()
    return _wrap_text(_serialize_post(post))


register_tool(
    Tool(
        name="cancel_post",
        description=(
            "Cancel a scheduled post, transitioning it back to draft. "
            "No-op error if there are no scheduled children to cancel."
        ),
        input_schema={
            "type": "object",
            "properties": {"post_id": {"type": "string", "format": "uuid"}},
            "required": ["post_id"],
            "additionalProperties": False,
        },
        handler=_cancel_post,
    )
)
