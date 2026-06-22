"""Persistent snapshot tables for analytics.

These tables ARE the cache — there's no separate Django cache layer. The
``captured_at`` column is the freshness signal the sync layer uses to
decide whether a re-fetch is needed.
"""

from __future__ import annotations

from django.db import models


class AccountInsightsSnapshot(models.Model):
    """One row per (account, metric, day) — the daily account-level series.

    Populated by ``apps.analytics.tasks.sync_account_analytics`` and the
    on-connect backfill. Read by the hero chart and KPI cards.
    """

    social_account = models.ForeignKey(
        "social_accounts.SocialAccount",
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
    )
    metric_key = models.CharField(max_length=40)
    date = models.DateField()
    # Stored as float so we can hold both counts (integers) and rates (e.g.
    # avg_view_pct, engagement). Templates format based on metrics.METRICS[kind].
    value = models.FloatField(default=0.0)
    raw = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_account_insights_snapshot"
        unique_together = [("social_account", "metric_key", "date")]
        indexes = [
            models.Index(fields=["social_account", "metric_key", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.social_account_id} · {self.metric_key} · {self.date} = {self.value}"


class PostInsightsSnapshot(models.Model):
    """One row per (platform_post, metric, day) — daily history per post.

    Sync writes are UPSERTs keyed on the unique tuple. Multiple hourly ticks
    in the same day overwrite today's row with the latest cumulative value,
    so the per-post growth sparkline shows one data point per day.
    """

    platform_post = models.ForeignKey(
        "composer.PlatformPost",
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
    )
    metric_key = models.CharField(max_length=40)
    date = models.DateField()
    value = models.FloatField(default=0.0)
    raw = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_post_insights_snapshot"
        unique_together = [("platform_post", "metric_key", "date")]
        indexes = [
            models.Index(fields=["platform_post", "metric_key", "date"]),
            models.Index(fields=["platform_post", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform_post_id} · {self.metric_key} · {self.date} = {self.value}"
