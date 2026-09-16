"""``/api/v1/posts/*`` — create, read, update, schedule, cancel.

Every write path:

1. Enforces HTTP-level rate limits (per-key, per-workspace, global).
2. Replays the response if an idempotency key matches an earlier request.
3. Checks workspace permission via the shared ``@require_permission`` helper.
4. Validates the target ``SocialAccount`` is in the key's allowlist.
5. Checks per-platform 24h quota.
6. Calls the composer service layer (single source of truth for state).
7. Writes an audit log row.
8. Persists the response under the idempotency key if one was passed.

This ordering means an expensive operation (the create) can't run until
both the cheap rate-limit check and the issuer-permission check pass —
defence against spending DB cycles for unauthorized callers.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError

from apps.api.limits import check_platform_quota, enforce_http_rate_limits
from apps.api.middleware import (
    claim_idempotency_slot,
    finalize_idempotent_response,
    fingerprint_request,
    log_audit_entry,
    release_idempotent_claim,
)
from apps.api.schemas import (
    CreatePostRequest,
    Metodo3RImportRequest,
    Metodo3RImportResponse,
    PostResponse,
    ScheduleRequest,
    UpdatePostRequest,
)
from apps.composer.models import PlatformPost, Post, PostMedia
from apps.composer.services import (
    create_post,
    sync_post_scheduled_at,
    transition_platform_post,
)
from apps.media_library.models import MediaAsset
from apps.social_accounts.models import SocialAccount

router = Router(tags=["posts"])


_METODO3R_PLATFORM_ALIASES = {
    "instagram": ("instagram", "instagram_login"),
    "youtube_shorts": ("youtube",),
    "youtube": ("youtube",),
    "facebook": ("facebook",),
    "tiktok": ("tiktok",),
    "linkedin": ("linkedin_company", "linkedin_personal"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_perm(request: HttpRequest, key: str) -> None:
    """Re-check a workspace permission inside a Ninja route body.

    We can't decorate Ninja routes with ``@require_permission`` because it
    expects a Django view signature; instead we inline the same check
    against the virtual membership shim.
    """
    membership = getattr(request, "workspace_membership", None)
    if membership is None or not membership.effective_permissions.get(key, False):
        raise HttpError(403, f"Permission denied: {key}")


def _resolve_account(request: HttpRequest, social_account_id: uuid.UUID) -> SocialAccount:
    """Resolve the target account and verify it is in the key's allowlist.

    Defence against confused-deputy attacks: even though the bearer is
    valid, the caller may only act on accounts the issuer explicitly
    listed at issuance time.
    """
    api_key = request.api_key  # type: ignore[attr-defined]  # set by ApiKeyAuth
    allowlist_ids = {sa.id for sa in api_key.social_accounts.all()}
    if social_account_id not in allowlist_ids:
        raise HttpError(403, "SocialAccount is not in this key's allowlist.")
    return SocialAccount.objects.get(id=social_account_id)


def _can_view_internal_notes(request: HttpRequest) -> bool:
    """Whether this caller may see a post's team-only ``internal_notes``.

    The composer hides ``internal_notes`` from the ``client`` / ``viewer``
    workspace roles ([views.py](apps/composer/views.py): ``can_view_internal_notes``).
    Those are exactly the builtin roles without ``create_posts`` (see
    ``BUILTIN_ROLE_PERMISSIONS``), so gating visibility on ``create_posts``
    reproduces that rule uniformly for both API keys and OAuth members. Reads
    (`GET /posts/{id}`) aren't otherwise permission-gated, so without this the
    shared serializer would leak notes to any read-capable client/viewer.
    """
    membership = getattr(request, "workspace_membership", None)
    return bool(membership and membership.effective_permissions.get("create_posts", False))


def _post_to_response(request: HttpRequest, post: Post) -> PostResponse:
    return PostResponse.from_post(post, include_internal_notes=_can_view_internal_notes(request))


def _metodo3r_platform_candidates(platform: str) -> tuple[str, ...]:
    return _METODO3R_PLATFORM_ALIASES.get(platform, (platform,))


def _resolve_metodo3r_accounts(request: HttpRequest, platforms: list[str]) -> list[SocialAccount]:
    api_key = request.api_key  # type: ignore[attr-defined]
    allowlisted = list(api_key.social_accounts.select_related("workspace").all())
    resolved: list[SocialAccount] = []
    seen_ids: set[uuid.UUID] = set()
    missing: list[str] = []
    for platform in platforms:
        candidates = _metodo3r_platform_candidates(platform)
        account = next(
            (
                social_account
                for social_account in allowlisted
                if social_account.workspace_id == api_key.workspace_id and social_account.platform in candidates
            ),
            None,
        )
        if account is None:
            missing.append(platform)
            continue
        if account.id not in seen_ids:
            resolved.append(account)
            seen_ids.add(account.id)
    if missing:
        raise HttpError(422, f"No allowlisted SocialAccount found for platform(s): {', '.join(missing)}.")
    return resolved


def _metodo3r_import_root() -> Path | None:
    root = getattr(settings, "METODO3R_IMPORT_ROOT", "") or ""
    if not root:
        return None
    try:
        return Path(root).expanduser().resolve()
    except OSError:
        return None


def _resolve_metodo3r_media_path(path: str) -> Path | None:
    root = _metodo3r_import_root()
    if root is None or not path or "://" in path:
        return None
    raw_path = Path(path)
    if raw_path.is_absolute():
        return None
    try:
        candidate = (root / raw_path).resolve()
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    if not candidate.is_file():
        return None
    return candidate


def _metodo3r_media_type(path: Path, mime_type: str) -> str:
    suffix = path.suffix.lower()
    if mime_type.startswith("image/gif") or suffix == ".gif":
        return MediaAsset.MediaType.GIF
    if mime_type.startswith("image/"):
        return MediaAsset.MediaType.IMAGE
    if mime_type.startswith("video/"):
        return MediaAsset.MediaType.VIDEO
    return MediaAsset.MediaType.DOCUMENT


def _import_metodo3r_media_asset(request: HttpRequest, source_path: str, duration_seconds: int | None) -> MediaAsset | None:
    file_path = _resolve_metodo3r_media_path(source_path)
    if file_path is None:
        return None

    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    media_type = _metodo3r_media_type(file_path, mime_type)
    asset = MediaAsset(
        organization=request.api_key.workspace.organization,  # type: ignore[attr-defined]
        workspace=request.api_key.workspace,  # type: ignore[attr-defined]
        uploaded_by=request.user if not request.user.is_anonymous else None,
        filename=file_path.name,
        media_type=media_type,
        mime_type=mime_type,
        file_size=file_path.stat().st_size,
        duration=duration_seconds if media_type == MediaAsset.MediaType.VIDEO and duration_seconds else 0,
        source="metodo3r",
        source_url=source_path,
        processing_status=MediaAsset.ProcessingStatus.COMPLETED,
    )
    with file_path.open("rb") as handle:
        asset.file.save(file_path.name, File(handle), save=True)
    return asset


def _attach_metodo3r_media(request: HttpRequest, post: Post, payload: Metodo3RImportRequest) -> list[MediaAsset]:
    assets: list[MediaAsset] = []
    for source_path in [payload.item.video, payload.item.selected_image, *payload.item.alternate_images]:
        asset = _import_metodo3r_media_asset(request, source_path, payload.item.duration_seconds)
        if asset is not None:
            assets.append(asset)

    for position, asset in enumerate(assets):
        PostMedia.objects.get_or_create(
            post=post,
            media_asset=asset,
            defaults={"position": position},
        )
    return assets


def _get_workspace_post(request: HttpRequest, post_id: uuid.UUID) -> Post:
    """Fetch a Post that belongs to the key's workspace **and** whose every
    ``PlatformPost`` child targets a ``SocialAccount`` in the key's
    allowlist.

    The workspace filter alone is not enough — a key scoped to LinkedIn-A
    could otherwise read or mutate a Post whose only child is for
    Twitter-B in the same workspace if it happened to know the Post UUID.
    The "all children in allowlist" rule (rather than "any child") means
    schedule/cancel/update can freely iterate ``post.platform_posts``
    without us having to scope each operation sub-Post — there is no
    foreign child for them to touch.

    We intentionally don't distinguish "doesn't exist" from "exists in
    another workspace" from "exists but partially out of scope" — all
    three return 404 so the API doesn't leak the existence of foreign
    IDs to a partial-scope bearer.
    """
    from django.http import Http404

    post = get_object_or_404(
        Post.objects.prefetch_related("platform_posts__social_account"),
        id=post_id,
        workspace_id=request.api_key.workspace_id,  # type: ignore[attr-defined]
    )
    allowed_ids = {sa.id for sa in request.api_key.social_accounts.all()}  # type: ignore[attr-defined]
    pp_account_ids = {pp.social_account_id for pp in post.platform_posts.all()}
    # No platform_posts → nothing this key could legitimately act on.
    # Foreign child → leaking even via a read would be a confused-deputy.
    if not pp_account_ids or not pp_account_ids.issubset(allowed_ids):
        raise Http404()
    return post


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/imports/metodo3r/",
    response={201: Metodo3RImportResponse, 200: Metodo3RImportResponse},
    summary="Import a Metodo 3R publication package",
)
def import_metodo3r(request, payload: Metodo3RImportRequest):
    """Bridge Metodo 3R's publication outbox into the editorial composer."""
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "create_posts")

    social_accounts = _resolve_metodo3r_accounts(request, payload.schedule.platforms)
    idempotency_key = payload.idempotency_key or request.headers.get("Idempotency-Key") or None
    fingerprint = fingerprint_request(request.method or "POST", request.path, payload.dict(by_alias=True))
    try:
        disposition, replay_status, replay_body = claim_idempotency_slot(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
    if disposition == "replay":
        return replay_status, replay_body
    if disposition == "in_flight":
        raise HttpError(409, "An identical Metodo 3R import is still in flight; retry shortly.")

    from django.db import transaction

    should_schedule = payload.human_gate != "required_before_publish"
    if should_schedule:
        _require_perm(request, "publish_directly")
        for social_account in social_accounts:
            check_platform_quota(social_account)

    try:
        with transaction.atomic():
            post = Post.objects.create(
                workspace=request.api_key.workspace,
                author=request.user if not request.user.is_anonymous else None,
                origin=Post.Origin.IMPORT,
                title=payload.item.title,
                caption=payload.schedule.caption,
                internal_notes=(
                    f"Imported from Metodo 3R item {payload.item.id}. "
                    f"Presenter: {payload.presenter}. Video: {payload.item.video}. "
                    f"Selected image: {payload.item.selected_image}."
                ),
                tags=["metodo3r", payload.project, payload.item.type, payload.item.id],
                scheduled_at=payload.schedule.scheduled_at if should_schedule else None,
                proposed_publish_at=None if should_schedule else payload.schedule.scheduled_at,
            )
            media_assets = _attach_metodo3r_media(request, post, payload)
            for social_account in social_accounts:
                PlatformPost.objects.create(
                    post=post,
                    social_account=social_account,
                    status=PlatformPost.Status.SCHEDULED if should_schedule else PlatformPost.Status.DRAFT,
                    scheduled_at=payload.schedule.scheduled_at if should_schedule else None,
                    platform_extra={
                        "source": "metodo3r",
                        "source_project": payload.project,
                        "source_item_id": payload.item.id,
                        "source_item_type": payload.item.type,
                        "video_path": payload.item.video,
                        "selected_image_path": payload.item.selected_image,
                        "alternate_image_paths": payload.item.alternate_images,
                        "media_asset_ids": [str(asset.id) for asset in media_assets],
                        "duration_seconds": payload.item.duration_seconds,
                        "timezone": payload.schedule.timezone,
                        "requested_platforms": payload.schedule.platforms,
                    },
                )

        body = Metodo3RImportResponse(
            id=str(post.id),
            post_id=post.id,
            status="scheduled" if should_schedule else "draft",
            imported_platforms=[account.platform for account in social_accounts],
            proposed_publish_at=post.proposed_publish_at,
            scheduled_at=post.scheduled_at,
            status_url=f"/api/v1/posts/{post.id}",
        )
        log_audit_entry(request, action="post.import.metodo3r", target_id=post.id, status_code=201)
        finalize_idempotent_response(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            status_code=201,
            body=body.model_dump(mode="json"),
        )
    except Exception:
        release_idempotent_claim(api_key=request.api_key, idempotency_key=idempotency_key)
        raise
    return 201, body


@router.post("/", response={201: PostResponse, 200: PostResponse}, summary="Create a draft or scheduled post")
def create(request, payload: CreatePostRequest):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "create_posts")
    # Scheduling implies "ready to publish without further human review",
    # which is exactly what ``publish_directly`` gates in the composer
    # ([views.py:797](apps/composer/views.py)). The REST API must mirror
    # that contract — a key issued with only ``create_posts`` can park
    # drafts but cannot send them into the publisher's poll loop.
    if payload.action == "schedule":
        _require_perm(request, "publish_directly")

    # ---- Cheap validation runs BEFORE we touch the idempotency table.
    # The motivation: an early failure here (403, 422) would otherwise
    # leave a placeholder claim row that release-on-error has to clean
    # up — and forgetting one release path locks the agent out for 24h.
    # Doing all "can this request possibly succeed?" checks pre-claim
    # keeps the claim/release pair tight and confined to the post-claim
    # path (platform quota + create_post).
    social_account = _resolve_account(request, payload.social_account_id)
    if payload.action == "schedule" and payload.scheduled_at is None:
        raise HttpError(422, "scheduled_at is required when action='schedule'.")

    # Build the platform_overrides dict and validate that each override's
    # social_account_id matches one of the post's target accounts. In the
    # current single-account API that's only ``payload.social_account_id``;
    # anything else would silently no-op at publish time, so we reject up
    # front. The plan's [Gap 2] section calls this out explicitly.
    platform_overrides: dict = {}
    for ov in payload.platform_overrides:
        if ov.social_account_id != payload.social_account_id:
            raise HttpError(
                422,
                (
                    f"platform_overrides[*].social_account_id must match the post's "
                    f"social_account_id ({payload.social_account_id}); got {ov.social_account_id}."
                ),
            )
        platform_overrides[ov.social_account_id] = {
            "title": ov.title,
            "caption": ov.caption,
            "first_comment": ov.first_comment,
        }

    # ---- Atomic claim-first idempotency. Three early-out branches
    # before we do *any* mutating work, so concurrent identical retries
    # can never both reach create_post:
    #   replay     — prior request already finished, return its response
    #   in_flight  — a concurrent peer holds the slot, return 409
    #   passthrough/claimed — caller proceeds; only the "claimed" path
    #                         must finalize or release before returning.
    fingerprint = fingerprint_request(request.method or "POST", request.path, payload.dict(by_alias=True))
    # Accept the canonical ``Idempotency-Key`` HTTP header (Stripe-style)
    # in addition to the body field. The header is the industry
    # convention — clients that retry on network timeout typically reuse
    # the header but can't easily re-send the same JSON body — so
    # ignoring it would silently break the "retry-safe" contract Codex
    # review (PR #53) flagged. The body field still wins when both are
    # present, so a deliberate caller can override.
    idempotency_key = payload.idempotency_key or request.headers.get("Idempotency-Key") or None
    try:
        disposition, replay_status, replay_body = claim_idempotency_slot(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
    if disposition == "replay":
        return replay_status, replay_body
    if disposition == "in_flight":
        raise HttpError(
            409,
            "An identical request with this idempotency_key is still in flight; retry shortly.",
        )

    # Platform-quota check has to be inside the claim window because it
    # depends on database state that other concurrent claims could
    # change. Drafts are excluded from the count inside
    # ``check_platform_quota`` so creating drafts cannot exhaust the
    # platform's posting cap.
    if payload.action == "schedule":
        try:
            check_platform_quota(social_account)
        except HttpError:
            release_idempotent_claim(api_key=request.api_key, idempotency_key=idempotency_key)
            raise

    # Single try/except covers every step from create_post through
    # finalize_idempotent_response. Codex review found that earlier
    # code committed the Post + PlatformPost via create_post and then
    # built the response / wrote the audit / called finalize OUTSIDE
    # the release path — so a transient DB error during response build
    # or finalize left the idempotency slot wedged in PENDING forever
    # while the work had already succeeded. Folding everything under
    # one ``try / except / release`` closes that window: any exception
    # after the claim releases the slot, the agent can retry, and the
    # retry will reach create_post fresh (or replay if finalize did
    # commit before the failure).
    try:
        post = create_post(
            workspace=request.api_key.workspace,
            social_account=social_account,
            caption=payload.caption,
            media_asset_ids=payload.media_asset_ids,
            title=payload.title,
            first_comment=payload.first_comment,
            internal_notes=payload.internal_notes,
            scheduled_at=payload.scheduled_at,
            # A scheduled post carries a real time, not a proposal — ignore any
            # proposed_publish_at when scheduling so the two never coexist.
            proposed_publish_at=None if payload.action == "schedule" else payload.proposed_publish_at,
            author=request.user if not request.user.is_anonymous else None,
            status="scheduled" if payload.action == "schedule" else "draft",
            platform_overrides=platform_overrides,
        )
        body = _post_to_response(request, post)
        status_code = 201
        log_audit_entry(
            request,
            action=f"post.create.{payload.action}",
            target_id=post.id,
            status_code=status_code,
        )
        # ``model_dump(mode='json')`` yields JSON-safe primitives
        # (UUID→str, datetime→ISO-8601 str) so the response_body
        # JSONField round-trips cleanly through psycopg's jsonb adapter.
        finalize_idempotent_response(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            status_code=status_code,
            body=body.model_dump(mode="json"),
        )
    except ValueError as exc:
        # Use the *effective* idempotency key (header fallback applied)
        # so a header-only client's claim is released too — Codex PR #53
        # round-3 flagged that the previous ``payload.idempotency_key``
        # was None on header-only requests and left the claim wedged in
        # PENDING until the 24h sweep.
        release_idempotent_claim(api_key=request.api_key, idempotency_key=idempotency_key)
        raise HttpError(422, str(exc)) from exc
    except Exception:
        release_idempotent_claim(api_key=request.api_key, idempotency_key=idempotency_key)
        raise
    return status_code, body


@router.get("/{post_id}", response=PostResponse, summary="Read a single post")
def retrieve(request, post_id: uuid.UUID):
    enforce_http_rate_limits(request, is_write=False)
    post = _get_workspace_post(request, post_id)
    log_audit_entry(request, action="post.read", target_id=post.id, status_code=200)
    return _post_to_response(request, post)


@router.patch("/{post_id}", response=PostResponse, summary="Update draft fields")
def update(request, post_id: uuid.UUID, payload: UpdatePostRequest):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "create_posts")  # mirrors composer's create-or-edit perm
    post = _get_workspace_post(request, post_id)

    # Only allow updates while editable.
    if not post.is_editable:
        raise HttpError(409, f"Post is not editable in status {post.status}.")

    # Re-timing a scheduled post is publish-budget behaviour: pushing
    # ``scheduled_at`` into the past makes the publisher fire the post on
    # its very next poll (~15 s), and pushing it far into the future buries
    # admin-scheduled content. Either is a privilege escalation for a key
    # that doesn't hold ``publish_directly`` — the create / schedule routes
    # and every MCP transition tool gate this exact mutation on that
    # permission, and the PATCH route must do the same to stay consistent.
    # Codex PR #53 security review (round 4) caught this gap.
    if payload.scheduled_at is not None and post.platform_posts.filter(status="scheduled").exists():
        _require_perm(request, "publish_directly")

    # ---- Validate-everything-first.
    #
    # Codex review found two bugs in the previous implementation:
    #   (a) ``scheduled_children.update(scheduled_at=...)`` ran BEFORE
    #       media validation, so a 422 from a foreign media asset still
    #       committed the new schedule timestamp to the DB.
    #   (b) ``post.media_attachments.all().delete()`` + the create loop
    #       were not wrapped in a transaction, so a mid-loop failure
    #       deleted the originals and persisted only a partial new set.
    # Fix: resolve every required reference and reject every invalid
    # input before any database mutation, then perform all mutations
    # inside a single ``transaction.atomic()`` block. Either everything
    # commits or nothing does.
    from django.db import transaction

    from apps.composer.models import PostMedia
    from apps.media_library.models import MediaAsset

    wanted_media: list = []
    resolved_assets: dict = {}
    if payload.media_asset_ids is not None:
        wanted_media = list(payload.media_asset_ids)
        resolved_assets = {a.id: a for a in MediaAsset.objects.filter(id__in=wanted_media, workspace=post.workspace)}
        missing = [i for i in wanted_media if i not in resolved_assets]
        if missing:
            raise HttpError(422, f"Media asset(s) not in workspace: {missing}")

    with transaction.atomic():
        update_fields: list[str] = []
        if payload.caption is not None:
            post.caption = payload.caption
            update_fields.append("caption")
        if payload.title is not None:
            post.title = payload.title
            update_fields.append("title")
        if payload.first_comment is not None:
            post.first_comment = payload.first_comment
            update_fields.append("first_comment")
        if payload.internal_notes is not None:
            post.internal_notes = payload.internal_notes
            update_fields.append("internal_notes")
        if payload.scheduled_at is not None:
            # Re-time any currently-scheduled child. Drafts are unaffected.
            # ``QuerySet.update()`` bypasses ``auto_now``, so we include
            # ``updated_at=timezone.now()`` explicitly. Otherwise each
            # child's ``updated_at`` would freeze at its creation time
            # despite an effective state change.
            from django.utils import timezone as _tz

            scheduled_children = post.platform_posts.filter(status="scheduled")
            scheduled_children.update(scheduled_at=payload.scheduled_at, updated_at=_tz.now())
            post.scheduled_at = payload.scheduled_at
            update_fields.append("scheduled_at")
        if payload.proposed_publish_at is not None:
            # Draft-stage suggestion; null is a no-op, consistent with the
            # other PATCH fields. Not gated on publish_directly — it never
            # reaches the publisher.
            post.proposed_publish_at = payload.proposed_publish_at
            update_fields.append("proposed_publish_at")
        if payload.media_asset_ids is not None:
            # Replace the attachment set in order. Validated above, so
            # the only remaining failure modes are DB-level — the atomic
            # block rolls back the whole route if any single
            # ``PostMedia.objects.create`` raises.
            post.media_attachments.all().delete()
            for position, mid in enumerate(wanted_media):
                PostMedia.objects.create(
                    post=post,
                    media_asset=resolved_assets[mid],
                    position=position,
                )

        if update_fields:
            post.save(update_fields=[*update_fields, "updated_at"])

        sync_post_scheduled_at(post)

    post.refresh_from_db()
    log_audit_entry(request, action="post.update", target_id=post.id, status_code=200)
    return _post_to_response(request, post)


@router.post("/{post_id}/schedule", response=PostResponse, summary="Schedule a draft")
def schedule(request, post_id: uuid.UUID, payload: ScheduleRequest):
    enforce_http_rate_limits(request, is_write=True)
    # Same ``publish_directly`` contract as the create-with-schedule
    # branch: only keys that can publish-directly may push a post into
    # the SCHEDULED state. See ``create``.
    _require_perm(request, "create_posts")
    _require_perm(request, "publish_directly")
    post = _get_workspace_post(request, post_id)

    # Schedule every draft child; a single-account key produces one child,
    # but defensively we apply the transition to all draft children so we
    # don't half-schedule.
    drafts = list(post.platform_posts.filter(status="draft"))
    if not drafts:
        raise HttpError(409, "No draft platform posts to schedule.")

    # Quota check is per-account, so we evaluate it once per child before
    # we touch any state. Doing the checks first means an over-quota
    # account fails the whole route with 429 — no partial commit.
    for pp in drafts:
        check_platform_quota(pp.social_account)

    # Wrap the per-child transitions in a single outer atomic so a
    # mid-loop ValueError rolls back any earlier ``scheduled`` commits.
    # Without this, child 1 could be persisted as ``scheduled`` while
    # child 2's ``transition_to`` rejects the move (concurrent admin
    # edit, state-machine conflict) — the route 422s but the post is
    # left in a half-scheduled state.
    from django.db import transaction

    with transaction.atomic():
        for pp in drafts:
            try:
                transition_platform_post(pp, "scheduled", scheduled_at=payload.scheduled_at)
            except ValueError as exc:
                raise HttpError(422, str(exc)) from exc

    post.refresh_from_db()
    log_audit_entry(request, action="post.schedule", target_id=post.id, status_code=200)
    return _post_to_response(request, post)


@router.post("/{post_id}/cancel", response=PostResponse, summary="Cancel a scheduled post (back to draft)")
def cancel(request, post_id: uuid.UUID):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "create_posts")
    post = _get_workspace_post(request, post_id)

    scheduled_children = list(post.platform_posts.filter(status="scheduled"))
    if not scheduled_children:
        raise HttpError(409, "No scheduled platform posts to cancel.")

    # Same atomic-loop reasoning as ``schedule``: any per-child transition
    # failure rolls back the whole cancellation. Half-cancelled posts
    # would otherwise leave the publisher with a mix of ``draft`` and
    # ``scheduled`` children, which is exactly the inconsistent state
    # the route was supposed to prevent.
    from django.db import transaction

    with transaction.atomic():
        for pp in scheduled_children:
            try:
                transition_platform_post(pp, "draft")
            except ValueError as exc:
                raise HttpError(422, str(exc)) from exc

    post.refresh_from_db()
    log_audit_entry(request, action="post.cancel", target_id=post.id, status_code=200)
    return _post_to_response(request, post)
