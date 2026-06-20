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

TERMINAL_QUEUE_STATUSES = {"published", "failed"}


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
    """
    from apps.composer.services import sync_post_scheduled_at

    cleanup_terminal_queue_entries(queue=queue)

    entries = list(queue.entries.select_related("post").order_by("position"))
    if not entries:
        return

    now = timezone.now()
    slot_times = _next_slot_datetimes(queue.social_account, now, count=len(entries) + 10)

    touched_posts = []
    for idx, entry in enumerate(entries):
        entry_updates = []
        if entry.position != idx:
            entry.position = idx
            entry_updates.append("position")

        slot_dt = slot_times[idx] if idx < len(slot_times) else None
        if entry.assigned_slot_datetime != slot_dt:
            entry.assigned_slot_datetime = slot_dt
            entry_updates.append("assigned_slot_datetime")
        if entry_updates:
            entry.save(update_fields=entry_updates)

        # Write the per-platform scheduled_at on the matching PlatformPost.
        pp = entry.post.platform_posts.filter(social_account=queue.social_account).first()
        if pp is not None and pp.status not in TERMINAL_QUEUE_STATUSES and pp.scheduled_at != slot_dt:
            pp.scheduled_at = slot_dt
            pp.save(update_fields=["scheduled_at", "updated_at"])

        touched_posts.append(entry.post)

    for post in touched_posts:
        sync_post_scheduled_at(post)


def cleanup_terminal_queue_entries(*, queue=None, social_account=None, dry_run=False):
    """Remove completed posts from channel queues and clear stale schedules.

    Queue entries are channel-specific through ``Queue.social_account`` while
    posts can have multiple platform children. A Facebook child publishing
    should remove only the Facebook queue entry, not the Instagram queue entry
    for the same parent post.
    """
    from apps.composer.models import PlatformPost, Post
    from apps.composer.services import sync_post_scheduled_at

    queues = Queue.objects.filter(is_active=True)
    if queue is not None:
        queues = queues.filter(pk=queue.pk)
    if social_account is not None:
        queues = queues.filter(social_account=social_account)

    removed_entries = 0
    touched_post_ids: set = set()
    for q in queues.select_related("social_account"):
        stale_entries = QueueEntry.objects.filter(
            queue=q,
            post__platform_posts__social_account=q.social_account,
            post__platform_posts__status__in=TERMINAL_QUEUE_STATUSES,
        ).distinct()
        touched_post_ids.update(stale_entries.values_list("post_id", flat=True))
        if dry_run:
            removed_entries += stale_entries.count()
        else:
            deleted, _ = stale_entries.delete()
            removed_entries += deleted

    terminal_posts = PlatformPost.objects.filter(status__in=TERMINAL_QUEUE_STATUSES)
    if social_account is not None:
        terminal_posts = terminal_posts.filter(social_account=social_account)
    elif queue is not None:
        terminal_posts = terminal_posts.filter(social_account=queue.social_account)

    scheduled_terminal_posts = terminal_posts.exclude(scheduled_at__isnull=True)
    touched_post_ids.update(scheduled_terminal_posts.values_list("post_id", flat=True))
    if dry_run:
        cleared_schedules = scheduled_terminal_posts.count()
    else:
        cleared_schedules = scheduled_terminal_posts.update(scheduled_at=None, updated_at=timezone.now())

    if not dry_run:
        for post in Post.objects.filter(pk__in=touched_post_ids):
            sync_post_scheduled_at(post)

    return {
        "removed_entries": removed_entries,
        "cleared_schedules": cleared_schedules,
    }


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
