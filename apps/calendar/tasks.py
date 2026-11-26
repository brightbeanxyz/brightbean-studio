"""Background tasks for the Content Calendar (F-2.3)."""

import copy
import logging
import zoneinfo
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from apps.composer.models import PlatformPost, Post, PostMedia
from apps.composer.services import platform_post_media_types, post_media_types, publish_blocker

from .models import RecurrenceRule

logger = logging.getLogger(__name__)

LOOKAHEAD_DAYS = 90

# Source rows whose future occurrences are still meant to publish on their own.
# A row the team pulled back to draft, put on hold, or sent for review or
# rejected has not committed its recurrences either, so those clone as drafts.
_RECURRING_COMMITTED_STATUSES = frozenset(
    {
        PlatformPost.Status.SCHEDULED,
        PlatformPost.Status.PUBLISHING,
        PlatformPost.Status.PUBLISHED,
        PlatformPost.Status.FAILED,
    }
)


def generate_recurring_posts():
    """Generate individual Post records from active RecurrenceRules.

    Runs daily. For each active rule, computes recurrence dates from the
    source post's scheduled_at up to 90 days ahead. Creates clones of the
    source post for each date not yet generated.
    """
    rules = RecurrenceRule.objects.filter(is_active=True).select_related("post")
    now = timezone.now()
    generated_total = 0

    for rule in rules:
        source = rule.post
        if not source.scheduled_at:
            continue

        # Recurrence dates and times are computed in the post's workspace
        # timezone so the wall-clock time is preserved across DST boundaries
        # (a 09:00-local series stays at 09:00 local, not drifting by the DST
        # offset). ``scheduled_at`` is stored as UTC, so convert it back first.
        ws_tz = zoneinfo.ZoneInfo(source.workspace.effective_timezone or "UTC")
        local_start = source.scheduled_at.astimezone(ws_tz)
        base_date = local_start.date()
        base_time = local_start.time()
        today_local = now.astimezone(ws_tz).date()

        # Bound the lookahead horizon in the workspace's local calendar so it
        # lands on the same local day for every timezone, not the UTC date.
        cutoff = today_local + timedelta(days=LOOKAHEAD_DAYS)
        end = rule.end_date or cutoff
        if end > cutoff:
            end = cutoff

        dates = _compute_recurrence_dates(base_date, rule.frequency, rule.interval, end)

        # Filter out dates already generated (posts with same source caption).
        # Extract dates in the workspace zone so they line up with the ws-local
        # recurrence dates above rather than UTC calendar days.
        with timezone.override(ws_tz):
            existing_dates = set(
                Post.objects.filter(
                    workspace=source.workspace,
                    caption=source.caption,
                    scheduled_at__date__in=dates,
                )
                .exclude(id=source.id)
                .values_list("scheduled_at__date", flat=True)
            )

        # Every clone carries the source's media, so one answer serves each
        # recurrence date and every platform of this rule without its own media.
        media_types = post_media_types(source)

        for d in dates:
            if d in existing_dates or d <= today_local:
                continue

            scheduled_dt = datetime.combine(d, base_time).replace(tzinfo=ws_tz)

            # Clone the post
            new_post = Post.objects.create(
                workspace=source.workspace,
                author=source.author,
                caption=source.caption,
                first_comment=source.first_comment,
                internal_notes=source.internal_notes,
                tags=source.tags,
                category=source.category,
                scheduled_at=scheduled_dt,
            )

            # Clone platform posts in bulk, preserving per-platform offsets
            source_pps = list(source.platform_posts.select_related("social_account"))
            if source_pps:
                new_pps = []
                for pp in source_pps:
                    # The source was checked when it was scheduled, but its media
                    # or board can have gone since. A clone that can only fail is
                    # left as a draft at its date: still on the calendar to fix,
                    # but not handed to the publisher.
                    blocked = publish_blocker(
                        pp.social_account,
                        # The clone carries the source row's own media, if it has any.
                        media_types=platform_post_media_types(pp, base_media_types=media_types),
                        platform_extra=pp.platform_extra,
                    )
                    if blocked:
                        logger.warning(
                            "Recurrence of post %s on %s left as a draft for %s: %s",
                            source.id,
                            d,
                            pp.social_account_id,
                            blocked,
                        )
                    # Preserve the offset between source PP's scheduled_at and
                    # source post's scheduled_at, so per-platform time deltas
                    # carry into each recurrence.
                    pp_scheduled = None
                    if pp.scheduled_at and source.scheduled_at:
                        delta = pp.scheduled_at - source.scheduled_at
                        pp_scheduled = scheduled_dt + delta
                    new_pps.append(
                        PlatformPost(
                            post=new_post,
                            social_account=pp.social_account,
                            platform_specific_caption=pp.platform_specific_caption,
                            platform_specific_first_comment=pp.platform_specific_first_comment,
                            platform_specific_media=pp.platform_specific_media,
                            # Carry per-platform settings (e.g. TikTok privacy level,
                            # comment/duet/stitch toggles, disclosure flags) into each
                            # recurrence. Without this the publisher falls back to
                            # provider defaults and loses the creator's choices.
                            platform_extra=copy.deepcopy(pp.platform_extra) if pp.platform_extra else {},
                            scheduled_at=pp_scheduled,
                            status=(
                                "scheduled" if pp.status in _RECURRING_COMMITTED_STATUSES and not blocked else "draft"
                            ),
                        )
                    )
                PlatformPost.objects.bulk_create(new_pps)

                # Sync Post.scheduled_at to min of children.
                from apps.composer.services import sync_post_scheduled_at

                sync_post_scheduled_at(new_post)

            # Clone media attachments in bulk
            source_media = list(source.media_attachments.all())
            if source_media:
                PostMedia.objects.bulk_create(
                    [
                        PostMedia(
                            post=new_post,
                            media_asset=pm.media_asset,
                            position=pm.position,
                            alt_text=pm.alt_text,
                            platform_overrides=pm.platform_overrides,
                        )
                        for pm in source_media
                    ]
                )

            generated_total += 1

        rule.last_generated_at = now
        rule.save(update_fields=["last_generated_at"])

    logger.info("Generated %d recurring posts.", generated_total)
    return generated_total


def _compute_recurrence_dates(base_date, frequency, interval, end_date):
    """Compute a list of recurrence dates from base_date to end_date."""
    dates = []
    current = base_date

    max_recurrences = LOOKAHEAD_DAYS * 2  # Safety limit
    for _ in range(max_recurrences):
        if frequency == "daily":
            current = current + timedelta(days=interval)
        elif frequency == "weekly":
            current = current + timedelta(weeks=interval)
        elif frequency == "monthly":
            current = current + relativedelta(months=interval)
        else:
            break

        if current > end_date:
            break

        dates.append(current)

    return dates
