"""Housekeeping for the shared tables in this app."""

import logging

from background_task import background

logger = logging.getLogger(__name__)

# Daily is often enough: the rows are tiny and only a week of them is kept.
COUNTER_PURGE_INTERVAL_SECONDS = 24 * 60 * 60


@background(schedule=0)
def purge_email_counters():
    """Drop email budget buckets whose period is long past.

    One row per recipient per hour accumulates quickly and nothing else ever
    deletes them. Exceptions are swallowed deliberately: django-background-tasks
    backs a raising task off exponentially and deletes it after 25 attempts, and
    losing the schedule over a housekeeping failure is worse than the rows.
    """
    from .mail import purge_expired_counters

    try:
        deleted = purge_expired_counters()
    except Exception:
        logger.exception("Email counter purge failed")
        return

    if deleted:
        logger.info("Purged %d expired email counter row(s)", deleted)
