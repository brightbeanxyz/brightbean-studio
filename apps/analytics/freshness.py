"""Freshness helpers for analytics API responses.

Computes ``(captured_at, next_sync_eta)`` for the agent-facing analytics
endpoints. ``captured_at`` is the most-recent snapshot row touched for the
target; ``next_sync_eta`` mirrors the background sync cadence in
``apps/analytics/tasks.py`` so callers can pick a sensible poll delay.

These helpers are intentionally separated from ``apps/analytics/services.py``
because that module is consumed by Django templates today and stays
rendering-agnostic.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Max
from django.utils import timezone

from apps.composer.models import PlatformPost
from apps.social_accounts.models import SocialAccount

from .constants import NO_ANALYTICS_PLATFORMS
from .models import AccountInsightsSnapshot, PostInsightsSnapshot

# How long to wait between account-level syncs (matches the daily cadence
# in ``apps/analytics/tasks.py``).
_ACCOUNT_SYNC_INTERVAL = timedelta(hours=24)

# Sentinel for a just-connected account / just-published post with no rows
# yet — we want the agent to poll back soon rather than wait a full day.
_FIRST_POLL_DELAY = timedelta(minutes=5)


def account_freshness(
    account: SocialAccount,
    *,
    last_captured_at: datetime | None = None,
    have_last_captured_at: bool = False,
) -> tuple[datetime | None, datetime | None]:
    """Return ``(captured_at, next_sync_eta)`` for an account.

    * ``(None, None)`` for platforms in :data:`NO_ANALYTICS_PLATFORMS` — no
      background sync is scheduled and no snapshots will ever land.
    * ``(None, now + 5 min)`` for an account that has been connected but
      hasn't been synced yet, so the agent polls back shortly.
    * ``(last, last + 24 h)`` once any account-level snapshot exists.

    Callers that have already touched the snapshots table (e.g. via
    :func:`apps.analytics.services.account_analytics_bundle`) can pass
    the latest ``captured_at`` they observed via ``last_captured_at`` and
    set ``have_last_captured_at=True`` to skip the redundant ``Max``
    aggregate query. ``have_last_captured_at`` disambiguates "no
    snapshots yet" from "caller didn't check".
    """
    if account.platform in NO_ANALYTICS_PLATFORMS:
        return None, None
    if have_last_captured_at:
        last = last_captured_at
    else:
        last = AccountInsightsSnapshot.objects.filter(social_account=account).aggregate(latest=Max("captured_at"))[
            "latest"
        ]
    if last is None:
        return None, timezone.now() + _FIRST_POLL_DELAY
    return last, last + _ACCOUNT_SYNC_INTERVAL


def post_freshness(
    platform_post: PlatformPost,
    *,
    last_captured_at: datetime | None = None,
    have_last_captured_at: bool = False,
) -> tuple[datetime | None, datetime | None]:
    """Return ``(captured_at, next_sync_eta)`` for a per-platform post.

    The cadence ladder is :func:`apps.analytics.tasks.post_sync_interval`
    so this helper and the sync loop cannot drift.

    Drafts / scheduled posts (no ``published_at``) and posts on platforms
    without an analytics surface return ``(None, None)``.

    Callers that have already fetched snapshot rows (e.g. via
    :func:`apps.analytics.services.post_detail`) can pass the latest
    ``captured_at`` they observed via ``last_captured_at`` to skip the
    extra ``Max`` aggregate query. Pass ``have_last_captured_at=True`` to
    signal that the caller's lookup was authoritative — otherwise the
    helper will fall back to its own query (``None`` is ambiguous: it
    could mean "no snapshots" OR "caller didn't check").
    """
    from .tasks import post_sync_interval

    if platform_post.social_account.platform in NO_ANALYTICS_PLATFORMS:
        return None, None
    if not platform_post.published_at:
        return None, None
    if have_last_captured_at:
        last = last_captured_at
    else:
        last = PostInsightsSnapshot.objects.filter(platform_post=platform_post).aggregate(latest=Max("captured_at"))[
            "latest"
        ]
    age = timezone.now() - platform_post.published_at
    interval = post_sync_interval(age)
    if interval is None:
        # >90d: syncs have stopped, so there is no meaningful next ETA even
        # if ``last`` exists from earlier in the post's life.
        return last, None
    # If no rows yet, poll back sooner than the cadence would otherwise
    # suggest — we want the first-sync delay to drive the next ETA.
    if last is None:
        return None, timezone.now() + min(interval, _FIRST_POLL_DELAY)
    return last, last + interval
