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


def _published_platform_post(account, *, platform_post_id="post-1"):
    """A fresh PUBLISHED PlatformPost, due for its first metrics sync."""
    from django.utils import timezone

    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=account.workspace, caption="hello")
    return PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.PUBLISHED,
        published_at=timezone.now(),
        platform_post_id=platform_post_id,
    )


def _deleted_object_error():
    """Meta's "the remote object no longer exists" error (code 100 / subcode
    33) — its own message text says "missing permissions", which is exactly
    what makes it look like a scope problem if you only read the text.
    """
    from providers.exceptions import APIError

    return APIError(
        "Threads API error 400: (#100) Object does not exist, cannot be loaded due to missing permissions",
        status_code=400,
        platform="Threads",
        raw_response={
            "error": {
                "message": "Object does not exist, cannot be loaded due to missing permissions",
                "type": "OAuthException",
                "code": 100,
                "error_subcode": 33,
            }
        },
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
    platform on the same day it last synced finds today's rows present, skips
    every offset, never calls the provider, and reports success for a token
    that cannot read insights.
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
    for offset in range(3):  # every day _sync_account_metrics would walk
        AccountInsightsSnapshot.objects.create(
            social_account=account,
            date=today - timedelta(days=offset),
            metric_key="reach",
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


class TestIsInsufficientScope:
    def test_deleted_remote_object_is_not_a_scope_error(self):
        """The subcode-33 "object does not exist" error must NOT classify as
        insufficient scope even though its own message contains "missing
        permissions" — that's exactly the false positive that tripped
        ``analytics_needs_reconnect`` on a Threads account in production.
        """
        from apps.analytics.tasks import _is_insufficient_scope

        assert _is_insufficient_scope(_deleted_object_error()) is False

    def test_genuine_scope_error_is_still_recognized(self):
        from apps.analytics.tasks import _is_insufficient_scope

        assert _is_insufficient_scope(Exception("insufficient permission (#10)")) is True


@pytest.mark.django_db
def test_sync_post_metrics_marks_deleted_post_gone_without_flagging_reconnect(workspace):
    """A post whose remote object is gone (code 100 / subcode 33) must be
    marked so future syncs skip it, and must NOT set
    ``analytics_needs_reconnect`` — the token is fine, the post just isn't
    there anymore.
    """
    from datetime import date
    from unittest.mock import MagicMock, patch

    from apps.analytics.tasks import _sync_post_metrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="threads",
        account_platform_id="th-1",
        account_name="Threads One",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    post = _published_platform_post(account)
    fake_provider = MagicMock()
    fake_provider.get_post_metrics.side_effect = _deleted_object_error()

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_post_metrics(post, date(2026, 6, 24))

    post.refresh_from_db()
    account.refresh_from_db()
    assert post.metrics_gone_at is not None
    assert account.analytics_needs_reconnect is False


@pytest.mark.django_db
def test_sync_post_metrics_deleted_object_is_idempotent(workspace):
    """A second sync attempt on an already-marked post must not error or
    bump the timestamp again — it's just skipped upstream by the queryset
    filter, but the marking helper itself should also be a safe no-op.
    """
    from datetime import date
    from unittest.mock import MagicMock, patch

    from apps.analytics.tasks import _sync_post_metrics

    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="threads",
        account_platform_id="th-1b",
        account_name="Threads One B",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    post = _published_platform_post(account)
    fake_provider = MagicMock()
    fake_provider.get_post_metrics.side_effect = _deleted_object_error()

    with patch("apps.analytics.tasks._resolve_provider", return_value=fake_provider):
        _sync_post_metrics(post, date(2026, 6, 24))
        post.refresh_from_db()
        first_marked_at = post.metrics_gone_at

        _sync_post_metrics(post, date(2026, 6, 25))
        post.refresh_from_db()

    assert post.metrics_gone_at == first_marked_at


@pytest.mark.django_db
def test_sync_all_account_analytics_skips_posts_marked_metrics_gone(workspace):
    from unittest.mock import patch

    from django.utils import timezone

    from apps.analytics.tasks import sync_all_account_analytics

    AnalyticsPlatformConfig.objects.update_or_create(platform="threads", defaults={"is_enabled": True})
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="threads",
        account_platform_id="th-2",
        account_name="Threads Two",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    gone_post = _published_platform_post(account, platform_post_id="gone-1")
    gone_post.metrics_gone_at = timezone.now()
    gone_post.save(update_fields=["metrics_gone_at"])
    live_post = _published_platform_post(account, platform_post_id="live-1")

    with (
        patch("apps.analytics.tasks._sync_account_metrics"),
        patch("apps.analytics.tasks._sync_post_metrics") as mock_sync_post,
    ):
        sync_all_account_analytics.now()

    synced_post_ids = {call.args[0].id for call in mock_sync_post.call_args_list}
    assert live_post.id in synced_post_ids
    assert gone_post.id not in synced_post_ids


@pytest.mark.django_db
def test_backfill_skips_posts_marked_metrics_gone(workspace):
    from unittest.mock import patch

    from django.utils import timezone

    from apps.analytics.tasks import backfill_account_analytics

    AnalyticsPlatformConfig.objects.update_or_create(platform="threads", defaults={"is_enabled": True})
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="threads",
        account_platform_id="th-3",
        account_name="Threads Three",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    gone_post = _published_platform_post(account, platform_post_id="gone-2")
    gone_post.metrics_gone_at = timezone.now()
    gone_post.save(update_fields=["metrics_gone_at"])
    live_post = _published_platform_post(account, platform_post_id="live-2")

    with (
        patch("apps.analytics.tasks._sync_account_metrics"),
        patch("apps.analytics.tasks._sync_post_metrics") as mock_sync_post,
    ):
        backfill_account_analytics.now(str(account.id))

    synced_post_ids = {call.args[0].id for call in mock_sync_post.call_args_list}
    assert live_post.id in synced_post_ids
    assert gone_post.id not in synced_post_ids


def test_no_analytics_platforms_all_have_a_zero_backfill_window():
    """``NO_ANALYTICS_PLATFORMS``'s docstring mandates the pairing: without a
    0-day window the cron still tries to fetch metrics the platform can't give.
    """
    from apps.analytics.constants import NO_ANALYTICS_PLATFORMS
    from apps.analytics.tasks import BACKFILL_DAYS_PER_PLATFORM

    assert {p: BACKFILL_DAYS_PER_PLATFORM.get(p) for p in NO_ANALYTICS_PLATFORMS} == dict.fromkeys(
        NO_ANALYTICS_PLATFORMS, 0
    )
