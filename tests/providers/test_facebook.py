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
