from datetime import UTC, datetime
from unittest.mock import MagicMock, call

from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider


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
                            {"name": "views", "period": "day", "total_value": {"value": 67}},
                            {"name": "profile_views", "period": "day", "total_value": {"value": 5}},
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


def test_instagram_post_metrics_use_valid_metric_names():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {"name": "impressions", "values": [{"value": 1000}]},
                        {"name": "reach", "values": [{"value": 800}]},
                        {"name": "saved", "values": [{"value": 25}]},
                        {"name": "likes", "values": [{"value": 120}]},
                        {"name": "comments", "values": [{"value": 10}]},
                        {"name": "shares", "values": [{"value": 5}]},
                    ]
                }
            )
        )
    )

    metrics = provider.get_post_metrics("page-token", "post-1")

    assert metrics.impressions == 1000
    assert metrics.reach == 800
    assert metrics.saves == 25
    assert metrics.likes == 120
    assert metrics.comments == 10
    assert metrics.shares == 5
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/post-1/insights",
        access_token="page-token",
        params={"metric": "impressions,reach,saved,likes,comments,shares"},
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
                            {"name": "views", "period": "day", "total_value": {"value": 67}},
                            {"name": "profile_views", "period": "day", "total_value": {"value": 5}},
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
