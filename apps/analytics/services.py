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

from .derive import DerivedMetric, derive, engagement_rate, kind_of
from .metrics import (
    ACCOUNT_ONLY,
    ENGAGEMENT_DENOMINATORS,
    PLATFORM_METRICS,
    PLATFORM_PRIMARY,
    hero_card_metrics,
    post_metrics_for,
)
from .models import AccountInsightsSnapshot, PostInsightsSnapshot


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
    by_day = {r.date: r.value for r in rows}
    out: list[float] = []
    for i in range(2 * days):
        d = start + timedelta(days=i)
        out.append(by_day.get(d, 0.0))
    return out


def account_series_map(
    account: SocialAccount,
    days: int,
) -> dict[str, list[float]]:
    """Return ``{metric_key: 2*days-long series}`` for every platform metric."""
    end = timezone.now().date()
    return {m: _series_for(account, m, end, days) for m in PLATFORM_METRICS.get(account.platform, [])}


def hero_cards(account: SocialAccount, days: int) -> list[dict[str, Any]]:
    """List of {metric, label, derived} for the hero KPI cards."""
    series_map = account_series_map(account, days)
    return [
        {
            "metric": m,
            "label": _label(m),
            "derived": derive(series_map.get(m, []), days, kind_of(m)),
        }
        for m in hero_card_metrics(account.platform)
    ]


def engagement_card(account: SocialAccount, days: int) -> dict[str, Any] | None:
    """Engagement-rate card payload, or ``None`` if the platform lacks a denom.

    Returns a dict with:
      - ``rate``: DerivedMetric for the rate headline + sparkline
      - ``parts``: list of {metric, label, derived} for the 2x2 sub-grid
    """
    from .metrics import ENGAGEMENT_PARTS, has_engagement_card

    if not has_engagement_card(account.platform):
        return None
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
) -> dict[str, Any]:
    """Payload for the hero area chart: selected metric, date labels, values."""
    chips = hero_chart_metrics(account)
    selected = metric if metric in chips else (PLATFORM_PRIMARY.get(account.platform) or (chips[0] if chips else ""))
    end = timezone.now().date()
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


def follower_growth(account: SocialAccount, days: int) -> DerivedMetric | None:
    """Account-level follower growth (new followers/subscribers) for the header."""
    growth_metric = next(
        (m for m in ("subscribers", "follows") if m in PLATFORM_METRICS.get(account.platform, [])),
        None,
    )
    if not growth_metric:
        return None
    series = _series_for(account, growth_metric, timezone.now().date(), days)
    return derive(series, days, kind_of(growth_metric))


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
    """Payload for the slide-over post-detail drawer."""
    account = post.social_account
    metrics = post_metrics_for(account.platform)
    stats = _latest_post_stats([post], metrics).get(post.id, {})
    sparklines_by_metric = _post_sparklines(post, metrics)
    return {
        "post": post,
        "account": account,
        "caption": (post.platform_specific_caption or post.post.caption or "").strip(),
        "date": post.published_at.date().isoformat() if post.published_at else "",
        "days_ago": (timezone.now() - post.published_at).days if post.published_at else None,
        "media_kind": _media_kind(post),
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
    rows = (
        PostInsightsSnapshot.objects.filter(platform_post_id__in=post_ids, metric_key__in=metrics)
        .order_by("platform_post_id", "metric_key", "-date")
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
    rows = PostInsightsSnapshot.objects.filter(platform_post=post, metric_key__in=metrics).order_by("metric_key", "date")
    out: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        out[r.metric_key].append(r.value)
    return dict(out)


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
