"""Rate-limit primitives for the Agent API.

Two orthogonal concerns live here:

1. ``PLATFORM_DAILY_POST_LIMIT`` — channel-aligned caps on how many
   scheduled-or-published PlatformPost rows an API key may create per
   ``SocialAccount`` per rolling 24h window. Numbers come from each
   platform's own developer docs (May 2026); see ``docs/agent-api.md``
   for the source links. The publisher's own ``RateLimitState`` tracks
   the *outgoing* upstream platform quota separately — these layers
   compose; neither replaces the other.

2. Per-key / per-workspace / per-IP HTTP throttles via ``django-ratelimit``,
   exposed as small wrapper helpers so each router stays declarative.

The 429 body shape is uniform across all tiers so agents can self-throttle
on ``tier`` without parsing free text.
"""

from __future__ import annotations

import datetime as dt

from django.conf import settings
from django.core.cache import cache as _cache
from django.http import HttpRequest
from django.utils import timezone
from django_ratelimit.core import is_ratelimited
from ninja.errors import HttpError

from apps.api_keys.models import ApiKey
from apps.composer.models import PlatformPost
from apps.social_accounts.models import SocialAccount

# ---------------------------------------------------------------------------
# Tier 2 — channel-aligned per-(SocialAccount, 24h) creation caps
# ---------------------------------------------------------------------------

#: Default platform cap when ``daily_post_limit_override`` on the
#: ``SocialAccount`` row isn't set. Numbers chosen at or just below the
#: platform's own published cap; see the plan file for justification and
#: source links. Lower bound (``_DEFAULT_FALLBACK``) covers unknown future
#: platforms safely.
#:
#: Keys MUST match the actual ``SocialAccount.platform`` values, which
#: come from ``apps.credentials.models.PlatformCredential.Platform`` —
#: not invented variants. Codex review flagged the previous
#: ``"facebook_page"`` key as a no-op (the real platform code is
#: ``"facebook"``), which silently dropped every Facebook account into
#: ``_DEFAULT_FALLBACK=50/day`` instead of the intended 200/day cap.
PLATFORM_DAILY_POST_LIMIT: dict[str, int] = {
    "linkedin_personal": 100,
    "linkedin_company": 100,
    "facebook": 200,
    "instagram": 25,
    "instagram_login": 25,
    "tiktok": 15,
    "youtube": 50,
    "pinterest": 100,
    "threads": 250,
    "mastodon": 200,
    "bluesky": 200,
    "google_business": 50,
}

_DEFAULT_FALLBACK = 50


def resolve_platform_limit(social_account: SocialAccount) -> int:
    """Effective per-24h cap for one ``SocialAccount``.

    Order: per-account override → platform default → fallback.

    Note the explicit ``is not None`` check: ``daily_post_limit_override``
    is a ``PositiveIntegerField(null=True)``, so an admin can legitimately
    set it to ``0`` to lock the account out of any creation. A naked
    ``if override:`` would treat 0 as "no override" and fall through to
    the platform default (e.g. LinkedIn 100/day), silently defeating the
    lockout.
    """
    override = getattr(social_account, "daily_post_limit_override", None)
    if override is not None:
        return int(override)
    return PLATFORM_DAILY_POST_LIMIT.get(social_account.platform, _DEFAULT_FALLBACK)


#: Statuses that *consume* the upstream platform's posting budget.
#:
#: A row only pressures the platform from the moment it leaves "draft" —
#: scheduled rows are queued for the publisher, publishing rows are
#: mid-flight on a platform API call, published rows already spent a
#: slot, and failed rows almost certainly did too (the platform 4xx'd
#: AFTER we made the call). Drafts are local DB state only; they have
#: not touched the platform yet, so counting them would block scheduling
#: for an agent who built a 25-post Instagram draft queue.
QUOTA_CONSUMING_STATUSES = frozenset({"scheduled", "publishing", "published", "failed"})


def count_recent_creations(social_account: SocialAccount, *, window_hours: int = 24) -> int:
    """Count PlatformPost rows in the platform-budget-consuming states.

    Filtered to ``QUOTA_CONSUMING_STATUSES`` and to rows whose
    ``updated_at`` falls inside the window. Codex review flagged that
    the previous ``created_at`` filter let an agent bypass the cap by
    creating drafts (which don't count) and then scheduling them more
    than 24 h later — the newly quota-consuming rows had a stale
    ``created_at`` outside the window and slipped through.

    ``updated_at`` is bumped by ``transition_platform_post`` whenever
    the status changes (including the moment a draft enters scheduled),
    so it is a faithful approximation of "when did this row consume a
    platform slot". Edits that touch other fields also bump it; the
    over-counting is conservative — agents hit the cap slightly earlier
    than the platform's own count, which is the safe direction.
    """
    cutoff = timezone.now() - dt.timedelta(hours=window_hours)
    return PlatformPost.objects.filter(
        social_account=social_account,
        updated_at__gte=cutoff,
        status__in=QUOTA_CONSUMING_STATUSES,
    ).count()


def check_platform_quota(social_account: SocialAccount) -> None:
    """Raise an ``HttpError(429, ...)`` if the per-account cap is reached.

    Call this immediately before creating a ``PlatformPost`` row in any
    write endpoint. The 24h-rolling check is a single indexed count, so
    it's cheap enough to run on every write.
    """
    limit = resolve_platform_limit(social_account)
    used = count_recent_creations(social_account)
    if used >= limit:
        # Compute when the oldest quota-consuming row ages out, so the
        # client gets an honest Retry-After rather than guessing. Match
        # the same filter as count_recent_creations to keep the two
        # numbers internally consistent.
        # Match the same filter as ``count_recent_creations`` so the
        # two numbers stay internally consistent; computing the oldest
        # quota-consuming ``updated_at`` lets ``retry_after`` reflect
        # when the bucket will next free up.
        oldest = (
            PlatformPost.objects.filter(
                social_account=social_account,
                updated_at__gte=timezone.now() - dt.timedelta(hours=24),
                status__in=QUOTA_CONSUMING_STATUSES,
            )
            .order_by("updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        retry_after_seconds = int((oldest + dt.timedelta(hours=24) - timezone.now()).total_seconds()) if oldest else 60
        # 1s floor so the client doesn't hammer us at the boundary.
        retry_after_seconds = max(retry_after_seconds, 1)
        raise HttpError(
            429,
            _format_quota_message(
                tier=f"platform_quota:{social_account.platform}",
                limit=limit,
                remaining=0,
                retry_after=retry_after_seconds,
            ),
        )


def _format_quota_message(*, tier: str, limit: int, remaining: int, retry_after: int) -> str:
    """Plain-text body for the HttpError so Ninja's default 429 page renders.

    The router-level error handler in ``api.py`` rewraps this into the
    uniform JSON shape with a ``Retry-After`` header.
    """
    return f"rate_limited tier={tier} limit={limit} remaining={remaining} retry_after={retry_after}"


# ---------------------------------------------------------------------------
# Tier 1 — HTTP DoS protection via django-ratelimit
# ---------------------------------------------------------------------------

#: Defaults — overridable per-key via ``ApiKey.rate_override_*`` columns
#: so an admin can loosen a single key without bumping the global default.
DEFAULT_WRITE_RATE = "120/m"
DEFAULT_READ_RATE = "300/m"
WORKSPACE_AGG_WRITE_RATE = "1000/m"
IP_FAILED_AUTH_RATE = "10/m"

# ``django-ratelimit`` keys are computed by callable accessors; these
# helpers consolidate the convention so individual routes stay clean.


def _ratelimit_key_apikey_writes(_group: str, request: HttpRequest) -> str:
    api_key: ApiKey = request.auth  # type: ignore[attr-defined]  # set by ApiKeyAuth
    return f"apikey:{api_key.id}:w"


def _ratelimit_key_apikey_reads(_group: str, request: HttpRequest) -> str:
    api_key: ApiKey = request.auth  # type: ignore[attr-defined]
    return f"apikey:{api_key.id}:r"


def _ratelimit_key_workspace_writes(_group: str, request: HttpRequest) -> str:
    api_key: ApiKey = request.auth  # type: ignore[attr-defined]
    return f"ws:{api_key.workspace_id}:w"


def _override_or(api_key: ApiKey, attr: str, default: str) -> str:
    """Pick the per-key override rate or fall back to the default.

    ``is not None`` (rather than ``if override:``) so that an explicit
    ``0`` value is honoured as "0 requests per minute" — admins use
    that to freeze a misbehaving key without revoking it.
    """
    override = getattr(api_key, attr, None)
    if override is not None:
        return f"{int(override)}/m"
    return default


def enforce_http_rate_limits(request: HttpRequest, *, is_write: bool) -> None:
    """Stack the HTTP-level tiers and raise 429 if any trip.

    Centralized here so routers don't each re-import django-ratelimit
    helpers. Per-tier rates honour per-key overrides; the workspace
    aggregate is global.
    """
    api_key: ApiKey = request.auth  # type: ignore[attr-defined]
    tier_rate = (
        _override_or(api_key, "rate_override_writes", DEFAULT_WRITE_RATE)
        if is_write
        else _override_or(api_key, "rate_override_reads", DEFAULT_READ_RATE)
    )
    tier_key = _ratelimit_key_apikey_writes if is_write else _ratelimit_key_apikey_reads
    if is_ratelimited(
        request=request,
        group=f"agent_api:apikey:{'w' if is_write else 'r'}",
        key=tier_key,
        rate=tier_rate,
        increment=True,
    ):
        raise HttpError(
            429,
            _format_quota_message(
                tier="per_key_writes" if is_write else "per_key_reads",
                limit=_parse_rate_num(tier_rate),
                remaining=0,
                retry_after=60,
            ),
        )
    if is_write and is_ratelimited(
        request=request,
        group="agent_api:workspace:w",
        key=_ratelimit_key_workspace_writes,
        rate=WORKSPACE_AGG_WRITE_RATE,
        increment=True,
    ):
        raise HttpError(
            429,
            _format_quota_message(
                tier="per_workspace_writes",
                limit=_parse_rate_num(WORKSPACE_AGG_WRITE_RATE),
                remaining=0,
                retry_after=60,
            ),
        )
    # Global instance cap — optional, env-driven.
    global_cap = getattr(settings, "BB_API_LIMIT", None)
    if global_cap and is_ratelimited(
        request=request,
        group="agent_api:global",
        key=lambda _g, _r: "global",
        rate=f"{int(global_cap)}/m",
        increment=True,
    ):
        raise HttpError(
            429,
            _format_quota_message(
                tier="global",
                limit=int(global_cap),
                remaining=0,
                retry_after=60,
            ),
        )


def _parse_rate_num(rate: str) -> int:
    return int(rate.split("/", 1)[0])


# ---------------------------------------------------------------------------
# Failed-auth IP throttle — special-case, no api_key on request
# ---------------------------------------------------------------------------
#
# We deliberately *don't* use django-ratelimit here. Its semantics are
# "ratelimited iff usage > limit" — which means a rate of "10/m" lets
# 10 requests in AND THEN serves an 11th before short-circuiting on
# the 12th. For a brute-force defense that's an off-by-one we don't
# want: the budget is "10 failed attempts," period.
#
# Instead we drive Django's cache directly: ``cache.add`` seeds the
# bucket with a TTL on the first failure, ``cache.incr`` bumps it on
# subsequent failures (preserving the TTL), and the threshold check
# is the tighter ``count >= limit``. Same response shape on the
# blocked path (401, not 429) so an attacker can't detect the throttle.

_AUTH_FAIL_LIMIT = 10
_AUTH_FAIL_WINDOW_SECONDS = 60


def _auth_fail_cache_key(request: HttpRequest) -> str:
    return f"agent_api:auth_fail:{_client_ip(request) or 'anon'}"


def is_failed_auth_ip_blocked(request: HttpRequest) -> bool:
    """True iff the IP has accumulated ``>= _AUTH_FAIL_LIMIT`` failures
    in the current rolling window. Read-only — no increment.
    """
    return _cache.get(_auth_fail_cache_key(request), 0) >= _AUTH_FAIL_LIMIT


def record_failed_auth(request: HttpRequest) -> None:
    """Increment the failed-auth counter for this IP.

    On the first failure, ``cache.add`` seeds the bucket with the
    window TTL. On subsequent failures, ``cache.incr`` bumps the
    counter without touching the TTL — so the window stays anchored
    at the *first* failure, not the most recent one.
    """
    key = _auth_fail_cache_key(request)
    if not _cache.add(key, 1, _AUTH_FAIL_WINDOW_SECONDS):
        try:
            _cache.incr(key)
        except ValueError:
            # Race: the key's TTL expired between our ``add`` (which
            # returned False because the key existed) and the incr
            # (which now finds nothing). Re-seed.
            _cache.set(key, 1, _AUTH_FAIL_WINDOW_SECONDS)


def _client_ip(request: HttpRequest) -> str | None:
    """Return the originating client IP, honouring proxies safely.

    Codex review flagged: the previous version unconditionally trusted
    the leftmost ``X-Forwarded-For`` value, which a remote client can
    set to any string. That defeats the failed-auth IP throttle (rotate
    XFF per request to escape the per-IP bucket) and lets the attacker
    pin audit-log rows to a victim's IP.

    Hardening: only honour ``X-Forwarded-For`` when the direct
    ``REMOTE_ADDR`` is in ``settings.BB_TRUSTED_PROXIES``. On platforms
    that terminate TLS at a proxy you actually run (Cloudflare, ALB,
    nginx, …), set that list in env config. Otherwise fall back to the
    socket peer — which is the only IP we can vouch for ourselves.
    """
    trusted = set(getattr(settings, "BB_TRUSTED_PROXIES", ()) or ())
    remote = request.META.get("REMOTE_ADDR")
    if trusted and remote in trusted:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            # Per RFC 7239 the rightmost value is the closest proxy to
            # us; we want the originating client, which is the leftmost
            # value that wasn't itself a trusted proxy. Cheapest safe
            # heuristic: take the leftmost untrusted hop.
            hops = [h.strip() for h in forwarded.split(",") if h.strip()]
            for hop in hops:
                if hop not in trusted:
                    return hop
            # Every hop was a trusted proxy — fall back to remote.
    return remote
