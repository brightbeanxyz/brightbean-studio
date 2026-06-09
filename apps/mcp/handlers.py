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

from apps.analytics.api_builders import build_account_analytics, build_post_analytics
from apps.api.limits import check_platform_quota
from apps.api.schemas import PostResponse
from apps.composer.models import Post
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
        raise JsonRpcError(INVALID_PARAMS, "social_account_id is not in this API key's allowlist")
    return SocialAccount.objects.get(id=sa_id)


def _serialize_post(post: Post) -> dict:
    """Serialize a Post for an MCP tool response.

    Delegates to the same Pydantic schema the REST router returns so
    the two surfaces cannot drift in either field set or wire format.
    """
    return PostResponse.from_post(post).model_dump(mode="json")


def _get_post_for_key(api_key, post_id_str: str) -> Post:
    """Allowlist-respecting Post fetch shared by ``get_post`` / ``cancel_post``.

    Same rule as REST's ``_get_workspace_post``: must be in the key's
    workspace AND every PlatformPost child must target an allowlisted
    account. Anything else looks like "not found" to the client, so a
    partial-scope key learns nothing about siblings.
    """
    post_id = _parse_uuid(post_id_str, "post_id")
    try:
        post = Post.objects.prefetch_related("platform_posts__social_account").get(
            id=post_id, workspace_id=api_key.workspace_id
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
    # Reuse the REST schema so MCP and REST stay byte-identical (Gap 4 + 5).
    from apps.api.schemas import AccountSummary

    accounts = [AccountSummary.from_social_account(sa).model_dump(mode="json") for sa in api_key.social_accounts.all()]
    return _wrap_text({"accounts": accounts})


register_tool(
    Tool(
        name="list_accounts",
        description=(
            "List the social media accounts this API key is allowed to act on. "
            "Returns id, platform, account_name, account_handle, connection_status, char_limit, "
            "needs_title, and supports_first_comment. Call this first to discover which "
            "social_account_id values are valid and what each platform requires."
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
    from django.db import transaction

    _require_perm(context, "create_posts")
    if "post_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "post_id is required")
    api_key = context["api_key"]
    post = _get_post_for_key(api_key, args["post_id"])
    scheduled = [pp for pp in post.platform_posts.all() if pp.status == "scheduled"]
    if not scheduled:
        raise JsonRpcError(INVALID_PARAMS, "No scheduled platform posts to cancel")
    # Wrap the per-child loop in a single outer atomic so a mid-loop
    # ValueError (concurrent admin transition, state-machine rejection
    # on a later child) rolls back any earlier ``draft`` commits.
    # Mirrors the REST ``/cancel`` route's atomic block — without this,
    # a multi-account post could end up in a mixed draft/scheduled state
    # that neither the publisher nor the agent expects. Codex PR #53
    # flagged this asymmetry between REST and MCP.
    with transaction.atomic():
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


# ---------------------------------------------------------------------------
# Tool: schedule_draft — REST-parity transition of an existing draft post
# ---------------------------------------------------------------------------


def _schedule_draft(args: dict, context: dict[str, Any]) -> dict:
    """Promote every draft child of an existing post to ``scheduled``.

    Mirrors the REST ``POST /api/v1/posts/{post_id}/schedule`` route.
    Closes the asymmetry where MCP previously had no way to transition
    an existing draft to scheduled — ``schedule_post`` always creates a
    NEW post in scheduled state. Without this tool, "draft now, schedule
    later" via pure MCP forced clients to recreate the post or fall back
    to REST for the one transition.
    """
    from django.db import transaction

    _require_perm(context, "create_posts")
    # Same permission contract as the REST route: pushing a post into
    # the publisher's poll loop requires ``publish_directly``.
    _require_perm(context, "publish_directly")
    if "post_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "post_id is required")
    if "scheduled_at" not in args:
        raise JsonRpcError(INVALID_PARAMS, "scheduled_at is required (ISO 8601)")
    scheduled_at = _parse_iso_datetime(args["scheduled_at"], "scheduled_at")

    api_key = context["api_key"]
    post = _get_post_for_key(api_key, args["post_id"])
    drafts = [pp for pp in post.platform_posts.all() if pp.status == "draft"]
    if not drafts:
        raise JsonRpcError(INVALID_PARAMS, "No draft platform posts to schedule")

    # Per-platform 24h quota check, one per child, BEFORE we mutate
    # anything — over-quota fails the whole call with no partial commit.
    for pp in drafts:
        try:
            check_platform_quota(pp.social_account)
        except HttpError as exc:
            raise JsonRpcError(
                INVALID_PARAMS,
                f"Per-platform daily quota reached for {pp.social_account.platform}: {exc.message}",
            ) from exc

    # Wrap the per-child loop in a single outer atomic — same reasoning
    # as ``cancel_post``: a mid-loop ValueError (concurrent admin
    # transition, state-machine rejection on a later child, workspace
    # approval-mode rejection from ``transition_platform_post``) rolls
    # back any earlier ``scheduled`` commits.
    with transaction.atomic():
        for pp in drafts:
            try:
                transition_platform_post(pp, "scheduled", scheduled_at=scheduled_at)
            except ValueError as exc:
                raise JsonRpcError(INVALID_PARAMS, str(exc)) from exc
    post.refresh_from_db()
    return _wrap_text(_serialize_post(post))


register_tool(
    Tool(
        name="schedule_draft",
        description=(
            "Schedule an EXISTING draft post — transitions every draft child to scheduled "
            "at the given UTC timestamp. Use this for the two-step flow "
            "'create_draft now, schedule_draft later'. For one-shot create-and-schedule, "
            "use schedule_post instead. Requires both create_posts and publish_directly."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "post_id": {"type": "string", "format": "uuid"},
                "scheduled_at": {
                    "type": "string",
                    "description": "ISO 8601 UTC timestamp (e.g. 2026-06-01T14:00:00Z)",
                },
            },
            "required": ["post_id", "scheduled_at"],
            "additionalProperties": False,
        },
        handler=_schedule_draft,
    )
)


# ---------------------------------------------------------------------------
# Media tools: search_media, get_media, upload_media (Gap 1 + 1b)
# ---------------------------------------------------------------------------


_MCP_MEDIA_LIMIT_DEFAULT = 20
_MCP_MEDIA_LIMIT_MAX = 100
# JSON-RPC payload sanity cap. Kept below Django's DATA_UPLOAD_MAX_MEMORY_SIZE
# default of 2.5 MB so this check fires with a structured JSON-RPC error
# before Django's RequestDataTooBig fires with an opaque HTML 500.
# For anything larger, agents must use POST /api/v1/media/ over REST.
_MCP_UPLOAD_MAX_BYTES = 1024 * 1024  # 1 MB raw


def _visible_media_qs(api_key):
    from apps.media_library.models import MediaAsset

    workspace = api_key.workspace
    return MediaAsset.objects.for_workspace_with_shared(
        workspace_id=workspace.id,
        organization_id=workspace.organization_id,
    )


def _serialize_media(asset) -> dict:
    """Return the same shape as ``GET /api/v1/media/{id}``."""
    from apps.api.schemas import MediaAssetResponse

    return MediaAssetResponse.from_asset(asset, last_used_at=getattr(asset, "last_used_at", None)).model_dump(
        mode="json"
    )


def _search_media(args: dict, context: dict[str, Any]) -> dict:
    from apps.media_library.models import MediaAsset

    api_key = context["api_key"]
    query = args.get("query") or None
    media_type = args.get("media_type") or None
    tags = args.get("tags") or []
    folder_id_raw = args.get("folder_id") or None
    is_starred = args.get("is_starred")
    limit = int(args.get("limit") or _MCP_MEDIA_LIMIT_DEFAULT)
    if limit < 1 or limit > _MCP_MEDIA_LIMIT_MAX:
        raise JsonRpcError(INVALID_PARAMS, f"limit must be between 1 and {_MCP_MEDIA_LIMIT_MAX}")

    qs = MediaAsset.objects.with_last_used_at(_visible_media_qs(api_key))
    # Default to ``completed`` so agents never reference half-processed
    # assets via MCP. Mirrors the REST default.
    qs = qs.filter(processing_status="completed")
    if media_type:
        qs = qs.filter(media_type=media_type)
    if folder_id_raw:
        qs = qs.filter(folder_id=_parse_uuid(folder_id_raw, "folder_id"))
    if is_starred is not None:
        qs = qs.filter(is_starred=bool(is_starred))
    if isinstance(tags, list):
        for tag in tags:
            if not isinstance(tag, str):
                raise JsonRpcError(INVALID_PARAMS, "tags must be a list of strings")
            qs = qs.filter(tags__contains=[tag])
    if query:
        qs = MediaAsset.objects.search(query, queryset=qs)

    qs = qs.order_by("-created_at", "id")[:limit]
    return _wrap_text({"items": [_serialize_media(a) for a in qs]})


register_tool(
    Tool(
        name="search_media",
        description=(
            "Find media assets already uploaded to this workspace. Defaults to the 20 most "
            "recent assets that are ready to reference. Use this before uploading to avoid "
            "duplicating evergreen content. Returns the same item shape as GET /api/v1/media/."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional substring match on filename and tags.",
                },
                "media_type": {
                    "type": "string",
                    "enum": ["image", "video", "gif", "document"],
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "All tags must match (AND semantics).",
                },
                "folder_id": {"type": "string", "format": "uuid"},
                "is_starred": {"type": "boolean"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": _MCP_MEDIA_LIMIT_MAX,
                    "default": _MCP_MEDIA_LIMIT_DEFAULT,
                },
            },
            "additionalProperties": False,
        },
        handler=_search_media,
    )
)


def _get_media(args: dict, context: dict[str, Any]) -> dict:
    from apps.media_library.models import MediaAsset

    if "media_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "media_id is required")
    media_id = _parse_uuid(args["media_id"], "media_id")
    api_key = context["api_key"]
    qs = MediaAsset.objects.with_last_used_at(_visible_media_qs(api_key))
    try:
        asset = qs.get(id=media_id)
    except MediaAsset.DoesNotExist as exc:
        raise JsonRpcError(INVALID_PARAMS, "Media asset not found") from exc
    return _wrap_text(_serialize_media(asset))


register_tool(
    Tool(
        name="get_media",
        description=(
            "Retrieve a single media asset by id. Same response shape as "
            "GET /api/v1/media/{id}. Use this to poll an upload's processing_status "
            "until it transitions from 'pending' to 'completed'."
        ),
        input_schema={
            "type": "object",
            "properties": {"media_id": {"type": "string", "format": "uuid"}},
            "required": ["media_id"],
            "additionalProperties": False,
        },
        handler=_get_media,
    )
)


def _upload_media(args: dict, context: dict[str, Any]) -> dict:
    """MCP-side upload accepts base64 content (≤5 MB).

    For larger files agents must use ``POST /api/v1/media/`` over REST —
    multipart can't ride a JSON-RPC envelope cleanly.
    """
    import base64
    import binascii

    from django.core.exceptions import ValidationError
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.media_library.quotas import StorageQuotaExceededError
    from apps.media_library.services import create_asset as media_create_asset

    _require_perm(context, "upload_media")
    if "filename" not in args:
        raise JsonRpcError(INVALID_PARAMS, "filename is required")
    if "content_base64" not in args:
        raise JsonRpcError(INVALID_PARAMS, "content_base64 is required")

    filename = args["filename"]
    if not isinstance(filename, str) or not filename.strip():
        raise JsonRpcError(INVALID_PARAMS, "filename must be a non-empty string")

    try:
        raw = base64.b64decode(args["content_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise JsonRpcError(INVALID_PARAMS, "content_base64 is not valid base64") from exc

    if len(raw) > _MCP_UPLOAD_MAX_BYTES:
        raise JsonRpcError(
            INVALID_PARAMS,
            (
                f"MCP upload limit is {_MCP_UPLOAD_MAX_BYTES // 1024 // 1024} MB. "
                "Use POST /api/v1/media/ (multipart) for larger files."
            ),
        )

    content_type = args.get("content_type") or "application/octet-stream"
    uploaded = SimpleUploadedFile(name=filename, content=raw, content_type=content_type)

    api_key = context["api_key"]
    workspace = api_key.workspace
    folder = None
    folder_id_raw = args.get("folder_id")
    if folder_id_raw:
        from apps.media_library.models import MediaFolder

        try:
            folder = MediaFolder.objects.get(
                id=_parse_uuid(folder_id_raw, "folder_id"),
                organization=workspace.organization,
            )
        except MediaFolder.DoesNotExist as exc:
            raise JsonRpcError(INVALID_PARAMS, "folder_id not found in this organization") from exc

    tags = args.get("tags") or []
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise JsonRpcError(INVALID_PARAMS, "tags must be a list of strings")

    try:
        asset = media_create_asset(
            organization=workspace.organization,
            workspace=workspace,
            uploaded_file=uploaded,
            uploaded_by=api_key.issued_by if api_key.issued_by_id else None,
            folder=folder,
            alt_text=args.get("alt_text", "") or "",
            title=args.get("title", "") or "",
            tags=tags,
        )
    except StorageQuotaExceededError as exc:
        raise JsonRpcError(
            INVALID_PARAMS,
            f"Storage quota exceeded: used={exc.used} limit={exc.limit} attempted={exc.attempted}",
        ) from exc
    except ValidationError as exc:
        raise JsonRpcError(INVALID_PARAMS, "; ".join(getattr(exc, "messages", [str(exc)]))) from exc

    from apps.media_library.tasks import process_media_asset

    process_media_asset(str(asset.id))

    return _wrap_text(_serialize_media(asset))


register_tool(
    Tool(
        name="upload_media",
        description=(
            "Upload a small media file (≤1 MB raw / ~1.3 MB base64) via base64. "
            "For anything larger use POST /api/v1/media/ over REST instead — multipart "
            "can't ride a JSON-RPC envelope. Returns the same shape as the REST upload "
            "response; processing_status starts at 'pending' until the background task "
            "transitions it to 'completed'."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "maxLength": 255},
                "content_base64": {
                    "type": "string",
                    "description": "Base64-encoded file content. Decoded size must be ≤5 MB.",
                },
                "content_type": {"type": "string"},
                "alt_text": {"type": "string", "maxLength": 2000},
                "title": {"type": "string", "maxLength": 255},
                "folder_id": {"type": "string", "format": "uuid"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["filename", "content_base64"],
            "additionalProperties": False,
        },
        handler=_upload_media,
    )
)


# ---------------------------------------------------------------------------
# Tool: get_account_analytics
# ---------------------------------------------------------------------------


def _get_account_analytics(args: dict, context: dict[str, Any]) -> dict:
    """Per-channel KPI summary over a rolling window.

    Body is byte-equal to ``GET /api/v1/analytics/accounts/{account_id}``
    because we reuse the same builder; ``test_rest_parity`` enforces
    that.
    """
    _require_perm(context, "view_analytics")
    if "account_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "account_id is required")
    days_raw = args.get("days", 30)
    # Match the REST surface's ``Query(ge=7, le=90)`` constraint so an
    # agent can't pick a wider window via MCP than via REST.
    if not isinstance(days_raw, int) or isinstance(days_raw, bool) or days_raw < 7 or days_raw > 90:
        raise JsonRpcError(INVALID_PARAMS, "days must be an integer between 7 and 90")
    api_key = context["api_key"]
    sa = _resolve_allowed_account(api_key, args["account_id"])
    return _wrap_text(build_account_analytics(sa, days_raw).model_dump(mode="json"))


register_tool(
    Tool(
        name="get_account_analytics",
        description=(
            "Read a channel's analytics summary over a rolling window: hero KPI metrics "
            "(views/likes/reach/etc.), an engagement-rate card when the platform supports it, "
            "and follower growth. Each metric is returned as ``{value, delta, series, kind}`` "
            "where ``delta`` is the percent change vs. the prior equal-length window and "
            "``series`` is the daily sparkline. Includes ``captured_at`` and ``next_sync_eta`` "
            "so an agent can pick a sensible poll delay. Platforms without an analytics surface "
            "(LinkedIn Personal, Bluesky, Mastodon) return ``analytics_available: false`` with "
            "``unavailable_reason``. Requires the view_analytics permission."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "SocialAccount ID. Must be in this API key's allowlist.",
                },
                "days": {
                    "type": "integer",
                    "minimum": 7,
                    "maximum": 90,
                    "default": 30,
                    "description": "Rolling window size in days. 7, 30, and 90 are the typical values.",
                },
            },
            "required": ["account_id"],
            "additionalProperties": False,
        },
        handler=_get_account_analytics,
    )
)


# ---------------------------------------------------------------------------
# Tool: get_post_analytics
# ---------------------------------------------------------------------------


def _get_post_analytics(args: dict, context: dict[str, Any]) -> dict:
    """Per-post analytics with one envelope per PlatformPost child.

    Designed for the polling loop after ``schedule_post`` /
    ``create_draft``: pass the same ``post_id`` you got back from
    creation and iterate until ``next_sync_eta`` recommends the next
    poll. Drafts and scheduled posts return a valid envelope with empty
    ``metric_tiles`` so the loop has a stable shape from day zero.
    """
    _require_perm(context, "view_analytics")
    if "post_id" not in args:
        raise JsonRpcError(INVALID_PARAMS, "post_id is required")
    api_key = context["api_key"]
    post = _get_post_for_key(api_key, args["post_id"])
    return _wrap_text(build_post_analytics(post).model_dump(mode="json"))


register_tool(
    Tool(
        name="get_post_analytics",
        description=(
            "Read a post's analytics, broken down per platform. For each PlatformPost child "
            "returns the latest value and a since-publish daily sparkline for every metric the "
            "platform reports, plus ``captured_at`` and ``next_sync_eta`` for polling. Drafts "
            "and scheduled posts return an empty ``metric_tiles`` array (not an error), so this "
            "tool is safe to call in a polling loop right after ``schedule_post``. Platforms "
            "without analytics (LinkedIn Personal, Bluesky, Mastodon) carry "
            "``analytics_available: false`` per child. Requires the view_analytics permission."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Parent Post ID (the same one returned by create_draft / schedule_post).",
                },
            },
            "required": ["post_id"],
            "additionalProperties": False,
        },
        handler=_get_post_analytics,
    )
)
