"""Queue scheduling services for the Content Calendar (F-2.3)."""

import zoneinfo
from datetime import datetime, time, timedelta

from django.db import models
from django.utils import timezone

from .models import PostingSlot, Queue, QueueEntry

# Default posting slots created automatically for newly connected channels.
DEFAULT_POSTING_SLOTS = {
    0: [time(9, 24), time(10, 10), time(11, 26), time(12, 42)],  # Monday
    1: [time(9, 55), time(10, 41), time(11, 57), time(12, 13)],  # Tuesday
    2: [time(9, 30), time(10, 17), time(11, 32), time(12, 41)],  # Wednesday
    3: [time(9, 38), time(10, 52)],  # Thursday
}


def create_default_queue_and_slots(social_account):
    """Create a default Queue and PostingSlots for a newly connected social account.

    Skips creation if the account already has a queue (e.g. on re-connection).
    """
    if Queue.objects.filter(social_account=social_account).exists():
        return None

    queue = Queue.objects.create(
        workspace=social_account.workspace,
        name=f"{social_account.account_name or social_account.account_handle} Queue",
        social_account=social_account,
    )

    slots = []
    for day, times in DEFAULT_POSTING_SLOTS.items():
        for t in times:
            slots.append(PostingSlot(social_account=social_account, day_of_week=day, time=t))
    PostingSlot.objects.bulk_create(slots, ignore_conflicts=True)

    return queue


def _next_slot_datetimes(social_account, after_dt, count=30):
    """Compute the next `count` PostingSlot datetimes for a social account.

    Starting from `after_dt`, walks forward through the week to find
    upcoming slot times based on the account's PostingSlot configuration.

    Slot times are naive wall-clock times in the account's workspace timezone
    (see ``PostingSlot.time``), so they are resolved in that zone regardless of
    the tzinfo carried by ``after_dt`` — the caller's baseline only sets the
    "not before" instant. ``after_dt`` is always timezone-aware (callers pass
    ``timezone.now()`` or a tz-aware floor).
    """
    slots = PostingSlot.objects.filter(social_account=social_account, is_active=True).order_by("day_of_week", "time")
    if not slots.exists():
        return []

    ws_tz = zoneinfo.ZoneInfo(social_account.workspace.effective_timezone or "UTC")
    after_local = after_dt.astimezone(ws_tz)

    slot_list = list(slots)
    results = []
    current_date = after_local.date()

    # Walk up to 60 days forward to find enough slots
    for day_offset in range(60):
        check_date = current_date + timedelta(days=day_offset)
        weekday = check_date.weekday()  # 0=Monday

        for slot in slot_list:
            if slot.day_of_week != weekday:
                continue

            # Interpret the slot's wall-clock time in the workspace zone (DST
            # offsets resolve per-date), then compare as instants (both aware).
            slot_dt = datetime.combine(check_date, slot.time).replace(tzinfo=ws_tz)
            if slot_dt <= after_dt:
                continue

            results.append(slot_dt)
            if len(results) >= count:
                return results

    return results


def assign_queue_slots(queue):
    """Recalculate assigned_slot_datetime for all entries in a queue.

    Iterates entries in position order and assigns each to the next
    available PostingSlot datetime for the queue's social account. For each
    entry, writes the slot datetime to the matching ``PlatformPost`` (the one
    whose ``social_account`` equals ``queue.social_account``) and keeps
    ``QueueEntry.assigned_slot_datetime`` in sync. ``Post.scheduled_at`` is
    then refreshed via ``sync_post_scheduled_at`` as min-of-children.

    Entries whose matching ``PlatformPost`` has already gone out (or is
    mid-publish) are skipped entirely: their schedule is history. Re-slotting
    them would drag a published post forward onto a future slot, where the
    calendar — which places chips by ``scheduled_at`` — would show it as
    "published" in the future. Skipped entries neither move nor consume a slot,
    so the live entries still flow into the soonest open times.
    """
    from apps.composer.models import PlatformPost
    from apps.composer.services import sync_post_scheduled_at

    entries = queue.entries.select_related("post").order_by("position")
    if not entries.exists():
        return

    now = timezone.now()
    slot_times = _next_slot_datetimes(queue.social_account, now, count=len(entries) + 10)

    touched_posts = []
    slot_idx = 0
    for entry in entries:
        pp = entry.post.platform_posts.filter(social_account=queue.social_account).first()

        # Never re-slot an already-published/publishing post (see docstring).
        if pp is not None and pp.status in PlatformPost.PROTECTED_STATUSES:
            continue

        slot_dt = slot_times[slot_idx] if slot_idx < len(slot_times) else None
        slot_idx += 1

        entry.assigned_slot_datetime = slot_dt
        entry.save(update_fields=["assigned_slot_datetime"])

        # Write the per-platform scheduled_at on the matching PlatformPost.
        if pp is not None:
            pp.scheduled_at = slot_dt
            pp.save(update_fields=["scheduled_at", "updated_at"])

        touched_posts.append(entry.post)

    for post in touched_posts:
        sync_post_scheduled_at(post)


def add_to_queue(post, queue, priority=False):
    """Add a post to a queue and recalculate slot assignments.

    If *priority* is True the post is inserted at position 0 (top of the
    queue) and all existing entries are shifted down.  Otherwise it is
    appended at the end.
    """
    from django.db.models import Max

    if priority:
        # Shift all existing entries down by 1
        queue.entries.update(position=models.F("position") + 1)
        position = 0
    else:
        max_pos = queue.entries.aggregate(max_pos=Max("position"))["max_pos"]
        position = (max_pos or 0) + 1

    QueueEntry.objects.update_or_create(
        queue=queue,
        post=post,
        defaults={"position": position},
    )

    assign_queue_slots(queue)


def reorder_queue(queue, ordered_entry_ids):
    """Reorder queue entries by a list of entry IDs and recalculate slots."""
    for idx, entry_id in enumerate(ordered_entry_ids):
        QueueEntry.objects.filter(id=entry_id, queue=queue).update(position=idx)

    assign_queue_slots(queue)


def repair_future_published_scheduled_at(*, workspace_id=None, apply=True):
    """Reset ``scheduled_at`` for published posts dragged into the future.

    Before the ``assign_queue_slots`` guard landed, re-running a queue (adding or
    reordering a post) re-slotted *every* entry — including already-published
    ones — pushing their ``scheduled_at`` onto a future posting slot. Because the
    calendar places chips by ``scheduled_at``, those posts then showed as
    "published" up to a week ahead.

    A correctly-published post always has ``scheduled_at <= published_at`` (you
    schedule, then it fires at or after that instant). ``scheduled_at >
    published_at`` is therefore an unambiguous signature of this corruption, so
    the repair targets exactly those rows and resets ``scheduled_at`` to the true
    ``published_at``. Idempotent and safe to re-run: once reset, a row no longer
    matches the filter.

    Returns a summary dict ``{"rows": [...], "platform_post_count": int,
    "post_count": int, "applied": bool}`` where each row is a plain dict
    describing one affected ``PlatformPost`` (for dry-run reporting).
    """
    from django.db.models import F

    from apps.composer.models import PlatformPost, Post
    from apps.composer.services import sync_post_scheduled_at

    affected = (
        PlatformPost.objects.filter(
            status=PlatformPost.Status.PUBLISHED,
            published_at__isnull=False,
            scheduled_at__isnull=False,
            scheduled_at__gt=F("published_at"),
        )
        .select_related("social_account", "post")
        .order_by("scheduled_at")
    )
    if workspace_id is not None:
        affected = affected.filter(post__workspace_id=workspace_id)

    rows = []
    post_ids = set()
    for pp in affected:
        rows.append(
            {
                "platform_post_id": str(pp.id),
                "post_id": str(pp.post_id),
                "workspace_id": str(pp.post.workspace_id),
                "platform": pp.social_account.platform,
                "account": pp.social_account.account_name or pp.social_account.account_handle,
                "old_scheduled_at": pp.scheduled_at,
                "new_scheduled_at": pp.published_at,
            }
        )
        post_ids.add(pp.post_id)

    if apply and rows:
        # Snap each child back to its real publish instant, then recompute the
        # parent ``Post.scheduled_at`` aggregate (min-of-children) so listings
        # and Coalesce fallbacks line up again.
        affected.update(scheduled_at=F("published_at"))
        for post in Post.objects.filter(id__in=post_ids):
            sync_post_scheduled_at(post)

    return {
        "rows": rows,
        "platform_post_count": len(rows),
        "post_count": len(post_ids),
        "applied": bool(apply and rows),
    }
