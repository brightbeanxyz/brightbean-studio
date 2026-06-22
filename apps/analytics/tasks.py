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

from background_task import background
from django.db import transaction
from django.utils import timezone

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
    # Bluesky / Mastodon / LinkedIn-Personal have no analytics surface — skip.
    # LinkedIn only exposes share statistics for Organization URNs, not
    # personal Person URNs, regardless of granted scopes.
    "bluesky": 0,
    "mastodon": 0,
    "linkedin_personal": 0,
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
        ("profile_views", "profile_visits"),
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
    # platform's catalog lists ``followers`` (today: TikTok). Use ``is not
    # None`` so brand-new accounts with 0 followers still get a baseline
    # snapshot — the chart needs the zero day to render a continuous line.
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
    """Mirror apps.social_accounts.tasks.check_social_account_health's credential
    resolution so platforms with org-level creds (Meta apps, etc.) work."""
    from apps.credentials.models import resolve_platform_credentials
    from providers import get_provider

    # .env is dominant; admin-entered org credentials are the fallback.
    credentials = resolve_platform_credentials(account.platform, account.workspace.organization_id)

    if account.platform == "mastodon" and account.instance_url:
        from apps.social_accounts.models import MastodonAppRegistration

        try:
            reg = MastodonAppRegistration.objects.get(instance_url=account.instance_url)
            credentials = {
                **credentials,
                "instance_url": account.instance_url,
                "client_id": reg.client_id,
                "client_secret": reg.client_secret,
            }
        except MastodonAppRegistration.DoesNotExist:
            pass
    elif account.platform == "instagram":
        credentials = {**credentials, "ig_user_id": account.account_platform_id}
    return get_provider(account.platform, credentials)


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


def _write_account_snapshot(account, metric_values: dict[str, float], on_date: dt_date) -> int:
    from .models import AccountInsightsSnapshot

    if not metric_values:
        return 0
    count = 0
    for key, value in metric_values.items():
        AccountInsightsSnapshot.objects.update_or_create(
            social_account=account,
            metric_key=key,
            date=on_date,
            defaults={"value": value},
        )
        count += 1
    return count


def _write_post_snapshot(post, metric_values: dict[str, float], on_date: dt_date) -> int:
    from .models import PostInsightsSnapshot

    if not metric_values:
        return 0
    count = 0
    for key, value in metric_values.items():
        PostInsightsSnapshot.objects.update_or_create(
            platform_post=post,
            metric_key=key,
            date=on_date,
            defaults={"value": value},
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


def _sync_account_metrics(account, on_date: dt_date) -> None:
    """Fetch account-level metrics for ``on_date`` and any recent missing days.

    Walks ``on_date`` and the prior ``_ACCOUNT_METRICS_RECENT_DAYS - 1`` days,
    skipping days that already have an :class:`AccountInsightsSnapshot`. For
    providers without lag (Instagram, Facebook) this is a no-op past
    ``on_date`` because the existing rows short-circuit the iteration.

    For YouTube, also fetches per-video Analytics-API metrics (watch_time,
    avg_view_pct, shares) that the Data API can't provide per-post — see
    :func:`_sync_youtube_post_analytics`.
    """
    from datetime import datetime, time

    from .models import AccountInsightsSnapshot

    provider = _resolve_provider(account)
    tz = timezone.get_current_timezone()
    # Providers whose stats endpoint returns only lifetime totals (TikTok)
    # must NOT have those totals written into past dates as if they were
    # historical observations — that fabricates fake history. Run only the
    # current day for them; backfill of true historical values is impossible
    # without an API that supports it.
    recent_days = _ACCOUNT_METRICS_RECENT_DAYS if getattr(provider, "account_metrics_supports_date_range", True) else 1
    for offset in range(recent_days):
        target = on_date - timedelta(days=offset)
        if AccountInsightsSnapshot.objects.filter(social_account=account, date=target).exists():
            continue
        start = datetime.combine(target, time.min, tzinfo=tz)
        end = datetime.combine(target, time.max, tzinfo=tz)
        try:
            metrics = provider.get_account_metrics(account.oauth_access_token, (start, end))
        except NotImplementedError:
            return
        except Exception as exc:
            if _is_insufficient_scope(exc):
                _mark_needs_reconnect(account)
            logger.warning("get_account_metrics failed for %s on %s: %s", account, target, exc)
            return
        _write_account_snapshot(account, _account_metrics_to_dict(metrics, account.platform), target)

    if account.platform == "youtube":
        _sync_youtube_post_analytics(account, provider, on_date)


def _sync_youtube_post_analytics(account, provider, on_date: dt_date) -> None:
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

    tz = timezone.get_current_timezone()
    start = datetime.combine(_YOUTUBE_ANALYTICS_LIFETIME_START, time.min, tzinfo=tz)
    end = datetime.combine(on_date, time.max, tzinfo=tz)

    try:
        per_video = provider.get_post_analytics(account.oauth_access_token, post_ids, (start, end))
    except NotImplementedError:
        return
    except Exception as exc:
        if _is_insufficient_scope(exc):
            _mark_needs_reconnect(account)
        logger.warning("get_post_analytics failed for %s on %s: %s", account, on_date, exc)
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
        _write_post_snapshot(post, _post_metrics_to_dict(metrics, "youtube"), on_date)


def _sync_post_metrics(post, on_date: dt_date) -> None:
    """Fetch this post's current metrics and write today's snapshot rows."""
    account = post.social_account
    provider = _resolve_provider(account)
    try:
        metrics = provider.get_post_metrics(account.oauth_access_token, post.platform_post_id)
    except NotImplementedError:
        return
    except Exception as exc:
        if _is_insufficient_scope(exc):
            _mark_needs_reconnect(account)
        logger.warning("get_post_metrics failed for post %s (%s): %s", post.id, account.platform, exc)
        return
    _write_post_snapshot(post, _post_metrics_to_dict(metrics, account.platform), on_date)


def _mark_needs_reconnect(account):
    if account.analytics_needs_reconnect:
        return
    account.analytics_needs_reconnect = True
    account.save(update_fields=["analytics_needs_reconnect", "updated_at"])


def _post_cadence_due(post, now=None, *, platform: str | None = None) -> bool:
    """Decide whether ``post`` is due for a new ``_sync_post_metrics`` sync.

    Looks at the latest ``PostInsightsSnapshot.captured_at`` for ``post`` and
    compares it against the decay schedule. Excludes the platform-specific
    Analytics-only metric keys listed in
    :data:`_POST_NON_CADENCE_METRICS_BY_PLATFORM` so a snapshot written by a
    different sync path (the batched YouTube per-video Analytics fetch in
    :func:`_sync_youtube_post_analytics`) doesn't reset the cadence and
    starve the Data-API loop of refreshes.

    ``platform`` may be supplied by callers iterating posts of a known
    account to avoid the implicit ``post.social_account.platform`` lookup.
    """
    from .models import PostInsightsSnapshot

    now = now or timezone.now()
    if not post.published_at:
        return False
    cadence = post_sync_interval(now - post.published_at)
    if cadence is None:
        return False  # past the 90-day horizon.
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
# Public entrypoints
# ---------------------------------------------------------------------------


@background(schedule=0)
def backfill_account_analytics(account_id: str, days: int | None = None) -> None:
    """One-shot backfill on account connect / reconnect.

    Account-level: writes today's row (the only one we can reliably get
    without provider time-series support — full historical backfill is
    deferred until we extend providers to return daily series).

    Per-post: for every published post within the platform's window, fetch
    its current cumulative metrics and write today's snapshot rows.
    """
    from apps.composer.models import PlatformPost
    from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount

    try:
        account = SocialAccount.objects.get(id=account_id)
    except SocialAccount.DoesNotExist:
        return
    enabled = set(AnalyticsPlatformConfig.enabled_platforms())
    if account.platform not in enabled:
        return
    cap = BACKFILL_DAYS_PER_PLATFORM.get(account.platform, DEFAULT_BACKFILL_DAYS)
    if cap == 0:
        return
    days = min(days or cap, cap)
    today = timezone.now().date()
    cutoff = timezone.now() - timedelta(days=days)

    _sync_account_metrics(account, today)

    posts = PlatformPost.objects.filter(
        social_account=account,
        status=PlatformPost.Status.PUBLISHED,
        published_at__gte=cutoff,
    ).exclude(platform_post_id="")
    for post in posts:
        with transaction.atomic():
            _sync_post_metrics(post, today)


@background(schedule=0)
def sync_all_account_analytics() -> None:
    """Hourly cron: refresh enabled accounts on the decay-by-age schedule."""
    from apps.composer.models import PlatformPost
    from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount

    enabled = set(AnalyticsPlatformConfig.enabled_platforms())
    if not enabled:
        return
    today = timezone.now().date()

    accounts = SocialAccount.objects.filter(
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        platform__in=enabled,
    ).select_related("workspace")
    from .models import AccountInsightsSnapshot

    for account in accounts:
        # Account-level: at most once per day per account. Skip if today's
        # row already exists so an hourly cron doesn't turn into 24 API calls.
        # Also skip accounts already flagged for analytics reconnect — their
        # token can't read the Analytics API, so retrying only re-fails and
        # re-logs every hour. Reconnecting clears the flag and runs a one-shot
        # backfill (see backfill_account_analytics), so the cron resumes on its
        # own. The per-post Data-API loop below still runs (it uses the
        # publish/read scopes the account already has).
        if (
            not account.analytics_needs_reconnect
            and not AccountInsightsSnapshot.objects.filter(social_account=account, date=today).exists()
        ):
            _sync_account_metrics(account, today)

        # Per-post: only those whose cadence window has elapsed
        cap_days = BACKFILL_DAYS_PER_PLATFORM.get(account.platform, DEFAULT_BACKFILL_DAYS)
        if cap_days == 0:
            continue
        cutoff = timezone.now() - timedelta(days=cap_days)
        posts = PlatformPost.objects.filter(
            social_account=account,
            status=PlatformPost.Status.PUBLISHED,
            published_at__gte=cutoff,
        ).exclude(platform_post_id="")
        for post in posts:
            if _post_cadence_due(post, platform=account.platform):
                _sync_post_metrics(post, today)
