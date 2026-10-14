"""Durable Mastodon progress, with short transactions around owned writes.

The provider advances remote state. This module owns leases, deadlines and
terminal transitions; neither credentials nor temporary paths enter JSON.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.composer.models import PlatformPost
from apps.social_accounts.error_messages import (
    PUBLISH_GENERIC_MESSAGE,
    PUBLISH_RECONNECT_MESSAGE,
    PUBLISH_REJECTED_MESSAGE,
    PUBLISH_UNCONFIRMED_MESSAGE,
)
from apps.social_accounts.error_messages import (
    PUBLISH_MASTODON_CONTENT_CHANGED_MESSAGE as CONTENT_CHANGED_MESSAGE,
)
from apps.social_accounts.error_messages import (
    PUBLISH_MASTODON_MEDIA_FAILED_MESSAGE as MEDIA_FAILED_MESSAGE,
)
from apps.social_accounts.error_messages import (
    PUBLISH_MASTODON_MEDIA_TIMEOUT_MESSAGE as MEDIA_TIMEOUT_MESSAGE,
)
from providers.exceptions import ProviderError, PublishError, RateLimitError
from providers.mastodon import MastodonProvider
from providers.types import PublishContent, PublishContext, PublishResult

from .models import PublishLog, RateLimitState

if TYPE_CHECKING:
    from .engine import PublishEngine

logger = logging.getLogger(__name__)

LEASE_SECONDS = 300
CHECK_SECONDS = 60
SWEEP_SECONDS = 10
DEADLINE_SECONDS = 1800


class LeaseLostError(Exception):
    """An obsolete execution must stop before making another remote request."""


def media_source(asset) -> str:
    return f"{asset.pk}:{asset.file.name}"


def _date(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value)
        return result if timezone.is_aware(result) else None
    except ValueError:
        return None


def _snapshot(engine: PublishEngine, post: PlatformPost) -> dict:
    account = post.social_account
    assets = [
        item.media_asset
        for item in post.post.media_attachments.select_related("media_asset").order_by("position")
        if item.media_asset.file
    ]
    extra = post.platform_extra or {}
    content = PublishContent(
        text=post.effective_caption or "",
        extra=extra,
        post_type=engine._resolve_post_type(
            platform="mastodon",
            platform_extra=extra,
            media_count=len(assets),
            first_media_type=assets[0].media_type if assets else None,
        ),
    )
    payload = {
        "identity": {
            "account_id": str(account.pk),
            "platform_id": account.account_platform_id,
            "instance": account.instance_url.rstrip("/"),
        },
        "params": MastodonProvider.status_parameters(content),
        "sources": [media_source(asset) for asset in assets],
        "first_comment": post.effective_first_comment,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {**payload, "content_fingerprint": fingerprint}


class CheckpointWriter:
    def __init__(self, post: PlatformPost, checkpoint: dict):
        self.post = post
        self.attempt_id = checkpoint["attempt_id"]
        self.owner = checkpoint["lease"]["owner"]

    def write(self, checkpoint: dict, **fields) -> None:
        with transaction.atomic():
            current = PlatformPost.objects.select_for_update().only("status", "publish_checkpoint").get(pk=self.post.pk)
            stored = current.publish_checkpoint
            lease = stored.get("lease", {})
            expires = _date(lease.get("expires_at"))
            if (
                current.status != PlatformPost.Status.PUBLISHING
                or stored.get("attempt_id") != self.attempt_id
                or lease.get("owner") != self.owner
                or expires is None
                or expires <= timezone.now()
            ):
                raise LeaseLostError()
            PlatformPost.objects.filter(pk=self.post.pk).update(
                publish_checkpoint=deepcopy(checkpoint), updated_at=timezone.now(), **fields
            )
        self.post.publish_checkpoint = deepcopy(checkpoint)
        for key, value in fields.items():
            setattr(self.post, key, value)


def _claim(engine: PublishEngine, post: PlatformPost, *, resume: bool) -> PublishContext | None:
    snapshot = _snapshot(engine, post)
    now = timezone.now()
    with transaction.atomic():
        current = PlatformPost.objects.select_for_update().only("status", "publish_checkpoint").get(pk=post.pk)
        if current.status != PlatformPost.Status.PUBLISHING:
            return None
        checkpoint = deepcopy(current.publish_checkpoint)
        if not checkpoint:
            if resume:
                return None
            checkpoint = {
                "version": 1,
                "attempt_id": str(uuid.uuid4()),
                "identity": snapshot["identity"],
                "content_fingerprint": snapshot["content_fingerprint"],
                "params": snapshot["params"],
                "media": [{"source": source, "media_id": "", "ready": False} for source in snapshot["sources"]],
                "phase": "uploading",
                "started_at": now.isoformat(),
            }
        lease_until = _date(checkpoint.get("lease", {}).get("expires_at"))
        if lease_until and lease_until > now:
            return None
        check_at = _date(checkpoint.get("next_check_at"))
        if resume and check_at and check_at > now:
            return None
        # Malformed/unknown versions are claimed only to fail safely, never to
        # execute a new upload or status submission.
        checkpoint.setdefault("attempt_id", str(uuid.uuid4()))
        checkpoint["lease"] = {
            "owner": str(uuid.uuid4()),
            "expires_at": (now + timedelta(seconds=LEASE_SECONDS)).isoformat(),
        }
        checkpoint["next_check_at"] = (now + timedelta(seconds=CHECK_SECONDS)).isoformat()
        PlatformPost.objects.filter(pk=post.pk).update(publish_checkpoint=checkpoint, updated_at=now)
    post.publish_checkpoint = deepcopy(checkpoint)
    post.status = PlatformPost.Status.PUBLISHING
    writer = CheckpointWriter(post, checkpoint)
    context = PublishContext(checkpoint=deepcopy(checkpoint), save_checkpoint=writer.write)
    if checkpoint.get("content_fingerprint") != snapshot["content_fingerprint"]:
        context.checkpoint["content_changed"] = True
    return context


def _log(post: PlatformPost, checkpoint: dict, event: str, *, error: Exception | None = None) -> None:
    started = _date(checkpoint.get("started_at")) or timezone.now()
    logger.info(
        "Mastodon publish event=%s post=%s attempt=%s phase=%s elapsed_seconds=%.3f error_type=%s status=%s",
        event,
        post.pk,
        checkpoint.get("attempt_id"),
        checkpoint.get("phase"),
        (timezone.now() - started).total_seconds(),
        type(error).__name__ if error else "none",
        getattr(error, "status_code", None),
    )


def _defer(post: PlatformPost, context: PublishContext, error: Exception | None = None) -> dict:
    checkpoint = context.checkpoint
    now = timezone.now()
    delay = max(CHECK_SECONDS, getattr(error, "retry_after", None) or 0)
    cutoff_start = (
        _date(checkpoint.get("first_submission_at"))
        or _date(checkpoint.get("processing_started_at"))
        or _date(checkpoint.get("started_at"))
        or now
    )
    checkpoint["next_check_at"] = min(
        now + timedelta(seconds=delay), cutoff_start + timedelta(seconds=DEADLINE_SECONDS)
    ).isoformat()
    checkpoint.pop("lease", None)
    context.save()
    _log(post, checkpoint, "deferred", error=error)
    return {"success": False, "deferred": True, "async_publish": True}


def _fail(engine: PublishEngine, post: PlatformPost, context: PublishContext, message: str, *, unknown=False) -> dict:
    checkpoint = context.checkpoint
    checkpoint.pop("lease", None)
    writer = context.save_checkpoint
    # The callable is the writer's bound method, so terminal updates use the
    # exact same ownership check as intermediate persistence.
    writer(checkpoint if unknown else {}, status=PlatformPost.Status.FAILED, publish_error=message)
    _log(post, checkpoint, "unconfirmed" if unknown else "failed")
    PublishLog.objects.create(
        platform_post=post,
        attempt_number=post.retry_count + 1,
        error_message=message,
    )
    engine._notify_publish_failed(post)
    return {"success": False, "settled": True, "error": message}


def _finish(
    engine: PublishEngine, post: PlatformPost, context: PublishContext, result: PublishResult, *, started: float
) -> dict:
    attempt_number = post.retry_count + 1
    context.save_checkpoint(
        {},
        status=PlatformPost.Status.PUBLISHED,
        platform_post_id=result.platform_post_id,
        published_at=timezone.now(),
        publish_error="",
        retry_count=0,
        next_retry_at=None,
        platform_extra={**(post.platform_extra or {}), **result.extra},
    )
    _log(post, context.checkpoint, "published")
    # A failure after the guarded terminal write must never resubmit a status.
    try:
        PublishLog.objects.create(
            platform_post=post,
            attempt_number=attempt_number,
            status_code=200,
            response_body=json.dumps({"id": result.platform_post_id})[:1000],
            duration_ms=max(0, int((time.monotonic() - started) * 1000)),
        )
        engine._drop_queue_entry(post)
        engine._sync_parent_published_at(post.post)
        engine._maybe_schedule_first_comment(post)
    except Exception:
        logger.exception("Mastodon post %s published; local completion cleanup failed", post.pk)
    return {"success": True, "settled": True, "platform_post_id": result.platform_post_id}


def publish_mastodon(
    engine: PublishEngine,
    post: PlatformPost,
    *,
    media_cache=None,
    resume=False,
    deadline: float | None = None,
) -> dict:
    """Advance only the currently owned attempt and leave polling to the sweep."""
    started = time.monotonic()
    context = _claim(engine, post, resume=resume)
    if context is None:
        return {"success": False, "deferred": True}
    context.deadline = deadline
    checkpoint = context.checkpoint
    try:
        if checkpoint.get("version") != 1 or checkpoint.get("phase") not in {
            "uploading",
            "processing",
            "submitting",
            "complete",
        }:
            return _fail(engine, post, context, PUBLISH_UNCONFIRMED_MESSAGE, unknown=True)
        if checkpoint.get("status_id"):
            return _finish(engine, post, context, MastodonProvider._completed_result(checkpoint), started=started)
        if checkpoint.get("content_changed"):
            unknown = bool(checkpoint.get("first_submission_at"))
            return _fail(
                engine,
                post,
                context,
                PUBLISH_UNCONFIRMED_MESSAGE if unknown else CONTENT_CHANGED_MESSAGE,
                unknown=unknown,
            )
        now = timezone.now()
        submitted = _date(checkpoint.get("first_submission_at"))
        processing = _date(checkpoint.get("processing_started_at"))
        if submitted and now - submitted >= timedelta(seconds=DEADLINE_SECONDS):
            return _fail(engine, post, context, PUBLISH_UNCONFIRMED_MESSAGE, unknown=True)
        processing = processing or _date(checkpoint.get("started_at"))
        if not submitted and processing and now - processing >= timedelta(seconds=DEADLINE_SECONDS):
            return _fail(engine, post, context, MEDIA_TIMEOUT_MESSAGE)
        rate = RateLimitState.objects.filter(social_account=post.social_account, platform="mastodon").first()
        if rate and rate.is_rate_limited and rate.window_resets_at is not None:
            delay = max(0, int((rate.window_resets_at - now).total_seconds()))
            return _defer(post, context, RateLimitError("Mastodon rate limit", retry_after=delay))
        if checkpoint["phase"] == "uploading":
            result = engine._dispatch_to_provider(post, media_cache=media_cache, publish_context=context)
            if result.get("deferred"):
                return _defer(post, context)
            published = PublishResult(
                result["platform_post_id"], url=result.get("url"), extra=result.get("response", {})
            )
        else:
            from .engine import _provider_and_access_token

            provider, token = _provider_and_access_token(post.social_account)
            published = provider.resume_publish(token, context)
            if published.deferred:
                return _defer(post, context)
        return _finish(engine, post, context, published, started=started)
    except LeaseLostError:
        _log(post, checkpoint, "lease_lost")
        return {"success": False, "stale": True}
    except Exception as exc:
        try:
            if isinstance(exc, ProviderError) and not exc.retryable:
                if getattr(exc, "status_code", None) in (401, 403):
                    from apps.social_accounts.models import SocialAccount

                    token = (
                        SocialAccount.objects.filter(pk=post.social_account_id)
                        .values_list("oauth_access_token", flat=True)
                        .first()
                    )
                    if token is not None and token != post.social_account.oauth_access_token:
                        return _defer(post, context, exc)
                if checkpoint.get("submission_uncertain"):
                    return _fail(engine, post, context, PUBLISH_UNCONFIRMED_MESSAGE, unknown=True)
                message = (
                    PUBLISH_RECONNECT_MESSAGE
                    if getattr(exc, "status_code", None) in (401, 403)
                    else PUBLISH_REJECTED_MESSAGE
                    if checkpoint.get("phase") == "submitting"
                    else MEDIA_FAILED_MESSAGE
                )
                if isinstance(exc, PublishError):
                    message = PUBLISH_GENERIC_MESSAGE
                _log(post, checkpoint, "permanent_error", error=exc)
                return _fail(engine, post, context, message)
            # HTTP timeouts, 5xx and rate limits retain uploaded IDs and, once
            # submitting, the same payload and idempotency key. No provider
            # exception string or raw response is written into operational logs.
            if checkpoint.get("phase") == "submitting" and not isinstance(exc, RateLimitError):
                checkpoint["submission_uncertain"] = True
            return _defer(post, context, exc)
        except LeaseLostError:
            _log(post, checkpoint, "lease_lost")
            return {"success": False, "stale": True}
