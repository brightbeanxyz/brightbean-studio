"""Publishing Engine - background worker logic (F-2.4).

This module implements the core publish loop:
1. Poll for posts where scheduled_at <= now() and status = 'scheduled'.
2. Transition to 'publishing'.
3. Dispatch platform posts in parallel.
4. Handle retries with exponential backoff.
5. Post first comment after 2-minute delay.
6. Update statuses and log results.
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
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.credentials.models import PlatformCredential
from providers import get_provider
from providers.types import AuthType, PostType, PublishContent

from .models import PublishLog, RateLimitState

logger = logging.getLogger(__name__)

# Retry backoff schedule (in seconds)
RETRY_BACKOFF = [60, 300, 1800]  # 1min, 5min, 30min
MAX_RETRIES = 3
FIRST_COMMENT_DELAY = getattr(settings, "PUBLISHER_FIRST_COMMENT_DELAY", 120)
MAX_CONCURRENT_PUBLISHES = getattr(settings, "PUBLISHER_MAX_CONCURRENT_PUBLISHES", 10)
MAX_CONCURRENT_POSTS = getattr(settings, "PUBLISHER_MAX_CONCURRENT_POSTS", 4)


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
                executor.submit(self._publish_post_group, pps[0].post, pps): post_id
                for post_id, pps in groups.items()
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
                post__status__in=[Post.Status.SCHEDULED, Post.Status.PUBLISHING],
                publish_status=PlatformPost.PublishStatus.PENDING,
            )
            .annotate(effective_at=Coalesce("scheduled_at", "post__scheduled_at"))
            .filter(effective_at__lte=now)
            .select_related("post__workspace", "social_account")
            .order_by("effective_at")[:MAX_CONCURRENT_PUBLISHES]
        )

    def _publish_post_group(self, post, due_pps):
        """Publish a group of due PlatformPosts belonging to the same Post."""
        # Transition post and platform posts atomically to prevent duplicate publishing
        with transaction.atomic():
            post = Post.objects.select_for_update().get(id=post.id)
            if post.status not in (Post.Status.SCHEDULED, Post.Status.PUBLISHING):
                return  # Already terminal
            if post.status == Post.Status.SCHEDULED:
                post.transition_to(Post.Status.PUBLISHING)
                post.save()

            # Re-filter due PPs under lock to avoid double-publishing
            platform_posts = list(
                post.platform_posts.select_for_update()
                .filter(
                    id__in=[pp.id for pp in due_pps],
                    publish_status=PlatformPost.PublishStatus.PENDING,
                )
                .select_related("social_account")
            )

            if not platform_posts:
                return

            PlatformPost.objects.filter(
                id__in=[pp.id for pp in platform_posts]
            ).update(publish_status=PlatformPost.PublishStatus.PUBLISHING)

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

        # Aggregate parent status based on *all* children (not just the group).
        self._update_parent_post_status(post)

        # Schedule first comments for successful publishes (non-blocking)
        for pp in platform_posts:
            pp.refresh_from_db()
            if pp.publish_status == PlatformPost.PublishStatus.PUBLISHED:
                comment_text = pp.effective_first_comment
                if comment_text:
                    _post_first_comment_task(str(pp.id), schedule=FIRST_COMMENT_DELAY)

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
            self._schedule_retry(platform_post, error_msg)
            return {"success": False, "error": error_msg}

        try:
            # Get the provider for this platform
            result = self._dispatch_to_provider(platform_post)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if result["success"]:
                platform_post.platform_post_id = result.get("platform_post_id", "")
                platform_post.publish_status = PlatformPost.PublishStatus.PUBLISHED
                platform_post.published_at = timezone.now()
                platform_post.save()

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

                self._schedule_retry(platform_post, error_msg)
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

            self._schedule_retry(platform_post, error_msg)
            return {"success": False, "error": error_msg}

    def _dispatch_to_provider(self, platform_post):
        """Dispatch to the appropriate platform provider.

        Resolves credentials, refreshes tokens if needed, builds a
        PublishContent payload, and calls provider.publish_post().
        Returns: {"success": bool, "platform_post_id": str, ...}
        """
        account = platform_post.social_account
        platform = account.platform

        # Resolve app credentials (org-specific first, then env fallback)
        try:
            cred = PlatformCredential.objects.for_org(
                account.workspace.organization_id
            ).get(platform=platform, is_configured=True)
            credentials = dict(cred.credentials)
        except PlatformCredential.DoesNotExist:
            env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
            credentials = dict(env_creds.get(platform, {}))

        # Inject per-account instance URL for federated providers
        if platform == "mastodon" and account.instance_url:
            from apps.common.validators import is_safe_url
            if is_safe_url(account.instance_url):
                credentials["instance_url"] = account.instance_url
                # Look up per-instance OAuth app registration if no org creds
                if not credentials.get("client_id"):
                    from apps.social_accounts.models import MastodonAppRegistration
                    try:
                        reg = MastodonAppRegistration.objects.get(
                            instance_url=account.instance_url
                        )
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
            credentials["pds_url"] = account.instance_url

        provider = get_provider(platform, credentials)

        # Refresh token if expired or expiring soon (OAuth2 providers only)
        access_token = account.oauth_access_token
        if (
            account.token_expires_at
            and account.is_token_expiring_soon
            and provider.auth_type == AuthType.OAUTH2
        ):
            try:
                new_tokens = provider.refresh_token(account.oauth_refresh_token)
                account.oauth_access_token = new_tokens.access_token
                if new_tokens.refresh_token:
                    account.oauth_refresh_token = new_tokens.refresh_token
                if new_tokens.expires_in:
                    account.token_expires_at = timezone.now() + timedelta(
                        seconds=new_tokens.expires_in
                    )
                account.connection_status = account.ConnectionStatus.CONNECTED
                account.save(
                    update_fields=[
                        "oauth_access_token",
                        "oauth_refresh_token",
                        "token_expires_at",
                        "connection_status",
                        "updated_at",
                    ]
                )
                access_token = new_tokens.access_token
                logger.info("Refreshed token for %s", account)
            except Exception:
                logger.exception("Token refresh failed for %s", account)

        # Download media from storage (S3/cloud) to temp files for upload
        # and collect public URLs (presigned R2 / absolute) for providers
        # that require fetchable URLs (Instagram, Threads, Google Business, etc.)
        media_files = []
        media_urls = []
        temp_files = []
        attachments = list(
            platform_post.post.media_attachments.select_related("media_asset")
            .order_by("position")
        )

        # For video-only platforms (YouTube, TikTok), skip non-video attachments
        video_only = set(provider.supported_post_types) <= {PostType.VIDEO, PostType.SHORT}
        if video_only:
            attachments = [pm for pm in attachments if pm.media_asset.media_type == "video"]

        first_media_type = None
        app_url = getattr(settings, "APP_URL", "").rstrip("/")
        try:
            for pm in attachments:
                asset = pm.media_asset
                if not asset.file:
                    continue
                # Track the first media type for post type detection
                if first_media_type is None:
                    first_media_type = asset.media_type

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
            "instagram", "instagram_personal", "threads",
        ):
            return PostType.CAROUSEL

        # 4. Fallback based on first media type
        if first_media_type == "video":
            return PostType.VIDEO
        if first_media_type == "image":
            return PostType.IMAGE
        return PostType.TEXT

    def _schedule_retry(self, platform_post, error_msg):
        """Schedule a retry with exponential backoff."""
        if platform_post.retry_count >= MAX_RETRIES:
            platform_post.publish_status = PlatformPost.PublishStatus.FAILED
            platform_post.publish_error = error_msg
            platform_post.save()
            logger.warning(
                "PlatformPost %s failed after %d retries: %s",
                platform_post.id,
                MAX_RETRIES,
                error_msg,
            )
            return

        backoff_seconds = RETRY_BACKOFF[min(platform_post.retry_count, len(RETRY_BACKOFF) - 1)]
        platform_post.retry_count += 1
        platform_post.next_retry_at = timezone.now() + timedelta(seconds=backoff_seconds)
        platform_post.publish_status = PlatformPost.PublishStatus.PENDING
        platform_post.publish_error = error_msg
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
        retry_posts = PlatformPost.objects.filter(
            publish_status=PlatformPost.PublishStatus.PENDING,
            retry_count__gt=0,
            retry_count__lte=MAX_RETRIES,
            next_retry_at__lte=now,
        ).select_related("social_account", "post")

        for pp in retry_posts:
            try:
                result = self._publish_platform_post(pp)
                if result.get("success"):
                    # Check if all platform posts for the parent are now done
                    self._update_parent_post_status(pp.post)
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

    def _update_parent_post_status(self, post):
        """Update parent Post status based on all PlatformPost statuses.

        Waits for pending/publishing siblings - the post only transitions to a
        terminal state once every child has resolved to published or failed.
        """
        platform_posts = post.platform_posts.all()
        statuses = set(platform_posts.values_list("publish_status", flat=True))

        # Any child still pending or publishing - stay in PUBLISHING, wait.
        if "pending" in statuses or "publishing" in statuses:
            if post.status != Post.Status.PUBLISHING:
                post.status = Post.Status.PUBLISHING
                post.save()
            return

        if statuses == {"published"}:
            post.status = Post.Status.PUBLISHED
            post.published_at = timezone.now()
        elif statuses == {"failed"}:
            post.status = Post.Status.FAILED
        elif "published" in statuses and "failed" in statuses:
            post.status = Post.Status.PARTIALLY_PUBLISHED
            if not post.published_at:
                post.published_at = timezone.now()

        post.save()


@background(schedule=0)
def _post_first_comment_task(platform_post_id):
    """Post the first comment as a background task (avoids blocking the publisher thread)."""
    try:
        platform_post = PlatformPost.objects.select_related(
            "social_account__workspace__organization"
        ).get(pk=platform_post_id)
    except PlatformPost.DoesNotExist:
        logger.warning("PlatformPost %s not found for first comment.", platform_post_id)
        return

    comment_text = platform_post.effective_first_comment
    if not comment_text:
        return

    account = platform_post.social_account
    try:
        try:
            cred = PlatformCredential.objects.for_org(
                account.workspace.organization_id
            ).get(platform=account.platform, is_configured=True)
            credentials = cred.credentials
        except PlatformCredential.DoesNotExist:
            env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
            credentials = env_creds.get(account.platform, {})

        provider = get_provider(account.platform, credentials)
        provider.publish_comment(
            access_token=account.oauth_access_token,
            post_id=platform_post.platform_post_id,
            text=comment_text,
        )
        logger.info("Posted first comment for PlatformPost %s", platform_post.id)
    except NotImplementedError:
        logger.info("First comment not supported for %s", account.platform)
    except Exception:
        logger.exception("Failed to post first comment for PlatformPost %s", platform_post.id)
