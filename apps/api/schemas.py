"""Pydantic request/response shapes for the Agent API.

Kept small on purpose: agents will rely on the auto-generated OpenAPI
spec at ``/api/v1/docs``, so every field needs a sensible description.

We deliberately don't expose internal fields like ``workspace_id`` in
request bodies — workspace scope comes from the bearer token, never
from client-supplied JSON. This is the same confused-deputy defence
Postiz uses.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from ninja import Field, Schema


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


class AccountSummary(Schema):
    id: uuid.UUID
    platform: str
    account_name: str
    account_handle: str = ""
    connection_status: str


class MeResponse(Schema):
    """Echoes everything the key is scoped to so an agent can self-introspect."""

    api_key_id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    organization_id: uuid.UUID
    permissions: list[str]
    allowlisted_accounts: list[AccountSummary]


# ---------------------------------------------------------------------------
# /accounts
# ---------------------------------------------------------------------------


class AccountsListResponse(Schema):
    accounts: list[AccountSummary]


# ---------------------------------------------------------------------------
# /posts — write
# ---------------------------------------------------------------------------


PostAction = Literal["draft", "schedule"]


class CreatePostRequest(Schema):
    """Create a draft or directly schedule a post against one account.

    ``social_account_id`` MUST be in the key's allowlist; the auth class
    raises 403 otherwise.
    """

    social_account_id: uuid.UUID = Field(
        ...,
        description="ID of the SocialAccount to target. Must be in the key's allowlist.",
    )
    caption: str = Field(..., max_length=10_000)
    title: str = Field("", max_length=255)
    first_comment: str = Field("", max_length=10_000)
    media_asset_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="MediaAsset IDs already uploaded to the workspace's media library. Position-ordered.",
    )
    action: PostAction = Field(
        "draft",
        description=(
            "``draft`` parks the post for later editing/scheduling; "
            "``schedule`` requires ``scheduled_at`` and queues for publishing."
        ),
    )
    scheduled_at: dt.datetime | None = Field(
        None,
        description="UTC timestamp. Required when ``action='schedule'``.",
    )
    idempotency_key: str | None = Field(
        None,
        max_length=128,
        description="Optional client-chosen retry key. Same key + same body → replay first response.",
    )


class UpdatePostRequest(Schema):
    caption: str | None = Field(None, max_length=10_000)
    title: str | None = Field(None, max_length=255)
    first_comment: str | None = Field(None, max_length=10_000)
    media_asset_ids: list[uuid.UUID] | None = None
    scheduled_at: dt.datetime | None = Field(
        None,
        description="If the post is currently scheduled, this re-times it. Ignored for drafts.",
    )


class ScheduleRequest(Schema):
    scheduled_at: dt.datetime = Field(
        ..., description="UTC timestamp at which the publisher should fire the post."
    )


# ---------------------------------------------------------------------------
# /posts — read
# ---------------------------------------------------------------------------


class PlatformPostSummary(Schema):
    id: uuid.UUID
    social_account_id: uuid.UUID
    platform: str
    status: str
    scheduled_at: dt.datetime | None
    published_at: dt.datetime | None
    platform_post_id: str = ""


class PostResponse(Schema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    caption: str
    first_comment: str
    scheduled_at: dt.datetime | None
    published_at: dt.datetime | None
    status: str  # derived aggregate
    platform_posts: list[PlatformPostSummary]
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------------------------------------------------------------------------
# Error envelope (used by the exception handler in api.py)
# ---------------------------------------------------------------------------


class ErrorResponse(Schema):
    error: str
    detail: str | None = None
    tier: str | None = None
    limit: int | None = None
    remaining: int | None = None
    retry_after: int | None = None
    reset_at: dt.datetime | None = None
