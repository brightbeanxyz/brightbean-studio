"""Publishing Engine - background worker logic (F-2.4).

This module implements the core publish loop:
1. Poll for PlatformPosts where scheduled_at <= now() and status = 'scheduled'.
2. Transition each due PlatformPost to 'publishing'.
3. Dispatch platform posts in parallel.
4. Handle retries with exponential backoff.
5. Post first comment after 2-minute delay.
6. Update per-platform status and log results.

Status is owned entirely by ``PlatformPost`` — the parent ``Post`` exposes an
aggregate ``status`` property derived from its children (see
``apps.composer.status``).
"""

import contextlib
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

from background_task import background
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.composer.models import PlatformPost
from apps.credentials.models import resolve_platform_credentials
from apps.social_accounts.error_messages import (
    FIRST_COMMENT_GENERIC_MESSAGE,
    PUBLISH_EXHAUSTED_MESSAGE,
    PUBLISH_GENERIC_MESSAGE,
    PUBLISH_RATE_LIMIT_MESSAGE,
    friendly_first_comment_error,
    friendly_publish_error,
)
from providers import get_provider
from providers.exceptions import ProviderError, RateLimitError
from providers.types import PostType, PublishContent

from .models import PublishLog, RateLimitState

logger = logging.getLogger(__name__)

# Retry backoff schedule (in seconds)
RETRY_BACKOFF = [60, 300, 1800]  # 1min, 5min, 30min


def _resolve_publish_credentials(account):
    """Resolve the credentials dict for publishing on behalf of `account`.

    Combines org-level `PlatformCredential` (with `.env` dominant) with
    per-account federation metadata (Mastodon `instance_url` +
    `MastodonAppRegistration`, Bluesky `pds_url`). Returns a plain dict
    suitable for `get_provider(platform, credentials)`.
    """
    platform = account.platform

    # .env is dominant; admin-entered org credentials are the fallback.
    credentials = resolve_platform_credentials(platform, account.workspace.organization_id)

    if platform == "mastodon" and account.instance_url:
        from apps.common.validators import is_safe_url

        if is_safe_url(account.instance_url):
            credentials["instance_url"] = account.instance_url
            if not credentials.get("client_id"):
                from apps.social_accounts.models import MastodonAppRegistration

                try:
                    reg = MastodonAppRegistration.objects.get(instance_url=account.instance_url)
                    credentials["client_id"] = reg.client_id
                    credentials["client_secret"] = reg.client_secret
                except MastodonAppRegistration.DoesNotExist:
                    pass
        else:
            logger.warning(
                "Mastodon instance URL failed SSRF check for account %s",
                account.id,
            )
    elif platform == "bluesky" and account.instance_url:
        from apps.common.validators import is_safe_url

        if is_safe_url(account.instance_url):
            credentials["pds_url"] = account.instance_url
        else:
            logger.warning(
                "Bluesky PDS URL failed SSRF check for account %s",
                account.id,
            )
    elif platform == "facebook":
        credentials["page_id"] = account.account_platform_id
    elif platform in ("instagram", "instagram_login"):
        credentials["ig_user_id"] = account.account_platform_id
        # The comment poll and the first-comment reconciliation both match our
        # own comments on handle as well as id: Instagram often returns a
        # comment's ``username`` without a ``from`` object, and an unrecognised
        # own comment lands in the inbox as an inbound message from ourselves.
        credentials["account_handle"] = account.account_handle

    return credentials


MAX_RETRIES = 3
MAX_CONCURRENT_PUBLISHES = getattr(settings, "PUBLISHER_MAX_CONCURRENT_PUBLISHES", 10)
MAX_CONCURRENT_POSTS = getattr(settings, "PUBLISHER_MAX_CONCURRENT_POSTS", 4)

# First comments retry on their own schedule, separate from the publish retry:
# the post has already gone out, so there is no double-post risk and no reason
# to hurry. Deliberately bounded — django-background-tasks' own retry default is
# 25 attempts, which is not a thing to do to a live Page.
FIRST_COMMENT_MAX_RETRIES = getattr(settings, "PUBLISHER_FIRST_COMMENT_MAX_RETRIES", 3)
FIRST_COMMENT_RETRY_BACKOFF = [120, 600, 1800]  # 2min, 10min, 30min
FirstCommentStatus = PlatformPost.FirstCommentStatus


def _first_comment_delay(workspace_id) -> int:
    """Seconds to wait after publishing before posting the first comment.

    Resolved per workspace at call time through the normal settings cascade
    (workspace → org → deployment default), so the
    ``publishing.first_comment_delay_seconds`` knob that already exists in the
    settings UI actually takes effect. ``PUBLISHER_FIRST_COMMENT_DELAY`` is
    passed in as the deployment default rather than read afterwards — the
    cascade's own APP_DEFAULTS floor would otherwise answer for every workspace
    without an override row, and the env var would never be consulted.
    """
    default = getattr(settings, "PUBLISHER_FIRST_COMMENT_DELAY", 120)
    try:
        from apps.settings_manager.helpers import get_setting

        value = get_setting(workspace_id, "publishing.first_comment_delay_seconds", default=default)
        return int(value) if value is not None else default
    except Exception:
        logger.warning("Could not resolve first_comment_delay_seconds; using %ss", default, exc_info=True)
        return default


def _provider_and_access_token(account):
    """Build the provider for ``account`` and return a usably-fresh token.

    Shared by the publish path and the first-comment task: the comment fires
    minutes after the publish, which is long enough for a token that was fine
    at publish time to have gone stale.

    Best-effort refresh — on failure we keep the old token and let the API call
    surface the real error rather than masking it with a refresh error.
    """
    provider = get_provider(account.platform, _resolve_publish_credentials(account))

    access_token = account.oauth_access_token
    if account.token_expires_at and account.is_token_expiring_soon and account.oauth_refresh_token:
        try:
            access_token = account.refresh_oauth_token(provider)
            logger.info("Refreshed token for %s", account)
        except Exception:
            logger.exception("Token refresh failed for %s", account)

    return provider, access_token


class PublishEngine:
    """Orchestrates the publishing of scheduled posts."""

    def poll_and_publish(self):
        """Main poll loop - find and publish due platform posts.

        Called every ~15 seconds by the background worker. Groups due
        PlatformPosts by parent Post and publishes each group.
        """
        due_pps = self._get_due_platform_posts()

        # Group by parent post_id
        groups: dict = {}
        for pp in due_pps:
            groups.setdefault(pp.post_id, []).append(pp)

        published_count = 0
        with ThreadPoolExecutor(max_workers=min(len(groups), MAX_CONCURRENT_POSTS) or 1) as executor:
            futures = {
                executor.submit(self._publish_post_group, pps[0].post, pps): post_id for post_id, pps in groups.items()
            }
            for future in as_completed(futures):
                post_id = futures[future]
                try:
                    future.result()
                    published_count += 1
                except Exception:
                    logger.exception("Unexpected error publishing post group %s", post_id)

        # Always process retries, even when no new posts are due
        self._process_retries()

        return published_count

    def _get_due_platform_posts(self):
        """Find PlatformPosts due for publishing, using Coalesce fallback."""
        now = timezone.now()
        return list(
            PlatformPost.objects.filter(
                status=PlatformPost.Status.SCHEDULED,
            )
            .annotate(effective_at=Coalesce("scheduled_at", "post__scheduled_at"))
            .filter(effective_at__lte=now)
            # Never publish a post that has any platform on hold — a client hold
            # parks the whole post out of the publish path even if a sibling
            # platform is already scheduled.
            .exclude(post__platform_posts__status=PlatformPost.Status.ON_HOLD)
            .select_related("post__workspace", "social_account")
            .order_by("effective_at")[:MAX_CONCURRENT_PUBLISHES]
        )

    def _publish_post_group(self, post, due_pps):
        """Publish a group of due PlatformPosts belonging to the same Post.

        Grouping is purely an operational optimization (shared media download,
        shared credential resolution). Status lives on the children — the
        parent Post is not touched.
        """
        # Lock and transition each due child from SCHEDULED → PUBLISHING.
        with transaction.atomic():
            # Lock ALL of this post's platform rows (not just the due scheduled
            # ones) so a concurrent client hold serializes against publishing:
            # request_hold()'s UPDATE on an approved sibling blocks on the locked
            # row until we commit, and we re-check on_hold here under the lock.
            locked = list(
                PlatformPost.objects.select_for_update()
                .filter(post_id=post.id)
                .select_related("social_account", "post__workspace")
            )

            if any(pp.status == PlatformPost.Status.ON_HOLD for pp in locked):
                return

            due_ids = {pp.id for pp in due_pps}
            platform_posts = [pp for pp in locked if pp.id in due_ids and pp.status == PlatformPost.Status.SCHEDULED]

            if not platform_posts:
                return

            PlatformPost.objects.filter(id__in=[pp.id for pp in platform_posts]).update(
                status=PlatformPost.Status.PUBLISHING
            )

        # Publish in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=min(len(platform_posts), 5)) as executor:
            futures = {executor.submit(self._publish_platform_post, pp): pp for pp in platform_posts}
            for future in as_completed(futures):
                pp = futures[future]
                try:
                    results[pp.id] = future.result()
                except Exception as e:
                    results[pp.id] = {"success": False, "error": str(e)}

        # Reflect the aggregate onto Post.published_at so dashboards that
        # display "last published" don't need to query every child.
        self._sync_parent_published_at(post)

        # Schedule first comments for successful publishes (non-blocking)
        for pp in platform_posts:
            pp.refresh_from_db()
            self._maybe_schedule_first_comment(pp)

    def _maybe_schedule_first_comment(self, platform_post):
        """Queue the first comment for a freshly published post, once.

        Called from both publish paths — a post that only succeeds on retry
        used to get no first comment at all. The PENDING guard keeps a second
        call from queueing a duplicate; the POSTED check inside the task is the
        real backstop against double-commenting.
        """
        if platform_post.status != PlatformPost.Status.PUBLISHED:
            return
        if not platform_post.social_account.supports_first_comment():
            return
        if not platform_post.effective_first_comment:
            return
        if platform_post.first_comment_status in (
            PlatformPost.FirstCommentStatus.PENDING,
            PlatformPost.FirstCommentStatus.POSTED,
        ):
            return

        # Enqueue before marking PENDING: @background writes its Task row
        # synchronously, so a crash between the two leaves a task that will
        # still run (and is idempotent) rather than a row stuck on PENDING
        # with nothing queued to clear it.
        delay = _first_comment_delay(platform_post.post.workspace_id)
        _post_first_comment_task(str(platform_post.id), schedule=delay)
        PlatformPost.objects.filter(pk=platform_post.pk).update(
            first_comment_status=PlatformPost.FirstCommentStatus.PENDING
        )

    def _publish_platform_post(self, platform_post):
        """Publish a single PlatformPost to its target platform.

        Returns dict: {"success": bool, "platform_post_id": str, "error": str}
        """
        start_time = time.monotonic()
        account = platform_post.social_account

        # Check rate limits
        rate_state = RateLimitState.objects.filter(
            social_account=account,
            platform=account.platform,
        ).first()

        if rate_state and rate_state.is_rate_limited:
            error_msg = f"Rate limited until {rate_state.window_resets_at}"
            # Our own sentence, not a provider body — but routed through the
            # same parameter so publish_error has exactly one writer.
            self._schedule_retry(platform_post, error_msg, user_message=PUBLISH_RATE_LIMIT_MESSAGE)
            return {"success": False, "error": error_msg}

        try:
            # Get the provider for this platform
            result = self._dispatch_to_provider(platform_post)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if result["success"]:
                platform_post.platform_post_id = result.get("platform_post_id", "")
                response_extra = result.get("response")
                if isinstance(response_extra, dict) and response_extra:
                    platform_post.platform_extra = {
                        **(platform_post.platform_extra or {}),
                        **response_extra,
                    }
                platform_post.status = PlatformPost.Status.PUBLISHED
                platform_post.published_at = timezone.now()
                platform_post.save()

                # A published post leaves the queue: drop the QueueEntry that
                # held this channel's slot so the queue shows only upcoming posts
                # and the slot frees up as a gap. Best-effort and isolated: the
                # publish has already succeeded, so a cleanup failure here must
                # NOT fall through to the `except` below (which would schedule a
                # retry and double-post). The PlatformPost + published_at are kept.
                try:
                    from apps.calendar.models import QueueEntry

                    QueueEntry.objects.filter(
                        post_id=platform_post.post_id,
                        queue__social_account_id=platform_post.social_account_id,
                    ).delete()
                except Exception:
                    logger.warning(
                        "Failed to drop QueueEntry for published PlatformPost %s",
                        platform_post.id,
                        exc_info=True,
                    )

                # Log success
                PublishLog.objects.create(
                    platform_post=platform_post,
                    attempt_number=platform_post.retry_count + 1,
                    status_code=result.get("status_code", 200),
                    response_body=str(result.get("response", ""))[:1000],
                    duration_ms=duration_ms,
                )

                # Update rate limit state
                self._update_rate_limit(account, result)

                return result
            else:
                error_msg = result.get("error", "Unknown publish error")
                duration_ms = int((time.monotonic() - start_time) * 1000)

                PublishLog.objects.create(
                    platform_post=platform_post,
                    attempt_number=platform_post.retry_count + 1,
                    status_code=result.get("status_code"),
                    response_body=str(result.get("response", ""))[:1000],
                    error_message=error_msg,
                    duration_ms=duration_ms,
                )

                # A provider that reports failure in the result dict rather than
                # raising gives us no exception to classify, and result["error"]
                # may well be a response body — so this one always gets the
                # generic sentence. The raw text is in the PublishLog row above.
                self._schedule_retry(platform_post, error_msg, user_message=PUBLISH_GENERIC_MESSAGE)
                return result

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            error_msg = str(e)

            PublishLog.objects.create(
                platform_post=platform_post,
                attempt_number=platform_post.retry_count + 1,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

            user_message = friendly_publish_error(e)
            if getattr(e, "retryable", True):
                self._schedule_retry(platform_post, error_msg, user_message=user_message)
            else:
                self._fail_permanently(platform_post, error_msg, user_message=user_message)
            return {"success": False, "error": error_msg}

    def _dispatch_to_provider(self, platform_post):
        """Dispatch to the appropriate platform provider.

        Resolves credentials, refreshes tokens if needed, builds a
        PublishContent payload, and calls provider.publish_post().
        Returns: {"success": bool, "platform_post_id": str, ...}
        """
        account = platform_post.social_account
        platform = account.platform

        # Refreshes an expiring token first — covers OAuth2 providers *and*
        # session providers like Bluesky, whose accessJwt expires after only a
        # few hours and must be renewed before each publish.
        provider, access_token = _provider_and_access_token(account)

        # Download media from storage (S3/cloud) to temp files for upload
        # and collect public URLs (presigned R2 / absolute) for providers
        # that require fetchable URLs (Instagram, Threads, Google Business, etc.)
        media_files = []
        media_urls = []
        temp_files = []
        attachments = list(platform_post.post.media_attachments.select_related("media_asset").order_by("position"))

        # For video-only platforms (YouTube, TikTok), skip non-video attachments
        video_only = set(provider.supported_post_types) <= {PostType.VIDEO, PostType.SHORT}
        if video_only:
            attachments = [pm for pm in attachments if pm.media_asset.media_type == "video"]

        first_media_type = None
        primary_video_duration = None
        app_url = getattr(settings, "APP_URL", "").rstrip("/")
        try:
            for pm in attachments:
                asset = pm.media_asset
                if not asset.file:
                    continue
                # Track the first media type for post type detection
                if first_media_type is None:
                    first_media_type = asset.media_type

                # Capture the first video's duration so providers can enforce
                # platform max-duration limits (e.g. TikTok max_video_post_duration_sec).
                if primary_video_duration is None and asset.media_type == "video":
                    primary_video_duration = asset.duration or None

                # Collect the public/presigned URL for this asset
                url = asset.file.url
                if url.startswith("/"):
                    # Local storage: make absolute using APP_URL
                    url = f"{app_url}{url}"
                media_urls.append(url)

                # Download to a temp file (works with any storage backend)
                suffix = os.path.splitext(asset.filename)[1] or ".tmp"
                tmp = tempfile.NamedTemporaryFile(  # noqa: SIM115
                    suffix=suffix, delete=False
                )
                temp_files.append(tmp.name)
                with asset.file.open("rb") as src:
                    for chunk in iter(lambda: src.read(8192), b""):
                        tmp.write(chunk)
                tmp.close()
                media_files.append(tmp.name)

            # Merge per-platform extras (e.g. YouTube privacy_status, custom
            # tags, thumbnail) on top of the base extra dict.
            extra = {"tags": platform_post.post.tags or []}
            platform_extra = platform_post.platform_extra or {}
            extra.update(platform_extra)

            # Inject page_id for Facebook from the connected account.
            if platform == "facebook" and "page_id" not in extra:
                extra["page_id"] = account.account_platform_id

            # Inject Instagram user ID for Facebook-login Instagram accounts.
            if platform == "instagram" and "ig_user_id" not in extra:
                extra["ig_user_id"] = account.account_platform_id

            # Inject org author URN for LinkedIn Company Page.
            if platform == "linkedin_company" and "author" not in extra:
                extra["author"] = f"urn:li:organization:{account.account_platform_id}"

            # Pop link_url from extra and set on PublishContent directly
            link_url = extra.pop("link_url", None)

            # Resolve thumbnail_asset_id → temp file path for providers that
            # need to upload a custom thumbnail (YouTube).
            thumb_asset_id = extra.pop("thumbnail_asset_id", None)
            if thumb_asset_id:
                from apps.media_library.models import MediaAsset

                try:
                    thumb_asset = MediaAsset.objects.get(id=thumb_asset_id)
                    if thumb_asset.file:
                        suffix = os.path.splitext(thumb_asset.filename)[1] or ".jpg"
                        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)  # noqa: SIM115
                        temp_files.append(tmp.name)
                        with thumb_asset.file.open("rb") as src:
                            for chunk in iter(lambda: src.read(8192), b""):
                                tmp.write(chunk)
                        tmp.close()
                        extra["thumbnail_file"] = tmp.name
                except MediaAsset.DoesNotExist:
                    logger.warning("Thumbnail asset %s not found", thumb_asset_id)

            # Resolve cover_image_asset_id → temp file (Pinterest video pins)
            cover_asset_id = extra.pop("cover_image_asset_id", None)
            if cover_asset_id:
                try:
                    cover_asset = MediaAsset.objects.get(id=cover_asset_id)
                    if cover_asset.file:
                        suffix = os.path.splitext(cover_asset.filename)[1] or ".jpg"
                        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)  # noqa: SIM115
                        temp_files.append(tmp.name)
                        with cover_asset.file.open("rb") as src:
                            for chunk in iter(lambda: src.read(8192), b""):
                                tmp.write(chunk)
                        tmp.close()
                        extra["cover_image_file"] = tmp.name
                except MediaAsset.DoesNotExist:
                    logger.warning("Cover image asset %s not found", cover_asset_id)

            post_type = self._resolve_post_type(
                platform=platform,
                platform_extra=platform_extra,
                media_count=len(media_files),
                first_media_type=first_media_type,
            )

            content = PublishContent(
                text=platform_post.effective_caption or "",
                title=platform_post.effective_title,
                description=platform_post.effective_caption,
                first_comment=platform_post.effective_first_comment,
                media_files=media_files,
                media_urls=media_urls,
                post_type=post_type,
                extra=extra,
                link_url=link_url,
                video_duration_sec=primary_video_duration,
            )

            logger.info(
                "Publishing to %s (account: %s, type: %s, media: %d)",
                platform,
                account.account_name,
                post_type.value,
                len(media_files),
            )
            result = provider.publish_post(access_token, content)
            return {
                "success": True,
                "platform_post_id": result.platform_post_id,
                "url": result.url,
                "response": result.extra,
            }
        finally:
            # Clean up temp files regardless of success/failure
            for path in temp_files:
                with contextlib.suppress(OSError):
                    os.unlink(path)

    @staticmethod
    def _resolve_post_type(
        platform: str,
        platform_extra: dict,
        media_count: int,
        first_media_type: str | None,
    ) -> PostType:
        """Derive the correct PostType from context.

        Priority:
        1. Explicit hint in platform_extra (validated against PostType enum)
        2. Platform defaults (Pinterest → PIN)
        3. Multi-media on carousel-capable platforms → CAROUSEL
        4. Fallback: video → VIDEO, image → IMAGE, else → TEXT
        """
        # 1. Explicit post_type hint from platform_extra
        hint = platform_extra.get("post_type")
        if hint:
            valid_values = {pt.value for pt in PostType}
            if hint in valid_values:
                return PostType(hint)
            logger.warning("Invalid post_type hint %r, ignoring", hint)

        # 2. Platform defaults
        if platform == "pinterest":
            return PostType.PIN

        # 3. Multi-media → CAROUSEL for Instagram/Threads
        if media_count > 1 and platform in (
            "instagram",
            "instagram_login",
            "threads",
        ):
            return PostType.CAROUSEL

        # 4. Fallback based on first media type
        if first_media_type == "video":
            return PostType.VIDEO
        if first_media_type == "image":
            return PostType.IMAGE
        return PostType.TEXT

    def _fail_permanently(self, platform_post, error_msg, *, user_message, reason="non-retryable"):
        """Mark a post FAILED with no further retries.

        ``error_msg`` is the diagnostic and stays in the log line below and in
        the PublishLog row the caller already wrote. ``publish_error`` holds
        what the composer and the calendar render, so it must never carry a raw
        provider response body — which is why ``user_message`` has no default:
        every caller has to decide, and a forgotten one is a leak.
        """
        platform_post.status = PlatformPost.Status.FAILED
        platform_post.publish_error = (user_message or PUBLISH_GENERIC_MESSAGE)[:2000]
        platform_post.save()
        logger.warning(
            "PlatformPost %s failed (%s): %s",
            platform_post.id,
            reason,
            error_msg,
        )

    def _schedule_retry(self, platform_post, error_msg, *, user_message):
        """Schedule a retry with exponential backoff."""
        if platform_post.retry_count >= MAX_RETRIES:
            # Not ``user_message``: everything that reaches this branch is a
            # retryable failure whose copy promises "We'll retry shortly", and
            # the post is about to be marked permanently failed.
            self._fail_permanently(
                platform_post,
                error_msg,
                user_message=PUBLISH_EXHAUSTED_MESSAGE,
                reason=f"after {MAX_RETRIES} retries",
            )
            return

        backoff_seconds = RETRY_BACKOFF[min(platform_post.retry_count, len(RETRY_BACKOFF) - 1)]
        platform_post.retry_count += 1
        platform_post.next_retry_at = timezone.now() + timedelta(seconds=backoff_seconds)
        # Drop back to SCHEDULED so the next _process_retries tick picks it up
        # once next_retry_at passes.
        platform_post.status = PlatformPost.Status.SCHEDULED
        platform_post.publish_error = (user_message or PUBLISH_GENERIC_MESSAGE)[:2000]
        platform_post.save()

        logger.info(
            "Scheduled retry %d for PlatformPost %s in %d seconds",
            platform_post.retry_count,
            platform_post.id,
            backoff_seconds,
        )

    def _process_retries(self):
        """Process platform posts that are due for retry."""
        now = timezone.now()
        # Mirror the primary due-query's hold guard: a retrying child must not
        # publish while any sibling is on_hold (the exclude covers the query
        # window; the per-row re-check below closes a hold placed after it).
        retry_posts = (
            PlatformPost.objects.filter(
                status=PlatformPost.Status.SCHEDULED,
                retry_count__gt=0,
                retry_count__lte=MAX_RETRIES,
                next_retry_at__lte=now,
            )
            .exclude(post__platform_posts__status=PlatformPost.Status.ON_HOLD)
            .select_related("social_account", "post")
        )

        for pp in retry_posts:
            if pp.post.platform_posts.filter(status=PlatformPost.Status.ON_HOLD).exists():
                continue
            try:
                pp.status = PlatformPost.Status.PUBLISHING
                pp.save(update_fields=["status", "updated_at"])
                result = self._publish_platform_post(pp)
                if result.get("success"):
                    self._sync_parent_published_at(pp.post)
                    self._maybe_schedule_first_comment(pp)
            except Exception:
                logger.exception("Error retrying PlatformPost %s", pp.id)

    def _update_rate_limit(self, account, result):
        """Update rate limit state from API response headers."""
        remaining = result.get("rate_limit_remaining")
        resets_at = result.get("rate_limit_resets_at")

        if remaining is not None:
            RateLimitState.objects.update_or_create(
                social_account=account,
                platform=account.platform,
                defaults={
                    "requests_remaining": remaining,
                    "window_resets_at": resets_at,
                },
            )

    def _sync_parent_published_at(self, post):
        """Reflect the latest child published_at onto the parent Post.

        Status itself lives entirely on PlatformPost now (Post.status is a
        derived property), but we still maintain ``Post.published_at`` so
        dashboards/lists that show "last published" don't have to aggregate
        children at read time.
        """
        latest = max(
            (pp.published_at for pp in post.platform_posts.all() if pp.published_at),
            default=None,
        )
        if latest and post.published_at != latest:
            post.published_at = latest
            post.save(update_fields=["published_at", "updated_at"])


def _is_ambiguous_submission_failure(exc) -> bool:
    """True when the comment may or may not have been created on the platform.

    A clean 4xx is the platform refusing the request outright, so nothing was
    created and retrying is safe. A timeout, a dropped connection, or a 5xx
    leaves it unknown — ``FacebookProvider.publish_comment`` already declines to
    retry a second target for this reason, and re-queueing the whole task would
    reintroduce exactly the double-comment it avoids.
    """
    if isinstance(exc, RateLimitError):
        # 429 is a rejection before the write, not an ambiguous outcome.
        return False
    status = getattr(exc, "status_code", None)
    return status is None or status >= 500


def _is_retryable_first_comment_failure(exc) -> bool:
    """Whether re-sending this exact comment could plausibly land differently.

    A provider that already called the error permanent is believed. Past that: a
    rate limit is a "not now", and a 5xx or a transport error is an unknown
    outcome (the caller gates those on reconciliation). A clean 4xx is the
    platform refusing *this request*, and re-sending it unchanged earns the same
    refusal — Instagram made that concrete by answering a comment POST carrying
    an unsupported ``fields`` param with a 400 while creating the comment
    anyway, so three retries left four comments on a live account.

    401 is the exception: ``_provider_and_access_token`` refreshes an expiring
    token between attempts, so the next attempt really is a different request.
    403 is not — Meta uses it for missing scopes and revoked grants, which need
    a reconnect rather than a backoff.
    """
    if not getattr(exc, "retryable", True):
        return False
    if isinstance(exc, RateLimitError):
        return True
    status = getattr(exc, "status_code", None)
    if status is None or status >= 500:
        return True
    return status == 401


def _can_reconcile_comments(provider) -> bool:
    """Whether this provider can check for an already-posted comment.

    The base implementation raises, so identity against it is what distinguishes
    a real lookup from the no-op default — same test as ``_supports_webhooks``.
    """
    from providers.base import SocialProvider

    implementation = getattr(type(provider), "find_own_comment", None)
    return implementation is not None and implementation is not SocialProvider.find_own_comment


def _mark_first_comment_posted(platform_post, comment_id: str) -> None:
    """Record a first comment that exists on the platform.

    Nothing here may raise: the comment is already live, and an escaping
    exception would let django-background-tasks re-run the task (its default is
    25 attempts) against a row still marked PENDING, posting a second one.
    """
    try:
        PlatformPost.objects.filter(pk=platform_post.pk).update(
            first_comment_status=FirstCommentStatus.POSTED,
            first_comment_id=str(comment_id or "")[:255],
            first_comment_error="",
            first_comment_posted_at=timezone.now(),
        )
    except Exception:
        logger.exception(
            "First comment for PlatformPost %s is POSTED on the platform but could not be recorded. "
            "The row still reads pending; do not re-run this task or it will comment twice.",
            platform_post.id,
        )


def _record_first_comment_failure(
    platform_post,
    error_msg: str,
    *,
    retryable: bool,
    user_message: str = "",
    retry_after: int | None = None,
    unexpected: bool = False,
):
    """Persist a first-comment failure, and re-queue it when that can help.

    Every exit records state. The old version logged and returned, so a comment
    that 4xx'd left the post looking completely successful — the failure was
    only recoverable from worker logs.

    ``error_msg`` is the diagnostic: raw provider text, logged, never stored.
    ``user_message`` is what the composer and the calendar render, so it must
    stay free of response bodies — the Graph payload that motivated this split
    reached the UI as a wall of OAuthException and fbtrace noise. The log line
    below is the only place the raw text survives, so it always emits.
    """
    stored = (user_message or FIRST_COMMENT_GENERIC_MESSAGE)[:2000]
    exhausted = platform_post.first_comment_retry_count >= FIRST_COMMENT_MAX_RETRIES

    if not retryable or exhausted:
        reason = "non-retryable" if not retryable else f"after {FIRST_COMMENT_MAX_RETRIES} retries"
        # An unexpected exception is a bug in this code path, not a platform
        # rejection — log the stack, or it is indistinguishable from a Graph 4xx.
        log = logger.exception if unexpected else logger.warning
        log(
            "First comment for PlatformPost %s failed (%s): %s",
            platform_post.id,
            reason,
            error_msg,
        )
        PlatformPost.objects.filter(pk=platform_post.pk).update(
            first_comment_status=FirstCommentStatus.FAILED,
            first_comment_error=stored,
        )
        return

    index = min(platform_post.first_comment_retry_count, len(FIRST_COMMENT_RETRY_BACKOFF) - 1)
    backoff = retry_after or FIRST_COMMENT_RETRY_BACKOFF[index]

    if unexpected:
        logger.exception("Unexpected error posting first comment for PlatformPost %s", platform_post.id)

    # F() so two tasks racing on the same row cannot both write the same count
    # and slip past FIRST_COMMENT_MAX_RETRIES.
    PlatformPost.objects.filter(pk=platform_post.pk).update(
        first_comment_status=FirstCommentStatus.PENDING,
        first_comment_error=stored,
        first_comment_retry_count=F("first_comment_retry_count") + 1,
    )
    _post_first_comment_task(str(platform_post.id), schedule=backoff)
    logger.info(
        "Retrying first comment for PlatformPost %s in %ss: %s",
        platform_post.id,
        backoff,
        error_msg,
    )


@background(schedule=0)
def _post_first_comment_task(platform_post_id):
    """Post the first comment as a background task (avoids blocking the publisher thread)."""
    try:
        platform_post = PlatformPost.objects.select_related("social_account__workspace__organization").get(
            pk=platform_post_id
        )
    except PlatformPost.DoesNotExist:
        logger.warning("PlatformPost %s not found for first comment.", platform_post_id)
        return

    # Idempotency: two publish paths and a retry queue can each land here for
    # the same row. Commenting twice on a live post is not recoverable.
    if platform_post.first_comment_status == FirstCommentStatus.POSTED:
        logger.info("First comment for PlatformPost %s already posted; skipping.", platform_post.id)
        return

    comment_text = platform_post.effective_first_comment
    if not comment_text:
        return

    if not platform_post.platform_post_id:
        _record_first_comment_failure(
            platform_post,
            "No platform post id recorded; nothing to comment on.",
            retryable=False,
            user_message="The post's id on the platform wasn't recorded, so the first comment couldn't be added.",
        )
        return

    account = platform_post.social_account
    try:
        provider, access_token = _provider_and_access_token(account)
    except Exception as exc:
        _record_first_comment_failure(
            platform_post,
            str(exc),
            retryable=getattr(exc, "retryable", True),
            user_message=friendly_first_comment_error(exc),
            unexpected=not isinstance(exc, ProviderError),
        )
        return

    # This is a retry, so a previous attempt may have created the comment before
    # failing (timeout, 5xx). Check before posting a second one.
    if platform_post.first_comment_retry_count:
        try:
            existing = provider.find_own_comment(access_token, platform_post.platform_post_id, comment_text)
        except NotImplementedError:
            existing = None
        except Exception as exc:
            # Whether the comment landed is unknown, so this attempt stops
            # without posting — but it must still be recorded and re-queued, or
            # the row sits PENDING forever with no task behind it and the post
            # reads as fully successful. The retry budget bounds it: a lookup
            # that never recovers ends FAILED and visible, never duplicated.
            logger.exception(
                "Could not check for an existing first comment on PlatformPost %s; skipping this attempt "
                "rather than risking a duplicate.",
                platform_post.id,
            )
            _record_first_comment_failure(
                platform_post,
                f"Could not check for an existing first comment: {exc}",
                retryable=True,
                user_message=friendly_first_comment_error(exc),
            )
            return
        if existing:
            logger.info("First comment for PlatformPost %s was already posted as %s", platform_post.id, existing)
            _mark_first_comment_posted(platform_post, existing)
            return

    try:
        result = provider.publish_comment(
            access_token=access_token,
            post_id=platform_post.platform_post_id,
            text=comment_text,
        )
    except NotImplementedError:
        logger.info("First comment not supported for %s", account.platform)
        return
    except Exception as exc:
        # An ambiguous failure is only safe to retry when we can first check
        # whether the comment landed; otherwise stop, because a duplicate
        # comment on a live post cannot be taken back.
        ambiguous = _is_ambiguous_submission_failure(exc)
        retryable = _is_retryable_first_comment_failure(exc)
        if ambiguous and not _can_reconcile_comments(provider):
            retryable = False
        _record_first_comment_failure(
            platform_post,
            str(exc),
            retryable=retryable,
            user_message=friendly_first_comment_error(exc),
            # RateLimitError is a sibling of APIError, not a subclass, so branch
            # on the attributes rather than on the exception type.
            retry_after=getattr(exc, "retry_after", None),
            # Provider errors are self-explanatory; anything else is a bug here
            # and needs the stack to be diagnosable.
            unexpected=not isinstance(exc, ProviderError),
        )
        return

    _mark_first_comment_posted(platform_post, getattr(result, "platform_comment_id", ""))
    logger.info("Posted first comment for PlatformPost %s", platform_post.id)
