"""Background tasks: on-connect backfill + scheduled incremental sync.

Both run inside the existing ``process_tasks`` worker (no new infra).

Cadence (per the plan's "How new metrics get pulled" section):
  * Account-level metrics            → once per day per account
  * Posts < 24h old                  → hourly
  * Posts 1–7 days old               → every 6 hours
  * Posts 7–30 days old              → daily
  * Posts 30–90 days old             → weekly
  * Posts > 90 days old              → stop

The per-post cadence is exposed via :func:`post_sync_interval` so callers
that need the same ladder (the agent-API freshness helpers in
``apps/analytics/freshness.py``) cannot drift from what the sync loop
actually does.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import date as dt_date
from datetime import timedelta
from uuid import UUID

from background_task import background
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from providers.exceptions import APIError, QuotaExceededError, TokenExpiredError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Post-sync cadence — single source of truth.
# ---------------------------------------------------------------------------

# Tail of the per-post sync schedule. Each entry is ``(max_age, interval)`` —
# the first row whose ``max_age`` is greater than the post's age wins. The
# final row is ``(None, None)`` to mark the past-horizon stop.
_POST_SYNC_CADENCE: tuple[tuple[timedelta | None, timedelta | None], ...] = (
    (timedelta(days=1), timedelta(hours=1)),
    (timedelta(days=7), timedelta(hours=6)),
    (timedelta(days=30), timedelta(days=1)),
    (timedelta(days=90), timedelta(days=7)),
    (None, None),  # > 90 days — background sync has stopped.
)


def post_sync_interval(age: timedelta) -> timedelta | None:
    """Return the sync interval for a post of the given ``age``.

    ``None`` means the post is past the 90-day horizon and the background
    sync no longer refreshes it. Shared between the sync loop
    (``_post_cadence_due``) and the agent-API freshness helpers so the
    two cannot drift.
    """
    for max_age, interval in _POST_SYNC_CADENCE:
        if max_age is None or age < max_age:
            return interval
    return None  # unreachable — the table always ends in (None, None)


# ---------------------------------------------------------------------------
# Failure backoff — the other half of the cadence.
# ---------------------------------------------------------------------------

# A post whose fetch fails writes no snapshot, so cadence alone cannot slow it
# down; without a backoff it is "due" on every tick forever. These bounds are
# the ladder's own: start at its tightest rung and stop at its loosest, so a
# failing post is never retried more often than a brand-new one nor less often
# than a three-month-old one.
_SYNC_FAILURE_BACKOFF_BASE = timedelta(hours=1)
_SYNC_FAILURE_BACKOFF_MAX = timedelta(days=7)

# The doubling reaches the cap at nine failures, but the stored counter keeps
# growing — a post failing for a year lands in the hundreds. Clamping the
# exponent keeps the arithmetic honest; without it the multiplication overflows
# long before the ``min()`` gets a chance to apply the cap.
_SYNC_FAILURE_MAX_DOUBLINGS = 16

# How close to expiry an access token has to be before the sync spends a refresh
# call on it. This is a clock-skew margin, not a schedule: a Google access token
# lives one hour, so anything wider is permanently true and would buy a refresh
# call per account per hour for nothing, while anything narrower risks handing a
# token to an API call that expires mid-pass. Contrast
# ``apps.publisher.engine._PUBLISH_REFRESH_WINDOW``, which is user-triggered and
# can afford to be generous.
_ANALYTICS_REFRESH_WINDOW = timedelta(minutes=10)

# The optional YouTube Analytics per-video fetch is independent of the Data
# API post sync. Retry only that fetch, twice, rather than replaying a full
# account backfill after an upstream 5xx.
_YOUTUBE_POST_ANALYTICS_RETRY_DELAYS = (timedelta(hours=1), timedelta(hours=3))


def _analytics_failure_backoff(failure_count: int) -> timedelta:
    """How long to leave a post alone after ``failure_count`` failures in a row.

    Doubles from one hour and caps at a week: 1h, 2h, 4h, 8h … A post that
    cannot be fetched at all (deleted video, revoked visibility) settles at one
    wasted call a week instead of one an hour, while a post failing for a
    transient reason is back within the hour.
    """
    if failure_count <= 0:
        return timedelta(0)
    # Clamp the shift before doing it: the cap is reached by the ninth failure,
    # but the counter keeps climbing, and ``timedelta * 2**40`` raises
    # OverflowError rather than saturating.
    doublings = min(failure_count - 1, _SYNC_FAILURE_MAX_DOUBLINGS)
    return min(_SYNC_FAILURE_BACKOFF_BASE * (2**doublings), _SYNC_FAILURE_BACKOFF_MAX)


# Per-platform backfill window (days) on initial connect.
BACKFILL_DAYS_PER_PLATFORM: dict[str, int] = {
    "facebook": 90,
    "instagram": 90,
    "instagram_login": 90,
    "linkedin_company": 90,
    "youtube": 90,
    "pinterest": 90,
    "threads": 90,
    "google_business": 90,
    "tiktok": 60,
    # Bluesky / Mastodon / LinkedIn-Personal / DEV.to have no analytics surface
    # — skip. LinkedIn only exposes share statistics for Organization URNs, not
    # personal Person URNs, regardless of granted scopes. Each of these must
    # also appear in ``NO_ANALYTICS_PLATFORMS``.
    "bluesky": 0,
    "mastodon": 0,
    "linkedin_personal": 0,
    "devto": 0,
}
DEFAULT_BACKFILL_DAYS = 90


# ---------------------------------------------------------------------------
# PostMetrics / AccountMetrics → snapshot rows
# ---------------------------------------------------------------------------

# Per-platform overrides for ``PostMetrics`` field → catalog metric_key.
# A missing platform entry uses the identity mapping (impressions→impressions,
# etc.) augmented with ``video_views``→``views``. Each provider stuffs its
# native fields into different ``PostMetrics`` slots — these overrides realign
# them with the keys the UI queries from ``PLATFORM_METRICS``.
_POST_FIELD_OVERRIDES: dict[str, dict[str, str]] = {
    "threads": {
        # providers/threads.py:419-423 stuffs views/replies/reposts into the
        # impressions/comments/shares dataclass fields.
        "impressions": "views",
        "comments": "replies",
        "shares": "reposts",
    },
    "linkedin_company": {
        # providers/linkedin.py:580-585 returns likeCount/shareCount; catalog
        # for linkedin_company uses 'reactions' and 'reposts'.
        "likes": "reactions",
        "shares": "reposts",
    },
    "mastodon": {
        # providers/mastodon.py:313-316: favourites→likes (ok), reblogs→shares,
        # replies→comments. Catalog wants reposts/replies.
        "shares": "reposts",
        "comments": "replies",
    },
    "bluesky": {
        # AT Protocol counts: align with the bluesky catalog.
        "shares": "reposts",
        "comments": "replies",
    },
}

# Per-platform overrides for ``PostMetrics.extra[key]`` → catalog metric_key.
# Generic ``extra`` keys recognized by the default code path are listed in
# ``_GENERIC_POST_EXTRA_KEYS`` below; per-platform overrides handle the
# vocabulary that providers actually use.
_POST_EXTRA_OVERRIDES: dict[str, dict[str, str]] = {
    "pinterest": {
        # providers/pinterest.py:328 stores Pinterest's OUTBOUND_CLICK under
        # ``outbound_clicks`` in extra; the catalog metric key is ``outbound``.
        "outbound_clicks": "outbound",
    },
}

_GENERIC_POST_EXTRA_KEYS = (
    "reactions",
    "replies",
    "reposts",
    "outbound",
    "watch_time",
    "avg_view_pct",
)


def _post_metrics_to_dict(metrics, platform: str) -> dict[str, float]:
    """Flatten ``providers.types.PostMetrics`` into ``{metric_key: value}``.

    Uses per-platform overrides so each provider's idiosyncratic field choices
    (Threads stuffing views into ``impressions``, LinkedIn returning likeCount
    where the catalog uses ``reactions``, …) land under the keys the UI queries.

    Unset (zero) fields are omitted so we don't pin zeros into snapshots for
    metrics the platform didn't return.
    """
    field_overrides = _POST_FIELD_OVERRIDES.get(platform, {})
    extra_overrides = _POST_EXTRA_OVERRIDES.get(platform, {})

    out: dict[str, float] = {}
    base_map = (
        ("impressions", "impressions"),
        ("reach", "reach"),
        ("likes", "likes"),
        ("comments", "comments"),
        ("shares", "shares"),
        ("saves", "saves"),
        ("clicks", "clicks"),
        ("video_views", "views"),
    )
    for src, default_key in base_map:
        v = getattr(metrics, src, 0) or 0
        if v:
            key = field_overrides.get(src, default_key)
            out[key] = float(v)

    extra = getattr(metrics, "extra", {}) or {}
    # Generic extras that match the catalog key exactly.
    for key in _GENERIC_POST_EXTRA_KEYS:
        v = extra.get(key)
        if v is not None:
            with contextlib.suppress(TypeError, ValueError):
                out[key] = float(v)
    # Per-platform extras (e.g. Pinterest ``outbound_clicks`` → ``outbound``).
    for src_key, dest_key in extra_overrides.items():
        v = extra.get(src_key)
        if v is not None:
            with contextlib.suppress(TypeError, ValueError):
                out[dest_key] = float(v)
    from .metrics import PLATFORM_METRICS

    if "engagement" in PLATFORM_METRICS.get(platform, []):
        from .derive import calculate_engagement_rate

        engagement_parts = (
            out.get("likes", 0.0)
            + out.get("reactions", 0.0)
            + out.get("comments", 0.0)
            + out.get("replies", 0.0)
            + out.get("shares", 0.0)
            + out.get("reposts", 0.0)
            + out.get("saves", 0.0)
            + out.get("clicks", 0.0)
            + out.get("outbound", 0.0)
        )
        out["engagement"] = calculate_engagement_rate(
            engagement_parts,
            views=out.get("views", 0.0),
            reach=out.get("reach", 0.0),
        )
    return out


def _account_metrics_to_dict(metrics, platform: str) -> dict[str, float]:
    """Flatten ``AccountMetrics`` into ``{metric_key: value}``.

    ``platform`` gates per-platform persistence rules (e.g. ``followers``
    is only persisted for platforms whose catalog lists it), so the
    function asks ``apps.analytics.metrics.PLATFORM_METRICS`` rather than
    writing every populated dataclass field for every platform.
    """
    from .metrics import PLATFORM_METRICS

    out: dict[str, float] = {}
    for src, key in (
        ("impressions", "impressions"),
        ("reach", "reach"),
    ):
        v = getattr(metrics, src, 0) or 0
        if v:
            out[key] = float(v)
    # followers_gained = daily new follows; catalog calls it ``follows`` for
    # most platforms (and ``subscribers`` for YouTube — promoted from extra).
    gained = getattr(metrics, "followers_gained", 0) or 0
    if gained:
        out["follows"] = float(gained)
    # ``followers`` = current total follower count, persisted only when the
    # platform's catalog lists ``followers`` (TikTok, Instagram). Use ``is not
    # None`` so brand-new accounts with 0 followers still get a baseline
    # snapshot — the chart needs the zero day to render a continuous line. A
    # failed fetch yields ``None`` (not 0), so it is skipped rather than written.
    if "followers" in PLATFORM_METRICS.get(platform, []):
        total_followers = getattr(metrics, "followers", None)
        if total_followers is not None:
            out["followers"] = float(total_followers)
    extra = getattr(metrics, "extra", {}) or {}
    for key in ("views", "watch_time", "avg_view_pct", "subscribers", "likes", "comments", "shares"):
        v = extra.get(key)
        if v is not None:
            with contextlib.suppress(TypeError, ValueError):
                out[key] = float(v)
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_provider(account):
    """Build the provider for ``account`` with the same credentials the publish
    engine and the health check use.

    This used to be a hand-copy of ``_resolve_publish_credentials`` and had
    drifted: no ``instagram_login`` branch (so Instagram Direct providers were
    built with no ``ig_user_id`` / ``account_handle``) and no Bluesky
    ``pds_url``. Calling the shared resolver is the only way that stays fixed.

    Adopting it deliberately changes two Mastodon behaviours to match
    publishing: ``MastodonAppRegistration``'s client_id/secret now apply only
    when the org's own credentials don't already carry one, and an
    ``instance_url`` that fails the SSRF check is dropped rather than passed
    through (analytics for such an account fails instead of dialling it).
    """
    from apps.publisher.engine import _resolve_publish_credentials
    from providers import get_provider

    return get_provider(account.platform, _resolve_publish_credentials(account))


def _analytics_provider_and_token(account) -> tuple:
    """Provider plus an access token fresh enough to survive this account's pass.

    The sync used to hand ``account.oauth_access_token`` straight to the
    provider, unrefreshed. For a platform whose access token lives an hour and
    whose only refresher is a six-hourly health check, that meant roughly five
    of every six hourly runs called the API with a token that had already
    expired — every call failing, every post left looking un-synced, and (before
    the backoff below) every post therefore retried again an hour later.

    Best-effort, like the publish path: a refresh we cannot complete leaves the
    old token in place so the API call surfaces the real error instead of a
    refresh error. The exception is a refusal that says the *grant* is gone —
    retrying that forever is pointless and invisible, so flag the account and
    let the health check, which owns ``connection_status``, decide the rest.
    """
    provider = _resolve_provider(account)
    access_token = account.oauth_access_token
    if not (account.token_expires_within(_ANALYTICS_REFRESH_WINDOW) and account.oauth_refresh_token):
        return provider, access_token

    try:
        access_token = account.refresh_oauth_token(provider, enqueue_backfill=False)
    except Exception as exc:
        if _is_dead_grant(exc):
            logger.warning("analytics: OAuth grant for %s is gone (%s); flagging for reconnect", account, exc)
            _mark_needs_reconnect(account)
            _enqueue_health_check(account)
        else:
            logger.warning("analytics: token refresh failed for %s: %s", account, exc)
    return provider, access_token


def _is_dead_grant(exc: Exception) -> bool:
    """Whether a refresh failure means the user's grant is gone for good.

    Classified with the same machinery the health check and the connection UI
    use, rather than by sniffing the message, so the three surfaces cannot drift
    on what counts as "reconnect required". A network blip or a 5xx on the token
    endpoint classifies as something else and is left alone — retrying is the
    right move there.
    """
    from apps.social_accounts.error_messages import _RECONNECT, _classify

    try:
        return _classify(exc) == _RECONNECT
    except Exception:  # pragma: no cover - classification must never break the sync
        return False


def _enqueue_health_check(account) -> None:
    """Hand a dead grant to the task that owns ``connection_status``.

    Deliberately not writing ``connection_status`` / ``last_error`` from here:
    ``apps.social_accounts.tasks.check_social_account_health`` is their single
    documented writer, and setting ``TOKEN_EXPIRING`` from the analytics path
    would also silently stop inbox polling, which filters on ``CONNECTED``.
    """
    from apps.social_accounts.tasks import check_social_account_health

    with contextlib.suppress(Exception):
        check_social_account_health(str(account.id))


def _record_post_sync_success(post_ids: list, now=None) -> None:
    """Stamp the attempt and clear the failure streak for posts we just fetched.

    Uses ``update()`` rather than ``instance.save()`` so it can never write back
    a stale copy of a row the publish engine is touching concurrently.
    """
    if not post_ids:
        return
    from apps.composer.models import PlatformPost

    PlatformPost.objects.filter(pk__in=post_ids).update(
        analytics_attempted_at=now or timezone.now(),
        analytics_failure_count=0,
    )


def _record_post_sync_failure(post_ids: list, now=None) -> None:
    """Stamp the attempt and extend the failure streak for posts that came back empty.

    Only for a call that actually reached the platform and returned no data for
    *that id*. A quota block, an expired token, or any other account-wide
    refusal must NOT come through here: those posts were never really attempted,
    and counting them would exile perfectly good posts for a week because of a
    problem that had nothing to do with them.
    """
    if not post_ids:
        return
    from apps.composer.models import PlatformPost

    PlatformPost.objects.filter(pk__in=post_ids).update(
        analytics_attempted_at=now or timezone.now(),
        analytics_failure_count=F("analytics_failure_count") + 1,
    )


def _is_insufficient_scope(exc: Exception) -> bool:
    """Best-effort recognition of "you don't have the right scope" errors.

    Each provider raises slightly different exceptions; rather than wire
    them all up here, sniff the message for the common signals.
    """
    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "scope",
            "permission",
            "insufficient",
            "forbidden",
            "(#10)",  # Meta's permission-error subcode
            "(#200)",  # Meta's permission-denied subcode
        )
    )


def _write_account_snapshot(
    account,
    metric_values: dict[str, float],
    on_date: dt_date,
    *,
    raw: dict | None = None,
    errors: dict | None = None,
) -> int:
    from .models import AccountInsightsSnapshot

    if not metric_values:
        return 0
    count = 0
    for key, value in metric_values.items():
        AccountInsightsSnapshot.objects.update_or_create(
            social_account=account,
            metric_key=key,
            date=on_date,
            defaults={"value": value, "raw": raw or {}, "errors": errors or {}},
        )
        count += 1
    return count


def _write_post_snapshot(
    post,
    metric_values: dict[str, float],
    on_date: dt_date,
    *,
    raw: dict | None = None,
    errors: dict | None = None,
) -> int:
    from .models import PostInsightsSnapshot

    if not metric_values:
        return 0
    count = 0
    for key, value in metric_values.items():
        PostInsightsSnapshot.objects.update_or_create(
            platform_post=post,
            metric_key=key,
            date=on_date,
            defaults={"value": value, "raw": raw or {}, "errors": errors or {}},
        )
        count += 1
    return count


# ---------------------------------------------------------------------------
# Per-account work
# ---------------------------------------------------------------------------


# Number of recent days to attempt when syncing account-level metrics.
# Some providers (YouTube Analytics) lag 1-2 days; today's call returns
# empty for them. Iterating recent days lets finalized data backfill into
# the snapshot table instead of being lost. Days that already have rows
# are skipped, so on a steady-state account this costs at most one extra
# API call when today is the only missing day.
_ACCOUNT_METRICS_RECENT_DAYS = 3

# Earliest plausible startDate for a YouTube Analytics ``/reports`` query —
# YouTube launched 2005-02-14, so any channel's creation date is on or after
# this. Used as the lower bound when fetching LIFETIME per-video metrics so
# the values match what YouTube Studio shows (total watch time, etc.).
_YOUTUBE_ANALYTICS_LIFETIME_START = dt_date(2005, 2, 14)

# Per-platform metric keys whose ``PostInsightsSnapshot`` rows are written by
# a sync path OTHER than the per-post Data-API ``_sync_post_metrics`` (e.g.,
# the batched YouTube Analytics call in ``_sync_youtube_post_analytics``).
# Excluding these from ``_post_cadence_due`` keeps the Analytics-only writes
# — which can fire hourly during the 1–2 day Analytics-API lag — from
# updating ``captured_at`` and starving the Data API of refreshes (the loop
# would think every video was just synced and skip ``_sync_post_metrics``).
_POST_NON_CADENCE_METRICS_BY_PLATFORM: dict[str, frozenset[str]] = {
    "youtube": frozenset({"watch_time", "avg_view_pct", "shares"}),
}

_FOLLOWER_TOTAL_REFRESH_PLATFORMS: frozenset[str] = frozenset({"facebook", "instagram", "instagram_login"})


def _needs_empty_follower_count_refresh(account) -> bool:
    return account.follower_count <= 0 and account.platform in _FOLLOWER_TOTAL_REFRESH_PLATFORMS


def _sync_account_metrics(
    account,
    on_date: dt_date,
    *,
    force_today: bool = False,
    provider=None,
    access_token: str | None = None,
    deadline=None,
) -> None:
    """Fetch account-level metrics for ``on_date`` and any recent missing days.

    Walks ``on_date`` and the prior ``_ACCOUNT_METRICS_RECENT_DAYS - 1`` days,
    skipping days that already have an :class:`AccountInsightsSnapshot`. For
    providers without lag (Instagram, Facebook) this is a no-op past
    ``on_date`` because the existing rows short-circuit the iteration.

    ``force_today`` re-fetches ``on_date`` even when its rows already exist.
    One-shot backfills pass it because they run at the moments the token's
    reach may have *changed* — a connect, a reconnect, or an admin switching
    the platform on — and the fetch is the only thing that surfaces an
    insufficient-scope error and sets ``analytics_needs_reconnect``. Without
    it, a same-day re-run finds today's rows present, skips every offset,
    never calls the provider, and reports success for a token that cannot
    read insights. The hourly cron does not pass it: there, existing rows
    genuinely mean the work is done.

    For YouTube, also fetches per-video Analytics-API metrics (watch_time,
    avg_view_pct, shares) that the Data API can't provide per-post — see
    :func:`_sync_youtube_post_analytics`.

    ``provider`` / ``access_token`` let a caller that is already iterating an
    account's work resolve them once and pass them down. Resolving per call
    means re-reading the account's credentials and decrypting its token every
    time; more importantly, a token resolved here is refreshed here, so the
    caller and the callee could otherwise end up holding different ones.

    ``deadline`` bounds the optional YouTube Analytics per-video sweep so a
    large channel cannot consume the entire hourly task budget in one account.
    """
    from datetime import datetime, time

    from .metrics import PLATFORM_METRICS
    from .models import AccountInsightsSnapshot

    if provider is None or access_token is None:
        provider, access_token = _analytics_provider_and_token(account)
    tz = timezone.get_current_timezone()
    # Providers whose stats endpoint returns only lifetime totals (TikTok)
    # must NOT have those totals written into past dates as if they were
    # historical observations — that fabricates fake history. Run only the
    # current day for them; backfill of true historical values is impossible
    # without an API that supports it.
    recent_days = _ACCOUNT_METRICS_RECENT_DAYS if getattr(provider, "account_metrics_supports_date_range", True) else 1
    # ``followers`` is a live point-in-time total: the provider returns the
    # current count regardless of the requested window, so it is valid only for
    # the day the sync runs. Capture it from whichever offset returns it (so a
    # value is recovered even when on_date's own fetch failed or its row already
    # exists) and write it once, to on_date only, after the loop — never into a
    # backfilled past date (which would fabricate flat history).
    current_followers = None
    for offset in range(recent_days):
        target = on_date - timedelta(days=offset)
        has_rows_for_day = AccountInsightsSnapshot.objects.filter(social_account=account, date=target).exists()
        needs_current_day_refetch = target == on_date and (force_today or _needs_empty_follower_count_refresh(account))
        if has_rows_for_day and not needs_current_day_refetch:
            continue
        start = datetime.combine(target, time.min, tzinfo=tz)
        end = datetime.combine(target, time.max, tzinfo=tz)
        try:
            metrics = provider.get_account_metrics(access_token, (start, end))
        except NotImplementedError:
            return
        except (QuotaExceededError, TokenExpiredError):
            # These are account-wide outcomes. Let _sync_one_account trip the
            # quota breaker or flag the token instead of turning them into a
            # per-day warning that the hourly cron quietly forgets.
            raise
        except Exception as exc:
            if _is_insufficient_scope(exc):
                _mark_needs_reconnect(account)
            logger.warning("get_account_metrics failed for %s on %s: %s", account, target, exc)
            return
        _refresh_follower_count(account, metrics)
        fetched_followers = getattr(metrics, "followers", None)
        if fetched_followers is not None:
            current_followers = fetched_followers
        extra = getattr(metrics, "extra", {}) or {}
        metric_values = _account_metrics_to_dict(metrics, account.platform)
        # The live followers total is written to on_date after the loop; keep it
        # out of every dated/backfilled snapshot written here.
        metric_values.pop("followers", None)
        _write_account_snapshot(
            account,
            metric_values,
            target,
            raw=extra.get("raw_insights", {}),
            errors=extra.get("insight_errors", {}),
        )

    if current_followers is not None and "followers" in PLATFORM_METRICS.get(account.platform, []):
        # Live total → on_date only, idempotently: recovers a value fetched at a
        # later offset and fills it in when on_date's other metrics already exist.
        _write_account_snapshot(account, {"followers": float(current_followers)}, on_date)

    if account.platform == "youtube":
        _sync_youtube_post_analytics(account, provider, access_token, on_date, deadline=deadline)


def _sync_youtube_post_analytics(
    account,
    provider,
    access_token: str,
    on_date: dt_date,
    *,
    deadline=None,
    retry_attempt: int = 0,
) -> None:
    """Snapshot lifetime per-video YouTube Analytics metrics for ``on_date``.

    Bridges the gap between the YouTube Data API (which exposes per-video
    views/likes/comments via ``videos.list?part=statistics``) and the
    Analytics API (which exposes ``watch_time``, ``avg_view_pct``, and
    ``shares`` per video via ``/reports?dimensions=video``). One batched
    Analytics request covers every published video on the channel, so
    quota cost is independent of post count up to the 500-video filter cap.

    Stores LIFETIME values keyed by ``on_date`` so the per-post table shows
    totals (matching what YouTube Studio shows), and so the chart fallback
    (:func:`apps.analytics.services._post_summed_series_for_metric`) can
    compute day-over-day deltas across consecutive snapshots — same
    cumulative-snapshot semantics as views/likes/comments.
    """
    from datetime import datetime, time

    from apps.composer.models import PlatformPost

    post_ids = list(
        PlatformPost.objects.filter(
            social_account=account,
            status=PlatformPost.Status.PUBLISHED,
            published_at__date__lte=on_date,
        )
        .exclude(platform_post_id="")
        .values_list("platform_post_id", flat=True)
    )
    if not post_ids:
        return

    if deadline is not None and timezone.now() >= deadline:
        logger.warning(
            "analytics: stopped YouTube post analytics for %s — %s budget spent; next tick resumes",
            account,
            _RUN_BUDGET,
        )
        return

    tz = timezone.get_current_timezone()
    start = datetime.combine(_YOUTUBE_ANALYTICS_LIFETIME_START, time.min, tzinfo=tz)
    end = datetime.combine(on_date, time.max, tzinfo=tz)

    try:
        per_video = provider.get_post_analytics(access_token, post_ids, (start, end), deadline=deadline)
    except NotImplementedError:
        return
    except (QuotaExceededError, TokenExpiredError):
        # The Analytics API failure applies to the account, not to each video.
        # The caller owns breaker/reconnect handling and must see it.
        raise
    except Exception as exc:
        if _is_insufficient_scope(exc):
            _mark_needs_reconnect(account)
        retryable = isinstance(exc, APIError) and exc.status_code is not None and exc.status_code >= 500
        if retryable and retry_attempt < len(_YOUTUBE_POST_ANALYTICS_RETRY_DELAYS):
            delay = _YOUTUBE_POST_ANALYTICS_RETRY_DELAYS[retry_attempt]
            retry_youtube_post_analytics(
                str(account.id),
                on_date.isoformat(),
                retry_attempt + 1,
                schedule=int(delay.total_seconds()),
                remove_existing_tasks=True,
            )
        else:
            delay = None
        logger.warning(
            "YouTube optional per-video Analytics failed for account %s on %s: status=%s error_type=%s; "
            "Data API post metrics are independent; next_retry=%s",
            account.id,
            on_date,
            getattr(exc, "status_code", None),
            type(exc).__name__,
            delay,
        )
        return

    if not per_video:
        return

    posts_by_pid = {
        p.platform_post_id: p
        for p in PlatformPost.objects.filter(social_account=account, platform_post_id__in=list(per_video.keys()))
    }
    for pid, metrics in per_video.items():
        post = posts_by_pid.get(pid)
        if post is None:
            continue
        extra = getattr(metrics, "extra", {}) or {}
        _write_post_snapshot(
            post,
            _post_metrics_to_dict(metrics, "youtube"),
            on_date,
            raw=extra.get("raw_insights", extra),
            errors=extra.get("insight_errors", {}),
        )

    if retry_attempt:
        logger.info("YouTube optional per-video Analytics retry recovered account %s on %s", account.id, on_date)


@background(schedule=0)
def retry_youtube_post_analytics(account_id: str, on_date_iso: str, attempt: int) -> None:
    """Retry only the optional Analytics API call after a transient 5xx."""
    from apps.common import quota
    from apps.social_accounts.models import SocialAccount

    from . import services

    try:
        account = SocialAccount.objects.get(id=account_id)
    except SocialAccount.DoesNotExist:
        return
    if (
        account.platform != "youtube"
        or account.connection_status != SocialAccount.ConnectionStatus.CONNECTED
        or account.analytics_needs_reconnect
        or services.analytics_availability(account.platform) is not None
    ):
        return
    if attempt < 1 or attempt > len(_YOUTUBE_POST_ANALYTICS_RETRY_DELAYS):
        return

    on_date = dt_date.fromisoformat(on_date_iso)
    try:
        provider, access_token = _analytics_provider_and_token(account)
    except Exception as exc:
        logger.warning(
            "YouTube optional Analytics retry could not build provider for account %s: error_type=%s",
            account.id,
            type(exc).__name__,
        )
        return

    key = quota.credential_key(getattr(provider, "credentials", None))
    blocked_until = quota.quota_blocked_until("youtube", key, "analytics")
    if blocked_until:
        # A quota block does not spend a 5xx retry. Preserve this account/date
        # even when the regular daily account snapshot prevents another fetch.
        retry_youtube_post_analytics(
            account_id,
            on_date_iso,
            attempt,
            schedule=blocked_until + timedelta(seconds=1),
            remove_existing_tasks=True,
        )
        logger.info(
            "YouTube optional Analytics retry deferred for account %s until %s due to quota block",
            account.id,
            blocked_until,
        )
        return

    try:
        _sync_youtube_post_analytics(
            account,
            provider,
            access_token,
            on_date,
            deadline=timezone.now() + _RUN_BUDGET,
            retry_attempt=attempt,
        )
    except QuotaExceededError as exc:
        _handle_quota_exhaustion(account, exc, key=key, scope="analytics", cache={})
    except TokenExpiredError:
        logger.warning("YouTube optional Analytics retry token rejected for account %s", account.id)
        _mark_needs_reconnect(account)
        _enqueue_health_check(account)


def _has_unusable_platform_post_id(post, platform: str) -> bool:
    """Meta posts whose ``platform_post_id`` is really an internal UUID.

    A publish that half-failed can leave our own row id in the field; calling
    Meta with it is guaranteed to fail, so skip without spending the request.
    """
    if platform in {"facebook", "instagram", "instagram_login"} and _looks_like_uuid(post.platform_post_id):
        logger.warning(
            "Skipping %s analytics for PlatformPost %s because platform_post_id looks like an internal UUID.",
            platform,
            post.id,
        )
        return True
    return False


def _sync_post_metrics(post, on_date: dt_date, *, provider=None, access_token: str | None = None) -> None:
    """Fetch one post's current metrics and write today's snapshot rows.

    The single-post path, used by platforms without a batch endpoint. Callers
    inside an account loop pass ``provider`` / ``access_token`` so they are
    resolved once rather than per post — resolving them here meant a credential
    query and a token decrypt for every post on the channel.
    """
    account = post.social_account
    if _has_unusable_platform_post_id(post, account.platform):
        return
    if provider is None or access_token is None:
        provider, access_token = _analytics_provider_and_token(account)
    try:
        metrics = provider.get_post_metrics(access_token, post.platform_post_id)
    except NotImplementedError:
        return
    except (QuotaExceededError, TokenExpiredError):
        raise
    except Exception as exc:
        if _is_insufficient_scope(exc):
            _mark_needs_reconnect(account)
        logger.warning("get_post_metrics failed for post %s (%s): %s", post.id, account.platform, exc)
        _record_post_sync_failure([post.pk])
        return
    _write_post_metrics_snapshot(post, metrics, account.platform, on_date)
    _record_post_sync_success([post.pk])


def _write_post_metrics_snapshot(post, metrics, platform: str, on_date: dt_date) -> None:
    """Write today's snapshot rows for one post's fetched metrics."""
    extra = getattr(metrics, "extra", {}) or {}
    _write_post_snapshot(
        post,
        _post_metrics_to_dict(metrics, platform),
        on_date,
        raw={
            "fields": extra.get("raw_fields", {}),
            "insights": extra.get("raw_insights", {}),
            "insight_post_id": extra.get("insight_post_id"),
            "attempted_insight_post_ids": extra.get("attempted_insight_post_ids", []),
        },
        errors=extra.get("insight_errors", {}),
    )


def _sync_account_posts(
    account,
    provider,
    access_token: str,
    posts,
    on_date: dt_date,
    *,
    deadline=None,
) -> tuple[int, int, int]:
    """Sync per-post metrics for one account. Returns ``(synced, failed, api_calls)``.

    Prefers the platform's batched endpoint when it has one: YouTube's
    ``videos.list`` charges the same single quota unit for fifty ids as for one,
    so asking one at a time spent fifty times the quota it needed to. Platforms
    without a batch endpoint keep the per-post loop, which costs the same number
    of requests either way and buys per-post error isolation — one bad id there
    must not cost the rest of the account.

    Raises :class:`QuotaExceededError` / :class:`TokenExpiredError` to the
    caller: those are account-wide verdicts, not facts about any one post, and
    the caller needs them to trip the breaker. Crucially, they leave every post's
    sync state untouched — see :func:`_record_post_sync_failure`.
    """
    posts = [p for p in posts if not _has_unusable_platform_post_id(p, account.platform)]
    if not posts:
        return 0, 0, 0

    batch_size = max(1, getattr(provider, "post_metrics_batch_size", 1))
    if batch_size == 1:
        return _sync_account_posts_individually(
            account,
            provider,
            access_token,
            posts,
            on_date,
            deadline=deadline,
        )

    synced = failed = api_calls = 0
    first_error = None
    for offset in range(0, len(posts), batch_size):
        if deadline is not None and timezone.now() >= deadline:
            logger.warning(
                "analytics: stopped post sync for %s — %s budget spent; next tick resumes",
                account,
                _RUN_BUDGET,
            )
            break
        chunk = posts[offset : offset + batch_size]
        by_platform_id = {p.platform_post_id: p for p in chunk}
        api_calls += 1
        try:
            metrics_by_id = provider.get_post_metrics_batch(access_token, list(by_platform_id))
        except NotImplementedError:
            return synced, failed, api_calls - 1
        except (QuotaExceededError, TokenExpiredError):
            # A quota or token failure is not a fact about this chunk. Leave all
            # post state untouched and let the account-level handler decide.
            raise
        except Exception as exc:
            # A regular API/transport failure belongs to this chunk only. Stamp
            # those posts so a bad response cannot make the whole account due
            # again on the next tick, then continue with later chunks.
            first_error = first_error or exc
            if _is_insufficient_scope(exc):
                _mark_needs_reconnect(account)
            attempted_at = timezone.now()
            _record_post_sync_failure([p.pk for p in by_platform_id.values()], attempted_at)
            failed += len(by_platform_id)
            logger.debug(
                "get_post_metrics_batch failed for %s (%s), %s posts: %s",
                account,
                account.platform,
                len(by_platform_id),
                exc,
            )
            continue

        # Everything below is local work. The transaction opens only once the
        # HTTP call has returned, so a slow platform never holds a database
        # connection open across the network — and one chunk's rows still land
        # together or not at all.
        attempted_at = timezone.now()
        hit_ids, miss_ids = [], []
        with transaction.atomic():
            for platform_post_id, post in by_platform_id.items():
                metrics = metrics_by_id.get(platform_post_id)
                if metrics is None:
                    # Absent from the response: deleted, made private, or not
                    # ours. Never write zeros — that would flatten real history.
                    miss_ids.append(post.pk)
                    continue
                _write_post_metrics_snapshot(post, metrics, account.platform, on_date)
                hit_ids.append(post.pk)

            _record_post_sync_success(hit_ids, attempted_at)
            _record_post_sync_failure(miss_ids, attempted_at)
        synced += len(hit_ids)
        failed += len(miss_ids)

    if first_error is not None:
        logger.warning(
            "analytics: %s of %s batched post metric fetches failed for %s (%s) — first error: %s",
            failed,
            synced + failed,
            account,
            account.platform,
            first_error,
        )
    return synced, failed, api_calls


def _sync_account_posts_individually(
    account,
    provider,
    access_token,
    posts,
    on_date,
    *,
    deadline=None,
) -> tuple[int, int, int]:
    """Per-post fallback for platforms with no batch endpoint.

    Each post's failure is contained to that post — which is the whole reason
    this path still exists — but an account-wide verdict still propagates, so a
    dead token doesn't quietly burn the whole channel one request at a time.
    """
    synced = failed = api_calls = 0
    first_error = None
    for post in posts:
        if deadline is not None and timezone.now() >= deadline:
            logger.warning(
                "analytics: stopped post sync for %s — %s budget spent; next tick resumes",
                account,
                _RUN_BUDGET,
            )
            break
        try:
            metrics = provider.get_post_metrics(access_token, post.platform_post_id)
        except NotImplementedError:
            return synced, failed, api_calls
        except (QuotaExceededError, TokenExpiredError):
            raise
        except Exception as exc:
            api_calls += 1
            failed += 1
            first_error = first_error or exc
            if _is_insufficient_scope(exc):
                _mark_needs_reconnect(account)
            logger.debug("get_post_metrics failed for post %s (%s): %s", post.id, account.platform, exc)
            _record_post_sync_failure([post.pk], timezone.now())
            continue
        api_calls += 1
        attempted_at = timezone.now()
        with transaction.atomic():
            _write_post_metrics_snapshot(post, metrics, account.platform, on_date)
            _record_post_sync_success([post.pk], attempted_at)
        synced += 1

    if first_error is not None:
        logger.warning(
            "analytics: %s of %s post metric fetches failed for %s (%s) — first error: %s",
            failed,
            synced + failed,
            account,
            account.platform,
            first_error,
        )
    return synced, failed, api_calls


def _looks_like_uuid(value: str) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _refresh_follower_count(account, metrics) -> None:
    followers = getattr(metrics, "followers", 0) or 0
    if followers <= 0 and account.follower_count != 0:
        return
    if followers == account.follower_count:
        return
    account.follower_count = followers
    account.save(update_fields=["follower_count", "updated_at"])


def _mark_needs_reconnect(account):
    if account.analytics_needs_reconnect:
        return
    account.analytics_needs_reconnect = True
    account.save(update_fields=["analytics_needs_reconnect", "updated_at"])


def _post_cadence_due(post, now=None, *, platform: str | None = None) -> bool:
    """Decide whether ``post`` is due for a new per-post metrics fetch.

    Driven by ``PlatformPost.analytics_attempted_at`` — when we last *tried* —
    rather than by when we last succeeded. That distinction is the whole point.
    Cadence used to be read from the newest ``PostInsightsSnapshot.captured_at``,
    and a failed fetch writes no snapshot, so a post that kept failing looked
    never-synced and came back due on every single hourly tick, ignoring the
    decay ladder entirely. Multiply that by every post on a channel and an
    account-wide problem (an expired token, say) turns into a self-sustaining
    storm that empties a day of API quota in an hour and then keeps failing
    *because* the quota is empty.

    On top of the ladder, a post with a failure streak waits out
    :func:`_analytics_failure_backoff`, so something permanently unfetchable
    settles at one wasted call a week.

    Posts with no attempt stamp — rows written before the field existed — fall
    back to the old snapshot signal. That fallback is what lets this ship with
    no data migration: each such post takes the branch at most once, because the
    first attempt stamps it. (It is also the last thing keeping
    :data:`_POST_NON_CADENCE_METRICS_BY_PLATFORM` alive; once no row has a null
    stamp, both can go.)

    ``platform`` may be supplied by callers iterating posts of a known
    account to avoid the implicit ``post.social_account.platform`` lookup.
    """
    now = now or timezone.now()
    if not post.published_at:
        return False
    cadence = post_sync_interval(now - post.published_at)
    if cadence is None:
        return False  # past the 90-day horizon.

    attempted = post.analytics_attempted_at
    if attempted is not None:
        wait = cadence
        if post.analytics_failure_count:
            wait = max(cadence, _analytics_failure_backoff(post.analytics_failure_count))
        return (now - attempted) >= wait

    from .models import PostInsightsSnapshot

    qs = PostInsightsSnapshot.objects.filter(platform_post=post)
    platform = platform or post.social_account.platform
    excluded = _POST_NON_CADENCE_METRICS_BY_PLATFORM.get(platform)
    if excluded:
        qs = qs.exclude(metric_key__in=excluded)
    last = qs.order_by("-captured_at").values_list("captured_at", flat=True).first()
    if last is None:
        return True
    return (now - last) >= cadence


# ---------------------------------------------------------------------------
# Per-account orchestration
# ---------------------------------------------------------------------------

# How long one cron pass may spend before it stops and leaves the rest to the
# next tick. Half the hourly interval, so a long pass can never still be running
# when its successor is due — django-background-tasks' MAX_RUN_TIME defaults to
# 3600s, exactly the repeat interval, so an over-running pass gets unlocked and
# can overlap itself. Fixing that globally is not an option: the same worker
# runs the publish cycle, where an unlock-and-rerun risks a double post.
#
# This is only safe because per-post attempt stamps make a truncated pass
# resumable, and because ``_due_posts_for`` orders by attempt time nulls-first
# so the next tick continues where this one stopped instead of re-walking the
# same head of the queue. Removing either would turn this into starvation.
_RUN_BUDGET = timedelta(minutes=30)


def _due_posts_for(account, now):
    """Posts of ``account`` that could plausibly be due, cheapest-first.

    Narrows in SQL before loading: the ladder's tightest rung is one hour, so
    anything attempted within the last hour is provably not due and need not be
    fetched at all. The remainder is ordered by attempt time, nulls first, so a
    pass cut short by ``_RUN_BUDGET`` resumes with the longest-neglected posts
    rather than re-walking the same ones every tick.
    """
    from apps.composer.models import PlatformPost

    cap_days = BACKFILL_DAYS_PER_PLATFORM.get(account.platform, DEFAULT_BACKFILL_DAYS)
    if cap_days == 0:
        return []
    return list(
        PlatformPost.objects.filter(
            social_account=account,
            status=PlatformPost.Status.PUBLISHED,
            published_at__gte=now - timedelta(days=cap_days),
        )
        .exclude(platform_post_id="")
        .filter(
            Q(analytics_attempted_at__isnull=True) | Q(analytics_attempted_at__lte=now - _SYNC_FAILURE_BACKOFF_BASE)
        )
        .order_by(F("analytics_attempted_at").asc(nulls_first=True))
    )


def _handle_quota_exhaustion(account, exc, *, key: str, scope: str | None = None, cache) -> None:
    """Record the block so the rest of this pass — and the next — stop calling.

    The platform has already answered "not until later". Every further request
    against that credential is a guaranteed failure that still costs a request
    and still logs, which is how one bad hour used to turn into a bad week.

    A thin wrapper now: the decision moved to ``apps.common.quota`` once the
    inbox needed it too, because the second copy is where the scope fallbacks
    silently diverged and split the breaker in two.
    """
    from apps.common import quota

    quota.trip_from_exception(
        account.platform,
        key,
        exc,
        default_scope=scope if scope is not None else "",
        fallback_backoff=_SYNC_FAILURE_BACKOFF_BASE,
        cache=cache,
    )


def _sync_one_account(account, on_date, now, *, cache, force_today=False, deadline=None) -> tuple[int, int, int]:
    """Run one account's whole analytics pass. Returns ``(synced, failed, api_calls)``.

    Quota and token verdicts are caught here rather than per post: they are
    facts about the account — or about the credential behind it — and the only
    useful response is to stop and let the breaker say when to try again.
    Handling them here is also what keeps them off the per-post failure
    counters, so an account-wide outage cannot exile every good post for a week.
    """
    from apps.common import quota

    from .models import AccountInsightsSnapshot

    try:
        provider, access_token = _analytics_provider_and_token(account)
    except Exception as exc:
        logger.warning("analytics: could not build provider for %s: %s", account, exc)
        return 0, 0, 0

    key = quota.credential_key(getattr(provider, "credentials", None))
    account_scope, post_scope = quota.scopes_for(account.platform)

    def blocked(scope):
        return quota.quota_blocked_until(account.platform, key, scope, cache=cache)

    try:
        if not blocked(account_scope):
            has_today_rows = AccountInsightsSnapshot.objects.filter(social_account=account, date=on_date).exists()
            if not account.analytics_needs_reconnect and (
                force_today or not has_today_rows or _needs_empty_follower_count_refresh(account)
            ):
                try:
                    _sync_account_metrics(
                        account,
                        on_date,
                        force_today=force_today,
                        provider=provider,
                        access_token=access_token,
                        deadline=deadline,
                    )
                except QuotaExceededError as exc:
                    _handle_quota_exhaustion(account, exc, key=key, scope=account_scope, cache=cache)
                    if account_scope == post_scope:
                        return 0, 0, 0

        if blocked(post_scope):
            return 0, 0, 0
        due = [p for p in _due_posts_for(account, now) if _post_cadence_due(p, now, platform=account.platform)]
        return _sync_account_posts(account, provider, access_token, due, on_date, deadline=deadline)
    except QuotaExceededError as exc:
        _handle_quota_exhaustion(account, exc, key=key, scope=post_scope, cache=cache)
        return 0, 0, 0
    except TokenExpiredError as exc:
        # Refused after we already tried to refresh, so the grant itself is
        # suspect. Hand it to the task that owns connection_status, and do not
        # count it against any post — none of them were really attempted.
        logger.warning("analytics: %s rejected our token for %s; flagging for reconnect", account.platform, account)
        _mark_needs_reconnect(account)
        _enqueue_health_check(account)
        logger.debug("token rejection detail for %s: %s", account, exc)
        return 0, 0, 0


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------


@background(schedule=0)
def backfill_account_analytics(account_id: str, days: int | None = None) -> None:
    """One-shot backfill on account connect / reconnect.

    Account-level: writes today's row (the only one we can reliably get
    without provider time-series support — full historical backfill is
    deferred until we extend providers to return daily series).

    Per-post: for every published post within the platform's window, fetch
    its current cumulative metrics and write today's snapshot rows. Goes
    through the same batched path as the cron, so connecting a channel with
    three months of history costs a handful of API calls rather than one per
    post.
    """
    from apps.common import quota
    from apps.composer.models import PlatformPost
    from apps.social_accounts.models import SocialAccount

    from . import services

    try:
        account = SocialAccount.objects.get(id=account_id)
    except SocialAccount.DoesNotExist:
        return
    if services.analytics_availability(account.platform) is not None:
        return
    cap = BACKFILL_DAYS_PER_PLATFORM.get(account.platform, DEFAULT_BACKFILL_DAYS)
    if cap == 0:
        return
    days = min(days or cap, cap)
    now = timezone.now()
    today = now.date()
    cache: dict = {}

    try:
        provider, access_token = _analytics_provider_and_token(account)
    except Exception as exc:
        logger.warning("analytics: could not build provider for %s: %s", account, exc)
        return

    key = quota.credential_key(getattr(provider, "credentials", None))
    account_scope, post_scope = quota.scopes_for(account.platform)

    try:
        if not quota.quota_blocked_until(account.platform, key, account_scope, cache=cache):
            try:
                _sync_account_metrics(
                    account,
                    today,
                    force_today=True,
                    provider=provider,
                    access_token=access_token,
                )
            except QuotaExceededError as exc:
                _handle_quota_exhaustion(account, exc, key=key, scope=account_scope, cache=cache)
                if account_scope == post_scope:
                    return

        if quota.quota_blocked_until(account.platform, key, post_scope, cache=cache):
            logger.info("analytics: skipping %s backfill — %s quota is spent", account, account.platform)
            return

        posts = list(
            PlatformPost.objects.filter(
                social_account=account,
                status=PlatformPost.Status.PUBLISHED,
                published_at__gte=now - timedelta(days=days),
            ).exclude(platform_post_id="")
        )
        synced, failed, api_calls = _sync_account_posts(account, provider, access_token, posts, today)
    except QuotaExceededError as exc:
        _handle_quota_exhaustion(account, exc, key=key, scope=post_scope, cache=cache)
        return
    except TokenExpiredError:
        logger.warning("analytics: %s rejected our token during backfill of %s", account.platform, account)
        _mark_needs_reconnect(account)
        _enqueue_health_check(account)
        return

    logger.info(
        "analytics backfill: %s — %s posts synced, %s failed, %s API calls",
        account,
        synced,
        failed,
        api_calls,
    )


@background(schedule=0)
def sync_all_account_analytics() -> None:
    """Hourly cron: refresh enabled accounts on the decay-by-age schedule."""
    from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount

    from . import services

    # Filter on the same predicate the page and the agent API use, not just the
    # admin toggle. A platform with no analytics API at all (DEV.to, Bluesky,
    # ...) is "enabled" as far as AnalyticsPlatformConfig is concerned, and the
    # ``cap_days == 0`` guard only skips the per-post loop — so without this
    # those accounts reached _sync_account_metrics every single hour, built a
    # provider, and failed. They never write a snapshot row, so ``has_today_rows``
    # never became True and the waste repeated forever.
    enabled = AnalyticsPlatformConfig.enabled_platforms()
    syncable = [p for p in enabled if services.analytics_availability(p, enabled) is None]
    if not syncable:
        return

    started = timezone.now()
    today = started.date()
    deadline = started + _RUN_BUDGET
    # One breaker lookup per credential per run, not per account: accounts
    # overwhelmingly share one OAuth client, so without this the breaker would
    # cost a query per account to answer the same question.
    cache: dict = {}

    accounts = SocialAccount.objects.filter(
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        platform__in=syncable,
    ).select_related("workspace")

    totals = [0, 0, 0]  # synced, failed, api_calls
    seen = truncated = 0
    for account in accounts:
        now = timezone.now()
        if now >= deadline:
            truncated = 1
            logger.warning(
                "analytics sync: stopped after %s accounts — %s budget spent; next tick resumes",
                seen,
                _RUN_BUDGET,
            )
            break
        seen += 1
        result = _sync_one_account(account, today, now, cache=cache, deadline=deadline)
        totals = [a + b for a, b in zip(totals, result, strict=True)]

    blocked = sum(1 for value in cache.values() if value is not None and value > timezone.now())
    logger.info(
        "analytics sync: %s accounts, %s posts synced, %s failed, %s API calls, %s credential(s) quota-blocked%s",
        seen,
        totals[0],
        totals[1],
        totals[2],
        blocked,
        " (run truncated)" if truncated else "",
    )
