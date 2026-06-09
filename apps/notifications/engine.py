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
from django.template.loader import render_to_string
from django.utils import timezone

from .models import (
    Channel,
    DeliveryStatus,
    EventType,
    Notification,
    NotificationDelivery,
    NotificationPreference,
)

logger = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MINUTES = [1, 5, 30]

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

    if _is_in_quiet_hours(user) and event_type in NON_CRITICAL_EVENTS:
        # During quiet hours, only deliver in-app (silent). Skip email/webhook.
        channels_to_dispatch = [c for c in channels_to_dispatch if c == Channel.IN_APP]

    for channel in channels_to_dispatch:
        delivery = NotificationDelivery.objects.create(
            notification=notification,
            channel=channel,
            status=DeliveryStatus.PENDING,
        )
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


def _is_in_quiet_hours(user) -> bool:
    """Check if the user is currently in their quiet hours window."""
    from django.core.exceptions import ObjectDoesNotExist

    try:
        qh = user.quiet_hours
    except (AttributeError, ObjectDoesNotExist):
        return False

    if not qh.is_enabled or not qh.start_time or not qh.end_time:
        return False

    import zoneinfo

    try:
        user_tz = zoneinfo.ZoneInfo(qh.timezone)
    except (KeyError, zoneinfo.ZoneInfoNotFoundError):
        user_tz = zoneinfo.ZoneInfo("UTC")

    now_local = timezone.now().astimezone(user_tz).time()

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
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)


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
    pending = NotificationDelivery.objects.filter(
        status=DeliveryStatus.PENDING,
        next_retry_at__isnull=False,
        next_retry_at__lte=now,
        attempts__lt=MAX_RETRY_ATTEMPTS,
    ).select_related("notification", "notification__user")

    count = 0
    for delivery in pending:
        _dispatch(delivery)
        count += 1

    return count
