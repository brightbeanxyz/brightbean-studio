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

    Each entry's ``position`` is treated as a direct index into the upcoming
    slot sequence, so intentional gaps between positions (created by manual
    deletes or prioritise operations) are preserved as empty slots in the
    schedule.  Positions are never normalised here — callers that want compact
    ordering must set positions explicitly (e.g. ``reorder_queue``).

    For each entry, writes the slot datetime to the matching ``PlatformPost``
    (the one whose ``social_account`` equals ``queue.social_account``) and
    keeps ``QueueEntry.assigned_slot_datetime`` in sync.  ``Post.scheduled_at``
    is then refreshed via ``sync_post_scheduled_at`` as min-of-children.
    """
    from apps.composer.services import sync_post_scheduled_at

    entries = list(queue.entries.select_related("post").order_by("position"))
    if not entries:
        return

    now = timezone.now()
    max_pos = max(e.position for e in entries)
    slot_times = _next_slot_datetimes(queue.social_account, now, count=max_pos + 10)

    touched_posts = []
    for entry in entries:
        slot_dt = slot_times[entry.position] if entry.position < len(slot_times) else None
        if entry.assigned_slot_datetime != slot_dt:
            entry.assigned_slot_datetime = slot_dt
            entry.save(update_fields=["assigned_slot_datetime"])

        # Write the per-platform scheduled_at on the matching PlatformPost.
        pp = entry.post.platform_posts.filter(social_account=queue.social_account).first()
        if pp is not None:
            pp.scheduled_at = slot_dt
            pp.save(update_fields=["scheduled_at", "updated_at"])

        touched_posts.append(entry.post)

    for post in touched_posts:
        sync_post_scheduled_at(post)


def add_to_queue(post, queue, priority=False):
    """Add a post to a queue and recalculate slot assignments.

    Re-adding an already queued post is idempotent unless ``priority`` is
    requested. Editing an existing queued post should not move it into an
    earlier gap and reshuffle the visible calendar.

    If *priority* is True the post is placed at position 0.  Existing entries
    are only shifted down by 1 when position 0 is already occupied, which
    preserves any gaps in the position sequence.  If position 0 is free (a
    gap), the new post fills it with no shifting needed.

    If *priority* is False, the post is placed at the earliest unoccupied
    position — filling any gap before appending after the last entry.
    """
    existing_entry = queue.entries.filter(post=post).first()
    if existing_entry is not None and not priority:
        assign_queue_slots(queue)
        return

    # Exclude the post's own existing entry so that re-queuing an already-queued
    # post does not treat its current position as a foreign obstacle.
    occupied = set(queue.entries.exclude(post=post).values_list("position", flat=True))

    if priority:
        if 0 in occupied:
            # Shift all existing entries down by 1, preserving relative gaps.
            queue.entries.update(position=models.F("position") + 1)
        position = 0
    else:
        position = 0
        while position in occupied:
            position += 1

    QueueEntry.objects.update_or_create(
        queue=queue,
        post=post,
        defaults={"position": position},
    )

    assign_queue_slots(queue)


def remove_from_queue(post, social_account_ids):
    """Remove *post* from queues for the given channels, preserving the freed slot as a gap.

    Called when a post leaves the queue (e.g. the user switches from "next
    available" / "prioritise" to a specific date or "publish now").
    ``assign_queue_slots`` is intentionally NOT called so the vacated position
    remains as an empty gap — the next "next available" placement will fill it.
    """
    if not social_account_ids:
        return
    QueueEntry.objects.filter(
        queue__social_account_id__in=social_account_ids,
        queue__is_active=True,
        post=post,
    ).delete()


def reorder_queue(queue, ordered_entry_ids):
    """Reorder queue entries by a list of entry IDs and recalculate slots."""
    for idx, entry_id in enumerate(ordered_entry_ids):
        QueueEntry.objects.filter(id=entry_id, queue=queue).update(position=idx)

    assign_queue_slots(queue)
