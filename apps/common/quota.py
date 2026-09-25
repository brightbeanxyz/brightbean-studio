"""The shared quota circuit breaker.

When a platform says "you have spent your budget", the only useful response is
to stop calling until the budget returns. Without that, every subsequent call in
the run — and every call in the next run — is a guaranteed failure that still
costs a request, still logs a warning, and still leaves the work looking undone.
The breaker turns one platform answer into a decision every caller respects.

It lives here, not under one app, because the budget being spent is not one
app's: YouTube meters its Data API per OAuth *client*, so the analytics sync,
the inbox poll and the health check all draw on the same regular pool of 10,000
units a day. A breaker only one of them consulted would watch the other two
spend the budget it was guarding. Uploads are not in that pool: since June 2026
``videos.insert`` has a bucket of its own (see ``_PLATFORM_SCOPES``), so video
publishing neither spends the budget these three share nor stops when it runs
out. The ``ProviderQuotaBlock`` row stays in ``apps.analytics``
(imported lazily below) because moving a table earns a migration and buys
nothing — what needed to be shared is the decision, not the storage.

The state lives in the database rather than the cache on purpose: ``REDIS_URL``
is optional (``config/settings/base.py``), so the fallback cache is per-process
LocMemCache, which is emptied by every deploy and every dyno restart — precisely
the moments a block most needs to survive.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from providers.exceptions import is_long_window

logger = logging.getLogger(__name__)

# Stand-in key for a platform whose credentials we could not resolve. Grouping
# those together is right: they all failed the same way, and none of them can be
# told apart by project.
_UNKNOWN_CREDENTIAL = "unknown"

# How each platform's budgets are named, and the single source for it.
#
# A platform that meters one pool uses "" — the empty scope is not a missing
# value, it is that platform's only budget. YouTube meters two that the readers
# here use, and conflating them would stop the cheap Data API call because the
# expensive Analytics one ran dry. Every caller must resolve the scope the same
# way or the breaker splits in two: one side writes a row the other never looks
# up, and both keep calling an API that has already refused.
#
# YouTube has a third budget, which is deliberately absent from this map:
# ``videos.insert`` draws on its own bucket of 100 calls a day, so the provider
# files an upload's refusal under "upload". Nothing here reads that scope, so
# a spent upload bucket cannot block the inbox, analytics or health check, and
# a spent regular pool cannot block an upload. Filed under "data", as it was
# until the provider learned of the split, a refusal recorded here would stop
# all three for the rest of the day over a budget none of them spends. The
# publisher does not consult the breaker at all: it reschedules each post for
# its exception's ``resets_at``.
_PLATFORM_SCOPES: dict[str, tuple[str, str]] = {
    "youtube": ("analytics", "data"),
}

# Used only when a platform refuses on quota without saying when it will stop.
# Long enough not to re-ask every cycle, short enough that a platform whose
# window we cannot read still recovers the same day.
DEFAULT_QUOTA_BACKOFF = timedelta(hours=1)


def scopes_for(platform: str) -> tuple[str, str]:
    """This platform's ``(account_scope, post_scope)`` budget names."""
    return _PLATFORM_SCOPES.get(platform, ("", ""))


def read_scope(platform: str) -> str:
    """The budget a comment poll or a profile probe draws on.

    Both are Data API reads on YouTube, and the platform's only budget
    everywhere else — so this is ``scopes_for``'s second element by definition,
    named because two callers outside analytics want it and neither should have
    to know which tuple position it is.
    """
    return scopes_for(platform)[1]


def credential_key(credentials: dict | None) -> str:
    """Stable, non-secret identifier for the app credentials behind a call.

    Two accounts that resolve to the same OAuth client are drawing on the same
    upstream quota pool, so they must share a breaker row. Hashing gives that
    equivalence without putting a client_id in the database or the logs.
    """
    client_id = (credentials or {}).get("client_id") or ""
    if not client_id:
        return _UNKNOWN_CREDENTIAL
    return hashlib.sha256(str(client_id).encode()).hexdigest()[:16]


def quota_blocked_until(
    platform: str,
    key: str,
    scope: str = "",
    *,
    cache: dict | None = None,
) -> datetime | None:
    """When this credential's quota comes back, or ``None`` if it is not blocked.

    ``cache`` is an optional per-run dict. A sync pass asks this once per
    account, and accounts overwhelmingly share one credential, so without it the
    breaker would cost a query per account to answer the same question.
    """
    cache_key = (platform, key, scope)
    if cache is not None and cache_key in cache:
        blocked_until = cache[cache_key]
    else:
        from apps.analytics.models import ProviderQuotaBlock

        blocked_until = (
            ProviderQuotaBlock.objects.filter(platform=platform, credential_key=key, quota_scope=scope)
            .values_list("blocked_until", flat=True)
            .first()
        )
        if cache is not None:
            cache[cache_key] = blocked_until

    if blocked_until is None or blocked_until <= timezone.now():
        return None
    return blocked_until


def trip_quota_block(
    platform: str,
    key: str,
    scope: str = "",
    *,
    until: datetime,
    reason: str = "",
    cache: dict | None = None,
) -> None:
    """Record that this credential's quota is spent until ``until``.

    Idempotent by ``(platform, credential_key, quota_scope)``: a later failure
    simply moves the expiry, so a throttle that arrives after a daily
    exhaustion cannot shorten the longer block.
    """
    from apps.analytics.models import ProviderQuotaBlock

    # Lock the row while comparing deadlines. Reading the old deadline before
    # update_or_create lets a concurrent short throttle overwrite a daily block.
    # get_or_create also handles two workers racing to insert the first row.
    with transaction.atomic():
        block, created = ProviderQuotaBlock.objects.select_for_update().get_or_create(
            platform=platform,
            credential_key=key,
            quota_scope=scope,
            defaults={"blocked_until": until, "reason": reason[:500]},
        )
        extended = not created and until > block.blocked_until
        if extended:
            block.blocked_until = until
            block.reason = reason[:500]
            block.save(update_fields=["blocked_until", "reason", "tripped_at"])
        until = block.blocked_until
    if cache is not None:
        cache[(platform, key, scope)] = until
    if not (created or extended):
        return

    # A lost day is worth an event in Sentry; a few minutes' throttle is the
    # breaker working as designed, and logging it at the same level is how an
    # alert gets trained away. Judged on the same threshold the user-facing copy
    # uses, so "we told someone it's serious" and "we told the user it's
    # serious" can never disagree.
    level = logging.ERROR if is_long_window(until) else logging.WARNING
    logger.log(
        level,
        "%s quota block tripped for credential %s (scope=%r) until %s — %s",
        platform,
        key,
        scope,
        until.isoformat(),
        reason[:200],
    )


def trip_from_exception(
    platform: str,
    key: str,
    exc: Exception,
    *,
    default_scope: str | None = None,
    fallback_backoff: timedelta = DEFAULT_QUOTA_BACKOFF,
    cache: dict | None = None,
) -> None:
    """Record a platform's refusal, reading the window and budget off ``exc``.

    One function rather than a copy per caller, because the copies are where the
    callers drifted: the inbox and the analytics sync each reimplemented this
    and picked *different* scope fallbacks, so a single-pool platform blocked by
    one was invisible to the other — each kept calling an API the other already
    knew had refused.

    The provider knows both facts and puts them on the exception: ``resets_at``
    (midnight US/Pacific for YouTube's Data API) and ``quota_scope``. Prefer
    them, and fall back only when a platform gives neither.
    """
    until = getattr(exc, "resets_at", None) or (timezone.now() + fallback_backoff)
    scope = getattr(exc, "quota_scope", "") or (default_scope if default_scope is not None else read_scope(platform))
    trip_quota_block(platform, key, scope, until=until, reason=str(exc), cache=cache)
