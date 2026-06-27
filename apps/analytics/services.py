"""Read-side services for the analytics page.

These functions return shapes the templates can iterate over directly.
They never call into the provider layer — that's the sync task's job.
Pages read from the snapshot tables; if the snapshots are empty, the UI
shows the empty state.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date as dt_date
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.composer.models import PlatformPost
from apps.social_accounts.models import SocialAccount

from .constants import NO_ANALYTICS_PLATFORMS
from .derive import DerivedMetric, derive, engagement_rate, kind_of
from .metrics import (
    ACCOUNT_ONLY,
    METRICS,
    PLATFORM_METRICS,
    PLATFORM_PRIMARY,
    hero_card_metrics,
    post_metrics_for,
)
from .models import AccountInsightsSnapshot, PostInsightsSnapshot

# Metrics whose per-post values are unique-user-per-post counts; summing them
# across an account's posts double-counts users who saw multiple posts, so the
# post-fallback can't substitute for an account-level number. Account-level
# reach (and Meta's impressions, depending on the variant) is the right
# source; without it the metric stays empty rather than misleadingly inflated.
_POST_FALLBACK_DENYLIST: frozenset[str] = frozenset({"reach"})


def unavailable_reason(platform: str, enabled_platforms: list[str] | None = None) -> str | None:
    """Why ``platform`` has no live analytics, or ``None`` if it does.

    Combines the two independent gates that the analytics stack honors:

    * :data:`apps.analytics.constants.NO_ANALYTICS_PLATFORMS` — the
      platform's API exposes no aggregate analytics at all (LinkedIn
      Personal, Bluesky, Mastodon).
    * :class:`apps.social_accounts.models.AnalyticsPlatformConfig` — an
      admin has switched the platform off (e.g. provider app-review for
      analytics scopes is still pending), so the background sync skips it.

    Lives in ``services.py`` (not the agent-API builders) so the web view
    (``apps/analytics/views.py``), the sync cron
    (``apps/analytics/tasks.py``) and the agent-API surface all import
    the same predicate — if a third gate ever lands, only this function
    needs to know.

    ``enabled_platforms`` may be supplied (e.g. in a per-request cache)
    to avoid re-querying ``AnalyticsPlatformConfig`` once per call.
    """
    inherent = NO_ANALYTICS_PLATFORMS.get(platform)
    if inherent is not None:
        return inherent
    if enabled_platforms is None:
        # Lazy import to avoid pulling the social_accounts app at module
        # load time — services.py is imported by URL config.
        from apps.social_accounts.models import AnalyticsPlatformConfig

        enabled_platforms = AnalyticsPlatformConfig.enabled_platforms()
    if platform not in enabled_platforms:
        return "Analytics is not currently enabled for this platform."
    return None


def _series_for(
    account: SocialAccount,
    metric_key: str,
    end: dt_date,
    days: int,
) -> list[float]:
    """Return ``2 * days`` values ending at ``end`` (older first).

    Missing days fill as 0.0 so the derive math has a contiguous series.
    """
    start = end - timedelta(days=2 * days - 1)
    rows = AccountInsightsSnapshot.objects.filter(
        social_account=account,
        metric_key=metric_key,
        date__gte=start,
        date__lte=end,
    ).order_by("date")
    by_day: dict[dt_date, float] = {r.date: r.value for r in rows}
    if not by_day and _supports_post_fallback(metric_key):
        fallback, _ = _post_summed_series_for_metric(account, metric_key, start, end)
        by_day.update(fallback)
    out: list[float] = []
    for i in range(2 * days):
        d = start + timedelta(days=i)
        out.append(by_day.get(d, 0.0))
    return out


def _supports_post_fallback(metric_key: str) -> bool:
    """Which metric keys can be derived by summing per-post deltas.

    Counts and minutes sum linearly. Account-only growth (subscribers,
    follows, followers) is undefined for posts; rate-style metrics
    (avg_view_pct, engagement) cannot be summed; and unique-user metrics
    (reach) double-count users when summed across posts. Unknown metric
    keys (not registered in :data:`METRICS`) return False so a forgotten
    catalog entry doesn't quietly run a per-post scan.
    """
    if metric_key not in METRICS:
        return False
    if metric_key in ACCOUNT_ONLY or metric_key in _POST_FALLBACK_DENYLIST:
        return False
    return kind_of(metric_key) in ("count", "minutes")


def _post_summed_series_for_metric(
    account: SocialAccount,
    metric_key: str,
    start: dt_date,
    end: dt_date,
) -> tuple[dict[dt_date, float], Any]:
    """Per-day deltas of cumulative post snapshots, summed across all posts.

    ``PostInsightsSnapshot.value`` stores the cumulative-lifetime count for
    that metric at sync time. To get "what happened on day D" we take
    ``snapshot(D) - snapshot(latest before D)`` per post and sum across the
    account's posts. Used as a hero/chart fallback when no
    ``AccountInsightsSnapshot`` rows exist for the metric — keeps the main
    page consistent with the per-post drawer for platforms that ship without
    an account-level analytics API.

    Returns ``(daily_totals, max_captured_at)``. The caller folds
    ``max_captured_at`` into the bundle's freshness signal so a fallback-only
    YouTube/TikTok response doesn't report "no data yet".

    Three correctness rules in the iteration:
      * The query is bounded to ``[start, end]`` for performance. The first
        observation per post (typical for accounts that just connected:
        backfill writes a single cumulative-lifetime row dated today) needs
        special handling — naively crediting ``value - 0`` dumps the entire
        lifetime onto the snapshot day. Three cases:
          - Post published BEFORE the window: anchor ``prev_value`` and
            skip the credit. The cumulative is mostly pre-window activity
            we can't attribute to days we don't have snapshots for.
          - Post published INSIDE the window: distribute the cumulative
            uniformly across ``[pub_day, snapshot_day]`` so the lifetime
            isn't piled onto the snapshot day. This matches what Codex's
            adversarial review flagged — for an account where backfill
            writes a single lifetime snapshot per post, the chart would
            otherwise inflate today by the sum of every in-window post's
            lifetime totals.
          - Missing/post-snapshot ``published_at``: fall back to crediting
            the snapshot day. Conservative, matches legacy behavior.
      * A negative delta (count reset, deleted reactions, platform recount)
        skips both the credit AND the ``prev_value`` advance, so a later
        recovery is measured against the pre-reset high-water mark instead
        of being over-credited.
    """
    rows = (
        PostInsightsSnapshot.objects.filter(
            platform_post__social_account=account,
            metric_key=metric_key,
            date__gte=start,
            date__lte=end,
        )
        .order_by("platform_post_id", "date")
        .values_list(
            "platform_post_id",
            "platform_post__published_at",
            "date",
            "value",
            "captured_at",
        )
    )
    out: dict[dt_date, float] = defaultdict(float)
    max_captured: Any = None
    current_post_id: Any = None
    prev_value = 0.0
    first_obs_for_post = True
    for post_id, published_at, day, value, captured_at in rows:
        if post_id != current_post_id:
            current_post_id = post_id
            first_obs_for_post = True
            prev_value = 0.0
        v = float(value)
        if captured_at and (max_captured is None or captured_at > max_captured):
            max_captured = captured_at
        if first_obs_for_post:
            first_obs_for_post = False
            pub_day = published_at.date() if published_at is not None else None
            if pub_day is None or pub_day > day:
                # No publish date or it's after the snapshot (data oddity);
                # credit the snapshot day if in window — least-bad guess.
                if start <= day <= end:
                    out[day] += v
            elif pub_day < start:
                # Predates window — first in-window snapshot is mostly
                # pre-window activity. Anchor only; don't credit.
                pass
            else:
                # Published inside the window — distribute uniformly across
                # [pub_day, day] so a single cumulative snapshot doesn't
                # spike one day with the post's lifetime total.
                n_days = (day - pub_day).days + 1
                per_day = v / n_days
                d = pub_day
                while d <= day:
                    if start <= d <= end:
                        out[d] += per_day
                    d += timedelta(days=1)
            prev_value = v
            continue
        delta = v - prev_value
        if delta <= 0:
            continue
        prev_value = v
        out[day] += delta
    return dict(out), max_captured


def account_series_map(
    account: SocialAccount,
    days: int,
) -> dict[str, list[float]]:
    """Return ``{metric_key: 2*days-long series}`` for every platform metric.

    Kept as a thin wrapper around :func:`account_analytics_bundle` for
    callers that don't need the freshness side-channel (the web view's
    chart-only HTMX partial). Most callers should use the bundle so they
    can also recover the latest ``captured_at`` without an extra query.
    """
    return account_analytics_bundle(account, days)["series_map"]


def account_analytics_bundle(account: SocialAccount, days: int) -> dict[str, Any]:
    """Single-pass snapshot fetch for one account over a ``2 * days`` window.

    Returns a dict with:
      - ``series_map``: ``{metric_key: 2*days-long series}``
      - ``max_captured_at``: latest ``captured_at`` across the fetched rows,
        or ``None`` if no snapshots exist in the window.

    Replaces the previous "1 query per metric" pattern (8 SELECTs for IG)
    with a single bulk SELECT, and exposes the freshness max so callers
    don't need a separate ``Max("captured_at")`` aggregate.
    """
    end = timezone.now().date()
    start = end - timedelta(days=2 * days - 1)
    platform_metrics = PLATFORM_METRICS.get(account.platform, [])

    rows = list(
        AccountInsightsSnapshot.objects.filter(
            social_account=account,
            metric_key__in=platform_metrics,
            date__gte=start,
            date__lte=end,
        )
    )
    by_metric: dict[str, dict[dt_date, float]] = defaultdict(dict)
    captured_by_metric: dict[str, Any] = {}
    max_captured: Any = None
    metrics_with_account_data: set[str] = set()
    for r in rows:
        by_metric[r.metric_key][r.date] = r.value
        metrics_with_account_data.add(r.metric_key)
        if r.metric_key not in captured_by_metric or r.captured_at > captured_by_metric[r.metric_key]:
            captured_by_metric[r.metric_key] = r.captured_at
        if max_captured is None or r.captured_at > max_captured:
            max_captured = r.captured_at

    # Hybrid fallback: for content-attribution metrics, derive a daily series
    # by summing per-post deltas so platforms without ``get_account_metrics``
    # (YouTube, TikTok, etc.) still get populated hero cards and charts.
    #
    # Also prefer the per-post series when it is fresher than account-level
    # rows. Facebook account insights are synced at most daily, while per-post
    # metrics can refresh hourly; without this freshness check the main graph
    # can lag behind the post drawer/table even though newer post snapshots are
    # already stored.
    for m in platform_metrics:
        if not _supports_post_fallback(m):
            continue
        daily, fallback_captured = _post_summed_series_for_metric(account, m, start, end)
        if not daily:
            continue
        account_captured = captured_by_metric.get(m)
        should_use_fallback = m not in metrics_with_account_data or (
            fallback_captured is not None and account_captured is not None and fallback_captured > account_captured
        )
        if should_use_fallback:
            by_metric[m].update(daily)
            if fallback_captured is not None and (max_captured is None or fallback_captured > max_captured):
                max_captured = fallback_captured

    series_map = {
        m: [by_metric[m].get(start + timedelta(days=i), 0.0) for i in range(2 * days)] for m in platform_metrics
    }
    return {"series_map": series_map, "max_captured_at": max_captured}


def hero_cards(
    account: SocialAccount,
    days: int,
    *,
    series_map: dict[str, list[float]] | None = None,
) -> list[dict[str, Any]]:
    """List of {metric, label, derived} for the hero KPI cards.

    Pass ``series_map`` to reuse an already-fetched
    :func:`account_analytics_bundle` result. Without it, the helper
    falls back to its own per-metric queries (kept for the views that
    iterate the trio individually).
    """
    if series_map is None:
        series_map = account_series_map(account, days)
    return [
        {
            "metric": m,
            "label": _label(m),
            "derived": derive(series_map.get(m, []), days, kind_of(m)),
        }
        for m in hero_card_metrics(account.platform)
    ]


def engagement_card(
    account: SocialAccount,
    days: int,
    *,
    series_map: dict[str, list[float]] | None = None,
) -> dict[str, Any] | None:
    """Engagement-rate card payload, or ``None`` if the platform lacks a denom.

    Returns a dict with:
      - ``rate``: DerivedMetric for the rate headline + sparkline
      - ``parts``: list of {metric, label, derived} for the 2x2 sub-grid

    Pass ``series_map`` to reuse an already-fetched
    :func:`account_analytics_bundle` result.
    """
    from .metrics import ENGAGEMENT_PARTS, has_engagement_card

    if not has_engagement_card(account.platform):
        return None
    if series_map is None:
        series_map = account_series_map(account, days)
    rate = engagement_rate(series_map, days, fallback_followers=account.follower_count)
    parts = [
        {
            "metric": m,
            "label": _label(m),
            "derived": derive(series_map.get(m, []), days, kind_of(m)),
        }
        for m in PLATFORM_METRICS.get(account.platform, [])
        if m in ENGAGEMENT_PARTS
    ]
    return {"rate": rate, "parts": parts}


def hero_chart_metrics(account: SocialAccount) -> list[str]:
    """Metric chips for the hero chart selector — counts only, no rates."""
    return [m for m in PLATFORM_METRICS.get(account.platform, []) if kind_of(m) == "count" and m not in ACCOUNT_ONLY]


def hero_chart_data(
    account: SocialAccount,
    days: int,
    metric: str | None = None,
    *,
    series_map: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    """Payload for the hero area chart: selected metric, date labels, values.

    Pass ``series_map`` to reuse an already-fetched
    :func:`account_analytics_bundle` result and skip the per-metric query
    inside :func:`_series_for` — the bundle already computed every metric's
    2*days-long series, including the post-fallback path.
    """
    chips = hero_chart_metrics(account)
    selected = metric if metric in chips else (PLATFORM_PRIMARY.get(account.platform) or (chips[0] if chips else ""))
    end = timezone.now().date()
    if series_map is not None and selected in series_map:
        series = series_map[selected]
    else:
        series = _series_for(account, selected, end, days)
    derived = derive(series, days, kind_of(selected))
    # Date labels for the X axis (current window only).
    labels = [(end - timedelta(days=days - 1 - i)).isoformat() for i in range(days)]
    return {
        "metric": selected,
        "label": _label(selected),
        "chips": [{"key": m, "label": _label(m)} for m in chips],
        "derived": derived,
        "labels": labels,
    }


def follower_growth(
    account: SocialAccount,
    days: int,
    *,
    series_map: dict[str, list[float]] | None = None,
) -> DerivedMetric | None:
    """Account-level follower growth (new followers/subscribers) for the header.

    Kept for the templates that destructure the bare ``DerivedMetric`` —
    callers that need the underlying metric key (e.g. the agent-API
    schema) should use :func:`follower_growth_metric` instead so they
    don't have to re-derive the key from ``PLATFORM_METRICS``.
    """
    pair = follower_growth_metric(account, days, series_map=series_map)
    return pair[1] if pair else None


def follower_growth_metric(
    account: SocialAccount,
    days: int,
    *,
    series_map: dict[str, list[float]] | None = None,
) -> tuple[str, DerivedMetric] | None:
    """Same as :func:`follower_growth` but also returns the metric key.

    Returns ``(metric_key, derived)`` where ``metric_key`` is
    ``"subscribers"`` on YouTube, ``"follows"`` for daily-delta platforms
    (Instagram, Facebook, LinkedIn …), ``"followers"`` for platforms whose
    API only exposes a cumulative lifetime total (TikTok), and ``None``
    on platforms without an account-level growth metric.

    Pass ``series_map`` to reuse an already-fetched
    :func:`account_analytics_bundle` result instead of issuing another
    per-metric query.
    """
    # Mutually exclusive per platform — first-match-wins. ``derive`` handles
    # both delta-style (``follows``/``subscribers``) and total-style
    # (``followers``) series correctly because both are catalog kind="count".
    growth_metric = next(
        (m for m in ("subscribers", "follows", "followers") if m in PLATFORM_METRICS.get(account.platform, [])),
        None,
    )
    if not growth_metric:
        return None
    if series_map is not None and growth_metric in series_map:
        series = series_map[growth_metric]
    else:
        series = _series_for(account, growth_metric, timezone.now().date(), days)
    if growth_metric == "followers":
        end = timezone.now().date()
        current_start = end - timedelta(days=days - 1)
        previous_start = end - timedelta(days=(2 * days) - 1)
        rows = list(
            AccountInsightsSnapshot.objects.filter(
                social_account=account,
                metric_key=growth_metric,
                date__gte=previous_start,
                date__lte=end,
            )
            .order_by("date")
            .values_list("date", "value")
        )

        def window_delta(start: dt_date, stop: dt_date) -> float:
            values = [value for day, value in rows if start <= day <= stop]
            if len(values) < 2:
                return 0.0
            return max(float(values[-1]) - float(values[0]), 0.0)

        cur_val = window_delta(current_start, end)
        prev_val = window_delta(previous_start, current_start - timedelta(days=1))
        delta = ((cur_val - prev_val) / prev_val) * 100 if prev_val else 0.0
        by_day = {day: float(value) for day, value in rows}
        previous_value = next(
            (float(value) for day, value in reversed(rows) if day < current_start),
            None,
        )
        daily_series: list[float] = []
        for i in range(days):
            day = current_start + timedelta(days=i)
            value = by_day.get(day)
            if value is None:
                daily_series.append(0.0)
                continue
            daily_series.append(max(value - previous_value, 0.0) if previous_value is not None else 0.0)
            previous_value = value
        return growth_metric, DerivedMetric(
            value=cur_val,
            delta=round(delta, 1),
            series=daily_series,
            kind=kind_of(growth_metric),
        )
    return growth_metric, derive(series, days, kind_of(growth_metric))


def all_posts_for(
    account: SocialAccount,
    *,
    days_filter: int | None,
    sort_key: str | None,
    sort_dir: str = "desc",
    type_filter: str = "all",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Page of posts + per-post stats, sortable + filterable.

    ``days_filter=None`` means "all time". ``sort_key=None`` falls back to the
    platform's primary metric.
    """
    qs = (
        PlatformPost.objects.filter(
            social_account=account,
            status=PlatformPost.Status.PUBLISHED,
            published_at__isnull=False,
        )
        .select_related("post")
        .prefetch_related("post__media_attachments__media_asset")
        .order_by("-published_at")
    )
    if days_filter is not None:
        cutoff = timezone.now() - timedelta(days=days_filter)
        qs = qs.filter(published_at__gte=cutoff)

    posts: list[PlatformPost] = list(qs)
    metrics = post_metrics_for(account.platform)
    stats_by_post = _latest_post_stats(posts, metrics)

    rows: list[dict[str, Any]] = []
    for p in posts:
        media_kind = _media_kind(p)
        rows.append(
            {
                "post": p,
                "caption": (p.platform_specific_caption or p.post.caption or "").strip(),
                "date": p.published_at.date().isoformat() if p.published_at else "",
                "days_ago": (timezone.now() - p.published_at).days if p.published_at else None,
                "media_kind": media_kind,
                "media_preview": _first_media_preview(p),
                "stats": stats_by_post.get(p.id, {}),
            }
        )
    if type_filter != "all":
        rows = [r for r in rows if r["media_kind"] == type_filter]

    primary = PLATFORM_PRIMARY.get(account.platform, "")
    effective_sort = sort_key if (sort_key in metrics or sort_key == "date") else primary
    reverse = sort_dir != "asc"
    if effective_sort == "date":
        rows.sort(key=lambda r: r["days_ago"] if r["days_ago"] is not None else 9999, reverse=not reverse)
    elif effective_sort:
        rows.sort(key=lambda r: r["stats"].get(effective_sort, 0), reverse=reverse)

    total = len(rows)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = max(1, min(page, total_pages))
    start = (safe_page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return {
        "metrics": metrics,
        "metric_labels": [{"key": m, "label": _label(m), "kind": kind_of(m)} for m in metrics],
        "media_kinds": sorted({r["media_kind"] for r in rows} - {""}),
        "type_filter": type_filter,
        "rows": page_rows,
        "total": total,
        "page": safe_page,
        "total_pages": total_pages,
        "page_from": 0 if total == 0 else start + 1,
        "page_to": min(end, total),
        "sort_key": effective_sort,
        "sort_dir": sort_dir,
        # The direction to send when re-clicking the currently-sorted column.
        # Computed here because Django's ``yesno`` filter treats both ``"asc"``
        # and ``"desc"`` as truthy, so it can't be used to flip the value.
        "toggled_dir": "desc" if sort_dir == "asc" else "asc",
        "days_filter": days_filter,
        "primary": primary,
    }


def post_detail(post: PlatformPost) -> dict[str, Any]:
    """Payload for the slide-over post-detail drawer.

    Includes ``captured_at`` — the latest snapshot timestamp across the
    rows backing this post's metric tiles — so callers that also need the
    freshness signal (the agent API's
    :func:`apps.analytics.freshness.post_freshness`) don't have to issue
    a separate ``Max`` aggregate query.
    """
    account = post.social_account
    metrics = post_metrics_for(account.platform)
    stats = _latest_post_stats([post], metrics).get(post.id, {})
    sparklines_by_metric, max_captured = _post_sparklines_with_freshness(post, metrics)
    return {
        "post": post,
        "account": account,
        "caption": (post.platform_specific_caption or post.post.caption or "").strip(),
        "date": post.published_at.date().isoformat() if post.published_at else "",
        "days_ago": (timezone.now() - post.published_at).days if post.published_at else None,
        "media_kind": _media_kind(post),
        "media_preview": _first_media_preview(post),
        "captured_at": max_captured,
        "metric_tiles": [
            {
                "key": m,
                "label": _label(m),
                "value": stats.get(m, 0),
                "kind": kind_of(m),
                "sparkline": sparklines_by_metric.get(m, []),
                "is_primary": m == PLATFORM_PRIMARY.get(account.platform),
            }
            for m in metrics
        ],
    }


# --- helpers -------------------------------------------------------------


def _label(metric_key: str) -> str:
    from .metrics import METRICS

    return METRICS.get(metric_key, {}).get("label", metric_key.replace("_", " ").title())


def _latest_post_stats(posts: Iterable[PlatformPost], metrics: list[str]) -> dict[Any, dict[str, float]]:
    """For each post, return ``{metric_key: latest value}``."""
    post_ids = [p.id for p in posts]
    if not post_ids:
        return {}
    rows = PostInsightsSnapshot.objects.filter(platform_post_id__in=post_ids, metric_key__in=metrics).order_by(
        "platform_post_id", "metric_key", "-date"
    )
    out: dict[Any, dict[str, float]] = defaultdict(dict)
    seen: set[tuple[Any, str]] = set()
    for r in rows:
        key = (r.platform_post_id, r.metric_key)
        if key in seen:
            continue
        seen.add(key)
        out[r.platform_post_id][r.metric_key] = r.value
    return out


def _post_sparklines(post: PlatformPost, metrics: list[str]) -> dict[str, list[float]]:
    """Daily history per metric since publish — for the detail-drawer sparkline."""
    return _post_sparklines_with_freshness(post, metrics)[0]


def _post_sparklines_with_freshness(post: PlatformPost, metrics: list[str]) -> tuple[dict[str, list[float]], Any]:
    """Same as :func:`_post_sparklines` but also returns the max ``captured_at``.

    Used by :func:`post_detail` so the freshness side-channel
    (:func:`apps.analytics.freshness.post_freshness`) doesn't need its own
    ``Max("captured_at")`` aggregate against the same rows.
    """
    rows = PostInsightsSnapshot.objects.filter(platform_post=post, metric_key__in=metrics).order_by(
        "metric_key", "date"
    )
    out: dict[str, list[float]] = defaultdict(list)
    max_captured: Any = None
    for r in rows:
        out[r.metric_key].append(r.value)
        if max_captured is None or r.captured_at > max_captured:
            max_captured = r.captured_at
    return dict(out), max_captured


def _media_kind(post: PlatformPost) -> str:
    """Best-effort media-kind label for the table filter and detail header."""
    platform_default = {
        "instagram": "Post",
        "instagram_login": "Post",
        "tiktok": "Video",
        "youtube": "Video",
        "linkedin_company": "Post",
        "linkedin_personal": "Post",
        "facebook": "Post",
        "bluesky": "Post",
        "threads": "Post",
        "pinterest": "Pin",
        "google_business": "Post",
        "mastodon": "Post",
    }
    return platform_default.get(post.social_account.platform, "Post")


def _first_media_preview(post: PlatformPost) -> dict[str, str] | None:
    """First attachment's preview: {"url", "kind"} where kind is "image" or "video".

    Prefers the asset's generated thumbnail (always an image). Falls back to the
    asset's own file so videos without a poster still render — the template uses
    a ``<video>`` element with ``#t=0.5`` to show a poster frame.
    """
    pm = next(iter(post.post.media_attachments.all()), None)
    if pm is None:
        return None
    asset = pm.media_asset
    if asset.thumbnail:
        return {"url": asset.thumbnail.url, "kind": "image"}
    if asset.file:
        return {"url": asset.file.url, "kind": "video" if asset.is_video else "image"}
    return None
