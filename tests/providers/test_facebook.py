from unittest.mock import MagicMock, call

import httpx
import pytest

from providers.exceptions import APIError, PublishError, RateLimitError
from providers.facebook import FacebookProvider
from providers.types import PostType, PublishContent

FACEBOOK_POST_FIELDS_PARAM = (
    "id,message,created_time,permalink_url,full_picture,post_id,shares,"
    "comments.limit(0).summary(true),reactions.limit(0).summary(true)"
)
FACEBOOK_POST_INSIGHTS_PARAM = "post_media_view,post_total_media_view_unique,post_clicks,post_reactions_by_type_total"


def _resp(data):
    return MagicMock(json=MagicMock(return_value=data))


def test_publish_multi_photo_post_stages_photos_then_publishes_feed_post():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(json=MagicMock(return_value={"id": "photo-1"})),
            MagicMock(json=MagicMock(return_value={"id": "photo-2"})),
            MagicMock(json=MagicMock(return_value={"id": "page-1_post-1"})),
        ]
    )

    result = provider.publish_post(
        "page-token",
        PublishContent(
            text="Caption for the album",
            media_urls=["https://cdn.example.com/one.jpg", "https://cdn.example.com/two.jpg"],
            post_type=PostType.IMAGE,
            extra={"page_id": "page-1"},
        ),
    )

    assert result.platform_post_id == "post-1"
    assert result.url == "https://www.facebook.com/page-1_post-1"
    assert result.extra["photo_ids"] == ["photo-1", "photo-2"]
    provider._request.assert_has_calls(
        [
            call(
                "POST",
                "https://graph.facebook.com/v25.0/page-1/photos",
                access_token="page-token",
                json={"url": "https://cdn.example.com/one.jpg", "published": False},
            ),
            call(
                "POST",
                "https://graph.facebook.com/v25.0/page-1/photos",
                access_token="page-token",
                json={"url": "https://cdn.example.com/two.jpg", "published": False},
            ),
            call(
                "POST",
                "https://graph.facebook.com/v25.0/page-1/feed",
                access_token="page-token",
                json={
                    "attached_media": [{"media_fbid": "photo-1"}, {"media_fbid": "photo-2"}],
                    "message": "Caption for the album",
                },
            ),
        ]
    )


def test_publish_multi_photo_post_requires_staged_photo_ids():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(return_value=MagicMock(json=MagicMock(return_value={"success": True})))

    with pytest.raises(PublishError, match="Failed to stage Facebook photo"):
        provider.publish_post(
            "page-token",
            PublishContent(
                media_urls=["https://cdn.example.com/one.jpg", "https://cdn.example.com/two.jpg"],
                post_type=PostType.IMAGE,
                extra={"page_id": "page-1"},
            ),
        )


def test_publish_multi_photo_post_requires_feed_post_id():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(json=MagicMock(return_value={"id": "photo-1"})),
            MagicMock(json=MagicMock(return_value={"id": "photo-2"})),
            MagicMock(json=MagicMock(return_value={"success": True})),
            # best-effort cleanup of the two staged photos after the feed call fails
            MagicMock(json=MagicMock(return_value={})),
            MagicMock(json=MagicMock(return_value={})),
        ]
    )

    with pytest.raises(PublishError, match="Failed to publish Facebook multi-photo post"):
        provider.publish_post(
            "page-token",
            PublishContent(
                media_urls=["https://cdn.example.com/one.jpg", "https://cdn.example.com/two.jpg"],
                post_type=PostType.IMAGE,
                extra={"page_id": "page-1"},
            ),
        )


def test_publish_single_photo_uses_photos_edge_without_staging():
    """A single image must publish directly via /photos (no unpublished staging, no attached_media)."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(json=MagicMock(return_value={"id": "photo-1", "post_id": "page-1_post-1"}))
    )

    result = provider.publish_post(
        "page-token",
        PublishContent(
            text="Single image caption",
            media_urls=["https://cdn.example.com/one.jpg"],
            post_type=PostType.IMAGE,
            extra={"page_id": "page-1"},
        ),
    )

    assert result.platform_post_id == "post-1"
    assert result.url == "https://www.facebook.com/page-1_post-1"
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/page-1/photos",
        access_token="page-token",
        json={"url": "https://cdn.example.com/one.jpg", "message": "Single image caption"},
    )
    sent = provider._request.call_args.kwargs["json"]
    assert "published" not in sent
    assert "attached_media" not in sent


def test_is_video_url_ignores_query_string():
    """Presigned URLs carry query strings; the check must look at the path only."""
    assert FacebookProvider._is_video_url("https://cdn.example.com/clip.mp4?X-Amz-Sig=abc&x=1") is True
    assert FacebookProvider._is_video_url("https://cdn.example.com/clip.MOV") is True
    assert FacebookProvider._is_video_url("https://cdn.example.com/pic.jpg?X-Amz-Sig=abc") is False


def test_publish_multi_photo_rejects_video_media():
    """Mixed image+video must fail with a clear error before any photo is staged."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock()

    with pytest.raises(PublishError, match="images only"):
        provider.publish_post(
            "page-token",
            PublishContent(
                media_urls=["https://cdn.example.com/one.jpg", "https://cdn.example.com/clip.mp4"],
                post_type=PostType.IMAGE,
                extra={"page_id": "page-1"},
            ),
        )
    provider._request.assert_not_called()


def test_publish_multi_photo_rejects_too_many_photos():
    """Over Facebook's attached_media cap must fail before any photo is staged."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock()

    urls = [f"https://cdn.example.com/{i}.jpg" for i in range(11)]
    with pytest.raises(PublishError, match="at most 10 photos"):
        provider.publish_post(
            "page-token",
            PublishContent(media_urls=urls, post_type=PostType.IMAGE, extra={"page_id": "page-1"}),
        )
    provider._request.assert_not_called()


def test_publish_multi_photo_cleans_up_staged_photos_on_feed_failure():
    """If the feed post fails, every already-staged photo is deleted (best effort)."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(json=MagicMock(return_value={"id": "photo-1"})),
            MagicMock(json=MagicMock(return_value={"id": "photo-2"})),
            MagicMock(json=MagicMock(return_value={"success": True})),  # feed: no id
            MagicMock(json=MagicMock(return_value={})),  # delete photo-1
            MagicMock(json=MagicMock(return_value={})),  # delete photo-2
        ]
    )

    with pytest.raises(PublishError, match="Failed to publish Facebook multi-photo post"):
        provider.publish_post(
            "page-token",
            PublishContent(
                media_urls=["https://cdn.example.com/one.jpg", "https://cdn.example.com/two.jpg"],
                post_type=PostType.IMAGE,
                extra={"page_id": "page-1"},
            ),
        )

    provider._request.assert_has_calls(
        [
            call("DELETE", "https://graph.facebook.com/v25.0/photo-1", access_token="page-token"),
            call("DELETE", "https://graph.facebook.com/v25.0/photo-2", access_token="page-token"),
        ]
    )


def test_publish_multi_photo_cleans_up_after_partial_staging_failure():
    """If staging the second photo fails, the first (already staged) photo is deleted."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            MagicMock(json=MagicMock(return_value={"id": "photo-1"})),
            MagicMock(json=MagicMock(return_value={"success": True})),  # stage 2: no id
            MagicMock(json=MagicMock(return_value={})),  # delete photo-1
        ]
    )

    with pytest.raises(PublishError, match="Failed to stage Facebook photo"):
        provider.publish_post(
            "page-token",
            PublishContent(
                media_urls=["https://cdn.example.com/one.jpg", "https://cdn.example.com/two.jpg"],
                post_type=PostType.IMAGE,
                extra={"page_id": "page-1"},
            ),
        )

    provider._request.assert_any_call("DELETE", "https://graph.facebook.com/v25.0/photo-1", access_token="page-token")


def test_get_user_pages_includes_follower_count():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Page One",
                            "access_token": "page-token",
                            "category": "Media",
                            "followers_count": 123,
                            "picture": {"data": {"url": "https://example.com/avatar.jpg"}},
                        }
                    ]
                }
            )
        )
    )

    pages = provider.get_user_pages("user-token")

    assert pages[0]["followers_count"] == 123
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v25.0/me/accounts",
        access_token="user-token",
        params={"fields": "id,name,access_token,category,picture,followers_count"},
    )


def test_get_profile_uses_user_safe_fields():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=_resp(
            {
                "id": "user-1",
                "name": "User One",
                "picture": {"data": {"url": "https://example.com/user.jpg"}},
            }
        )
    )

    profile = provider.get_profile("user-token")

    assert profile.platform_id == "user-1"
    assert profile.name == "User One"
    assert profile.avatar_url == "https://example.com/user.jpg"
    assert profile.follower_count == 0
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v25.0/me",
        access_token="user-token",
        params={"fields": "id,name,picture"},
    )


def test_get_post_metrics_uses_v25_media_view_metrics_and_object_counts():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp(
                {
                    "id": "page-1_post-1",
                    "shares": {"count": 7},
                    "comments": {"summary": {"total_count": 5}},
                    "reactions": {"summary": {"total_count": 9}},
                }
            ),
            _resp(
                {
                    "data": [
                        {"name": "post_media_view", "values": [{"value": 54}]},
                        {"name": "post_total_media_view_unique", "values": [{"value": 42}]},
                        {"name": "post_clicks", "values": [{"value": 4}]},
                        {
                            "name": "post_reactions_by_type_total",
                            "values": [{"value": {"like": 3, "love": 2, "wow": 1}}],
                        },
                    ]
                }
            ),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "page-1_post-1")

    assert metrics.reach == 42
    assert metrics.video_views == 54
    assert metrics.clicks == 4
    assert metrics.likes == 0
    assert metrics.comments == 5
    assert metrics.shares == 7
    assert metrics.extra["reactions"] == 6
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1_post-1",
                access_token="page-token",
                params={"fields": FACEBOOK_POST_FIELDS_PARAM},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1_post-1/insights",
                access_token="page-token",
                params={"metric": FACEBOOK_POST_INSIGHTS_PARAM},
            ),
        ]
    )


def test_get_post_metrics_keeps_object_counts_when_insights_edge_is_missing():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp(
                {
                    "id": "page-1_post-1",
                    "shares": {"count": 3},
                    "comments": {"summary": {"total_count": 2}},
                    "reactions": {"summary": {"total_count": 4}},
                }
            ),
            APIError("nonexisting field insights", platform="Facebook"),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "page-1_post-1")

    assert metrics.video_views == 0
    assert metrics.reach == 0
    assert metrics.comments == 2
    assert metrics.shares == 3
    assert metrics.extra["reactions"] == 4
    assert set(metrics.extra["insight_errors"]) == {
        "post_media_view",
        "post_total_media_view_unique",
        "post_clicks",
        "post_reactions_by_type_total",
    }


def test_get_post_metrics_accepts_integer_object_counts():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "page-1_post-1", "shares": 3, "comments": 2}),
            _resp({"data": []}),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "page-1_post-1")

    assert metrics.comments == 2
    assert metrics.shares == 3


def test_get_post_metrics_resolves_photo_id_to_feed_post_for_comments_and_shares():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "photo-1", "post_id": "page-1_post-1"}),
            _resp(
                {
                    "id": "page-1_post-1",
                    "shares": {"count": 2},
                    "comments": {"summary": {"total_count": 4}},
                    "reactions": {"summary": {"total_count": 5}},
                }
            ),
            _resp(
                {
                    "data": [
                        {"name": "post_media_view", "values": [{"value": 500}]},
                        {"name": "post_total_media_view_unique", "values": [{"value": 300}]},
                        {"name": "post_clicks", "values": [{"value": 20}]},
                        {
                            "name": "post_reactions_by_type_total",
                            "values": [{"value": {"like": 10, "love": 3, "haha": 2}}],
                        },
                    ]
                }
            ),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "photo-1")

    assert metrics.reach == 300
    assert metrics.video_views == 500
    assert metrics.clicks == 20
    assert metrics.comments == 4
    assert metrics.shares == 2
    assert metrics.extra["reactions"] == 15
    provider._request.assert_any_call(
        "GET",
        "https://graph.facebook.com/v25.0/page-1_post-1/insights",
        access_token="page-token",
        params={"metric": FACEBOOK_POST_INSIGHTS_PARAM},
    )


def test_get_post_metrics_tries_page_scoped_feed_id_for_numeric_object_id():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "1668168861075953"}),
            _resp(
                {
                    "id": "page-1_1668168861075953",
                    "shares": {"count": 8},
                    "comments": {"summary": {"total_count": 6}},
                    "reactions": {"summary": {"total_count": 3}},
                }
            ),
            _resp(
                {
                    "data": [
                        {"name": "post_media_view", "values": [{"value": 90}]},
                        {"name": "post_total_media_view_unique", "values": [{"value": 70}]},
                        {"name": "post_clicks", "values": [{"value": 5}]},
                        {"name": "post_reactions_by_type_total", "values": [{"value": {"like": 3}}]},
                    ]
                }
            ),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "1668168861075953")

    assert metrics.reach == 70
    assert metrics.video_views == 90
    assert metrics.comments == 6
    assert metrics.shares == 8
    assert metrics.extra["insight_post_id"] == "page-1_1668168861075953"
    provider._request.assert_any_call(
        "GET",
        "https://graph.facebook.com/v25.0/page-1_1668168861075953",
        access_token="page-token",
        params={"fields": FACEBOOK_POST_FIELDS_PARAM},
    )
    provider._request.assert_any_call(
        "GET",
        "https://graph.facebook.com/v25.0/page-1_1668168861075953/insights",
        access_token="page-token",
        params={"metric": FACEBOOK_POST_INSIGHTS_PARAM},
    )


def test_get_post_metrics_tries_next_candidate_when_feed_id_has_no_insights_edge():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "1668168861075953"}),
            _resp({"id": "page-1_1668168861075953", "comments": {"summary": {"total_count": 2}}}),
            APIError("nonexisting field insights", platform="Facebook"),
            _resp(
                {
                    "data": [
                        {"name": "post_media_view", "values": [{"value": 12}]},
                        {"name": "post_total_media_view_unique", "values": [{"value": 10}]},
                    ]
                }
            ),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "1668168861075953")

    assert metrics.reach == 10
    assert metrics.video_views == 12
    assert metrics.comments == 2
    assert metrics.extra["insight_post_id"] == "1668168861075953"
    assert metrics.extra["attempted_insight_post_ids"] == ["page-1_1668168861075953", "1668168861075953"]
    provider._request.assert_any_call(
        "GET",
        "https://graph.facebook.com/v25.0/page-1_1668168861075953/insights",
        access_token="page-token",
        params={"metric": FACEBOOK_POST_INSIGHTS_PARAM},
    )
    provider._request.assert_any_call(
        "GET",
        "https://graph.facebook.com/v25.0/1668168861075953/insights",
        access_token="page-token",
        params={"metric": FACEBOOK_POST_INSIGHTS_PARAM},
    )


def test_get_post_metrics_reports_batched_insights_failure_for_each_metric():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "page-1_post-1", "comments": {"summary": {"total_count": 1}}}),
            APIError("nonexisting field insights", platform="Facebook", raw_response={"error": {"code": 100}}),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "page-1_post-1")

    assert metrics.video_views == 0
    assert metrics.reach == 0
    assert metrics.clicks == 0
    assert metrics.comments == 1
    assert metrics.extra["reactions"] == 0
    assert "post_total_media_view_unique" in metrics.extra["insight_errors"]


def test_publish_comment_reconstructs_page_scoped_facebook_post_id():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(return_value=_resp({"id": "comment-1"}))

    result = provider.publish_comment("page-token", "post-1", "Nice")

    assert result.platform_comment_id == "comment-1"
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/page-1_post-1/comments",
        access_token="page-token",
        json={"message": "Nice"},
    )


def test_get_account_metrics_uses_v25_page_media_view_metrics_and_followers_count():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"name": "page_media_view", "values": [{"value": 100}]}]}),
            _resp({"data": [{"name": "page_total_media_view_unique", "values": [{"value": 80}]}]}),
            _resp({"data": [{"name": "page_daily_follows_unique", "values": [{"value": 6}]}]}),
            _resp({"data": [{"name": "page_follows", "values": [{"value": 532790}]}]}),
            _resp({"data": [{"name": "page_post_engagements", "values": [{"value": 11}]}]}),
            _resp({"followers_count": 250}),
        ]
    )

    metrics = provider.get_account_metrics(
        "page-token", (MagicMock(timestamp=lambda: 10), MagicMock(timestamp=lambda: 20))
    )

    assert metrics.followers == 250
    assert metrics.followers_gained == 6
    assert metrics.reach == 80
    assert metrics.extra["views"] == 100
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1/insights",
                access_token="page-token",
                params={"metric": "page_media_view", "period": "day", "since": 10, "until": 20},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1/insights",
                access_token="page-token",
                params={"metric": "page_total_media_view_unique", "period": "day", "since": 10, "until": 20},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1/insights",
                access_token="page-token",
                params={"metric": "page_daily_follows_unique", "period": "day", "since": 10, "until": 20},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1/insights",
                access_token="page-token",
                params={"metric": "page_follows", "period": "day", "since": 10, "until": 20},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1/insights",
                access_token="page-token",
                params={"metric": "page_post_engagements", "period": "day", "since": 10, "until": 20},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/page-1",
                access_token="page-token",
                params={"fields": "followers_count"},
            ),
        ]
    )


def test_get_account_metrics_uses_page_follows_only_as_total_fallback():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret", "page_id": "page-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": []}),
            _resp({"data": []}),
            _resp({"data": [{"name": "page_daily_follows_unique", "values": [{"value": 4}]}]}),
            _resp({"data": [{"name": "page_follows", "values": [{"value": 532790}]}]}),
            _resp({"data": []}),
            APIError("followers_count unavailable", platform="Facebook"),
        ]
    )

    metrics = provider.get_account_metrics(
        "page-token", (MagicMock(timestamp=lambda: 10), MagicMock(timestamp=lambda: 20))
    )

    assert metrics.followers == 532790
    assert metrics.followers_gained == 4


def test_facebook_analytics_uuid_guard_detects_internal_ids():
    from apps.analytics.tasks import _looks_like_uuid

    assert _looks_like_uuid("0c77c88e-73f4-4986-a93f-87af966bb4ad") is True
    assert _looks_like_uuid("123456789_987654321") is False
    assert _looks_like_uuid("123456789") is False


def test_get_post_fields_retries_without_post_id_when_field_rejected():
    """``post_id`` is a Video-node field, not a Post-node field: on a plain feed
    post the first request 400s, so we retry without it instead of dropping the
    comments/shares summaries."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            APIError("(#100) nonexisting field (post_id) on node type (Page)", platform="Facebook"),
            _resp(
                {
                    "id": "page-1_post-1",
                    "comments": {"summary": {"total_count": 7}},
                    "shares": {"count": 3},
                }
            ),
        ]
    )

    fields = provider._get_post_fields("page-token", "page-1_post-1")

    assert fields["comments"]["summary"]["total_count"] == 7
    assert fields["shares"]["count"] == 3
    first_params = provider._request.call_args_list[0].kwargs["params"]
    second_params = provider._request.call_args_list[1].kwargs["params"]
    assert "post_id" in first_params["fields"].split(",")
    assert "post_id" not in second_params["fields"].split(",")


def test_publish_video_resolves_feed_post_id_for_analytics():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "video-1"}),
            _resp(
                {
                    "post_id": "page-1_post-1",
                    "permalink_url": "https://www.facebook.com/page-1/videos/video-1/",
                }
            ),
        ]
    )

    result = provider.publish_post(
        "page-token",
        PublishContent(
            text="Video caption",
            media_urls=["https://cdn.example.com/clip.mp4"],
            post_type=PostType.VIDEO,
            extra={"page_id": "page-1"},
        ),
    )

    assert result.platform_post_id == "post-1"
    assert result.url == "https://www.facebook.com/page-1/videos/video-1/"
    assert result.extra["video_id"] == "video-1"
    provider._request.assert_has_calls(
        [
            call(
                "POST",
                "https://graph.facebook.com/v25.0/page-1/videos",
                access_token="page-token",
                json={"file_url": "https://cdn.example.com/clip.mp4", "description": "Video caption"},
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/video-1",
                access_token="page-token",
                params={"fields": "post_id,permalink_url"},
            ),
        ]
    )


@pytest.mark.parametrize(
    "lookup_error",
    [
        RateLimitError("rate limited", platform="Facebook"),
        httpx.ConnectError("connection failed"),
    ],
)
def test_publish_video_treats_metadata_lookup_failures_as_best_effort(lookup_error):
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "video-1"}),
            lookup_error,
        ]
    )

    result = provider.publish_post(
        "page-token",
        PublishContent(
            text="Video caption",
            media_urls=["https://cdn.example.com/clip.mp4"],
            post_type=PostType.VIDEO,
            extra={"page_id": "page-1"},
        ),
    )

    assert result.platform_post_id == "video-1"
    assert result.url == "https://www.facebook.com/video-1"
    assert result.extra["video_id"] == "video-1"


def test_publish_video_survives_malformed_metadata_response():
    """The post-publish metadata GET runs AFTER the video is already live, so a
    non-API error (e.g. .json() raising on a malformed 2xx body) must NOT
    propagate — otherwise the publish engine retries and double-posts the video."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "video-1"}),
            MagicMock(json=MagicMock(side_effect=ValueError("not JSON"))),
        ]
    )

    result = provider.publish_post(
        "page-token",
        PublishContent(
            text="Video caption",
            media_urls=["https://cdn.example.com/clip.mp4"],
            post_type=PostType.VIDEO,
            extra={"page_id": "page-1"},
        ),
    )

    assert result.platform_post_id == "video-1"
    assert result.url == "https://www.facebook.com/video-1"
    assert result.extra["video_id"] == "video-1"


def test_get_post_fields_does_not_retry_on_non_field_error():
    """A non-`post_id` error (auth, 5xx, not-found) won't be fixed by dropping
    post_id, so _get_post_fields must not fire a second doomed request."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(side_effect=APIError("(#190) Error validating access token", platform="Facebook"))

    fields = provider._get_post_fields("page-token", "page-1_post-1")

    assert fields == {}
    assert provider._request.call_count == 1
