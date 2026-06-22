"""Queue scheduling services for the Content Calendar (F-2.3)."""

import zoneinfo
from datetime import datetime, time, timedelta

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


# ---------------------------------------------------------------------------
# Stable slot-occupancy model
#
# A queue's "slots" are the upcoming PostingSlot datetimes for its channel; each
# is either OCCUPIED (a non-published post on the channel already holds that
# instant) or a GAP. Operations are LOCAL — they fill or vacate a single slot
# and never recompute unrelated entries — so an entry's time stays stable until
# that entry is explicitly moved. Occupancy is keyed off PlatformPost.scheduled_at
# (the publisher's source of truth), not the queue rows, so a manually-scheduled
# post or a recurrence clone on the same channel also reserves its instant — no
# double-booking. PROTECTED_STATUSES (published/publishing) are history and never
# occupy a future candidate or get moved.
# ---------------------------------------------------------------------------


class QueueFullError(Exception):
    """No open posting slot exists within the scheduling lookahead horizon."""


def _occupied_datetimes(social_account, *, exclude_pp_ids=()):
    """Future slot instants already claimed on this channel.

    Non-published/-publishing PlatformPosts with a future ``scheduled_at`` on
    ``social_account``. ``exclude_pp_ids`` drops a post's own row so it never
    blocks itself while being re-slotted.
    """
    from apps.composer.models import PlatformPost

    qs = (
        PlatformPost.objects.filter(
            social_account=social_account,
            scheduled_at__isnull=False,
            scheduled_at__gt=timezone.now(),
        )
        .exclude(status__in=PlatformPost.PROTECTED_STATUSES)
        .exclude(id__in=list(exclude_pp_ids))
    )
    return set(qs.values_list("scheduled_at", flat=True))


def _next_available_slot(social_account, *, exclude_pp_ids=(), after=None):
    """First upcoming PostingSlot datetime not already occupied, or ``None``.

    ``None`` means every slot within the lookahead horizon (``_next_slot_datetimes``
    caps at 60 days) is taken — the queue is full.
    """
    after = after or timezone.now()
    occupied = _occupied_datetimes(social_account, exclude_pp_ids=exclude_pp_ids)
    # Among the first ``len(occupied) + 1`` distinct slots at most ``len(occupied)``
    # can be taken, so one is guaranteed free if any free slot exists at all.
    candidates = _next_slot_datetimes(social_account, after, count=len(occupied) + 1)
    for slot_dt in candidates:
        if slot_dt not in occupied:
            return slot_dt
    return None


def _platform_post_for(post, social_account):
    """The post's PlatformPost child on this channel (or ``None``)."""
    return post.platform_posts.filter(social_account=social_account).first()


def _is_protected(pp):
    from apps.composer.models import PlatformPost

    return pp is not None and pp.status in PlatformPost.PROTECTED_STATUSES


def _lock_channel(queue):
    """Serialize slot writes for a channel within the current transaction.

    Occupancy is computed from ``PlatformPost`` rows (the publisher's truth),
    which a per-queue ``select_for_update`` on QueueEntry rows does not cover —
    two concurrent ops on *different* queues of the same channel would otherwise
    read the same free slot and double-book. Locking the ``SocialAccount`` row
    makes every slot op on a channel mutually exclusive.
    """
    from apps.social_accounts.models import SocialAccount

    list(SocialAccount.objects.select_for_update().filter(id=queue.social_account_id))


def _ensure_entry(post, queue):
    """Return the post's QueueEntry, creating it (appended) if absent."""
    from django.db.models import Max

    entry = queue.entries.filter(post=post).first()
    if entry is None:
        max_pos = queue.entries.aggregate(m=Max("position"))["m"]
        entry = QueueEntry.objects.create(queue=queue, post=post, position=(max_pos or 0) + 1)
    return entry


def _write_slot(entry, pp, slot_dt):
    """Persist one slot assignment to the QueueEntry and its PlatformPost."""
    from apps.composer.services import sync_post_scheduled_at

    entry.assigned_slot_datetime = slot_dt
    entry.save(update_fields=["assigned_slot_datetime"])
    if pp is not None:
        pp.scheduled_at = slot_dt
        pp.save(update_fields=["scheduled_at", "updated_at"])
        sync_post_scheduled_at(pp.post)


def add_post_next_available(post, queue):
    """Place ``post`` into this queue's first open slot (upsert-aware).

    Comment §1 (Create · Next Available) and §4 (Edit · Next Available): if the
    post is already queued, its own slot is vacated first and it is re-slotted to
    the next gap; existing entries are never disturbed. Raises ``QueueFullError`` when
    no slot is free within the horizon.
    """
    from django.db import transaction

    with transaction.atomic():
        _lock_channel(queue)

        pp = _platform_post_for(post, queue.social_account)
        # A published/publishing post's schedule is history — never re-slot it
        # (mirrors the guard in prioritize/reorder; protects the reslot endpoint).
        if _is_protected(pp):
            return queue.entries.filter(post=post).first()
        exclude = [pp.id] if pp is not None else []
        slot_dt = _next_available_slot(queue.social_account, exclude_pp_ids=exclude)
        if slot_dt is None:
            raise QueueFullError(f"Queue {queue.id} has no open slot within the scheduling horizon.")

        entry = _ensure_entry(post, queue)
        _write_slot(entry, pp, slot_dt)
        return entry


def prioritize(post, queue):
    """Place ``post`` at the queue's earliest slot, laddering others up by one.

    Comment §2: if the earliest upcoming slot is free, ``post`` takes it and
    nothing moves. Otherwise every other occupied queue entry shifts one slot
    later (``[k]→[k+1]``, preserving the gap pattern) before ``post`` takes
    slot ``[0]``. Upsert-aware. Raises ``QueueFullError`` past the horizon.
    """
    from django.db import transaction

    with transaction.atomic():
        _lock_channel(queue)

        now = timezone.now()
        pp = _platform_post_for(post, queue.social_account)

        # This queue's movable entries (exclude `post`, exclude protected), each
        # keyed on the ``PlatformPost.scheduled_at`` the publisher fires on — NOT
        # ``QueueEntry.assigned_slot_datetime``, which a manual calendar drag via
        # ``reschedule_post`` can leave stale and divergent (then the ladder would
        # mis-place the post or double-book a slot another post really holds).
        movable = []  # (entry, pp, current_slot_dt)
        for e in queue.entries.exclude(post=post).select_related("post"):
            p = _platform_post_for(e.post, queue.social_account)
            if p is None or _is_protected(p) or p.scheduled_at is None or p.scheduled_at <= now:
                continue
            movable.append((e, p, p.scheduled_at))
        movable_dts = {dt for _, _, dt in movable}

        candidates = _next_slot_datetimes(queue.social_account, now, count=len(movable) + 2)
        if not candidates:
            raise QueueFullError(f"Queue {queue.id} has no posting slots within the horizon.")

        entry = _ensure_entry(post, queue)
        target = candidates[0]

        # Slot 0 is free among the queue's own entries.
        if target not in movable_dts:
            # If a foreign/fixed post (manual schedule, clone, other queue) holds
            # slot 0, we cannot preempt it — degrade to the next genuine gap.
            occupied = _occupied_datetimes(queue.social_account, exclude_pp_ids=[pp.id] if pp else [])
            if target in occupied:
                free = _next_available_slot(queue.social_account, exclude_pp_ids=[pp.id] if pp else [])
                if free is None:
                    raise QueueFullError(f"Queue {queue.id} has no open slot within the scheduling horizon.")
                _write_slot(entry, pp, free)
                return entry
            _write_slot(entry, pp, target)
            return entry

        # Slot 0 taken by a queue entry: ladder every movable entry up to its
        # next free slot. Each mover lands on the earliest candidate after its
        # current index that is neither held by a post we can't move (foreign /
        # manual / out-of-horizon) nor already claimed by another mover — so the
        # ladder never double-books and never runs off the lookahead horizon.
        index_of = {dt: i for i, dt in enumerate(candidates)}
        movers = [(index_of[dt], e, p) for e, p, dt in movable if dt in index_of]
        mover_old_dts = {dt for _, _, dt in movable if dt in index_of}
        # Datetimes that must stay free: everything occupied on this channel
        # except the movers we are about to relocate (their slots are vacated).
        avoid_dts = (
            _occupied_datetimes(queue.social_account, exclude_pp_ids=[pp.id] if pp is not None else []) - mover_old_dts
        )

        assigned_idx = {0}  # slot 0 is reserved for the prioritized post
        # Descending so a destination is always vacated before it is written.
        for cur_idx, e, p in sorted(movers, key=lambda t: t[0], reverse=True):
            j = cur_idx + 1
            while True:
                if j >= len(candidates):
                    candidates = _next_slot_datetimes(queue.social_account, now, count=j + 2)
                    if j >= len(candidates):
                        raise QueueFullError(f"Queue {queue.id} has no open slot within the scheduling horizon.")
                if j not in assigned_idx and candidates[j] not in avoid_dts:
                    break
                j += 1
            assigned_idx.add(j)
            _write_slot(e, p, candidates[j])
        _write_slot(entry, pp, candidates[0])
        return entry


def remove_from_queue(entry):
    """Remove a single entry, leaving a gap; neighbours are untouched.

    Comment §3: delete the QueueEntry and clear the matching PlatformPost's
    schedule. The child is transitioned ``scheduled→draft`` (which nulls
    ``scheduled_at``) rather than nulled directly, so it can't become instantly
    due via the publisher's ``Coalesce(scheduled_at, post__scheduled_at)``
    fallback while the parent aggregate still points at a past time.
    """
    from django.db import transaction

    from apps.composer.services import sync_post_scheduled_at, transition_platform_post

    with transaction.atomic():
        post = entry.post
        queue = entry.queue
        _lock_channel(queue)
        pp = _platform_post_for(post, queue.social_account)
        # Clear the schedule for any non-protected child (scheduled OR failed),
        # not just 'scheduled', so a removed failed post stops rendering on the
        # calendar at its past attempt time. Published/publishing stay (history).
        if pp is not None and not _is_protected(pp) and pp.can_transition_to("draft"):
            transition_platform_post(pp, "draft")
        entry.delete()
        sync_post_scheduled_at(post)


def reslot_to_next_available(entry):
    """Free this entry's slot and move it to the queue's next gap."""
    return add_post_next_available(entry.post, entry.queue)


def add_to_queue(post, queue, priority=False):
    """Add a post to a queue (back-compat dispatcher).

    Routes to the stable-slot ops: ``prioritize`` (top of queue) or
    ``add_post_next_available`` (first open gap). Kept so existing callers and
    the composer's ``add_to_queue`` / ``add_to_queue_priority`` actions only
    need their resolved service swapped, not their wiring.
    """
    if priority:
        return prioritize(post, queue)
    return add_post_next_available(post, queue)


def reorder_queue(queue, ordered_entry_ids):
    """Reassign the queue's occupied slot times to entries in a new order.

    Drag-reorder under the slot model: the SET of occupied datetimes is
    preserved (gaps stay put); only which post sits in which slot changes. The
    movable, slotted entries named in ``ordered_entry_ids`` are matched — in that
    visual order — to their datetimes sorted ascending. Protected
    (published/publishing) entries are immovable and skipped.
    """
    from django.db import transaction

    with transaction.atomic():
        _lock_channel(queue)

        ordered = []
        for eid in ordered_entry_ids:
            e = queue.entries.filter(id=eid).select_related("post").first()
            if e is None:
                continue
            p = _platform_post_for(e.post, queue.social_account)
            if _is_protected(p):
                continue
            ordered.append((e, p))

        # Redistribute the slot instants already held — keyed on the publisher's
        # ``PlatformPost.scheduled_at`` (not ``assigned_slot_datetime``, which a
        # manual drag can leave stale) — among the entries that hold one. Never
        # invent or drop a slot during a reorder.
        slotted = [(e, p) for e, p in ordered if p is not None and p.scheduled_at is not None]
        slots = sorted(p.scheduled_at for _, p in slotted)
        for idx, (e, p) in enumerate(slotted):
            _write_slot(e, p, slots[idx])

        # Keep ``position`` as a stable visual tie-break in the dragged order.
        for idx, (e, _p) in enumerate(ordered):
            if e.position != idx:
                QueueEntry.objects.filter(id=e.id).update(position=idx)


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

    The same bad future slot was also written to the matching
    ``QueueEntry.assigned_slot_datetime`` (the queue the bug walked, where
    ``queue.social_account == platform_post.social_account``). ``queue_detail``
    renders that field and the published-status guard stops ``assign_queue_slots``
    from ever recomputing a published entry, so the repair snaps that stale queue
    timestamp back to ``published_at`` too (same ``> published_at`` signature).

    Returns a summary dict ``{"rows": [...], "platform_post_count": int,
    "post_count": int, "queue_entry_count": int, "applied": bool}`` where each
    row is a plain dict describing one affected ``PlatformPost`` (for dry-run
    reporting).
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
    queue_targets = []
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
        queue_targets.append((pp.post_id, pp.social_account_id, pp.published_at))

    # The bug stamped the same future slot onto the matching QueueEntry
    # (queue.social_account == pp.social_account); queue_detail renders it, and
    # the published-status guard now keeps assign_queue_slots from ever
    # recomputing a published entry. Snap those stale timestamps back too — same
    # ``> published_at`` signature, so a correctly null/past entry is left alone.
    queue_entry_targets = [
        (
            published_at,
            QueueEntry.objects.filter(
                post_id=post_id,
                queue__social_account_id=social_account_id,
                assigned_slot_datetime__gt=published_at,
            ),
        )
        for post_id, social_account_id, published_at in queue_targets
    ]
    queue_entry_count = 0

    if apply and rows:
        from django.db import transaction

        with transaction.atomic():
            posts = list(Post.objects.filter(id__in=post_ids))
            # Snapping a published child back to its past ``published_at`` lowers
            # the parent ``Post.scheduled_at`` aggregate (min-of-children) into
            # the past. A SCHEDULED sibling with ``scheduled_at=NULL`` resolves
            # its due time through the publisher's
            # ``Coalesce(scheduled_at, post__scheduled_at)`` fallback, so a
            # backward parent move would make that sibling instantly due and
            # publish it early. Pin such siblings to their current effective time
            # *before* lowering the parent, so the repair never drags a pending
            # post's schedule into the past.
            for post in posts:
                if post.scheduled_at is not None:
                    post.platform_posts.filter(
                        status=PlatformPost.Status.SCHEDULED,
                        scheduled_at__isnull=True,
                    ).update(scheduled_at=post.scheduled_at)
            # Snap each corrupt published child back to its real publish instant,
            # then recompute the parent aggregate so listings and Coalesce
            # fallbacks line up again.
            affected.update(scheduled_at=F("published_at"))
            for published_at, stale_entries in queue_entry_targets:
                queue_entry_count += stale_entries.update(assigned_slot_datetime=published_at)
            for post in posts:
                sync_post_scheduled_at(post)
    else:
        # Dry run: report how many stale QueueEntry rows would be reset.
        for _published_at, stale_entries in queue_entry_targets:
            queue_entry_count += stale_entries.count()

    return {
        "rows": rows,
        "platform_post_count": len(rows),
        "post_count": len(post_ids),
        "queue_entry_count": queue_entry_count,
        "applied": bool(apply and rows),
    }
