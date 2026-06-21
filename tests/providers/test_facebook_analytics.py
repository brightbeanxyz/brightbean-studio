from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call

from apps.analytics.tasks import _resolve_provider
from providers.exceptions import APIError
from providers.facebook import FacebookProvider


def test_account_metrics_use_current_page_insights_metrics():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {"name": "page_post_engagements", "values": [{"value": 34}]},
                        {"name": "page_daily_follows", "values": [{"value": 5}]},
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

    assert metrics.reach == 0
    assert metrics.followers_gained == 5
    assert metrics.extra["raw_insights"]["page_post_engagements"] == 34
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/page-1/insights",
        access_token="page-token",
        params={
            "metric": "page_post_engagements,page_daily_follows",
            "since": 1781740800,
            "until": 1781827200,
        },
    )


def test_post_metrics_use_supported_facebook_insights_and_basic_counts():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(
                json=MagicMock(
                    return_value={
                        "data": [
                            {"name": "post_clicks", "values": [{"value": 4}]},
                            {"name": "post_reactions_by_type_total", "values": [{"value": {"like": 5, "love": 2}}]},
                            {"name": "post_video_views", "values": [{"value": 11}]},
                        ]
                    }
                )
            ),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "id": "post-1",
                        "likes": {"summary": {"total_count": 10}},
                        "comments": {"summary": {"total_count": 3}},
                    }
                )
            ),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "id": "post-1",
                        "shares": {"count": 2},
                    }
                )
            ),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "post-1")

    assert metrics.clicks == 4
    assert metrics.likes == 7
    assert metrics.comments == 3
    assert metrics.shares == 2
    assert metrics.video_views == 11
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.facebook.com/v21.0/post-1/insights",
                access_token="page-token",
                params={"metric": "post_clicks,post_reactions_by_type_total,post_video_views"},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v21.0/post-1",
                access_token="page-token",
                params={"fields": "id,likes.summary(true),comments.summary(true)"},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v21.0/post-1",
                access_token="page-token",
                params={"fields": "id,shares"},
            ),
        ]
    )


def test_facebook_post_metrics_persist_reactions_key():
    from apps.analytics.tasks import _post_metrics_to_dict
    from providers.types import PostMetrics

    metrics = PostMetrics(likes=7, comments=3, shares=2, clicks=4)

    out = _post_metrics_to_dict(metrics, "facebook")

    assert out["reactions"] == 7.0
    assert "likes" not in out
    assert out["comments"] == 3.0
    assert out["shares"] == 2.0
    assert out["clicks"] == 4.0


def test_facebook_catalog_uses_supported_metrics():
    from apps.analytics.metrics import PLATFORM_METRICS, PLATFORM_PRIMARY

    assert PLATFORM_PRIMARY["facebook"] == "views"
    assert "reach" not in PLATFORM_METRICS["facebook"]
    assert "impressions" not in PLATFORM_METRICS["facebook"]
    assert {"views", "reactions", "comments", "shares", "clicks", "follows"} <= set(PLATFORM_METRICS["facebook"])


def test_post_metrics_falls_back_for_objects_without_insights_edge():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            APIError('Facebook API error 400: {"error":{"message":"(#100) Tried accessing nonexisting field (insights)"}}'),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "id": "reel-1",
                        "likes": {"summary": {"total_count": 7}},
                        "comments": {"summary": {"total_count": 3}},
                    }
                )
            ),
            APIError('Facebook API error 400: {"error":{"message":"(#100) Tried accessing nonexisting field (shares)"}}'),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "reel-1")

    assert metrics.likes == 7
    assert metrics.comments == 3
    assert metrics.shares == 0
    assert metrics.extra["raw_fallback"]["id"] == "reel-1"
    assert provider._request.call_args_list[1].kwargs["params"] == {
        "fields": "id,likes.summary(true),comments.summary(true)"
    }


def test_facebook_analytics_provider_uses_connected_page_id(monkeypatch):
    captured = {}

    def fake_resolve(platform, organization_id):
        captured["resolved"] = (platform, organization_id)
        return {"client_id": "id", "client_secret": "secret"}

    def fake_get_provider(platform, credentials):
        captured["provider"] = (platform, credentials)
        return object()

    monkeypatch.setattr("apps.credentials.models.resolve_platform_credentials", fake_resolve)
    monkeypatch.setattr("providers.get_provider", fake_get_provider)
    account = SimpleNamespace(
        platform="facebook",
        account_platform_id="page-123",
        workspace=SimpleNamespace(organization_id="org-1"),
    )

    _resolve_provider(account)

    assert captured["resolved"] == ("facebook", "org-1")
    assert captured["provider"] == (
        "facebook",
        {"client_id": "id", "client_secret": "secret", "page_id": "page-123"},
    )
