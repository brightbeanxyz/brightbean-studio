from datetime import UTC, datetime
from unittest.mock import MagicMock, call

from providers.facebook import FacebookProvider
from providers.types import PostType, PublishContent


def test_publish_single_photo_returns_photo_id():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(json=MagicMock(return_value={"id": "photo-1", "post_id": "page-1_post-1"}))
    )

    result = provider.publish_post(
        "page-token",
        PublishContent(
            text="Caption for the photo",
            media_urls=["https://cdn.example.com/one.jpg"],
            post_type=PostType.IMAGE,
            extra={"page_id": "page-1"},
        ),
    )

    assert result.platform_post_id == "photo-1"
    assert result.url == "https://www.facebook.com/page-1_post-1"


def test_post_metrics_use_valid_graph_api_v21_metrics():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {"name": "post_impressions", "values": [{"value": 5000}]},
                        {"name": "post_impressions_unique", "values": [{"value": 3200}]},
                        {"name": "post_clicks", "values": [{"value": 80}]},
                        {"name": "post_reactions_like_total", "values": [{"value": 42}]},
                    ]
                }
            )
        )
    )

    metrics = provider.get_post_metrics("page-token", "post-1")

    assert metrics.impressions == 5000
    assert metrics.reach == 3200
    assert metrics.clicks == 80
    assert metrics.likes == 42
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/post-1/insights",
        access_token="page-token",
        params={"metric": "post_impressions,post_impressions_unique,post_clicks,post_reactions_like_total"},
    )


def test_account_metrics_use_valid_graph_api_v21_metrics_with_period():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {"name": "page_impressions", "values": [{"value": 12000}]},
                        {"name": "page_impressions_unique", "values": [{"value": 8500}]},
                        {"name": "page_fan_adds", "values": [{"value": 37}]},
                    ]
                }
            )
        )
    )

    metrics = provider.get_account_metrics(
        "page-token",
        (
            datetime(2026, 6, 18, tzinfo=UTC),
            datetime(2026, 6, 19, tzinfo=UTC),
        ),
    )

    assert metrics.impressions == 12000
    assert metrics.reach == 8500
    assert metrics.followers_gained == 37
    assert metrics.followers == 0
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/page-1/insights",
        access_token="page-token",
        params={
            "metric": "page_impressions,page_impressions_unique,page_fan_adds",
            "period": "day",
            "since": 1781740800,
            "until": 1781827200,
        },
    )
