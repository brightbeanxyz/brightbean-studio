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


class ProviderQuotaBlock(models.Model):
    """A platform API quota we know is spent, and when it comes back.

    The grain is the *credential*, not the account. YouTube charges Data API
    quota to the Google Cloud project behind the OAuth client, so one exhausted
    project must stop every account that shares it — a per-account breaker would
    let the second account keep burning a budget the first one already emptied.
    Per-platform would be too coarse in the other direction: an org that brings
    its own credentials has its own project and must not be blocked by someone
    else's exhaustion. ``credential_key`` is a hash of the resolved client_id,
    never the client_id itself, so the same project maps to the same row without
    storing a secret.

    ``quota_scope`` separates budgets the same platform meters independently —
    YouTube's Data API and Analytics API have separate quotas, and blocking the
    cheap batched Analytics call because the Data API ran dry would throw away
    the part of the sync that was never the problem. Empty for platforms with a
    single pool.

    Deliberately not ``apps.publisher.models.RateLimitState``: that table is
    read by the publish engine as a hard gate on *publishing*, so writing a
    read-side analytics block into it would silently stop the account posting.
    """

    platform = models.CharField(max_length=30)
    credential_key = models.CharField(max_length=64)
    quota_scope = models.CharField(max_length=20, blank=True, default="")
    blocked_until = models.DateTimeField()
    reason = models.TextField(blank=True, default="")
    tripped_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_provider_quota_block"
        unique_together = [("platform", "credential_key", "quota_scope")]

    def __str__(self) -> str:
        scope = f"/{self.quota_scope}" if self.quota_scope else ""
        return f"{self.platform}{scope} blocked until {self.blocked_until:%Y-%m-%d %H:%M}"
