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
