from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.analytics.models import PostSnapshot, RefreshLog
from apps.analytics.services import refresh_metrics
from providers.exceptions import APIError, RateLimitError
from providers.types import PostMetrics


@pytest.mark.django_db
class TestRefreshMetrics:
    def test_success_creates_snapshots_and_log(self, workspace, social_account):
        mock_metrics = [
            PostMetrics(
                likes=100, comments=20, shares=10, saves=30,
                engagements=160, impressions=2000,
                extra={
                    "platform_post_id": "post_1",
                    "post_url": "https://instagram.com/p/post_1",
                    "post_text": "Test post",
                    "posted_at": "2026-04-10T12:00:00+00:00",
                    "post_type": "image",
                },
            ),
            PostMetrics(
                likes=50, comments=5, shares=2, saves=10,
                engagements=67, impressions=1000,
                extra={
                    "platform_post_id": "post_2",
                    "post_url": "https://instagram.com/p/post_2",
                    "post_text": "Another post",
                    "posted_at": "2026-04-08T15:30:00+00:00",
                    "post_type": "video",
                },
            ),
        ]

        mock_provider = MagicMock()
        mock_provider.get_recent_post_metrics.return_value = mock_metrics

        with patch("apps.analytics.services.get_provider", return_value=mock_provider):
            results = refresh_metrics(workspace)

        assert PostSnapshot.objects.filter(workspace=workspace).count() == 2
        assert RefreshLog.objects.filter(workspace=workspace, status="success").count() == 1

        snapshot = PostSnapshot.objects.get(platform_post_id="post_1")
        assert snapshot.likes == 100
        assert snapshot.social_account == social_account

    def test_upsert_updates_existing_snapshot(self, workspace, social_account):
        mock_metrics = [
            PostMetrics(
                likes=100, comments=20, shares=10, saves=30,
                engagements=160, impressions=2000,
                extra={
                    "platform_post_id": "post_1",
                    "post_url": "https://instagram.com/p/post_1",
                    "post_text": "Test post",
                    "posted_at": "2026-04-10T12:00:00+00:00",
                    "post_type": "image",
                },
            ),
        ]

        mock_provider = MagicMock()
        mock_provider.get_recent_post_metrics.return_value = mock_metrics

        with patch("apps.analytics.services.get_provider", return_value=mock_provider):
            refresh_metrics(workspace)

        # Update likes
        mock_metrics_updated = [
            PostMetrics(
                likes=200, comments=20, shares=10, saves=30,
                engagements=260, impressions=3000,
                extra={
                    "platform_post_id": "post_1",
                    "post_url": "https://instagram.com/p/post_1",
                    "post_text": "Test post",
                    "posted_at": "2026-04-10T12:00:00+00:00",
                    "post_type": "image",
                },
            ),
        ]
        mock_provider.get_recent_post_metrics.return_value = mock_metrics_updated

        with patch("apps.analytics.services.get_provider", return_value=mock_provider):
            refresh_metrics(workspace)

        assert PostSnapshot.objects.filter(platform_post_id="post_1").count() == 1
        assert PostSnapshot.objects.get(platform_post_id="post_1").likes == 200

    def test_partial_failure_logs_error(self, workspace):
        """If one account fails, others still succeed."""
        from apps.social_accounts.models import SocialAccount

        SocialAccount.objects.create(
            workspace=workspace, platform="instagram",
            account_platform_id="ig_ok", account_name="OK Account",
        )
        SocialAccount.objects.create(
            workspace=workspace, platform="tiktok",
            account_platform_id="tt_fail", account_name="Fail Account",
        )

        def mock_get_provider(platform, credentials=None):
            provider = MagicMock()
            if platform == "tiktok":
                provider.get_recent_post_metrics.side_effect = APIError(
                    "TikTok API error 500", status_code=500, platform="tiktok",
                )
            else:
                provider.get_recent_post_metrics.return_value = [
                    PostMetrics(
                        likes=10, engagements=10, impressions=100,
                        extra={
                            "platform_post_id": "p1",
                            "post_url": "https://example.com",
                            "post_text": "ok",
                            "posted_at": "2026-04-10T12:00:00Z",
                            "post_type": "image",
                        },
                    ),
                ]
            return provider

        with patch("apps.analytics.services.get_provider", side_effect=mock_get_provider):
            results = refresh_metrics(workspace)

        assert RefreshLog.objects.filter(status="success").count() == 1
        assert RefreshLog.objects.filter(status="error").count() == 1
        assert PostSnapshot.objects.count() == 1

    def test_rate_limit_logged(self, workspace, social_account):
        mock_provider = MagicMock()
        mock_provider.get_recent_post_metrics.side_effect = RateLimitError(
            "Rate limited", retry_after=300, platform="instagram",
        )

        with patch("apps.analytics.services.get_provider", return_value=mock_provider):
            refresh_metrics(workspace)

        log = RefreshLog.objects.get(social_account=social_account)
        assert log.status == "rate_limited"

    def test_unsupported_platform_skipped(self, workspace):
        from apps.social_accounts.models import SocialAccount

        SocialAccount.objects.create(
            workspace=workspace, platform="mastodon",
            account_platform_id="m_1", account_name="Mastodon Account",
        )

        mock_provider = MagicMock()
        mock_provider.get_recent_post_metrics.side_effect = NotImplementedError

        with patch("apps.analytics.services.get_provider", return_value=mock_provider):
            results = refresh_metrics(workspace)

        # No crash, no error log — just skipped
        assert RefreshLog.objects.count() == 0
        assert PostSnapshot.objects.count() == 0
