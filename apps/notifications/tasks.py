"""Background tasks for the notification system.

These are meant to be called by django-background-tasks or a cron schedule.
"""

import logging
from datetime import timedelta

from background_task import background
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_daily_digests():
    """Send daily email digests to users who have digest mode enabled.

    NOT REGISTERED on any schedule, and so never runs today — ``QuietHours``
    exposes a "Daily digest" toggle in the preferences UI that currently does
    nothing. Wiring it up properly means routing those users' mail through
    ``engine.send_batched_email_digests`` with a daily window instead of adding
    a second email on top of the immediate one, which is a change worth making
    on its own rather than inside the storm fix. Left here, and kept rendering
    correctly against the shared digest templates, so that work starts from
    something that runs.
    """
    from .models import Notification, QuietHours

    digest_users = QuietHours.objects.filter(digest_mode=True).select_related("user")

    for qh in digest_users:
        user = qh.user
        if not user.is_active:
            continue

        since = timezone.now() - timedelta(hours=24)
        notifications = list(
            Notification.objects.filter(
                user=user,
                created_at__gte=since,
            ).order_by("-created_at")[:50]
        )

        if not notifications:
            continue

        context = {
            "heading": f"Daily digest - {len(notifications)} notification{'s' if len(notifications) != 1 else ''}",
            "notifications": notifications,
            "total": len(notifications),
            "overflow": 0,
            "user": user,
            "date": timezone.now(),
            "app_url": getattr(settings, "APP_URL", "http://localhost:8000"),
        }

        try:
            text_content = render_to_string("notifications/email/digest.txt", context)
            html_content = render_to_string("notifications/email/digest.html", context)

            msg = EmailMultiAlternatives(
                subject=f"Daily Digest - {len(notifications)} notification{'s' if len(notifications) != 1 else ''}",
                body=text_content,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            logger.info("Sent daily digest to %s (%d notifications)", user.email, len(notifications))
        except Exception:
            logger.exception("Failed to send daily digest to %s", user.email)


# How often the recurring delivery-retry sweep runs; registered on a repeating
# schedule by apps.notifications.apps.NotificationsConfig.
NOTIFICATION_RETRY_INTERVAL_SECONDS = 60  # every minute

# The batched-email sweep runs on the same cadence. It is the batching window
# (engine.BATCH_WINDOW_MINUTES), not this interval, that decides when a digest
# actually goes out; running every minute only keeps the delay from the window
# closing to the email leaving down to seconds.
NOTIFICATION_BATCH_INTERVAL_SECONDS = 60


@background(schedule=0)
def retry_failed_deliveries():
    """Retry pending notification deliveries that are past their backoff window.

    Registered on a 1-minute repeating schedule. ``notify()`` dispatches the
    first attempt inline; transient email/webhook failures leave the delivery
    PENDING with a ``next_retry_at`` that only this sweep acts on.
    """
    from .engine import retry_failed_deliveries as _retry

    count = _retry()
    if count > 0:
        logger.info("Retried %d failed notification deliveries", count)


@background(schedule=0)
def send_batched_email_digests():
    """Collapse each user's waiting notifications into a single email.

    Registered on a 1-minute repeating schedule. ``notify()`` deliberately does
    not dispatch email for the events in ``engine.BATCHED_EMAIL_EVENTS``, so
    this is the ONLY thing that ever sends them — which is why nothing is
    allowed to escape here.

    django-background-tasks reacts to a raising task by backing off
    ``attempts ** 4 + 5`` seconds and, after 25 attempts, deleting the task
    outright with no repetition. A single bad row — a user with no email
    address, a template that won't render — would therefore turn "every minute"
    into "every few hours" and then into "never", and the only thing that would
    bring it back is the next release running ``migrate``. Publish-failure mail
    would stop with no error anyone would see.
    """
    from .engine import send_batched_email_digests as _send

    try:
        count = _send()
    except Exception:
        logger.exception("Batched digest sweep failed")
        return

    if count > 0:
        logger.info("Sent %d batched notification digest(s)", count)
