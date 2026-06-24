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
