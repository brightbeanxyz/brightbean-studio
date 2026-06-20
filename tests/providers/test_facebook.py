from datetime import UTC, datetime
from unittest.mock import MagicMock

from providers.facebook import FacebookProvider


def test_facebook_post_metrics_use_current_insights_metrics():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {"name": "post_impressions", "values": [{"value": 100}]},
                        {"name": "post_clicks", "values": [{"value": 7}]},
                        {
                            "name": "post_reactions_by_type_total",
                            "values": [{"value": {"like": 4, "love": 2}}],
                        },
                    ]
                }
            )
        )
    )

    metrics = provider.get_post_metrics("page-token", "post-1")

    assert metrics.impressions == 100
    assert metrics.clicks == 7
    assert metrics.likes == 6
    assert metrics.engagements == 13
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/post-1/insights",
        access_token="page-token",
        params={
            "metric": "post_impressions,post_clicks,post_reactions_by_type_total",
            "period": "lifetime",
        },
    )


def test_facebook_account_metrics_use_current_page_insights_metrics():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {"name": "page_impressions", "values": [{"value": 100}]},
                        {"name": "page_impressions_unique", "values": [{"value": 80}]},
                        {"name": "page_post_engagements", "values": [{"value": 15}]},
                        {"name": "page_fans", "values": [{"value": 42}]},
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

    assert metrics.impressions == 100
    assert metrics.reach == 80
    assert metrics.followers == 42
    assert metrics.extra["engagement"] == 15
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/page-1/insights",
        access_token="page-token",
        params={
            "metric": "page_impressions,page_impressions_unique,page_post_engagements,page_fans",
            "period": "day",
            "since": 1781740800,
            "until": 1781827200,
        },
    )
