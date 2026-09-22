"""Tests for analytics background tasks."""

import logging
from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.analytics.tasks import sync_all_account_analytics
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount
from providers.exceptions import APIError, OAuthError, QuotaExceededError, TokenExpiredError


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


def test_no_analytics_platforms_all_have_a_zero_backfill_window():
    """``NO_ANALYTICS_PLATFORMS``'s docstring mandates the pairing: without a
    0-day window the cron still tries to fetch metrics the platform can't give.
    """
    from apps.analytics.constants import NO_ANALYTICS_PLATFORMS
    from apps.analytics.tasks import BACKFILL_DAYS_PER_PLATFORM

    assert {p: BACKFILL_DAYS_PER_PLATFORM.get(p) for p in NO_ANALYTICS_PLATFORMS} == dict.fromkeys(
        NO_ANALYTICS_PLATFORMS, 0
    )


# ---------------------------------------------------------------------------
# The incident: a failed fetch used to make a post permanently "due".
# ---------------------------------------------------------------------------


def _published_post(account, *, age=timedelta(days=2), platform_post_id="vid-1"):
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=account.workspace, caption="c")
    return PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.PUBLISHED,
        platform_post_id=platform_post_id,
        published_at=timezone.now() - age,
    )


def _provider(*, batch_size=1):
    provider = MagicMock()
    provider.post_metrics_batch_size = batch_size
    provider.credentials = {"client_id": "client-abc"}
    return provider


@pytest.mark.django_db
class TestFailureBackoff:
    """Regression cover for the YouTube quota storm.

    A failed fetch writes no ``PostInsightsSnapshot``. Cadence used to be read
    from the newest snapshot, so a post that kept failing looked never-synced
    and came back due on *every* hourly tick, ignoring the decay ladder. Across
    a whole channel that turned one bad token into ~10,000 wasted API calls a
    day — enough to empty YouTube's daily budget, after which every call failed
    for a second reason and the loop sustained itself.
    """

    def test_failed_fetch_stamps_the_attempt_and_counts_the_failure(self, workspace):
        from apps.analytics.models import PostInsightsSnapshot
        from apps.analytics.tasks import _sync_post_metrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account)
        provider = _provider()
        provider.get_post_metrics.side_effect = APIError("boom", status_code=404)

        _sync_post_metrics(post, timezone.now().date(), provider=provider, access_token="tok")

        post.refresh_from_db()
        assert not PostInsightsSnapshot.objects.filter(platform_post=post).exists()
        assert post.analytics_attempted_at is not None
        assert post.analytics_failure_count == 1

    def test_failed_post_is_not_due_again_within_the_backoff(self, workspace):
        """The direct regression test: one failure must buy an hour of quiet."""
        from apps.analytics.tasks import _post_cadence_due

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account, age=timedelta(hours=2))  # tightest rung: hourly
        now = timezone.now()
        post.analytics_attempted_at = now
        post.analytics_failure_count = 1

        assert not _post_cadence_due(post, now + timedelta(minutes=30), platform="youtube")
        assert _post_cadence_due(post, now + timedelta(minutes=90), platform="youtube")

    def test_repeated_failures_widen_the_gap(self, workspace):
        from apps.analytics.tasks import _post_cadence_due

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account, age=timedelta(hours=2))
        now = timezone.now()
        post.analytics_attempted_at = now
        post.analytics_failure_count = 5  # 16h

        assert not _post_cadence_due(post, now + timedelta(hours=8), platform="youtube")
        assert _post_cadence_due(post, now + timedelta(hours=17), platform="youtube")

    @pytest.mark.parametrize(
        ("failures", "expected"),
        [
            (0, timedelta(0)),
            (1, timedelta(hours=1)),
            (2, timedelta(hours=2)),
            (4, timedelta(hours=8)),
            (9, timedelta(days=7)),
            (40, timedelta(days=7)),  # must not overflow into an absurd wait
        ],
    )
    def test_backoff_ladder_grows_and_caps(self, failures, expected):
        from apps.analytics.tasks import _analytics_failure_backoff

        assert _analytics_failure_backoff(failures) == expected

    def test_success_clears_the_failure_streak(self, workspace):
        from apps.analytics.tasks import _sync_post_metrics
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account)
        post.analytics_failure_count = 4
        post.save(update_fields=["analytics_failure_count"])
        provider = _provider()
        provider.get_post_metrics.return_value = PostMetrics(video_views=9, likes=1)

        _sync_post_metrics(post, timezone.now().date(), provider=provider, access_token="tok")

        post.refresh_from_db()
        assert post.analytics_failure_count == 0
        assert post.analytics_attempted_at is not None

    def test_post_with_no_attempt_stamp_falls_back_to_the_snapshot_signal(self, workspace):
        """Rows written before the field existed keep the old behaviour exactly.

        This fallback is what lets the change ship with no data migration, so it
        has to stay byte-identical to the previous rule.
        """
        from apps.analytics.models import PostInsightsSnapshot
        from apps.analytics.tasks import _post_cadence_due

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account, age=timedelta(hours=2))
        assert post.analytics_attempted_at is None

        # No snapshot at all → due, as before.
        assert _post_cadence_due(post, platform="youtube")

        # A fresh snapshot → not due, as before.
        PostInsightsSnapshot.objects.create(platform_post=post, metric_key="video_views", date=timezone.now().date())
        assert not _post_cadence_due(post, platform="youtube")

    def test_analytics_only_metrics_still_do_not_reset_the_legacy_cadence(self, workspace):
        """``_POST_NON_CADENCE_METRICS_BY_PLATFORM`` still applies on the null path."""
        from apps.analytics.models import PostInsightsSnapshot
        from apps.analytics.tasks import _post_cadence_due

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account, age=timedelta(hours=2))
        PostInsightsSnapshot.objects.create(platform_post=post, metric_key="watch_time", date=timezone.now().date())

        assert _post_cadence_due(post, platform="youtube")


@pytest.mark.django_db
class TestBatching:
    """One ``videos.list`` call covers 50 ids for the same single quota unit."""

    def test_batched_platform_makes_one_call_per_fifty_posts(self, workspace):
        from apps.analytics.tasks import _sync_account_posts
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        posts = [_published_post(account, platform_post_id=f"v{i}") for i in range(120)]
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = lambda _tok, ids: {i: PostMetrics(video_views=1) for i in ids}

        synced, failed, api_calls = _sync_account_posts(account, provider, "tok", posts, timezone.now().date())

        assert api_calls == 3
        assert (synced, failed) == (120, 0)
        assert provider.get_post_metrics.call_count == 0

    def test_ids_missing_from_the_response_count_as_failures_not_zeros(self, workspace):
        from apps.analytics.models import PostInsightsSnapshot
        from apps.analytics.tasks import _sync_account_posts
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        kept = _published_post(account, platform_post_id="kept")
        gone = _published_post(account, platform_post_id="gone")
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.return_value = {"kept": PostMetrics(video_views=5)}

        synced, failed, _ = _sync_account_posts(account, provider, "tok", [kept, gone], timezone.now().date())

        assert (synced, failed) == (1, 1)
        gone.refresh_from_db()
        assert gone.analytics_failure_count == 1
        # Crucially, no fabricated zero row for the deleted video.
        assert not PostInsightsSnapshot.objects.filter(platform_post=gone).exists()

    def test_a_generic_batch_error_marks_only_that_chunk_and_continues(self, workspace):
        """A permission/5xx/429 response must not abort the account or cron."""
        from apps.analytics.tasks import _sync_account_posts
        from apps.composer.models import PlatformPost
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        posts = [_published_post(account, platform_post_id=f"v{i}") for i in range(100)]
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = [
            APIError("temporary failure", status_code=503),
            {post.platform_post_id: PostMetrics(video_views=1) for post in posts[50:]},
        ]

        synced, failed, api_calls = _sync_account_posts(account, provider, "tok", posts, timezone.now().date())

        assert (synced, failed, api_calls) == (50, 50, 2)
        assert provider.get_post_metrics_batch.call_count == 2
        assert all(
            post.analytics_failure_count == 1 for post in PlatformPost.objects.filter(pk__in=[p.pk for p in posts[:50]])
        )
        assert all(
            post.analytics_failure_count == 0 for post in PlatformPost.objects.filter(pk__in=[p.pk for p in posts[50:]])
        )

    def test_non_batching_platform_isolates_per_post_failures(self, workspace):
        from apps.analytics.tasks import _sync_account_posts
        from providers.types import PostMetrics

        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="IG",
            oauth_access_token="token",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        good = _published_post(account, platform_post_id="good")
        bad = _published_post(account, platform_post_id="bad")
        provider = _provider(batch_size=1)

        def _metrics(_tok, pid):
            if pid == "bad":
                raise APIError("nope", status_code=400)
            return PostMetrics(video_views=3)

        provider.get_post_metrics.side_effect = _metrics

        synced, failed, _ = _sync_account_posts(account, provider, "tok", [good, bad], timezone.now().date())

        assert (synced, failed) == (1, 1)
        good.refresh_from_db()
        bad.refresh_from_db()
        assert good.analytics_failure_count == 0
        assert bad.analytics_failure_count == 1

    def test_meta_posts_with_uuid_platform_ids_are_skipped_without_a_call(self, workspace):
        from apps.analytics.tasks import _sync_account_posts

        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="fb-1",
            account_name="FB",
            oauth_access_token="token",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        post = _published_post(account, platform_post_id=str(uuid4()))
        provider = _provider(batch_size=1)

        assert _sync_account_posts(account, provider, "tok", [post], timezone.now().date()) == (0, 0, 0)
        assert provider.get_post_metrics.call_count == 0


@pytest.mark.django_db
class TestQuotaBreaker:
    """Once the platform says "budget spent", every further call is waste."""

    def test_quota_error_trips_the_breaker_and_aborts_the_account(self, workspace):
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import _sync_one_account

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        for i in range(10):
            _published_post(account, platform_post_id=f"v{i}")
        resets_at = timezone.now() + timedelta(hours=6)
        provider = _provider(batch_size=1)
        provider.get_post_metrics.side_effect = QuotaExceededError(
            "spent", resets_at=resets_at, quota_scope="data", status_code=403
        )

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        # Exactly one call, not ten: the first refusal ends the account's pass.
        assert provider.get_post_metrics.call_count == 1
        block = ProviderQuotaBlock.objects.get(platform="youtube", quota_scope="data")
        assert block.blocked_until == resets_at

    def test_quota_block_does_not_touch_per_post_sync_state(self, workspace):
        """The rule a later refactor will break.

        None of these posts were really attempted; counting the account-wide
        refusal against them would exile good posts for a week.
        """
        from apps.analytics.tasks import _sync_one_account

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        posts = [_published_post(account, platform_post_id=f"v{i}") for i in range(3)]
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = QuotaExceededError("spent", quota_scope="data")

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        for post in posts:
            post.refresh_from_db()
            assert post.analytics_failure_count == 0
            assert post.analytics_attempted_at is None

    def test_account_metrics_quota_error_trips_the_analytics_breaker(self, workspace):
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import _sync_one_account

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        provider = _provider(batch_size=1)
        provider.account_metrics_supports_date_range = True
        provider.get_account_metrics.side_effect = QuotaExceededError("spent", quota_scope="analytics")

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        assert ProviderQuotaBlock.objects.filter(platform="youtube", quota_scope="analytics").exists()

    def test_an_analytics_quota_block_does_not_stop_data_api_posts(self, workspace):
        """The two YouTube APIs have independent quota pools.

        An Analytics-API exhaustion must skip only the account/per-video
        Analytics work; the Data API still has useful post counts to collect.
        """
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import _sync_one_account
        from apps.common.quota import credential_key

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        _published_post(account)
        provider = _provider(batch_size=50)
        provider.account_metrics_supports_date_range = True
        provider.get_account_metrics.side_effect = QuotaExceededError("spent", quota_scope="analytics")
        provider.get_post_metrics_batch.return_value = {}

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        assert provider.get_post_metrics_batch.call_count == 1
        assert ProviderQuotaBlock.objects.filter(
            platform="youtube",
            credential_key=credential_key(provider.credentials),
            quota_scope="analytics",
        ).exists()

    def test_a_blocked_credential_skips_the_account_without_calling_the_provider(self, workspace):
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import _sync_one_account
        from apps.common.quota import credential_key

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        _published_post(account)
        provider = _provider(batch_size=50)
        ProviderQuotaBlock.objects.create(
            platform="youtube",
            credential_key=credential_key(provider.credentials),
            quota_scope="data",
            blocked_until=timezone.now() + timedelta(hours=3),
        )

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        assert provider.get_post_metrics_batch.call_count == 0

    def test_an_expired_block_lets_the_sync_resume(self, workspace):
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import _sync_one_account
        from apps.common.quota import credential_key
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        _published_post(account, platform_post_id="v0")
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.return_value = {"v0": PostMetrics(video_views=1)}
        ProviderQuotaBlock.objects.create(
            platform="youtube",
            credential_key=credential_key(provider.credentials),
            quota_scope="data",
            blocked_until=timezone.now() - timedelta(minutes=1),
        )

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        assert provider.get_post_metrics_batch.call_count == 1

    def test_a_data_quota_block_does_not_stop_the_analytics_api_fetch(self, workspace):
        """YouTube meters the two APIs separately; conflating them throws away
        the cheap batched call because the expensive one ran dry."""
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import _sync_one_account
        from apps.common.quota import credential_key

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        provider = _provider(batch_size=50)
        ProviderQuotaBlock.objects.create(
            platform="youtube",
            credential_key=credential_key(provider.credentials),
            quota_scope="data",
            blocked_until=timezone.now() + timedelta(hours=3),
        )

        with (
            patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")),
            patch("apps.analytics.tasks._sync_account_metrics") as account_metrics,
        ):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        assert account_metrics.call_count == 1
        assert provider.get_post_metrics_batch.call_count == 0

    def test_quota_exhaustion_does_not_flag_the_account_for_reconnect(self, workspace):
        """An empty budget is not a broken connection.

        Before classification, a quota 403 reached ``error_messages`` as a plain
        403 and told every YouTube user to reconnect a healthy account — which
        minted a fresh token and resumed the storm.
        """
        from apps.analytics.tasks import _sync_one_account

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        _published_post(account)
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = QuotaExceededError("spent", quota_scope="data")

        with (
            patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")),
            patch("apps.analytics.tasks._sync_account_metrics"),
        ):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        account.refresh_from_db()
        assert account.analytics_needs_reconnect is False

    def test_accounts_sharing_credentials_share_one_block(self, workspace):
        from apps.common.quota import credential_key

        assert credential_key({"client_id": "same"}) == credential_key({"client_id": "same"})
        assert credential_key({"client_id": "a"}) != credential_key({"client_id": "b"})
        # Never the client_id itself.
        assert "same" not in credential_key({"client_id": "same"})

    def test_a_longer_block_is_not_shortened_by_a_later_throttle(self):
        from apps.analytics.models import ProviderQuotaBlock
        from apps.common.quota import trip_quota_block

        day = timezone.now() + timedelta(hours=8)
        trip_quota_block("youtube", "key", "data", until=day, reason="daily")
        trip_quota_block("youtube", "key", "data", until=timezone.now() + timedelta(minutes=5), reason="throttle")

        assert ProviderQuotaBlock.objects.get(platform="youtube", quota_scope="data").blocked_until == day

    def test_token_rejection_flags_reconnect_without_counting_posts(self, workspace):
        from apps.analytics.tasks import _sync_one_account

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        post = _published_post(account)
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = TokenExpiredError("nope", status_code=401)

        with (
            patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")),
            patch("apps.analytics.tasks._sync_account_metrics"),
            patch("apps.analytics.tasks._enqueue_health_check") as health,
        ):
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        account.refresh_from_db()
        post.refresh_from_db()
        assert account.analytics_needs_reconnect is True
        assert health.call_count == 1
        assert post.analytics_failure_count == 0


@pytest.mark.django_db
class TestTokenRefresh:
    """The trigger: the sync used to pass a token it never refreshed.

    A Google access token lives an hour and the only refresher runs every six,
    so roughly five of every six hourly runs called the API with a dead token.
    """

    def _account(self, workspace, *, expires_in):
        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        account.token_expires_at = timezone.now() + expires_in
        account.save(update_fields=["token_expires_at"])
        return account

    def test_refreshes_an_expiring_token_once_per_account(self, workspace):
        from apps.analytics.tasks import _analytics_provider_and_token

        account = self._account(workspace, expires_in=timedelta(minutes=2))
        provider = _provider()

        with (
            patch("apps.analytics.tasks._resolve_provider", return_value=provider),
            patch.object(SocialAccount, "refresh_oauth_token", return_value="fresh-token") as refresh,
        ):
            _, token = _analytics_provider_and_token(account)

        assert token == "fresh-token"
        assert refresh.call_count == 1

    def test_analytics_refresh_does_not_enqueue_a_duplicate_backfill(self, workspace):
        from apps.analytics.tasks import _analytics_provider_and_token

        account = self._account(workspace, expires_in=timedelta(minutes=2))
        provider = _provider()
        provider.refresh_token.return_value = MagicMock(
            access_token="fresh-token",
            refresh_token="refresh",
            expires_in=3600,
        )

        with (
            patch("apps.analytics.tasks._resolve_provider", return_value=provider),
            patch("apps.analytics.tasks.backfill_account_analytics") as backfill,
        ):
            _, token = _analytics_provider_and_token(account)

        assert token == "fresh-token"
        backfill.assert_not_called()

    def test_skips_the_refresh_when_the_token_has_headroom(self, workspace):
        """Fails if anyone reinstates the 7-day ``is_token_expiring_soon``.

        That window is permanently true for a 1-hour Google token, so using it
        here would buy a refresh call per account per hour for nothing.
        """
        from apps.analytics.tasks import _analytics_provider_and_token

        account = self._account(workspace, expires_in=timedelta(minutes=50))
        provider = _provider()

        with (
            patch("apps.analytics.tasks._resolve_provider", return_value=provider),
            patch.object(SocialAccount, "refresh_oauth_token") as refresh,
        ):
            _, token = _analytics_provider_and_token(account)

        assert refresh.call_count == 0
        assert token == account.oauth_access_token

    def test_a_dead_grant_flags_reconnect_and_hands_off_to_the_health_check(self, workspace):
        from apps.analytics.tasks import _analytics_provider_and_token

        account = self._account(workspace, expires_in=timedelta(minutes=2))
        provider = _provider()

        with (
            patch("apps.analytics.tasks._resolve_provider", return_value=provider),
            patch.object(SocialAccount, "refresh_oauth_token", side_effect=OAuthError("revoked")),
            patch("apps.analytics.tasks._enqueue_health_check") as health,
        ):
            _analytics_provider_and_token(account)

        account.refresh_from_db()
        assert account.analytics_needs_reconnect is True
        assert health.call_count == 1
        # connection_status belongs to the health check, not to us.
        assert account.connection_status == SocialAccount.ConnectionStatus.CONNECTED

    def test_a_transient_refresh_failure_keeps_the_old_token_and_says_nothing(self, workspace):
        """A 5xx on the token endpoint is not a revoked grant."""
        from apps.analytics.tasks import _analytics_provider_and_token

        account = self._account(workspace, expires_in=timedelta(minutes=2))
        provider = _provider()

        with (
            patch("apps.analytics.tasks._resolve_provider", return_value=provider),
            patch.object(SocialAccount, "refresh_oauth_token", side_effect=APIError("gateway", status_code=503)),
            patch("apps.analytics.tasks._enqueue_health_check") as health,
        ):
            _, token = _analytics_provider_and_token(account)

        account.refresh_from_db()
        assert token == account.oauth_access_token
        assert account.analytics_needs_reconnect is False
        assert health.call_count == 0

    def test_token_expires_within_treats_an_unknown_expiry_as_not_expiring(self, workspace):
        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=False)
        assert account.token_expires_at is None
        assert account.token_expires_within(timedelta(days=3650)) is False


@pytest.mark.django_db
class TestYouTubeOptionalAnalyticsRetry:
    def test_repeated_500_enqueues_only_one_retry_for_account_and_date(self, workspace):
        from background_task.models import Task

        from apps.analytics.tasks import _sync_youtube_post_analytics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        _published_post(account)
        today = timezone.now().date()
        provider = _provider()
        provider.get_post_analytics.side_effect = APIError("backend error", status_code=500)

        _sync_youtube_post_analytics(account, provider, "tok", today)
        _sync_youtube_post_analytics(account, provider, "tok", today)

        assert Task.objects.filter(task_name="apps.analytics.tasks.retry_youtube_post_analytics").count() == 1

    def test_500_schedules_narrow_retry_without_changing_data_api_snapshot(self, workspace):
        from apps.analytics.models import PostInsightsSnapshot
        from apps.analytics.tasks import _sync_youtube_post_analytics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        post = _published_post(account)
        today = timezone.now().date()
        PostInsightsSnapshot.objects.create(platform_post=post, metric_key="views", date=today, value=12)
        provider = _provider()
        provider.get_post_analytics.side_effect = APIError("backend error", status_code=500)

        with patch("apps.analytics.tasks.retry_youtube_post_analytics") as retry:
            _sync_youtube_post_analytics(account, provider, "tok", today)

        retry.assert_called_once_with(str(account.id), today.isoformat(), 1, schedule=3600, remove_existing_tasks=True)
        assert PostInsightsSnapshot.objects.get(platform_post=post, metric_key="views", date=today).value == 12
        assert not PostInsightsSnapshot.objects.filter(platform_post=post, metric_key="watch_time", date=today).exists()

    def test_retries_after_three_more_hours_then_stops(self, workspace):
        from apps.analytics.tasks import _sync_youtube_post_analytics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        _published_post(account)
        today = timezone.now().date()
        provider = _provider()
        provider.get_post_analytics.side_effect = APIError("backend error", status_code=503)

        with patch("apps.analytics.tasks.retry_youtube_post_analytics") as retry:
            _sync_youtube_post_analytics(account, provider, "tok", today, retry_attempt=1)
            retry.assert_called_once_with(
                str(account.id), today.isoformat(), 2, schedule=10800, remove_existing_tasks=True
            )
            retry.reset_mock()
            _sync_youtube_post_analytics(account, provider, "tok", today, retry_attempt=2)
            retry.assert_not_called()

    def test_retry_task_recovers_only_optional_snapshot(self, workspace):
        from apps.analytics.models import PostInsightsSnapshot
        from apps.analytics.tasks import retry_youtube_post_analytics
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        post = _published_post(account)
        today = timezone.now().date()
        provider = _provider()
        provider.get_post_analytics.return_value = {
            post.platform_post_id: PostMetrics(shares=3, extra={"watch_time": 42, "avg_view_pct": 50})
        }

        with (
            patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")),
            patch("apps.analytics.tasks._sync_account_posts") as data_api_sync,
        ):
            retry_youtube_post_analytics.now(str(account.id), today.isoformat(), 1)

        assert PostInsightsSnapshot.objects.get(platform_post=post, metric_key="watch_time", date=today).value == 42
        assert PostInsightsSnapshot.objects.get(platform_post=post, metric_key="shares", date=today).value == 3
        data_api_sync.assert_not_called()

    @pytest.mark.parametrize("attempt", [1, 2])
    def test_retry_respects_analytics_quota_block(self, workspace, attempt):
        from background_task.models import Task

        from apps.analytics.tasks import retry_youtube_post_analytics
        from apps.common.quota import credential_key, trip_quota_block

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        _published_post(account)
        provider = _provider()
        on_date = timezone.now().date().isoformat()
        blocked_until = timezone.now() + timedelta(hours=4)
        trip_quota_block(
            "youtube",
            credential_key(provider.credentials),
            "analytics",
            until=blocked_until,
        )

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            retry_youtube_post_analytics.now(str(account.id), on_date, attempt)
            retry_youtube_post_analytics.now(str(account.id), on_date, attempt)

        provider.get_post_analytics.assert_not_called()
        tasks = Task.objects.filter(task_name="apps.analytics.tasks.retry_youtube_post_analytics")
        assert tasks.count() == 1
        task = tasks.get()
        assert task.params() == ([str(account.id), on_date, attempt], {})
        assert task.run_at == blocked_until + timedelta(seconds=1)

    def test_quota_and_auth_do_not_schedule_generic_500_retry(self, workspace):
        from apps.analytics.tasks import _sync_youtube_post_analytics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        _published_post(account)
        provider = _provider()
        today = timezone.now().date()

        with patch("apps.analytics.tasks.retry_youtube_post_analytics") as retry:
            for exc in (QuotaExceededError("quota"), TokenExpiredError("auth", status_code=401)):
                provider.get_post_analytics.side_effect = exc
                with pytest.raises(type(exc)):
                    _sync_youtube_post_analytics(account, provider, "tok", today)
            retry.assert_not_called()

    def test_retry_task_trips_quota_block_instead_of_retrying_as_500(self, workspace):
        from apps.analytics.models import ProviderQuotaBlock
        from apps.analytics.tasks import retry_youtube_post_analytics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        _published_post(account)
        provider = _provider()
        provider.get_post_analytics.side_effect = QuotaExceededError(
            "quota", status_code=403, quota_scope="analytics", resets_at=timezone.now() + timedelta(hours=4)
        )

        with (
            patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")),
            patch("apps.analytics.tasks.retry_youtube_post_analytics") as retry,
        ):
            retry_youtube_post_analytics.now(str(account.id), timezone.now().date().isoformat(), 1)

        retry.assert_not_called()
        assert ProviderQuotaBlock.objects.filter(platform="youtube", quota_scope="analytics").exists()

    def test_retry_task_hands_off_token_rejection_without_generic_retry(self, workspace):
        from apps.analytics.tasks import retry_youtube_post_analytics

        account = _youtube_account(workspace, platform_id="yt-retry", needs_reconnect=False)
        _published_post(account)
        provider = _provider()
        provider.get_post_analytics.side_effect = TokenExpiredError("auth", status_code=401)

        with (
            patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")),
            patch("apps.analytics.tasks._enqueue_health_check") as health,
            patch("apps.analytics.tasks.retry_youtube_post_analytics") as retry,
        ):
            retry_youtube_post_analytics.now(str(account.id), timezone.now().date().isoformat(), 1)

        retry.assert_not_called()
        health.assert_called_once()
        account.refresh_from_db()
        assert account.analytics_needs_reconnect is True


@pytest.mark.django_db
class TestSyncAllAccountAnalyticsEfficiency:
    def test_resolves_the_provider_once_per_account_not_once_per_post(self, workspace):
        """Each resolution is a credential query plus a token decrypt."""
        from apps.analytics.tasks import _sync_one_account
        from providers.types import PostMetrics

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        for i in range(50):
            _published_post(account, platform_post_id=f"v{i}")
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = lambda _tok, ids: {i: PostMetrics(video_views=1) for i in ids}

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")) as resolve:
            _sync_one_account(account, timezone.now().date(), timezone.now(), cache={})

        assert resolve.call_count == 1

    def test_posts_attempted_within_the_hour_are_excluded_in_sql(self, workspace):
        """The tightest rung is hourly, so those are provably not due."""
        from apps.analytics.tasks import _due_posts_for

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        fresh = _published_post(account, platform_post_id="fresh")
        stale = _published_post(account, platform_post_id="stale")
        now = timezone.now()
        fresh.analytics_attempted_at = now - timedelta(minutes=10)
        fresh.save(update_fields=["analytics_attempted_at"])
        stale.analytics_attempted_at = now - timedelta(hours=5)
        stale.save(update_fields=["analytics_attempted_at"])

        due = _due_posts_for(account, now)

        assert [p.pk for p in due] == [stale.pk]

    def test_due_posts_are_ordered_longest_neglected_first(self, workspace):
        """What makes a run truncated by ``_RUN_BUDGET`` resumable rather than
        starving the tail of the queue forever."""
        from apps.analytics.tasks import _due_posts_for

        account = _youtube_account(workspace, platform_id="yt-1", needs_reconnect=True)
        now = timezone.now()
        old = _published_post(account, platform_post_id="old")
        older = _published_post(account, platform_post_id="older")
        never = _published_post(account, platform_post_id="never")
        old.analytics_attempted_at = now - timedelta(hours=2)
        old.save(update_fields=["analytics_attempted_at"])
        older.analytics_attempted_at = now - timedelta(hours=9)
        older.save(update_fields=["analytics_attempted_at"])

        assert [p.pk for p in _due_posts_for(account, now)] == [never.pk, older.pk, old.pk]

    def test_failures_log_once_per_account_not_once_per_post(self, workspace, caplog):
        """The storm was illegible for hours because it logged per post."""
        from apps.analytics.tasks import _sync_account_posts

        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="IG",
            oauth_access_token="token",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        posts = [_published_post(account, platform_post_id=f"p{i}") for i in range(10)]
        provider = _provider(batch_size=1)
        provider.get_post_metrics.side_effect = APIError("nope", status_code=400)

        with caplog.at_level(logging.WARNING, logger="apps.analytics.tasks"):
            _sync_account_posts(account, provider, "tok", posts, timezone.now().date())

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "10 of 10" in warnings[0].getMessage()

    def test_individual_attempts_use_their_completion_time(self, workspace):
        """A long account must not stamp every tail post with the loop start."""
        from apps.analytics.tasks import _sync_account_posts

        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="IG",
            oauth_access_token="token",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        posts = [_published_post(account, platform_post_id=f"p{i}") for i in range(2)]
        provider = _provider(batch_size=1)
        provider.get_post_metrics.side_effect = APIError("nope", status_code=400)
        first_attempt = timezone.now()
        second_attempt = first_attempt + timedelta(minutes=2)

        with (
            patch("apps.analytics.tasks.timezone.now", side_effect=[first_attempt, second_attempt]),
            patch("apps.analytics.tasks._record_post_sync_failure") as record_failure,
        ):
            _sync_account_posts(account, provider, "tok", posts, first_attempt.date())

        assert [call.args[1] for call in record_failure.call_args_list] == [first_attempt, second_attempt]


@pytest.mark.django_db
class TestTheQuotaStormEndToEnd:
    """The incident itself, reproduced against the real cron entrypoint.

    Before this change the hourly cron made one Data-API call per published
    post, every hour, for every post whose fetch had failed — because a failure
    writes no snapshot and cadence was read from snapshots. With a real channel
    that is ~10,000 calls a day against a 10,000-unit budget, so the first
    failure guaranteed the next day's exhaustion too, and the loop sustained
    itself indefinitely.
    """

    def _channel(self, workspace, *, posts):
        AnalyticsPlatformConfig.objects.update_or_create(platform="youtube", defaults={"is_enabled": True})
        account = _youtube_account(workspace, platform_id="yt-storm", needs_reconnect=True)
        for i in range(posts):
            _published_post(account, platform_post_id=f"v{i}", age=timedelta(days=3))
        return account

    def test_an_exhausted_quota_costs_one_call_this_tick_and_none_the_next(self, workspace):
        from apps.analytics.models import ProviderQuotaBlock

        self._channel(workspace, posts=60)
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = QuotaExceededError(
            "YouTube daily quota exhausted (data API)",
            resets_at=timezone.now() + timedelta(hours=8),
            quota_scope="data",
            status_code=403,
        )

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            sync_all_account_analytics.now()
            calls_first_tick = provider.get_post_metrics_batch.call_count
            sync_all_account_analytics.now()
            calls_second_tick = provider.get_post_metrics_batch.call_count - calls_first_tick

        # One refusal ends the pass; the persisted block ends the next one before
        # it starts. The old code made 60 calls on each tick, forever.
        assert calls_first_tick == 1
        assert calls_second_tick == 0
        assert ProviderQuotaBlock.objects.filter(platform="youtube", quota_scope="data").exists()

    def test_a_healthy_channel_syncs_60_posts_in_two_calls_and_then_goes_quiet(self, workspace):
        """Cadence has to keep working — the fix must not sync everything forever."""
        from providers.types import PostMetrics

        self._channel(workspace, posts=60)
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = lambda _tok, ids: {i: PostMetrics(video_views=1) for i in ids}

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            sync_all_account_analytics.now()
            first = provider.get_post_metrics_batch.call_count
            # An hour later: 3-day-old posts sit on the 6-hourly rung, so nothing
            # is due yet and the pass must cost nothing at all.
            sync_all_account_analytics.now()
            second = provider.get_post_metrics_batch.call_count - first

        assert first == 2  # 50 + 10, one quota unit each
        assert second == 0

    def test_a_dead_token_does_not_exile_every_post_for_a_week(self, workspace):
        """The trigger and the amplifier, together.

        The account-wide failure must leave per-post state alone, so once the
        token is fixed every post is immediately eligible again rather than
        serving out a backoff it never earned.
        """
        from apps.analytics.tasks import _post_cadence_due

        account = self._channel(workspace, posts=10)
        provider = _provider(batch_size=50)
        provider.get_post_metrics_batch.side_effect = TokenExpiredError("Invalid Credentials", status_code=401)

        with patch("apps.analytics.tasks._analytics_provider_and_token", return_value=(provider, "tok")):
            sync_all_account_analytics.now()

        posts = list(account.platform_posts.all())
        assert all(p.analytics_failure_count == 0 for p in posts)
        assert all(p.analytics_attempted_at is None for p in posts)
        assert all(_post_cadence_due(p, platform="youtube") for p in posts)
