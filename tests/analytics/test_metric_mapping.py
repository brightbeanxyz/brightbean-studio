"""Tests for provider metrics -> analytics snapshot key mapping."""

from apps.analytics.services import _canonical_metric_key, _metric_query_keys
from apps.analytics.tasks import _account_metrics_to_dict, _post_metrics_to_dict
from providers.types import AccountMetrics, PostMetrics


def test_facebook_reactions_are_written_under_catalog_key():
    metrics = PostMetrics(likes=9, clicks=3)

    assert _post_metrics_to_dict(metrics, "facebook") == {
        "reactions": 9.0,
        "clicks": 3.0,
    }


def test_instagram_post_views_and_profile_visits_use_page_catalog_keys():
    metrics = PostMetrics(
        impressions=40,
        reach=30,
        likes=7,
        comments=2,
        shares=1,
        saves=3,
        extra={"profile_visits": 5},
    )

    assert _post_metrics_to_dict(metrics, "instagram") == {
        "views": 40.0,
        "reach": 30.0,
        "likes": 7.0,
        "comments": 2.0,
        "shares": 1.0,
        "saves": 3.0,
        "profile_visits": 5.0,
    }


def test_instagram_account_views_and_profile_visits_use_page_catalog_keys():
    metrics = AccountMetrics(
        impressions=100,
        reach=80,
        followers_gained=6,
        profile_views=12,
    )

    assert _account_metrics_to_dict(metrics, "instagram") == {
        "views": 100.0,
        "reach": 80.0,
        "profile_visits": 12.0,
        "follows": 6.0,
    }


def test_instagram_direct_account_can_store_total_followers():
    metrics = AccountMetrics(
        impressions=100,
        reach=80,
        followers=250,
        profile_views=12,
    )

    assert _account_metrics_to_dict(metrics, "instagram_login") == {
        "views": 100.0,
        "reach": 80.0,
        "profile_visits": 12.0,
        "followers": 250.0,
    }


def test_legacy_snapshot_aliases_keep_existing_rows_visible():
    assert "likes" in _metric_query_keys("facebook", ["reactions"])
    assert _canonical_metric_key("facebook", "likes") == "reactions"
    assert "impressions" in _metric_query_keys("instagram", ["views"])
    assert _canonical_metric_key("instagram", "impressions") == "views"
