from unittest.mock import MagicMock, call

import pytest

from providers.exceptions import PublishError
from providers.facebook import FacebookProvider
from providers.types import PostType, PublishContent


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

    assert result.platform_post_id == "page-1_post-1"
    assert result.url == "https://www.facebook.com/page-1_post-1"
    assert result.extra["photo_ids"] == ["photo-1", "photo-2"]
    provider._request.assert_has_calls(
        [
            call(
                "POST",
                "https://graph.facebook.com/v21.0/page-1/photos",
                access_token="page-token",
                json={"url": "https://cdn.example.com/one.jpg", "published": False},
            ),
            call(
                "POST",
                "https://graph.facebook.com/v21.0/page-1/photos",
                access_token="page-token",
                json={"url": "https://cdn.example.com/two.jpg", "published": False},
            ),
            call(
                "POST",
                "https://graph.facebook.com/v21.0/page-1/feed",
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

    assert result.platform_post_id == "photo-1"
    assert result.url == "https://www.facebook.com/page-1_post-1"
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v21.0/page-1/photos",
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
            call("DELETE", "https://graph.facebook.com/v21.0/photo-1", access_token="page-token"),
            call("DELETE", "https://graph.facebook.com/v21.0/photo-2", access_token="page-token"),
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

    provider._request.assert_any_call("DELETE", "https://graph.facebook.com/v21.0/photo-1", access_token="page-token")
