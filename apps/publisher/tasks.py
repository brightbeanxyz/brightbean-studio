"""Background tasks for the publishing engine."""

import logging

from background_task import background

logger = logging.getLogger(__name__)


@background(schedule=0)
def run_publish_cycle():
    """Poll for due posts and publish them.

    Registered as a recurring task (every 15s) so that
    ``python manage.py process_tasks`` handles publishing
    without needing a separate ``run_publisher`` process.
    """
    from apps.publisher.engine import PublishEngine

    engine = PublishEngine()
    published = engine.poll_and_publish()
    if published:
        logger.info("Publish cycle completed - %d post(s) published", published)


# --- async publish verification ---------------------------------------------
# TikTok (and any future provider with verifies_publish_async=True) validates
# the file after accepting the upload; the post must not stay "published" in
# our DB when the platform's processing rejected it.

VERIFY_DELAY_SECONDS = 30
VERIFY_MAX_ATTEMPTS = 10  # 10 x 30s = a 5-minute verification window

# User-facing hints for the fail reasons we can explain; publish_error must
# stay human-readable (raw codes go to the PublishLog row instead).
ASYNC_FAIL_REASON_HINTS = {
    "frame_rate_check_failed": (
        "TikTok rejected the video during processing: its frame rate must be between 23 and 60 fps."
    ),
    "picture_size_check_failed": (
        "TikTok rejected the video during processing: the resolution is too low or the dimensions are unsupported."
    ),
    "duration_check_failed": (
        "TikTok rejected the video during processing: its duration is outside the allowed range."
    ),
    "file_format_check_failed": (
        "TikTok rejected the video during processing: unsupported file format (use an H.264 MP4)."
    ),
    "video_pull_failed": "TikTok could not download the video file.",
}


@background(schedule=VERIFY_DELAY_SECONDS)
def verify_platform_post_publish(platform_post_id, attempt=1):
    """Re-check a published post against the platform's processing status."""
    from apps.composer.models import PlatformPost
    from apps.publisher.models import PublishLog

    platform_post = PlatformPost.objects.filter(id=platform_post_id).first()
    if not platform_post or platform_post.status != PlatformPost.Status.PUBLISHED:
        return

    from apps.publisher.engine import _provider_and_access_token

    try:
        provider, access_token = _provider_and_access_token(platform_post.social_account)
        verdict = provider.verify_publish(access_token, platform_post.platform_post_id)
    except Exception:
        logger.warning(
            "Publish verification errored for PlatformPost %s (attempt %d)",
            platform_post_id,
            attempt,
            exc_info=True,
        )
        verdict = {"state": "processing", "reason": ""}

    state = (verdict or {}).get("state", "complete")

    if state == "failed":
        reason = (verdict or {}).get("reason") or "unknown"
        platform_post.status = PlatformPost.Status.FAILED
        platform_post.publish_error = ASYNC_FAIL_REASON_HINTS.get(
            reason,
            f"The platform rejected the post during processing ({reason}).",
        )[:2000]
        platform_post.save()
        PublishLog.objects.create(
            platform_post=platform_post,
            attempt_number=platform_post.retry_count + 1,
            error_message=f"async processing failed: {reason}",
        )
        logger.warning(
            "PlatformPost %s failed platform-side processing: %s", platform_post.id, reason
        )
        return

    if state == "processing":
        if attempt < VERIFY_MAX_ATTEMPTS:
            verify_platform_post_publish(str(platform_post.id), attempt + 1)
        else:
            logger.warning(
                "Gave up verifying PlatformPost %s after %d attempts; leaving as published",
                platform_post.id,
                attempt,
            )
    # state == "complete": nothing to do — the published status is confirmed.
