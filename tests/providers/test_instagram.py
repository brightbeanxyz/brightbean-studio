from datetime import UTC, datetime
from unittest.mock import MagicMock, call

from apps.analytics.tasks import _post_metrics_to_dict
from providers.exceptions import APIError
from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider
from providers.types import PostMetrics


def test_get_user_pages_returns_linked_instagram_business_accounts():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Facebook Page",
                            "access_token": "page-token",
                            "category": "Creator",
                            "picture": {"data": {"url": "https://example.com/page.jpg"}},
                            "instagram_business_account": {
                                "id": "17841400000000000",
                                "username": "brightbean",
                                "name": "Brightbean",
                                "profile_picture_url": "https://example.com/ig.jpg",
                                "followers_count": 42,
                            },
                        },
                        {
                            "id": "page-2",
                            "name": "No Instagram Here",
                            "access_token": "unused-token",
                        },
                    ]
                }
            )
        )
    )

    accounts = provider.get_user_pages("user-token")

    assert accounts == [
        {
            "id": "17841400000000000",
            "name": "Brightbean",
            "handle": "brightbean",
            "access_token": "page-token",
            "category": "Creator",
            "picture": "https://example.com/ig.jpg",
            "followers_count": 42,
            "page_id": "page-1",
            "page_name": "Facebook Page",
        }
    ]
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/me/accounts",
        access_token="user-token",
        params={
            "fields": (
                "id,name,access_token,category,picture,"
                "instagram_business_account{id,username,name,profile_picture_url,followers_count}"
            ),
        },
    )


def test_get_user_pages_omits_blank_page_access_token():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})

    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Facebook Page",
                            "access_token": "",
                            "instagram_business_account": {
                                "id": "17841400000000000",
                                "username": "brightbean",
                                "name": "Brightbean",
                            },
                        },
                    ]
                }
            )
        )
    )

    accounts = provider.get_user_pages("user-token")

    assert len(accounts) == 1
    assert "access_token" not in accounts[0]


def test_account_metrics_use_current_instagram_insights_metrics():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(
                json=MagicMock(
                    return_value={
                        "data": [
                            {"name": "reach", "values": [{"value": 12}]},
                            {"name": "follower_count", "values": [{"value": 34}]},
                        ]
                    }
                )
            ),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "data": [
                            {
                                "name": "views",
                                "period": "day",
                                "total_value": {"value": 67},
                            },
                            {
                                "name": "profile_views",
                                "period": "day",
                                "total_value": {"value": 5},
                            },
                        ]
                    }
                )
            ),
        ]
    )

    metrics = provider.get_account_metrics(
        "page-token",
        (
            datetime(2026, 6, 18, tzinfo=UTC),
            datetime(2026, 6, 19, tzinfo=UTC),
        ),
    )

    assert metrics.impressions == 0
    assert metrics.reach == 12
    assert metrics.followers == 34
    assert metrics.profile_views == 5
    assert metrics.extra["views"] == 67
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.facebook.com/v21.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "reach,follower_count",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v21.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "views,profile_views",
                    "period": "day",
                    "metric_type": "total_value",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
        ]
    )


def test_instagram_login_account_metrics_use_current_insights_metrics():
    provider = InstagramLoginProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(
                json=MagicMock(
                    return_value={
                        "data": [
                            {"name": "reach", "values": [{"value": 12}]},
                            {"name": "follower_count", "values": [{"value": 34}]},
                        ]
                    }
                )
            ),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "data": [
                            {
                                "name": "views",
                                "period": "day",
                                "total_value": {"value": 67},
                            },
                            {
                                "name": "profile_views",
                                "period": "day",
                                "total_value": {"value": 5},
                            },
                        ]
                    }
                )
            ),
        ]
    )

    metrics = provider.get_account_metrics(
        "ig-token",
        (
            datetime(2026, 6, 18, tzinfo=UTC),
            datetime(2026, 6, 19, tzinfo=UTC),
        ),
    )

    assert metrics.impressions == 0
    assert metrics.reach == 12
    assert metrics.followers == 34
    assert metrics.profile_views == 5
    assert metrics.extra["views"] == 67
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.instagram.com/v21.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "reach,follower_count",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v21.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "views,profile_views",
                    "period": "day",
                    "metric_type": "total_value",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
        ]
    )


def test_instagram_extra_post_metrics_map_to_dashboard_keys():
    metrics = PostMetrics(
        reach=10,
        video_views=20,
        engagements=7,
        clicks=3,
        extra={
            "follows": 2,
            "profile_visits": 4,
            "profile_activity": 5,
            "watch_time": 1.5,
            "avg_watch_time": 0.25,
            "skip_rate": 12.5,
            "facebook_views": 6,
            "crossposted_views": 8,
        },
    )

    out = _post_metrics_to_dict(metrics, "instagram")

    assert out["reach"] == 10
    assert out["views"] == 20
    assert out["interactions"] == 7
    assert out["clicks"] == 3
    assert out["post_follows"] == 2
    assert out["profile_visits"] == 4
    assert out["profile_activity"] == 5
    assert out["watch_time"] == 1.5
    assert out["avg_watch_time"] == 0.25
    assert out["skip_rate"] == 12.5
    assert out["facebook_views"] == 6
    assert out["crossposted_views"] == 8


def test_instagram_media_metric_skips_product_type_specific_unsupported_metric():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1"})
    provider._request = MagicMock(
        side_effect=APIError(
            "Instagram API error 400: "
            '{"error":{"message":"(#100) The Media Insights API does not support the '
            'ig_reels_video_view_total_time metric for this media product type."}}',
            status_code=400,
        )
    )

    assert provider._get_media_insight_metric("page-token", "media-1", "ig_reels_video_view_total_time") == {}
