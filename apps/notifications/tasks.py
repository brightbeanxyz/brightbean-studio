"""Background tasks for the notification system.

These are meant to be called by django-background-tasks or a cron schedule.
"""

import logging

from background_task import background

logger = logging.getLogger(__name__)


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
