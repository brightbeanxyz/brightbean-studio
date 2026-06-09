"""Queue scheduling services for the Content Calendar (F-2.3)."""

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
    """
    slots = PostingSlot.objects.filter(social_account=social_account, is_active=True).order_by("day_of_week", "time")
    if not slots.exists():
        return []

    slot_list = list(slots)
    results = []
    current_date = after_dt.date()

    # Walk up to 60 days forward to find enough slots
    for day_offset in range(60):
        check_date = current_date + timedelta(days=day_offset)
        weekday = check_date.weekday()  # 0=Monday

        for slot in slot_list:
            if slot.day_of_week != weekday:
                continue

            slot_dt = datetime.combine(check_date, slot.time)
            if after_dt.tzinfo:
                slot_dt = slot_dt.replace(tzinfo=after_dt.tzinfo)

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

    entries = queue.entries.select_related("post").order_by("position")
    if not entries.exists():
        return

    now = timezone.now()
    slot_times = _next_slot_datetimes(queue.social_account, now, count=len(entries) + 10)

    touched_posts = []
    for idx, entry in enumerate(entries):
        slot_dt = slot_times[idx] if idx < len(slot_times) else None
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
