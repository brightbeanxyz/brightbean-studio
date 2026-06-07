"""Tests for Meta analytics metric compatibility handling."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from providers.exceptions import APIError
from providers.facebook import FacebookProvider
from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider


def _response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


def _invalid_metric_error(platform: str = "Meta") -> APIError:
    return APIError(
        f"{platform} API error 400",
        status_code=400,
        platform=platform,
        raw_response={
            "error": {
                "message": "(#100) The value must be a valid insights metric",
                "type": "OAuthException",
                "code": 100,
            }
        },
    )


class TestFacebookAnalyticsMetrics:
    @patch.object(FacebookProvider, "_request")
    def test_skips_invalid_metrics_and_returns_valid_values(self, mock_request):
        mock_request.side_effect = [
            _invalid_metric_error("Facebook"),
            _response({"data": [{"name": "post_impressions_unique", "values": [{"value": 12}]}]}),
            _response({"data": [{"name": "post_engaged_users", "values": [{"value": 4}]}]}),
            _invalid_metric_error("Facebook"),
            _response(
                {
                    "data": [
                        {
                            "name": "post_reactions_by_type_total",
                            "values": [{"value": {"like": 2, "love": 3, "wow": 1}}],
                        }
                    ]
                }
            ),
            _response({"comments": {"summary": {"total_count": 8}}, "shares": {"count": 5}}),
        ]

        metrics = FacebookProvider().get_post_metrics("token", "post-id")

        assert metrics.reach == 12
        assert metrics.engagements == 4
        assert metrics.likes == 6
        assert metrics.comments == 8
        assert metrics.shares == 5
        assert mock_request.call_count == 6


class TestInstagramAnalyticsMetrics:
    @patch.object(InstagramProvider, "_request")
    def test_uses_current_media_metric_names(self, mock_request):
        mock_request.side_effect = [
            _response({"data": [{"name": "views", "values": [{"value": 20}]}]}),
            _response({"data": [{"name": "reach", "values": [{"value": 15}]}]}),
            _response({"data": [{"name": "saved", "values": [{"value": 3}]}]}),
            _response({"data": [{"name": "likes", "values": [{"value": 7}]}]}),
            _response({"data": [{"name": "comments", "values": [{"value": 2}]}]}),
            _response({"data": [{"name": "shares", "values": [{"value": 1}]}]}),
            _response({"data": [{"name": "total_interactions", "values": [{"value": 13}]}]}),
        ]

        metrics = InstagramProvider().get_post_metrics("token", "ig-media-id")

        assert metrics.impressions == 20
        assert metrics.reach == 15
        assert metrics.saves == 3
        assert metrics.likes == 7
        assert metrics.comments == 2
        assert metrics.shares == 1
        assert metrics.extra["total_interactions"] == 13
        requested = [kwargs["params"]["metric"] for _args, kwargs in mock_request.call_args_list]
        assert "engagement" not in requested
        assert "impressions" not in requested
        assert "views" in requested

    @patch.object(InstagramProvider, "_request")
    def test_account_views_use_total_value_metric_type(self, mock_request):
        mock_request.side_effect = [
            _response({"data": [{"name": "views", "values": [{"value": 50}]}]}),
            _response({"data": [{"name": "reach", "values": [{"value": 40}]}]}),
            _response({"data": [{"name": "profile_views", "values": [{"value": 6}]}]}),
            _response({"data": [{"name": "follows", "values": [{"value": 2}]}]}),
        ]

        metrics = InstagramProvider({"ig_user_id": "ig-user"}).get_account_metrics(
            "token",
            (datetime(2026, 6, 7, tzinfo=timezone.utc), datetime(2026, 6, 8, tzinfo=timezone.utc)),
        )

        assert metrics.impressions == 50
        first_params = mock_request.call_args_list[0].kwargs["params"]
        assert first_params["metric"] == "views"
        assert first_params["metric_type"] == "total_value"


class TestInstagramDirectAnalyticsMetrics:
    @patch.object(InstagramLoginProvider, "_request")
    def test_uses_current_media_metric_names(self, mock_request):
        mock_request.side_effect = [
            _response({"data": [{"name": "views", "values": [{"value": 20}]}]}),
            _response({"data": [{"name": "reach", "values": [{"value": 15}]}]}),
            _response({"data": [{"name": "saved", "values": [{"value": 3}]}]}),
            _response({"data": [{"name": "likes", "values": [{"value": 7}]}]}),
            _response({"data": [{"name": "comments", "values": [{"value": 2}]}]}),
            _response({"data": [{"name": "shares", "values": [{"value": 1}]}]}),
            _response({"data": [{"name": "profile_visits", "values": [{"value": 5}]}]}),
            _response({"data": [{"name": "total_interactions", "values": [{"value": 13}]}]}),
        ]

        metrics = InstagramLoginProvider().get_post_metrics("token", "ig-media-id")

        assert metrics.impressions == 20
        assert metrics.reach == 15
        assert metrics.saves == 3
        assert metrics.likes == 7
        assert metrics.comments == 2
        assert metrics.shares == 1
        assert metrics.extra["profile_visits"] == 5
        assert metrics.extra["total_interactions"] == 13
        requested = [kwargs["params"]["metric"] for _args, kwargs in mock_request.call_args_list]
        assert "engagement" not in requested
        assert "impressions" not in requested
        assert "views" in requested

    @patch.object(InstagramLoginProvider, "_request")
    def test_account_views_use_total_value_metric_type(self, mock_request):
        mock_request.side_effect = [
            _response({"data": [{"name": "views", "values": [{"value": 50}]}]}),
            _response({"data": [{"name": "reach", "values": [{"value": 40}]}]}),
            _response({"data": [{"name": "profile_views", "values": [{"value": 6}]}]}),
            _response({"data": [{"name": "follows", "values": [{"value": 2}]}]}),
            _response({"data": [{"name": "follower_count", "values": [{"value": 200}]}]}),
        ]

        metrics = InstagramLoginProvider().get_account_metrics(
            "token",
            (datetime(2026, 6, 7, tzinfo=timezone.utc), datetime(2026, 6, 8, tzinfo=timezone.utc)),
        )

        assert metrics.impressions == 50
        first_params = mock_request.call_args_list[0].kwargs["params"]
        assert first_params["metric"] == "views"
        assert first_params["metric_type"] == "total_value"
