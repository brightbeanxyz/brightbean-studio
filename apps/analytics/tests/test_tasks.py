"""Tests for analytics background tasks."""

from unittest.mock import patch

import pytest

from apps.analytics.tasks import sync_all_account_analytics
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test WS", organization=organization)


def _youtube_account(workspace, *, platform_id, needs_reconnect):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="youtube",
        account_platform_id=platform_id,
        account_name=f"YT {platform_id}",
        oauth_access_token="token",
        oauth_refresh_token="refresh",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        analytics_needs_reconnect=needs_reconnect,
    )


@pytest.mark.django_db
class TestSyncAllAccountAnalytics:
    @patch("apps.analytics.tasks._sync_account_metrics")
    def test_skips_accounts_flagged_for_reconnect(self, mock_sync_account_metrics, workspace):
        """An account already flagged ``analytics_needs_reconnect`` must not
        trigger another Analytics-API account-metrics attempt (the call that
        re-fails and re-logs every hour), while an unflagged account still does.
        """
        # A seed migration may already have a youtube row; ensure it's enabled.
        AnalyticsPlatformConfig.objects.update_or_create(platform="youtube", defaults={"is_enabled": True})
        healthy = _youtube_account(workspace, platform_id="healthy", needs_reconnect=False)
        flagged = _youtube_account(workspace, platform_id="flagged", needs_reconnect=True)

        sync_all_account_analytics.now()

        synced_ids = {call.args[0].id for call in mock_sync_account_metrics.call_args_list}
        assert healthy.id in synced_ids
        assert flagged.id not in synced_ids


def test_account_metrics_to_dict_instagram_emits_followers_not_profile_visits():
    """A1+A3: Instagram no longer emits the deprecated ``profile_visits``; follower
    growth is carried by the ``followers`` total (derived to a daily delta downstream
    by ``follower_growth_metric``)."""
    from apps.analytics.tasks import _account_metrics_to_dict
    from providers.types import AccountMetrics

    metrics = AccountMetrics(followers=1234, reach=50, extra={"views": 70})
    out = _account_metrics_to_dict(metrics, "instagram")

    assert out["followers"] == 1234.0
    assert out["reach"] == 50.0
    assert out["views"] == 70.0
    assert "profile_visits" not in out
    assert "follows" not in out


def test_account_metrics_to_dict_skips_followers_when_none():
    """A failed IG profile fetch yields followers=None; the mapper must skip it so
    no spurious 0-followers snapshot poisons the growth series."""
    from apps.analytics.tasks import _account_metrics_to_dict
    from providers.types import AccountMetrics

    metrics = AccountMetrics(followers=None, reach=50, extra={"views": 70})
    out = _account_metrics_to_dict(metrics, "instagram")

    assert "followers" not in out
    assert out["reach"] == 50.0
    assert out["views"] == 70.0


@pytest.mark.django_db
def test_sync_account_metrics_does_not_backfill_followers_total(workspace):
    """The cumulative followers total must be written for the current day only, not
    backfilled into past dates (which would fabricate flat follower history)."""
    from datetime import date
    from unittest.mock import MagicMock, patch

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import _sync_account_metrics
    from providers.types import AccountMetrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-1",
        account_name="IG One",
        oauth_access_token="token",
        oauth_refresh_token="refresh",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    fake_provider = MagicMock()
    fake_provider.account_metrics_supports_date_range = True
    fake_provider.get_account_metrics.return_value = AccountMetrics(followers=1000, reach=5, extra={"views": 7})
    today = date(2026, 6, 24)

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_account_metrics(account, today)

    # Current day persists the followers total...
    assert AccountInsightsSnapshot.objects.filter(social_account=account, date=today, metric_key="followers").exists()
    # ...but backfilled past days must NOT (the total isn't a historical value).
    assert not AccountInsightsSnapshot.objects.filter(
        social_account=account, date__lt=today, metric_key="followers"
    ).exists()
    # Date-ranged metrics ARE still backfilled.
    assert AccountInsightsSnapshot.objects.filter(social_account=account, date__lt=today, metric_key="reach").exists()


@pytest.mark.django_db
def test_sync_account_metrics_recovers_followers_from_later_offset(workspace):
    """If on_date's own fetch returns followers=None but a later offset fetches the
    current total, it must still be written to on_date (not dropped)."""
    from datetime import date
    from unittest.mock import MagicMock, patch

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import _sync_account_metrics
    from providers.types import AccountMetrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-1",
        account_name="IG One",
        oauth_access_token="token",
        oauth_refresh_token="refresh",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    fake_provider = MagicMock()
    fake_provider.account_metrics_supports_date_range = True
    # offset 0 (on_date): profile fetch failed -> followers=None; later offsets recover it.
    fake_provider.get_account_metrics.side_effect = [
        AccountMetrics(followers=None, reach=5, extra={"views": 7}),
        AccountMetrics(followers=1000, reach=4, extra={"views": 6}),
        AccountMetrics(followers=1000, reach=3, extra={"views": 5}),
    ]
    today = date(2026, 6, 24)

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_account_metrics(account, today)

    # on_date recovered the current follower total from the later offset...
    row = AccountInsightsSnapshot.objects.get(social_account=account, date=today, metric_key="followers")
    assert row.value == 1000.0
    # ...and no past date got a followers row.
    assert not AccountInsightsSnapshot.objects.filter(
        social_account=account, date__lt=today, metric_key="followers"
    ).exists()


@pytest.mark.django_db
def test_sync_account_metrics_refreshes_empty_follower_count_when_today_rows_exist(workspace):
    """Existing daily account snapshots must not strand the header follower total
    at 0. This commonly affects Facebook accounts connected before
    ``followers_count`` was persisted during page selection.
    """
    from datetime import date
    from unittest.mock import MagicMock, patch

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import _sync_account_metrics
    from providers.types import AccountMetrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="FB One",
        follower_count=0,
        oauth_access_token="token",
        oauth_refresh_token="refresh",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    today = date(2026, 6, 24)
    AccountInsightsSnapshot.objects.create(
        social_account=account,
        date=today,
        metric_key="views",
        value=10,
    )
    fake_provider = MagicMock()
    fake_provider.account_metrics_supports_date_range = True
    fake_provider.get_account_metrics.return_value = AccountMetrics(followers=1234, followers_gained=2)

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_account_metrics(account, today)

    account.refresh_from_db()
    assert account.follower_count == 1234


@pytest.mark.django_db
def test_sync_account_metrics_refetches_today_when_forced(workspace):
    """A one-shot backfill must call the provider even when today's rows exist.

    The fetch is the only thing that surfaces an insufficient-scope error and
    sets ``analytics_needs_reconnect``. Without ``force_today``, re-enabling a
    platform on the same day it last synced finds every day already
    COMPLETE (every metric key instagram_login's account-level sync can
    produce is present), skips every offset, never calls the provider, and
    reports success for a token that cannot read insights.
    """
    from datetime import date, timedelta
    from unittest.mock import MagicMock, patch

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import _sync_account_metrics
    from providers.types import AccountMetrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram_login",
        account_platform_id="ig-direct-1",
        account_name="Direct IG",
        follower_count=500,  # non-zero, so the follower-refresh override can't be what re-fetches
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    today = date(2026, 6, 24)
    # Every metric key instagram_login's account-level writer can produce —
    # a genuinely complete day, not just "some row exists".
    for offset in range(3):  # every day _sync_account_metrics would walk
        for metric_key in ("reach", "views", "likes", "comments", "shares"):
            AccountInsightsSnapshot.objects.create(
                social_account=account,
                date=today - timedelta(days=offset),
                metric_key=metric_key,
                value=10,
            )
    fake_provider = MagicMock()
    fake_provider.account_metrics_supports_date_range = True
    fake_provider.get_account_metrics.return_value = AccountMetrics(reach=42, followers=500)

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_account_metrics(account, today)
        assert fake_provider.get_account_metrics.call_count == 0

        _sync_account_metrics(account, today, force_today=True)
        assert fake_provider.get_account_metrics.call_count == 1


@pytest.mark.django_db
def test_sync_account_metrics_gap_fills_a_missing_metric_without_overwriting_existing_rows(workspace):
    """A day that already has SOME of a platform's metric keys but not all
    (Instagram writing ``views``/``followers`` while ``reach`` failed to
    write) must be treated as partial, not complete — the missing key gets
    backfilled, but a key that's already there keeps its first-captured
    value untouched (the first capture of a day stays authoritative).
    """
    from datetime import date, timedelta
    from unittest.mock import MagicMock, patch

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import _sync_account_metrics
    from providers.types import AccountMetrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-2",
        account_name="IG Two",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    today = date(2026, 6, 24)
    yesterday = today - timedelta(days=1)
    # Yesterday captured "views" but "reach" never made it in — a partial day.
    AccountInsightsSnapshot.objects.create(
        social_account=account,
        date=yesterday,
        metric_key="views",
        value=999,
    )
    fake_provider = MagicMock()
    fake_provider.account_metrics_supports_date_range = True
    fake_provider.get_account_metrics.return_value = AccountMetrics(
        reach=5, extra={"views": 7, "likes": 2, "comments": 1, "shares": 1}
    )

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_account_metrics(account, today)

    # The missing key was backfilled...
    assert AccountInsightsSnapshot.objects.get(social_account=account, date=yesterday, metric_key="reach").value == 5
    assert AccountInsightsSnapshot.objects.get(social_account=account, date=yesterday, metric_key="comments").value == 1
    # ...but the pre-existing "views" row was NOT overwritten by the fresh
    # fetch's value of 7 — the first capture of a day stays authoritative.
    assert AccountInsightsSnapshot.objects.get(social_account=account, date=yesterday, metric_key="views").value == 999


@pytest.mark.django_db
def test_sync_account_metrics_complete_day_is_not_refetched(workspace):
    """A day with every expected metric key present costs no API call, even
    without ``force_today``."""
    from datetime import date, timedelta
    from unittest.mock import MagicMock, patch

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import _sync_account_metrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-3",
        account_name="IG Three",
        follower_count=500,
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    today = date(2026, 6, 24)
    for offset in range(3):  # every day _sync_account_metrics would walk
        for metric_key in ("reach", "views", "likes", "comments", "shares"):
            AccountInsightsSnapshot.objects.create(
                social_account=account,
                date=today - timedelta(days=offset),
                metric_key=metric_key,
                value=10,
            )
    fake_provider = MagicMock()
    fake_provider.account_metrics_supports_date_range = True

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_account_metrics(account, today)

    assert fake_provider.get_account_metrics.call_count == 0


@pytest.mark.django_db
def test_sync_all_account_analytics_still_syncs_when_today_has_some_rows(workspace):
    """Before Fix 4, the caller skipped ``_sync_account_metrics`` entirely
    once ANY row existed for today, so a day that was merely partial (some
    metric keys captured, others not) never got a chance to gap-fill —
    that's the IG "reach" gap. The caller must now defer that decision to
    ``_sync_account_metrics`` itself, which knows per-metric completeness.
    """
    from unittest.mock import patch

    from django.utils import timezone

    from apps.analytics.models import AccountInsightsSnapshot
    from apps.analytics.tasks import sync_all_account_analytics

    AnalyticsPlatformConfig.objects.update_or_create(platform="instagram", defaults={"is_enabled": True})
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-4",
        account_name="IG Four",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    today = timezone.now().date()
    AccountInsightsSnapshot.objects.create(
        social_account=account,
        date=today,
        metric_key="views",
        value=10,
    )

    with patch("apps.analytics.tasks._sync_account_metrics") as mock_sync:
        sync_all_account_analytics.now()

    synced_ids = {call.args[0].id for call in mock_sync.call_args_list}
    assert account.id in synced_ids


@pytest.mark.django_db
def test_backfill_forces_todays_refetch(workspace):
    """``backfill_account_analytics`` is the one-shot path, so it forces."""
    from unittest.mock import patch

    from apps.analytics.tasks import backfill_account_analytics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram_login",
        account_platform_id="ig-direct-2",
        account_name="Direct IG",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    AnalyticsPlatformConfig.objects.update_or_create(platform="instagram_login", defaults={"is_enabled": True})

    with patch("apps.analytics.tasks._sync_account_metrics") as sync:
        backfill_account_analytics.now(str(account.id))

    assert sync.call_args.kwargs["force_today"] is True


@pytest.mark.django_db
def test_resolve_provider_carries_instagram_login_credentials(workspace):
    """``_resolve_provider`` was a hand-copy of the publish engine's resolver and
    had drifted: no ``instagram_login`` branch, so Instagram Direct providers
    were built with neither ``ig_user_id`` nor ``account_handle``.
    """
    from apps.analytics.tasks import _resolve_provider

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram_login",
        account_platform_id="ig-direct-1",
        account_name="Direct IG",
        account_handle="direct.ig",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )

    provider = _resolve_provider(account)

    assert provider.credentials["ig_user_id"] == "ig-direct-1"
    assert provider.credentials["account_handle"] == "direct.ig"


def test_no_analytics_platforms_all_have_a_zero_backfill_window():
    """``NO_ANALYTICS_PLATFORMS``'s docstring mandates the pairing: without a
    0-day window the cron still tries to fetch metrics the platform can't give.
    """
    from apps.analytics.constants import NO_ANALYTICS_PLATFORMS
    from apps.analytics.tasks import BACKFILL_DAYS_PER_PLATFORM

    assert {p: BACKFILL_DAYS_PER_PLATFORM.get(p) for p in NO_ANALYTICS_PLATFORMS} == dict.fromkeys(
        NO_ANALYTICS_PLATFORMS, 0
    )
