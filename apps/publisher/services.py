"""Publisher service helpers usable from views, management commands, and MCP tools."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.composer.models import PlatformPost


class PublishStateError(Exception):
    """Raised when a PlatformPost cannot transition to the requested state."""


_PUBLISHABLE_FROM = {
    PlatformPost.Status.DRAFT,
    PlatformPost.Status.SCHEDULED,
    PlatformPost.Status.APPROVED,
    PlatformPost.Status.CHANGES_REQUESTED,
    PlatformPost.Status.FAILED,
}


def publish_now(platform_post: PlatformPost) -> PlatformPost:
    """Move a PlatformPost to SCHEDULED with scheduled_at=now so the engine publishes it next tick.

    Does not block on the publish itself; the background worker picks it up via
    `PublishEngine.poll_and_publish()`.
    """
    with transaction.atomic():
        pp = PlatformPost.objects.select_for_update().get(pk=platform_post.pk)
        if pp.status not in _PUBLISHABLE_FROM:
            raise PublishStateError(f"PlatformPost {pp.id} is in status '{pp.status}' and cannot be published now.")
        pp.scheduled_at = timezone.now()
        if pp.status != PlatformPost.Status.SCHEDULED:
            pp.transition_to(PlatformPost.Status.SCHEDULED)
        pp.save(update_fields=["scheduled_at", "status", "updated_at"])
    return pp


def retry_failed(platform_post: PlatformPost) -> PlatformPost:
    """Re-queue a FAILED PlatformPost for an immediate retry."""
    with transaction.atomic():
        pp = PlatformPost.objects.select_for_update().get(pk=platform_post.pk)
        if pp.status != PlatformPost.Status.FAILED:
            raise PublishStateError(f"PlatformPost {pp.id} is in status '{pp.status}', expected 'failed'.")
        pp.transition_to(PlatformPost.Status.SCHEDULED)
        pp.scheduled_at = timezone.now()
        pp.retry_count = 0
        pp.next_retry_at = None
        pp.publish_error = ""
        pp.save(update_fields=["scheduled_at", "status", "retry_count", "next_retry_at", "publish_error", "updated_at"])
    return pp
