"""Reading Google's shared API error envelope.

Every Google API this project talks to — YouTube Data v3, YouTube Analytics v2,
Google Business Profile — answers a failure with the same shape::

    {"error": {"code": 403, "message": "...", "status": "UNAUTHENTICATED",
               "errors": [{"reason": "quotaExceeded", "domain": "youtube.quota"}]}}

The interesting fact lives in ``errors[].reason`` or in ``status``, never in the
HTTP code alone: Google reports a spent daily quota as **403**, not 429, which is
why a naive ``status_code == 429`` check never sees it. This module is the one
place that knows how to read those fields, so the providers that share the
envelope don't each grow their own copy.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# A daily (or otherwise hard) budget is gone. Nothing will work again until the
# window rolls over, so the right response is to stop calling until then.
QUOTA_REASONS = frozenset({"quotaexceeded", "dailylimitexceeded"})

# A short burst throttle — requests-per-second, not requests-per-day. These
# deserve a pause measured in minutes; blocking until tomorrow would throw away
# a day of syncing over a momentary spike.
THROTTLE_REASONS = frozenset({"ratelimitexceeded", "userratelimitexceeded"})

# The token was rejected. Google spells this several ways depending on which of
# its API front-ends answered.
AUTH_REASONS = frozenset({"authenticationfailure", "autherror", "unauthenticated"})

_TAG_RE = re.compile(r"<[^>]+>")


def google_error_reasons(body: dict) -> set[str]:
    """Lower-cased ``error.errors[].reason`` values, plus ``error.status``.

    Both are read because neither is reliably present: the Data API populates
    ``errors[].reason`` while the Analytics API leans on ``status``
    (``"UNAUTHENTICATED"``), and a single response can carry both.
    """
    error = (body or {}).get("error")
    if not isinstance(error, dict):
        return set()

    reasons = set()
    for item in error.get("errors") or []:
        if isinstance(item, dict) and item.get("reason"):
            reasons.add(str(item["reason"]).lower())
    if error.get("status"):
        reasons.add(str(error["status"]).lower())
    return reasons


def google_error_message(body: dict) -> str:
    """``error.message`` with Google's inline HTML stripped, else ``""``.

    The quota message ships an ``<a href="...">quota</a>`` link that reads as
    markup anywhere we surface it.
    """
    error = (body or {}).get("error")
    if not isinstance(error, dict):
        return ""
    message = error.get("message")
    if not isinstance(message, str):
        return ""
    return _TAG_RE.sub("", message).strip()


# YouTube's Data API quota resets at midnight US/Pacific, not UTC.
_QUOTA_RESET_TZ = "America/Los_Angeles"

# Pacific midnight is 08:00 UTC under PST (UTC-8) and 07:00 under PDT (UTC-7).
# With no tz database to tell them apart, take the later one: unblocking an hour
# after the quota actually reset wastes an hour, unblocking an hour early spends
# the first calls of the new day re-learning that we are still blocked.
_QUOTA_RESET_FALLBACK_UTC_HOUR = 8


def next_google_quota_reset(now: datetime | None = None) -> datetime:
    """The next midnight US/Pacific, as an aware UTC datetime.

    Always *strictly* after ``now``, boundary seconds included: standing on a
    reset moment, the reset underfoot is spent and the answer is tomorrow's.
    Callers put this in ``QuotaExceededError.resets_at``, which the publisher
    and the analytics sync read as "blocked until", so an instant that had
    already elapsed would wave a blocked account straight back at an API still
    refusing it. ``_roll_until_future`` is where that guarantee is enforced,
    for both the zone-aware and the fallback branch.

    A naive ``now`` is taken as UTC, never as the host's zone. ``astimezone``
    would otherwise read it as local time and shift it by the host offset —
    on a machine east of Greenwich that is enough to return a reset moment
    that has already passed, which is the one thing this function must not do.

    Falls back to a fixed 08:00 UTC when the host has no tz database — some
    slim images ship without one, and ``requirements.txt`` pins ``tzdata`` for
    exactly that reason, but a missing zone must degrade rather than raise.
    """
    if now is None:
        now = datetime.now(UTC)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    try:
        pacific = ZoneInfo(_QUOTA_RESET_TZ)
    except (ZoneInfoNotFoundError, KeyError):
        return _next_utc_hour(now, _QUOTA_RESET_FALLBACK_UTC_HOUR)

    local = now.astimezone(pacific)
    midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return _roll_until_future(midnight.astimezone(UTC), now)


def _next_utc_hour(now: datetime, hour: int) -> datetime:
    target = now.astimezone(UTC).replace(hour=hour, minute=0, second=0, microsecond=0)
    return _roll_until_future(target, now)


def _roll_until_future(target: datetime, now: datetime) -> datetime:
    """Push ``target`` forward whole days until it is strictly after ``now``.

    Both branches end here so "strictly after" is enforced in one place rather
    than inferred separately from each branch's arithmetic — the zone-aware one
    reaches this already satisfied, and the shape of a later refactor can't
    quietly weaken it. Rolling in whole UTC days is fine as a backstop: a day
    that lands an hour off across a DST switch is still, emphatically, ahead.
    """
    while target <= now:
        target += timedelta(days=1)
    return target
