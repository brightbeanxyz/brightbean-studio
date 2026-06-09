"""Cross-module constants for the analytics app."""

from __future__ import annotations

# Platforms whose APIs don't expose aggregate analytics. The analytics
# page renders a per-platform "not available" variant instead of zeroed-
# out KPI cards and charts.
#
# Each entry MUST also have ``BACKFILL_DAYS_PER_PLATFORM[<platform>] = 0``
# in ``apps/analytics/tasks.py`` — otherwise the background cron will
# still try to fetch metrics that don't exist.
NO_ANALYTICS_PLATFORMS: dict[str, str] = {
    "linkedin_personal": ("LinkedIn doesn't expose personal-profile analytics. Only Company Pages have analytics."),
    "bluesky": ("Bluesky's AT Protocol doesn't surface aggregate post analytics."),
    "mastodon": ("The Mastodon API doesn't expose aggregate post analytics."),
}
