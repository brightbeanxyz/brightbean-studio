"""The one place outbound email can be stopped.

Every email in the product is built inline with ``EmailMultiAlternatives`` in
half a dozen places, plus allauth's own — there is no ``send_email()`` helper to
hang a guard on. ``EMAIL_BACKEND`` is therefore the only true choke point, and
this is it.

``BudgetedEmailBackend`` wraps whatever backend ``EMAIL_INNER_BACKEND`` names
rather than subclassing the SMTP one. Wrapping is what lets development
(console) and the test suite (locmem) exercise exactly the same decisions, so
the drops are testable; a subclass of the SMTP backend would be dead code
everywhere except production.

Four things can stop a message, checked in this order:

1. ``EMAIL_SENDING_ENABLED = False`` — the incident lever, no deploy needed.
2. The recipient is in ``EmailSuppression`` (hard bounce or spam complaint).
3. The per-recipient hourly/daily cap, for ``notification``-class mail only.
4. The global daily cap, which nothing bypasses.

The class comes from an ``X-Brightbean-Email-Class`` header (see
``transactional()``). ``transactional`` mail — password reset, an invitation, a
magic link — skips the per-recipient cap but never the global one, so a storm of
notifications can never lock someone out of their own account.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django.db import DatabaseError, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

EMAIL_CLASS_HEADER = "X-Brightbean-Email-Class"
CLASS_TRANSACTIONAL = "transactional"
CLASS_NOTIFICATION = "notification"


class BudgetExceededError(Exception):
    """Raised internally to unwind a partial reservation. Never escapes ``_allow``."""


class EmailNotSentError(Exception):
    """The backend declined to send. Not a failure worth retrying."""


def send_or_raise(msg) -> None:
    """Send a message, or raise ``EmailNotSentError`` if it was dropped.

    Use this instead of ``msg.send()`` anywhere the outcome matters.

    Django's contract is that ``send()`` returns the number of messages
    accepted, and a backend that declines one raises nothing — so a caller
    wrapped in ``try/except`` sees a drop as success. That is how the portal
    came to invalidate a client's only working login link and then report the
    replacement as sent, and how an invitation could spend the recipient's
    allowance on an email that never left. Raising turns "0 accepted" into
    something a caller has to deal with.
    """
    if not msg.send(fail_silently=False):
        raise EmailNotSentError("stopped by the outbound email budget, or no address to send to")


def transactional() -> dict[str, str]:
    """Headers marking a message as one the user is actively waiting on.

    Pass as ``extra_headers=transactional()`` when building the message. Use it
    only for mail a person asked for and is sitting in front of — a password
    reset, an invitation, a magic link. Everything else is a notification and
    should stay subject to the per-recipient cap.
    """
    return {EMAIL_CLASS_HEADER: CLASS_TRANSACTIONAL}


def _hour_start(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0)


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _recipient_key(address: str) -> str:
    """Stable, non-reversible identifier for a recipient.

    Hashed so the budget table does not become a second copy of the user list —
    the counters only ever need equality, never the address itself.
    """
    return hashlib.sha256(address.strip().lower().encode()).hexdigest()[:32]


def _limit(name: str, default: int) -> int:
    """The configured cap. Negative means unlimited; 0 means send nothing.

    That way round deliberately: an operator reaching for this during an
    incident and typing 0 means "stop", and it would be a nasty surprise if 0
    were the code for "no limit at all".
    """
    value = getattr(settings, name, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring non-numeric %s=%r; falling back to %d", name, value, default)
        return default


def reserve_budget(scope: str, key: str, period_start: datetime, limit: int, *, fail_open: bool = True) -> bool:
    """Claim one unit of a budget, or report that it is spent.

    Locks the single counter row for the check-and-increment, which is the only
    way two workers cannot both see "one left". At the volumes involved — a few
    thousand messages a day, not a second — the lock costs nothing, and it is
    taken and released *before* the SMTP conversation starts, never held across
    it.

    A negative ``limit`` means unlimited: the counter is still incremented,
    because the count is the thing that tells us where to set the limit.

    ``fail_open`` decides what an unreachable database means. For mail someone
    is waiting on, it means "send anyway" — a broken counter table must not
    stop a password reset. For everything else it means "don't", because a send
    storm is exactly what exhausts the connection pool (see apps/common/db.py),
    so the moment this query starts failing is the moment the cap matters most.
    Failing open there would lift the ceiling precisely during the incident it
    exists to contain.
    """
    from .models import EmailSendCounter

    try:
        with transaction.atomic():
            EmailSendCounter.objects.get_or_create(
                scope=scope,
                key=key,
                period_start=period_start,
                defaults={"count": 0},
            )
            row = EmailSendCounter.objects.select_for_update().get(scope=scope, key=key, period_start=period_start)
            if limit >= 0 and row.count >= limit:
                return False
            # Not F("count") + 1: the row is locked, so the value in hand is
            # current, and a plain integer keeps ``row`` usable afterwards.
            row.count += 1
            row.save(update_fields=["count"])
            return True
    except DatabaseError:
        logger.exception(
            "Email budget check failed for %s:%s — %s the send",
            scope,
            key,
            "allowing" if fail_open else "dropping",
        )
        return fail_open


def _is_suppressed(addresses: list[str]) -> bool:
    from .models import EmailSuppression

    lowered = [a.strip().lower() for a in addresses if a]
    if not lowered:
        return False
    try:
        return EmailSuppression.objects.filter(address__in=lowered).exists()
    except DatabaseError:
        logger.exception("Suppression lookup failed for %s — allowing the send", lowered)
        return False


class BudgetedEmailBackend(BaseEmailBackend):
    """Applies the budget, then hands the survivors to the real backend."""

    def __init__(self, fail_silently: bool = False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._kwargs = kwargs

    def _inner(self):
        inner = getattr(settings, "EMAIL_INNER_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
        return get_connection(backend=inner, fail_silently=self.fail_silently, **self._kwargs)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        allowed = [m for m in email_messages if self._allow(m)]
        if not allowed:
            return 0

        # Strip the routing header only from the messages that survived. Doing
        # it during the decision would mean a dropped message came back
        # unclassified, and anything that re-sent it would quietly demote a
        # password reset to a notification.
        for message in allowed:
            if message.extra_headers:
                message.extra_headers.pop(EMAIL_CLASS_HEADER, None)

        return self._inner().send_messages(allowed) or 0

    def _allow(self, message) -> bool:
        # recipients() is to + cc + bcc. Suppression has to cover all of them —
        # a bounced address is bounced wherever it appears — but the
        # per-recipient cap is about the person the message is addressed to, so
        # a bcc'd audit mailbox must not eat their budget.
        recipients = list(getattr(message, "recipients", lambda: [])())
        addressed = list(getattr(message, "to", None) or [])
        subject = (getattr(message, "subject", "") or "")[:120]
        klass = (message.extra_headers or {}).get(EMAIL_CLASS_HEADER, CLASS_NOTIFICATION)

        if not getattr(settings, "EMAIL_SENDING_ENABLED", True):
            logger.warning("Email dropped (sending disabled): %r to %s", subject, recipients)
            return False

        if not recipients:
            return False

        if _is_suppressed(recipients):
            logger.warning("Email dropped (recipient suppressed): %r to %s", subject, recipients)
            return False

        now = timezone.now()
        hourly = _limit("EMAIL_RECIPIENT_HOURLY_LIMIT", 6)
        daily = _limit("EMAIL_RECIPIENT_DAILY_LIMIT", 20)
        global_limit = _limit("EMAIL_DAILY_SEND_LIMIT", 2000)

        # Every reservation for one message happens in one transaction, so a cap
        # hit at the last step gives back what the earlier steps took. Charging
        # for a message that is then dropped would inflate the counters during
        # exactly the storm this exists to contain, making the caps bite harder
        # and harder for mail nobody ever received.
        waited_on = klass == CLASS_TRANSACTIONAL
        try:
            with transaction.atomic():
                if not waited_on:
                    for address in addressed:
                        key = _recipient_key(address)
                        if not reserve_budget("recipient_hour", key, _hour_start(now), hourly, fail_open=False):
                            raise BudgetExceededError(f"recipient hourly cap {hourly}")
                        if not reserve_budget("recipient_day", key, _day_start(now), daily, fail_open=False):
                            raise BudgetExceededError(f"recipient daily cap {daily}")

                if not reserve_budget("global_day", "", _day_start(now), global_limit, fail_open=waited_on):
                    raise BudgetExceededError(f"global daily cap {global_limit}")
        except BudgetExceededError as exc:
            log = logger.error if "global" in str(exc) else logger.warning
            log("Email dropped (%s): %r to %s — class=%s", exc, subject, recipients, klass)
            return False

        return True


def purge_expired_counters(older_than_days: int = 7) -> int:
    """Drop counter rows whose period is long past. Returns the number deleted."""
    from .models import EmailSendCounter

    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = EmailSendCounter.objects.filter(period_start__lt=cutoff).delete()
    return deleted
