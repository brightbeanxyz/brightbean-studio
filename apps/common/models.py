"""Durable bookkeeping for outbound email.

Two tables, both read and written on the send path in ``apps.common.mail``:

``EmailSendCounter``
    The budget. One row per (scope, key, period) — the global daily total, and
    per-recipient hourly/daily totals.

``EmailSuppression``
    Addresses we have been told to stop mailing (hard bounce, spam complaint).

The state lives in the database rather than the cache for the same reason
``apps.analytics.quota`` gives: ``REDIS_URL`` is optional
(``config/settings/base.py``), so the fallback cache is a per-process
LocMemCache that every deploy and every dyno restart empties — precisely the
moments a budget most needs to hold. A cache-backed cap is also per-process, so
it silently multiplies by the worker count the first time the app scales out.
"""

from __future__ import annotations

from django.db import models


class EmailSendCounter(models.Model):
    """One counted bucket of outbound email.

    ``key`` is empty for the global scope and a truncated SHA-256 of the
    lowercased address for the per-recipient scopes, so the table never becomes
    a second copy of the user list. ``period_start`` is the bucket boundary
    (midnight UTC for daily scopes, the top of the hour for hourly ones), which
    is what makes expiry a comparison rather than a cleanup job.
    """

    class Scope(models.TextChoices):
        GLOBAL_DAY = "global_day", "Global (day)"
        RECIPIENT_HOUR = "recipient_hour", "Recipient (hour)"
        RECIPIENT_DAY = "recipient_day", "Recipient (day)"
        INVITE_ORG_DAY = "invite_org_day", "Invitations per organization (day)"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    key = models.CharField(max_length=64, blank=True, default="")
    period_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "common_email_send_counter"
        unique_together = [("scope", "key", "period_start")]

    def __str__(self) -> str:
        return f"{self.scope}:{self.key or '-'} @ {self.period_start.isoformat()} = {self.count}"


class EmailSuppression(models.Model):
    """An address we must stop sending to.

    Populated by the Resend bounce/complaint webhook and by hand through the
    admin. Rows are deleted, not flagged, to release an address — there is no
    state worth keeping for an address that has started accepting mail again.
    """

    class Reason(models.TextChoices):
        BOUNCED = "bounced", "Hard bounce"
        COMPLAINED = "complained", "Spam complaint"
        MANUAL = "manual", "Added by hand"

    address = models.EmailField(unique=True)
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.MANUAL)
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "common_email_suppression"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.address} ({self.reason})"
