"""Compose analytics service output into the agent-API response schemas.

Both the REST router (``apps/api/routers/analytics.py``) and the MCP
handlers (``apps/mcp/handlers.py``) call into this module so the two
surfaces emit identical bodies. The REST router only adds HTTP-shaped
concerns (rate limits, audit logging); the actual model → schema work
lives here.

Routers in this codebase are pure dispatch, so MCP imports from this
module rather than from the router — mirroring how ``apps.mcp.handlers``
already pulls ``PostResponse`` straight from ``apps.api.schemas`` for
parity-safe serialization.
"""

from __future__ import annotations

from apps.api.schemas import (
    AccountAnalyticsResponse,
    DerivedMetricResponse,
    EngagementCardResponse,
    PlatformPostAnalyticsResponse,
    PostAnalyticsResponse,
    PostMetricTileResponse,
)
from apps.composer.models import Post
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount

from .freshness import account_freshness, post_freshness
from .services import (
    _label,
    account_analytics_bundle,
    engagement_card,
    follower_growth_metric,
    hero_cards,
    post_detail,
    unavailable_reason,
)


def build_account_analytics(account: SocialAccount, days: int) -> AccountAnalyticsResponse:
    """Assemble the per-channel analytics response.

    For platforms with no live analytics — either inherently
    (:data:`NO_ANALYTICS_PLATFORMS`) or because an admin disabled the
    platform in :class:`AnalyticsPlatformConfig` — returns an
    ``analytics_available: false`` envelope with empty metric arrays and
    no freshness ETA, and issues no snapshot queries. Otherwise composes
    hero metrics, engagement, follower growth and freshness from the
    existing service layer.
    """
    reason = unavailable_reason(account.platform)
    if reason is not None:
        return AccountAnalyticsResponse(
            account_id=account.id,
            platform=account.platform,
            account_name=account.account_name,
            connection_status=account.connection_status,
            days=days,
            analytics_available=False,
            unavailable_reason=reason,
            hero_metrics=[],
            engagement=None,
            follower_growth=None,
            captured_at=None,
            next_sync_eta=None,
        )

    # Single-pass snapshot fetch — feed the same series_map to
    # hero_cards / engagement_card / follower_growth so they don't each
    # re-issue the per-metric SELECTs. Also recovers ``captured_at`` from
    # the same scan, so ``account_freshness`` skips its ``Max`` aggregate.
    bundle = account_analytics_bundle(account, days)
    series_map = bundle["series_map"]
    captured_at, next_sync_eta = account_freshness(
        account,
        last_captured_at=bundle["max_captured_at"],
        have_last_captured_at=True,
    )
    hero = [
        DerivedMetricResponse.from_derived(card["metric"], card["label"], card["derived"])
        for card in hero_cards(account, days, series_map=series_map)
    ]
    engagement_card_payload = engagement_card(account, days, series_map=series_map)
    engagement = None
    if engagement_card_payload is not None:
        rate = engagement_card_payload["rate"]
        engagement = EngagementCardResponse(
            rate=DerivedMetricResponse.from_derived("engagement", _label("engagement"), rate),
            parts=[
                DerivedMetricResponse.from_derived(part["metric"], part["label"], part["derived"])
                for part in engagement_card_payload["parts"]
            ],
        )
    growth_pair = follower_growth_metric(account, days, series_map=series_map)
    growth_response = None
    if growth_pair is not None:
        growth_key, growth = growth_pair
        growth_response = DerivedMetricResponse.from_derived(growth_key, _label(growth_key), growth)

    return AccountAnalyticsResponse(
        account_id=account.id,
        platform=account.platform,
        account_name=account.account_name,
        connection_status=account.connection_status,
        days=days,
        analytics_available=True,
        unavailable_reason=None,
        hero_metrics=hero,
        engagement=engagement,
        follower_growth=growth_response,
        captured_at=captured_at,
        next_sync_eta=next_sync_eta,
    )


def build_post_analytics(post: Post) -> PostAnalyticsResponse:
    """Assemble per-platform analytics for every child of a Post.

    Each ``PlatformPost`` gets its own envelope so a mixed-platform post
    (e.g. one Threads child + one Bluesky child) reports
    ``analytics_available`` independently per platform.
    """
    # ``_get_workspace_post`` (REST) and ``_get_post_for_key`` (MCP) already
    # prefetch ``platform_posts__social_account``; calling ``.all()`` here
    # serves from that cache. ``.select_related(...)`` would create a fresh
    # queryset that bypasses the prefetch and fires an extra query.
    children = list(post.platform_posts.all())
    # Resolve the admin-configured enable list once, not per child, so a
    # mixed-platform post stays at a single config query.
    enabled_platforms = AnalyticsPlatformConfig.enabled_platforms()
    return PostAnalyticsResponse(
        post_id=post.id,
        workspace_id=post.workspace_id,
        title=post.title,
        caption=post.caption,
        platform_posts=[_build_platform_post_analytics(child, enabled_platforms) for child in children],
    )


def _build_platform_post_analytics(platform_post, enabled_platforms: list[str]) -> PlatformPostAnalyticsResponse:
    account = platform_post.social_account
    reason = unavailable_reason(account.platform, enabled_platforms)

    # Short-circuit unavailable-platform and draft/scheduled cases BEFORE
    # any snapshot queries — drafts have nothing to fetch, and unavailable
    # platforms never have snapshots in the first place.
    if reason is not None:
        return PlatformPostAnalyticsResponse(
            platform_post_id=platform_post.id,
            social_account_id=account.id,
            platform=account.platform,
            status=platform_post.status,
            published_at=platform_post.published_at,
            analytics_available=False,
            unavailable_reason=reason,
            metric_tiles=[],
            captured_at=None,
            next_sync_eta=None,
        )
    if not platform_post.published_at:
        return PlatformPostAnalyticsResponse(
            platform_post_id=platform_post.id,
            social_account_id=account.id,
            platform=account.platform,
            status=platform_post.status,
            published_at=None,
            analytics_available=True,
            unavailable_reason=None,
            metric_tiles=[],
            captured_at=None,
            next_sync_eta=None,
        )

    detail = post_detail(platform_post)
    captured_at, next_sync_eta = post_freshness(
        platform_post,
        last_captured_at=detail["captured_at"],
        have_last_captured_at=True,
    )
    tiles = [
        PostMetricTileResponse(
            key=tile["key"],
            label=tile["label"],
            kind=tile["kind"],
            value=tile["value"],
            series=list(tile["sparkline"]),
            is_primary=tile["is_primary"],
        )
        for tile in detail["metric_tiles"]
    ]
    return PlatformPostAnalyticsResponse(
        platform_post_id=platform_post.id,
        social_account_id=account.id,
        platform=account.platform,
        status=platform_post.status,
        published_at=platform_post.published_at,
        analytics_available=True,
        unavailable_reason=None,
        metric_tiles=tiles,
        captured_at=captured_at,
        next_sync_eta=next_sync_eta,
    )
