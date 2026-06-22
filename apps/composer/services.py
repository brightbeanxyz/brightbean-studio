"""Composer service helpers.

Where reusable "build me a post" logic lives so it can be called from the
HTMX-driven composer view *and* from the Agent API without duplicating
state-machine semantics.

The Phase 1 helper ``sync_post_scheduled_at`` keeps ``Post.scheduled_at``
in sync with the earliest per-platform ``PlatformPost.scheduled_at``;
the Phase 2 additions wrap ``Post`` + ``PlatformPost`` creation and
status transitions so audit + idempotency live in one place.
"""

from __future__ import annotations

import copy
import datetime as dt
import uuid
from collections.abc import Iterable
from typing import Any


def sync_post_scheduled_at(post):
    """Keep ``Post.scheduled_at`` in sync with the earliest child time.

    Three cases:

    * Some children have a ``scheduled_at`` → set parent to the min.
    * No children have a ``scheduled_at`` AND parent has one cached →
      clear the parent so listings, calendars, and Coalesce fallbacks
      don't keep showing the post as scheduled. This branch covers the
      "agent cancels the last scheduled child" flow — without it,
      ``Post.scheduled_at`` lingered at the old value and the post
      kept appearing as scheduled in the UI.
    * No children, parent already null → no-op.

    A post that gains a committed schedule also drops any draft-stage
    ``proposed_publish_at``: this is the chokepoint the scheduling paths flow
    through (``create_post``, ``transition_platform_post`` for the REST
    ``/schedule`` route and the MCP ``schedule_draft`` tool, and the PATCH
    re-time which calls this after saving), so the suggestion and a real
    schedule never coexist. The ``scheduled_at`` aggregate logic is unchanged —
    the publisher's ``Coalesce(scheduled_at, post__scheduled_at)`` fallback
    depends on it — so only the proposal clear is added here. The one path that
    commits a child WITHOUT a ``scheduled_at`` (the composer's per-account chip
    endpoint) clears the proposal itself rather than routing through here, to
    avoid disturbing that aggregate.
    """
    times = list(post.platform_posts.exclude(scheduled_at__isnull=True).values_list("scheduled_at", flat=True))
    if not times:
        if post.scheduled_at is not None:
            post.scheduled_at = None
            post.save(update_fields=["scheduled_at", "updated_at"])
        return
    earliest = min(times)
    update_fields = []
    if post.scheduled_at != earliest:
        post.scheduled_at = earliest
        update_fields.append("scheduled_at")
    if post.proposed_publish_at is not None:
        post.proposed_publish_at = None
        update_fields.append("proposed_publish_at")
    if update_fields:
        post.save(update_fields=[*update_fields, "updated_at"])


# ---------------------------------------------------------------------------
# Phase 2 — Agent-API-facing post creation
# ---------------------------------------------------------------------------


_INITIAL_STATUSES = {"draft", "scheduled"}


def create_post(
    *,
    workspace,
    social_account,
    caption: str,
    media_asset_ids: Iterable[Any] | None = None,
    title: str = "",
    first_comment: str = "",
    internal_notes: str = "",
    scheduled_at: dt.datetime | None = None,
    proposed_publish_at: dt.datetime | None = None,
    author=None,
    status: str = "draft",
    platform_overrides: dict[Any, dict[str, str | None]] | None = None,
):
    """Create a ``Post`` + one ``PlatformPost`` for ``social_account``.

    The canonical service-layer entry point for the Agent API. The
    composer's HTMX-driven ``save_post`` view will be refactored to call
    this in a follow-up; for now both code paths coexist and only the
    API uses it.

    Contract:

    * ``status`` must be one of ``draft`` or ``scheduled``. Other
      states (``approved``, ``publishing``, …) are produced only via
      explicit transitions through ``transition_platform_post``.
    * If ``status='scheduled'``, ``scheduled_at`` is required and must
      be in the future. The publisher polls every ~15 s; a past
      ``scheduled_at`` is accepted and will fire on the very next tick,
      but the caller almost certainly meant "now-ish" so we leave the
      decision to them.
    * ``proposed_publish_at`` is an optional draft-stage suggestion. It is
      stored as-is regardless of ``status`` and carries no future-time
      requirement — it never reaches the publisher.
    * ``social_account.workspace_id`` must equal ``workspace.id``. The
      caller (auth class / view) already enforced scope, but we
      double-check here so anyone reaching the service directly can't
      bypass it.
    * Media assets are attached in order by their position in
      ``media_asset_ids``. They must already live in the workspace's
      media library.

    Returns the persisted ``Post`` with one ``PlatformPost`` child.
    """
    from django.db import transaction

    from apps.composer.models import PlatformPost, Post, PostMedia
    from apps.media_library.models import MediaAsset

    if status not in _INITIAL_STATUSES:
        raise ValueError(
            f"create_post can only initialise status in {sorted(_INITIAL_STATUSES)}; "
            f"got {status!r}. Use transition_platform_post for other states."
        )
    if status == "scheduled" and scheduled_at is None:
        raise ValueError("status='scheduled' requires scheduled_at.")
    if social_account.workspace_id != workspace.id:
        raise ValueError(f"SocialAccount {social_account.id} is not in workspace {workspace.id}.")

    # Refuse to queue work against a connection the platform itself has
    # rejected. ``failed`` rows still count against the platform quota
    # (see ``QUOTA_CONSUMING_STATUSES`` in apps/api/limits.py), so each
    # silently-scheduled post against a disconnected/errored account
    # would burn one slot without ever publishing. Forcing an explicit
    # error here makes the agent reconnect first.
    if getattr(social_account, "needs_reconnect", False):
        raise ValueError(
            f"SocialAccount {social_account.id} is in connection_status "
            f"{social_account.connection_status!r}; reconnect it before scheduling."
        )

    if status == "scheduled":
        _require_approval_gate_passes(workspace)

    media_ids = list(media_asset_ids or [])
    # Pull and validate all referenced assets in a single query — fail
    # closed if any ID is missing or belongs to a different workspace.
    #
    # Normalize every id to a ``UUID`` for keying/lookup so all caller shapes
    # match identically: UUID objects (REST, coerced by Pydantic) and UUID
    # *strings* in any form (MCP, off the JSON-RPC wire — including uppercase or
    # braced). A raw string never compares equal to a UUID key, so without this
    # MCP-supplied assets are wrongly rejected as "not found in workspace".
    asset_map: dict[uuid.UUID, MediaAsset] = {}
    resolved: list[tuple[Any, uuid.UUID | None]] = []
    if media_ids:

        def _to_uuid(value):
            try:
                return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
            except (ValueError, TypeError, AttributeError):
                return None

        resolved = [(mid, _to_uuid(mid)) for mid in media_ids]
        found = list(MediaAsset.objects.filter(id__in=[u for _, u in resolved if u is not None], workspace=workspace))
        asset_map = {a.id: a for a in found}
        missing = [mid for mid, u in resolved if u is None or u not in asset_map]
        if missing:
            raise ValueError(f"Media asset(s) not found in workspace {workspace.id}: {missing}")

    override = (platform_overrides or {}).get(social_account.id) or {}

    with transaction.atomic():
        post = Post.objects.create(
            workspace=workspace,
            author=author,
            title=title,
            caption=caption,
            first_comment=first_comment,
            internal_notes=internal_notes,
            scheduled_at=scheduled_at if status == "scheduled" else None,
            # A proposal is plain draft metadata — keep it independent of
            # ``status`` (unlike ``scheduled_at``, which only exists once the
            # post is committed to the publisher).
            proposed_publish_at=proposed_publish_at,
        )
        # Each override field is independent: ``None`` (or omitted)
        # means "no platform-specific override; fall back to the post
        # value via ``PlatformPost.effective_*``". Any string —
        # including ``""`` — is treated as an explicit override.
        PlatformPost.objects.create(
            post=post,
            social_account=social_account,
            status=status,
            scheduled_at=scheduled_at if status == "scheduled" else None,
            platform_specific_title=override.get("title"),
            platform_specific_caption=override.get("caption"),
            platform_specific_first_comment=override.get("first_comment"),
        )
        for position, (_mid, u) in enumerate(resolved):
            # ``u`` is validated non-None and present in ``asset_map`` above
            # (the ``missing`` check raises otherwise); narrow for mypy.
            assert u is not None
            PostMedia.objects.create(
                post=post,
                media_asset=asset_map[u],
                position=position,
            )

    # Keep the aggregate column consistent — the publisher polls
    # PlatformPost directly so this is just for listings/UI, but the
    # composer view code relies on it.
    sync_post_scheduled_at(post)
    return post


def transition_platform_post(
    platform_post,
    target_status: str,
    *,
    scheduled_at: dt.datetime | None = None,
):
    """Apply a state-machine transition and persist.

    Wraps ``PlatformPost.transition_to`` (which only mutates the model
    in memory) with the persistence + side-effects the API needs:

    * Save the new status.
    * On ``scheduled``, set ``scheduled_at`` if provided, and sync the
      aggregate ``Post.scheduled_at`` column.
    * On ``draft``, clear ``scheduled_at`` so the row stops being a
      target for the publisher's polling query.

    Raises ``ValueError`` (from ``transition_to``) if the transition
    isn't in ``VALID_TRANSITIONS``.
    """
    from django.db import transaction

    # Approval workflow gate — Codex review (PR #53) flagged that the
    # ``POST /posts/{id}/schedule`` route reached this function with
    # ``target_status="scheduled"`` and bypassed the approval check
    # ``create_post`` enforces. The gate belongs here so EVERY path that
    # promotes a draft to scheduled (REST `/schedule` route, any future
    # MCP transition tool, the composer's HTMX `transition_platform_post`
    # view) is covered.
    if target_status == "scheduled":
        _require_approval_gate_passes(platform_post.post.workspace)

    with transaction.atomic():
        platform_post.transition_to(target_status)
        # Always include ``updated_at`` — Django docs: when ``update_fields``
        # is explicit, ``auto_now`` fields are NOT touched unless listed.
        # Without this every API/MCP-driven transition would leave
        # ``PlatformPost.updated_at`` frozen at creation time, breaking
        # any "modified since X" sync and ORDER BY updated_at view.
        update_fields = {"status", "updated_at"}
        if target_status == "scheduled":
            if scheduled_at is not None:
                platform_post.scheduled_at = scheduled_at
                update_fields.add("scheduled_at")
        elif target_status == "draft":
            if platform_post.scheduled_at is not None:
                platform_post.scheduled_at = None
                update_fields.add("scheduled_at")
            # A drafted child is no longer queued — drop its QueueEntry so the
            # slot frees as a gap. Covers cancel / unschedule paths that would
            # otherwise orphan the row with a stale assigned_slot_datetime.
            from apps.calendar.models import QueueEntry

            QueueEntry.objects.filter(
                post=platform_post.post,
                queue__social_account=platform_post.social_account,
            ).delete()
        elif target_status == "published":
            update_fields.add("published_at")  # set by transition_to
        platform_post.save(update_fields=list(update_fields))

    sync_post_scheduled_at(platform_post.post)
    return platform_post


def clone_post(post, *, author=None):
    """Create a fresh DRAFT duplicate of *post* (Clone / Repost).

    Copies caption, title, first comment, internal notes, tags, category, every
    per-platform override (``platform_specific_*`` + ``platform_extra``) and all
    media attachments. The copy starts as a ``draft`` with no schedule, so a
    published (or any) post can be re-edited and re-queued without touching the
    original. ``author`` defaults to the source author.
    """
    from django.db import transaction

    from apps.composer.models import PlatformPost, Post, PostMedia

    with transaction.atomic():
        new_post = Post.objects.create(
            workspace=post.workspace,
            author=author or post.author,
            title=(f"Copy of {post.title}" if post.title else ""),
            caption=post.caption,
            first_comment=post.first_comment,
            internal_notes=post.internal_notes,
            tags=post.tags,
            category=post.category,
        )
        children = list(post.platform_posts.all())
        if children:
            PlatformPost.objects.bulk_create(
                [
                    PlatformPost(
                        post=new_post,
                        social_account=pp.social_account,
                        status="draft",
                        platform_specific_title=pp.platform_specific_title,
                        platform_specific_caption=pp.platform_specific_caption,
                        platform_specific_first_comment=pp.platform_specific_first_comment,
                        platform_specific_media=copy.deepcopy(pp.platform_specific_media),
                        platform_extra=copy.deepcopy(pp.platform_extra) if pp.platform_extra else {},
                    )
                    for pp in children
                ]
            )
        media = list(post.media_attachments.all())
        if media:
            PostMedia.objects.bulk_create(
                [
                    PostMedia(
                        post=new_post,
                        media_asset=pm.media_asset,
                        position=pm.position,
                        alt_text=pm.alt_text,
                        platform_overrides=copy.deepcopy(pm.platform_overrides),
                    )
                    for pm in media
                ]
            )
    return new_post


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


#: Workspace approval modes that BLOCK a direct draft → scheduled
#: transition. The composer's HTMX path routes around this via a
#: separate ``submit_for_approval`` action; the Agent API surface uses
#: the same service layer so the constraint lives here once.
_APPROVAL_MODES_BLOCKING_DIRECT_SCHEDULE = frozenset({"required_internal", "required_internal_and_client"})


def _require_approval_gate_passes(workspace) -> None:
    """Raise ``ValueError`` if the workspace forbids direct scheduling.

    Drafts are always allowed (they're explicit save-for-later);
    scheduling implies "ready to publish," which is exactly what the
    approval workflow gates.
    """
    if getattr(workspace, "approval_workflow_mode", "none") in _APPROVAL_MODES_BLOCKING_DIRECT_SCHEDULE:
        raise ValueError(
            "Workspace requires approval before scheduling; create the post as a "
            "draft and route it through the approval workflow."
        )
