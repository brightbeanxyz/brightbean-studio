"""Notification engine - the single entry point all features call.

Usage:
    from apps.notifications.engine import notify

    notify(
        user=some_user,
        event_type="post_approved",
        title="Post approved",
        body="Your post 'New product launch' was approved by Jane.",
        data={"post_id": str(post.id), "workspace_id": str(ws.id)},
    )
"""

import hashlib
import hmac
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count, F, Min, Q
from django.template.loader import render_to_string
from django.utils import timezone

from apps.common.mail import EmailNotSentError, send_or_raise
from apps.settings_manager.defaults import APP_DEFAULTS

from .models import (
    Channel,
    DeliveryStatus,
    EventType,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    QuietHours,
)
from .unsubscribe import list_unsubscribe_headers

logger = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MINUTES = [1, 5, 30]
# Cap how many deliveries a single retry sweep processes, so a PENDING backlog
# that accumulated before the periodic retry was scheduled drains gradually
# across runs instead of bursting all at once.
RETRY_BATCH_LIMIT = 200

# Wait this long after the first failure before mailing, so the rest of a burst
# lands in the same email. Read from ``org.email_batching_delay_minutes``, which
# has described this behaviour in settings_manager since the beginning and
# configured nothing until now — taking the value from there rather than
# repeating it keeps the documented default and the real one from drifting.
# ``.get`` rather than a subscript: that key had no readers before this module,
# so a later cleanup could plausibly drop it, and a KeyError here would break
# importing the app rather than just the digest.
#
# That key is org-scoped and a digest spans every workspace a user can see, so
# this uses the application default rather than a per-org override; honouring
# one needs a rule for which of a user's orgs wins, which is a separate
# decision.
#
# Read through isinstance rather than used directly: APP_DEFAULTS holds ints,
# strings, bools and None, so the value is typed too loosely to hand to
# timedelta() — and an override that is not a number should fall back here
# rather than raise from inside the sweep.
_configured_batch_window = APP_DEFAULTS.get("org.email_batching_delay_minutes", 5)
BATCH_WINDOW_MINUTES: int = _configured_batch_window if isinstance(_configured_batch_window, int) else 5
# ...unless this many are already waiting, which is a storm, not a trickle:
# send immediately rather than letting the user watch it build.
BATCH_SIZE_TRIGGER = 10
# Never itemise more than this in one email; the rest become "and N more".
BATCH_MAX_ITEMS = 20
# Cap the work per run for the same reason RETRY_BATCH_LIMIT exists: a backlog
# should drain across runs rather than become a storm of its own.
BATCH_GROUP_LIMIT = 50
# A claim older than this belonged to a run that died holding it. Same reasoning
# as the publisher's stale-``publishing`` timeout: the row has to be reclaimable
# or it is stranded for good.
BATCH_CLAIM_TIMEOUT = timedelta(minutes=10)

# Local hour at which a ``QuietHours.digest_mode`` user receives their digest,
# in the timezone on their own QuietHours row. Anchored to the clock rather than
# measured from the oldest queued row: a rolling 24h window would walk the
# delivery time forward by however long the user happened to be idle, and a
# toggle labelled "Daily digest" should arrive at the same time each day.
DAILY_DIGEST_HOUR = 8

# Events whose email is collapsed into one message per user instead of one per
# notification, and the heading each one gets. A broken integration fails every
# scheduled post at once — one ``PlatformPost`` at a time, so a single revoked
# token used to mean one email per post — and nobody needs to be told two
# hundred times.
#
# The in-app notification is still created per post: the bell and the Publish
# page are where the detail belongs, and nothing is lost by not mailing it.
#
# A batch is always one event type, so the heading is never a compromise
# between two of them. Singular and plural are both spelled out because
# "1 posts failed" is the kind of detail that makes an alert look automated and
# ignorable.
BATCH_HEADINGS: dict[str, tuple[str, str]] = {
    EventType.POST_FAILED: ("{n} post failed to publish", "{n} posts failed to publish"),
}

# Derived, never maintained by hand: an event that is batched but has no
# heading would silently mail "12 new notifications" instead of saying what
# happened.
BATCHED_EMAIL_EVENTS = frozenset(BATCH_HEADINGS)

# The daily digest is not per-event-type, so it has no BATCH_HEADINGS entry.
DAILY_DIGEST_HEADINGS = ("Your daily digest: {n} notification", "Your daily digest: {n} notifications")

# Default channel enablement per event type.
# Key: event_type, Value: dict of channel → default enabled.
DEFAULT_CHANNELS: dict[str, dict[str, bool]] = {
    EventType.POST_SUBMITTED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.POST_APPROVED: {Channel.IN_APP: True, Channel.EMAIL: False},
    EventType.POST_CHANGES_REQUESTED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.POST_REJECTED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.POST_PUBLISHED: {Channel.IN_APP: True, Channel.EMAIL: False},
    EventType.POST_FAILED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.NEW_INBOX_MESSAGE: {Channel.IN_APP: True, Channel.EMAIL: False},
    EventType.INBOX_SLA_OVERDUE: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.CLIENT_APPROVAL_REQUESTED: {Channel.IN_APP: False, Channel.EMAIL: True},
    EventType.TEAM_MEMBER_INVITED: {Channel.IN_APP: False, Channel.EMAIL: True},
    EventType.SOCIAL_ACCOUNT_DISCONNECTED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.REPORT_GENERATED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.ENGAGEMENT_ALERT: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.COMMENT_MENTION: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.APPROVAL_REMINDER: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.APPROVAL_STALLED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.APPROVAL_HOLD_REQUESTED: {Channel.IN_APP: True, Channel.EMAIL: True},
    EventType.CLIENT_CONNECTED_ACCOUNTS: {Channel.IN_APP: True, Channel.EMAIL: True},
}

# Event types considered non-critical (suppressed during quiet hours).
NON_CRITICAL_EVENTS = {
    EventType.POST_PUBLISHED,
    EventType.REPORT_GENERATED,
    EventType.ENGAGEMENT_ALERT,
}


def notify(
    user,
    event_type: str,
    title: str,
    body: str = "",
    data: dict | None = None,
) -> Notification | None:
    """Create a notification and dispatch to enabled channels.

    This is the single entry point that all features call. The function:
    1. Creates the Notification record (always).
    2. Checks the user's per-event/per-channel preferences.
    3. Respects quiet hours (suppresses non-critical events).
    4. Creates NotificationDelivery records for each enabled channel.
    5. Dispatches immediately (in-app is a DB write, email/webhook are async-safe).

    Returns the created Notification, or None if the user or event_type is invalid.
    """
    if not user or not user.is_active:
        return None

    if event_type not in EventType.values:
        logger.warning("Unknown event_type: %s", event_type)
        return None

    notification = Notification.objects.create(
        user=user,
        event_type=event_type,
        title=title,
        body=body,
        data=data or {},
    )

    channels_to_dispatch = _resolve_channels(user, event_type)
    digest_mode = _is_digest_mode(user)

    if _is_in_quiet_hours(user) and event_type in NON_CRITICAL_EVENTS:
        # During quiet hours, only deliver in-app (silent). Skip email/webhook.
        #
        # EMAIL is exempt for digest_mode users, and only for them. Their email
        # is queued, not sent, so dropping the channel here would LOSE the
        # notification rather than silence it — it would never appear in any
        # digest. The digest's own send hour is what keeps them undisturbed. The
        # webhook stays suppressed either way: it fires immediately, so
        # exempting it too would defeat quiet hours outright.
        quiet_channels = {Channel.IN_APP, Channel.EMAIL} if digest_mode else {Channel.IN_APP}
        channels_to_dispatch = [c for c in channels_to_dispatch if c in quiet_channels]

    for channel in channels_to_dispatch:
        # digest_mode queues EVERY event type, not just the batched ones: the
        # queued row IS the delivery, so this replaces the immediate email
        # rather than adding a digest on top of it.
        batched = channel == Channel.EMAIL and (digest_mode or event_type in BATCHED_EMAIL_EVENTS)
        delivery = NotificationDelivery.objects.create(
            notification=notification,
            channel=channel,
            status=DeliveryStatus.PENDING,
            batch_queued_at=timezone.now() if batched else None,
        )
        if batched:
            # Handed to send_batched_email_digests() instead of dispatched.
            # batch_queued_at is what marks it as queued — not the absence of a
            # next_retry_at, which would also describe a row whose inline
            # dispatch was cut short by a deploy or an OOM kill.
            continue
        _dispatch(delivery)

    return notification


def _resolve_channels(user, event_type: str, pref_cache: dict | None = None) -> list[str]:
    """Determine which channels are enabled for this user + event_type.

    Checks user preferences first; falls back to DEFAULT_CHANNELS.
    Accepts an optional pref_cache dict to avoid repeated queries in batch operations.
    """
    if pref_cache is not None and event_type in pref_cache:
        pref_map = pref_cache[event_type]
    else:
        prefs = NotificationPreference.objects.filter(user=user, event_type=event_type).values_list(
            "channel", "is_enabled"
        )
        pref_map = dict(prefs)
        if pref_cache is not None:
            pref_cache[event_type] = pref_map

    defaults = DEFAULT_CHANNELS.get(event_type, {})
    channels: list[str] = []

    for channel_value in [Channel.IN_APP, Channel.EMAIL, Channel.WEBHOOK]:
        if channel_value in pref_map:
            if pref_map[channel_value]:
                channels.append(str(channel_value))
        elif defaults.get(channel_value, False):
            channels.append(str(channel_value))

    return channels


def _resolve_timezone(tz_name: str):
    """An IANA timezone, falling back to UTC on anything unusable.

    ``QuietHours.timezone`` is free text from a form, so it can be a name this
    machine's tzdata does not have.
    """
    import zoneinfo

    try:
        return zoneinfo.ZoneInfo(tz_name)
    except (KeyError, ValueError, zoneinfo.ZoneInfoNotFoundError):
        return zoneinfo.ZoneInfo("UTC")


def _is_digest_mode(user) -> bool:
    """Whether this user asked for their notification email as a daily digest."""
    from django.core.exceptions import ObjectDoesNotExist

    try:
        return bool(user.quiet_hours.digest_mode)
    except (AttributeError, ObjectDoesNotExist):
        return False


def _is_in_quiet_hours(user) -> bool:
    """Check if the user is currently in their quiet hours window."""
    from django.core.exceptions import ObjectDoesNotExist

    try:
        qh = user.quiet_hours
    except (AttributeError, ObjectDoesNotExist):
        return False

    if not qh.is_enabled or not qh.start_time or not qh.end_time:
        return False

    now_local = timezone.now().astimezone(_resolve_timezone(qh.timezone)).time()

    # Coerce to time objects - fields may be raw strings if the in-memory
    # QuietHours instance was populated from POST data and not yet refreshed.
    from datetime import time as dt_time

    start = qh.start_time
    end = qh.end_time
    if isinstance(start, str):
        try:
            parts = start.split(":")
            start = dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return False
    if isinstance(end, str):
        try:
            parts = end.split(":")
            end = dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return False

    if start <= end:
        return start <= now_local <= end
    else:
        # Overnight range (e.g., 22:00 - 07:00)
        return now_local >= start or now_local <= end


def _dispatch(delivery: NotificationDelivery) -> None:
    """Dispatch a single delivery to its channel."""
    delivery.attempts += 1
    delivery.save(update_fields=["attempts"])

    try:
        if delivery.channel == Channel.IN_APP:
            _dispatch_in_app(delivery)
        elif delivery.channel == Channel.EMAIL:
            _dispatch_email(delivery)
        elif delivery.channel == Channel.WEBHOOK:
            _dispatch_webhook(delivery)
        else:
            logger.warning("Unknown channel: %s", delivery.channel)
            return

        delivery.status = DeliveryStatus.DELIVERED
        delivery.delivered_at = timezone.now()
        delivery.save(update_fields=["status", "delivered_at"])

    except EmailNotSentError as exc:
        # The outbound budget declined this one. Retrying would just spend the
        # sweep on a message the budget will decline again, so record it and
        # stop — and above all do not mark it delivered, which is what made the
        # delivery table lie about mail that never left.
        logger.info("Delivery %s not sent: %s", delivery.id, exc)
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = str(exc)[:500]
        delivery.save(update_fields=["status", "error_message"])

    except Exception as exc:
        logger.exception("Delivery failed: %s", delivery.id)
        delivery.error_message = str(exc)[:500]

        if delivery.attempts >= MAX_RETRY_ATTEMPTS:
            delivery.status = DeliveryStatus.FAILED
        else:
            delivery.status = DeliveryStatus.PENDING
            backoff_idx = min(delivery.attempts - 1, len(RETRY_BACKOFF_MINUTES) - 1)
            delivery.next_retry_at = timezone.now() + timedelta(minutes=RETRY_BACKOFF_MINUTES[backoff_idx])

        delivery.save(update_fields=["status", "error_message", "next_retry_at"])


def _dispatch_in_app(delivery: NotificationDelivery) -> None:
    """In-app delivery is just the DB record - already created."""
    pass


def _dispatch_email(delivery: NotificationDelivery) -> None:
    """Send notification email using Django's email backend."""
    notification = delivery.notification
    user = notification.user

    context = {
        "notification": notification,
        "user": user,
        "app_url": getattr(settings, "APP_URL", "http://localhost:8000"),
    }

    text_content = render_to_string("notifications/email/notification.txt", context)
    html_content = render_to_string("notifications/email/notification.html", context)

    subject = notification.title

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
        to=[user.email],
        headers=list_unsubscribe_headers(user.pk, notification.event_type),
    )
    msg.attach_alternative(html_content, "text/html")
    send_or_raise(msg)


def _dispatch_webhook(delivery: NotificationDelivery) -> None:
    """Send notification via webhook (HTTP POST with HMAC-SHA256 signature).

    The webhook URL is re-validated with is_safe_url at dispatch time (not just
    when stored), and redirects are not followed. This narrows the DNS-rebind
    window between validation and connection. We still rely on the OS-level DNS
    cache to resolve consistently within a single dispatch; deployments with
    aggressive DNS-rebind threat models should additionally enforce egress
    firewall rules.
    """
    import httpx

    from apps.common.validators import is_safe_url

    notification = delivery.notification

    webhook_url = notification.data.get("webhook_url")
    if not webhook_url:
        logger.info("No webhook_url in notification data, skipping webhook delivery")
        return

    # Re-validate immediately before the request. The single-pass DNS resolve
    # used by is_safe_url is reused by httpx via the OS resolver cache; this
    # is the simplest defence that doesn't add an httpx-transport dependency.
    if not is_safe_url(webhook_url):
        raise RuntimeError("Webhook URL rejected: must be a public http(s) endpoint")

    payload = json.dumps(
        {
            "event_type": notification.event_type,
            "title": notification.title,
            "body": notification.body,
            "data": notification.data,
            "created_at": notification.created_at.isoformat(),
            "user_id": str(notification.user_id),
        },
        default=str,
    ).encode("utf-8")

    webhook_secret = getattr(settings, "WEBHOOK_SECRET", settings.SECRET_KEY)
    signature = hmac.new(
        webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Signature-256": f"sha256={signature}",
        "X-Event-Type": notification.event_type,
    }

    # follow_redirects=False prevents a 302→private-IP bait-and-switch from a
    # legitimate-looking endpoint. Any redirect is surfaced as a delivery
    # failure, not silently followed.
    response = httpx.post(webhook_url, content=payload, headers=headers, timeout=10.0, follow_redirects=False)
    if 300 <= response.status_code < 400:
        raise RuntimeError(f"Webhook URL replied with redirect {response.status_code} — refusing to follow.")
    if response.status_code >= 400:
        raise RuntimeError(f"Webhook returned HTTP {response.status_code}")


def retry_failed_deliveries() -> int:
    """Retry deliveries that are pending and past their next_retry_at.

    Called by a background task on a periodic schedule.
    Returns the count of retried deliveries.
    """
    now = timezone.now()
    pending = (
        NotificationDelivery.objects.filter(
            status=DeliveryStatus.PENDING,
            next_retry_at__isnull=False,
            next_retry_at__lte=now,
            attempts__lt=MAX_RETRY_ATTEMPTS,
        )
        .select_related("notification", "notification__user")
        .order_by("next_retry_at")[:RETRY_BATCH_LIMIT]
    )

    count = 0
    for delivery in pending:
        _dispatch(delivery)
        count += 1

    return count


def _batchable_deliveries():
    """Every delivery waiting to go out in a digest.

    Keyed on ``batch_queued_at``, which ``notify()`` sets when it deliberately
    queues a row. Identifying them by what *didn't* happen instead — PENDING
    with no next_retry_at — would also match a row whose inline dispatch was
    interrupted, and sweeping one of those into a digest would mark an invite
    delivered that was never sent.

    Deactivated recipients are excluded. ``notify()`` already refuses to create
    anything for an inactive user, but batching puts minutes — or, for a daily
    digest, a day — between queueing and sending, and an account can be closed
    in that gap. The ``send_daily_digests`` this replaced skipped inactive users
    for the same reason. Every caller goes through here, so the exclusion covers
    both choosing the groups and the re-query that claims the rows.
    """
    return NotificationDelivery.objects.filter(
        channel=Channel.EMAIL,
        status=DeliveryStatus.PENDING,
        batch_queued_at__isnull=False,
        attempts__lt=MAX_RETRY_ATTEMPTS,
        notification__user__is_active=True,
    )


def _digest_heading(event_type: str | None, count: int) -> str:
    """The subject line. Every batched event has one — see BATCHED_EMAIL_EVENTS.

    ``event_type is None`` is the daily digest, which spans every type and so
    has no per-event heading to use.
    """
    singular, plural = DAILY_DIGEST_HEADINGS if event_type is None else BATCH_HEADINGS[event_type]
    return (singular if count == 1 else plural).format(n=count)


def _last_daily_send_boundary(now, tz_name: str):
    """The most recent moment DAILY_DIGEST_HOUR passed in this timezone.

    A digest is due when something has been waiting since before this instant:
    that flushes everything queued before today's send hour and leaves anything
    queued after it for tomorrow, so the send time never drifts.
    """
    local = now.astimezone(_resolve_timezone(tz_name))
    boundary = local.replace(hour=DAILY_DIGEST_HOUR, minute=0, second=0, microsecond=0)
    if boundary > local:
        boundary -= timedelta(days=1)
    return boundary


def _due_daily_digest_users(now, unclaimed) -> list:
    """digest_mode users whose send hour has passed for a queue that predates it.

    Deliberately no size trigger: a busy morning must not ship "today's digest"
    hours before the day is up, and the rest of the day would then queue behind
    a second one. The window is the whole point of the toggle.

    The boundary is per timezone, so it cannot be a single comparison. Distinct
    timezones are few — one OR'd term each keeps this one query rather than one
    per user, and keeps the due-ness test in the database like the rolling one.
    """
    timezones = set(QuietHours.objects.filter(digest_mode=True).values_list("timezone", flat=True))
    if not timezones:
        return []

    due = Q()
    for tz_name in timezones:
        due |= Q(
            notification__user__quiet_hours__timezone=tz_name,
            oldest__lte=_last_daily_send_boundary(now, tz_name),
        )

    groups = (
        _batchable_deliveries()
        .filter(unclaimed)
        .filter(notification__user__quiet_hours__digest_mode=True)
        # Timezone is in the grouping so the HAVING above can reference it; it
        # is one-to-one with the user, so this is still one group per user.
        .values("notification__user_id", "notification__user__quiet_hours__timezone")
        .annotate(oldest=Min("batch_queued_at"))
        .filter(due)
        .order_by("oldest")[:BATCH_GROUP_LIMIT]
    )
    return [g["notification__user_id"] for g in groups]


def send_batched_email_digests() -> int:
    """Collapse each user's waiting notifications into one email per event type.

    Called by a background task on a periodic schedule. Returns the number of
    digests sent.
    """
    now = timezone.now()
    window_start = now - timedelta(minutes=BATCH_WINDOW_MINUTES)
    stale_claim = now - BATCH_CLAIM_TIMEOUT
    unclaimed = Q(batch_claimed_at__isnull=True) | Q(batch_claimed_at__lt=stale_claim)

    _reap_exhausted_batches()
    _reap_deactivated_recipients()

    # Grouped with values().annotate() rather than values_list().distinct() so
    # the result can be ordered by the aggregate. An unordered LIMIT lets
    # Postgres return any matching rows it likes — and return the same ones
    # every run — so a backlog wider than BATCH_GROUP_LIMIT could starve some
    # users indefinitely. Oldest first is what actually drains it.
    #
    # The send/wait decision is a HAVING clause here rather than a check in
    # _send_one_digest: it belongs with the grouping it describes, and it keeps
    # the sweep from waking a group only to decide it is not due yet.
    groups = list(
        _batchable_deliveries()
        .filter(unclaimed)
        # digest_mode users are swept below on their own daily boundary. They
        # must also not share this query's budget: their rows sit queued for
        # hours while these sit for minutes, so on one oldest-first LIMIT every
        # digest row would sort ahead of every rolling row and starve it.
        .exclude(notification__user__quiet_hours__digest_mode=True)
        .values("notification__user_id", "notification__event_type")
        .annotate(oldest=Min("batch_queued_at"), waiting=Count("pk"))
        .filter(Q(oldest__lte=window_start) | Q(waiting__gte=BATCH_SIZE_TRIGGER))
        .order_by("oldest")[:BATCH_GROUP_LIMIT]
    )

    # (user_id, event_type); event_type None is one digest_mode user's daily
    # email, which covers every event type at once.
    due: list[tuple] = [(g["notification__user_id"], g["notification__event_type"]) for g in groups]
    due += [(user_id, None) for user_id in _due_daily_digest_users(now, unclaimed)]

    sent = 0
    for user_id, event_type in due:
        try:
            if _send_one_digest(user_id, event_type, now=now, unclaimed=unclaimed):
                sent += 1
        except Exception:
            # One user's bad address must not stop everyone else's digest.
            logger.exception("Digest failed for user %s (%s)", user_id, event_type or "daily")
    return sent


def _reap_deactivated_recipients() -> int:
    """Retire queued email for recipients deactivated after it was queued.

    _batchable_deliveries() stops it being sent; this is what takes it out of
    the queue afterwards. Without it the rows stay PENDING for good — invisible
    to every sweep, and counting against nothing that would ever clear them.
    """
    return NotificationDelivery.objects.filter(
        channel=Channel.EMAIL,
        status=DeliveryStatus.PENDING,
        batch_queued_at__isnull=False,
        notification__user__is_active=False,
    ).update(
        status=DeliveryStatus.FAILED,
        batch_claimed_at=None,
        error_message="Cancelled: the recipient's account was deactivated before the digest was sent.",
    )


def _reap_exhausted_batches() -> int:
    """Retire queued rows that have used up their attempts.

    A run can die between sending the email and recording it — a deploy or an
    OOM kill, both of which this codebase has seen. The claim is then reclaimed
    after BATCH_CLAIM_TIMEOUT and the digest goes out again. Charging the
    attempt at claim time (see _send_one_digest) bounds that at
    MAX_RETRY_ATTEMPTS duplicates instead of forever, and this is what takes the
    spent rows out of the queue afterwards — otherwise they sit PENDING for good,
    invisible to every sweep.
    """
    return NotificationDelivery.objects.filter(
        channel=Channel.EMAIL,
        status=DeliveryStatus.PENDING,
        batch_queued_at__isnull=False,
        attempts__gte=MAX_RETRY_ATTEMPTS,
    ).update(
        status=DeliveryStatus.FAILED,
        batch_claimed_at=None,
        error_message="Gave up after repeated digest delivery failures.",
    )


def _send_one_digest(user_id, event_type: str | None, *, now, unclaimed) -> bool:
    """Claim, send and settle one user's digest. Returns True when mail went out.

    ``event_type is None`` is a digest_mode user's daily email, which covers
    every event type they have waiting instead of one.
    """
    wanted = _batchable_deliveries().filter(notification__user_id=user_id).filter(unclaimed)
    if event_type is not None:
        wanted = wanted.filter(notification__event_type=event_type)
    wanted = list(wanted.values_list("pk", flat=True))
    if not wanted:
        return False

    # Claim by conditional UPDATE rather than SELECT FOR UPDATE. Under READ
    # COMMITTED, Postgres re-checks the WHERE against the row version it blocks
    # on, so a competing sweep's rows simply fall out of our result — and no
    # lock or transaction is left open across the SMTP conversation that
    # follows, which the connection budget in apps/common/db.py does not have
    # room for.
    #
    # The attempt is charged HERE, not after a successful send. A worker that
    # dies between the send and the settle would otherwise leave attempts
    # untouched, and the reclaim would mail the same digest again every
    # BATCH_CLAIM_TIMEOUT with nothing counting the repeats.
    claimed = (
        NotificationDelivery.objects.filter(pk__in=wanted)
        .filter(unclaimed)
        .update(batch_claimed_at=now, attempts=F("attempts") + 1)
    )
    if not claimed:
        return False

    rows = list(
        NotificationDelivery.objects.filter(pk__in=wanted, batch_claimed_at=now)
        .select_related("notification", "notification__user")
        .order_by("created_at")
    )
    if not rows:
        return False

    ids = [r.pk for r in rows]
    user = rows[0].notification.user
    notifications = [r.notification for r in rows]

    # Batching puts minutes between the decision to email and the email, and
    # the user can withdraw consent in that gap — from the unsubscribe link or
    # the preferences page. The preference is therefore re-read here rather
    # than trusted from queue time; cancelling on the unsubscribe endpoint
    # alone would have missed every other way to turn it off.
    # A daily digest spans event types, so the check is per row: one type being
    # switched off cancels its own notifications without taking the rest of the
    # digest with them.
    pref_cache: dict = {}
    keeping = [r for r in rows if Channel.EMAIL in _resolve_channels(user, r.notification.event_type, pref_cache)]
    keep_ids = {r.pk for r in keeping}
    cancelled = [r.pk for r in rows if r.pk not in keep_ids]

    if cancelled:
        logger.info("Cancelling %d queued email(s) for user %s: turned off", len(cancelled), user_id)
        NotificationDelivery.objects.filter(pk__in=cancelled).update(
            status=DeliveryStatus.FAILED,
            batch_claimed_at=None,
            error_message="Cancelled: the recipient turned this email off before it was sent.",
        )

    if not keeping:
        return False

    rows = keeping
    ids = [r.pk for r in rows]
    notifications = [r.notification for r in rows]

    try:
        _send_digest_email(user, event_type, notifications)
    except EmailNotSentError as exc:
        # The budget declined it, or there is no address to send to. Neither
        # gets better by trying again, and marking the rows delivered would put
        # a lie in the delivery table — the same trap the inline path had.
        logger.info("Digest for user %s (%s) not sent: %s", user_id, event_type, exc)
        NotificationDelivery.objects.filter(pk__in=ids).update(
            status=DeliveryStatus.FAILED,
            batch_claimed_at=None,
            error_message=str(exc)[:500],
        )
        return False
    except Exception as exc:
        logger.exception("Could not send the %s digest to %s", event_type, user_id)
        NotificationDelivery.objects.filter(pk__in=ids).update(
            batch_claimed_at=None,
            error_message=str(exc)[:500],
        )
        # Rows that have now run out of attempts leave the queue for good,
        # rather than being retried forever against an address that cannot
        # receive them.
        _reap_exhausted_batches()
        return False

    NotificationDelivery.objects.filter(pk__in=ids).update(
        status=DeliveryStatus.DELIVERED,
        delivered_at=timezone.now(),
    )
    logger.info("Sent %s digest covering %d notification(s) to user %s", event_type or "daily", len(ids), user_id)
    return True


def _send_digest_email(user, event_type: str | None, notifications: list) -> None:
    """One email standing in for every notification in the batch."""
    total = len(notifications)
    heading = _digest_heading(event_type, total)
    shown = notifications[:BATCH_MAX_ITEMS]

    context = {
        "heading": heading,
        "notifications": shown,
        "total": total,
        "overflow": total - len(shown),
        "user": user,
        "date": timezone.now(),
        "app_url": getattr(settings, "APP_URL", "http://localhost:8000"),
    }

    text_content = render_to_string("notifications/email/digest.txt", context)
    html_content = render_to_string("notifications/email/digest.html", context)

    msg = EmailMultiAlternatives(
        subject=heading,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
        to=[user.email],
        headers=list_unsubscribe_headers(user.pk, event_type),
    )
    msg.attach_alternative(html_content, "text/html")
    send_or_raise(msg)
