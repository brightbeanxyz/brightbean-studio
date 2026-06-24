from datetime import UTC, datetime
from unittest.mock import MagicMock, call

from providers.exceptions import APIError
from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider


def _resp(data):
    return MagicMock(json=MagicMock(return_value=data))


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
        "https://graph.facebook.com/v25.0/me/accounts",
        access_token="user-token",
        params={
            "fields": (
                "id,name,access_token,category,picture,"
                "instagram_business_account{id,username,name,profile_picture_url,followers_count,media_count}"
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
            _resp({"data": [{"name": "reach", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "views", "period": "day", "total_value": {"value": 67}}]}),
            _resp({"data": [{"name": "accounts_engaged", "values": [{"value": 8}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 9}]}]}),
            _resp({"followers_count": 34}),
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
    assert metrics.extra["views"] == 67
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "reach",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "views",
                    "period": "day",
                    "metric_type": "total_value",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "accounts_engaged",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "total_interactions",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1",
                access_token="page-token",
                params={"fields": "id,username,name,profile_picture_url,followers_count,media_count"},
            ),
        ]
    )


def test_instagram_media_metrics_use_current_metrics_and_field_fallbacks():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "ig-media-1", "like_count": 12, "comments_count": 3}),
            _resp({"data": [{"name": "reach", "values": [{"value": 250}]}]}),
            _resp({"data": [{"name": "views", "values": [{"value": 400}]}]}),
            _resp({"data": [{"name": "likes", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "comments", "values": [{"value": 3}]}]}),
            _resp({"data": [{"name": "saved", "values": [{"value": 5}]}]}),
            _resp({"data": [{"name": "shares", "values": [{"value": 2}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 22}]}]}),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "ig-media-1")

    assert metrics.video_views == 400
    assert metrics.reach == 250
    assert metrics.likes == 12
    assert metrics.comments == 3
    assert metrics.saves == 5
    assert metrics.shares == 2
    assert metrics.extra["total_interactions"] == 22


def test_instagram_login_account_metrics_use_current_insights_metrics():
    provider = InstagramLoginProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"name": "reach", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "views", "period": "day", "total_value": {"value": 67}}]}),
            _resp({"data": [{"name": "accounts_engaged", "values": [{"value": 8}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 9}]}]}),
            _resp({"followers_count": 34}),
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
    assert metrics.extra["views"] == 67
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "reach",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "views",
                    "period": "day",
                    "metric_type": "total_value",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "accounts_engaged",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "total_interactions",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me",
                access_token="ig-token",
                params={"fields": "user_id,username,name,profile_picture_url,followers_count,media_count"},
            ),
        ]
    )


def test_account_metrics_followers_none_when_profile_fetch_fails():
    """A transient profile-fetch failure must yield followers=None (not 0) so the
    analytics layer can skip it instead of writing a poisoning 0 snapshot for a
    real account."""
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"name": "reach", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "views", "period": "day", "total_value": {"value": 67}}]}),
            _resp({"data": [{"name": "accounts_engaged", "values": [{"value": 8}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 9}]}]}),
            APIError("(#190) Error validating access token", platform="Instagram"),
        ]
    )

    metrics = provider.get_account_metrics(
        "page-token",
        (datetime(2026, 6, 18, tzinfo=UTC), datetime(2026, 6, 19, tzinfo=UTC)),
    )

    assert metrics.followers is None
    assert metrics.reach == 12
