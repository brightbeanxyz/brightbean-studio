from unittest.mock import MagicMock

from providers.facebook import FacebookProvider
from providers.types import PostType, PublishContent


def test_publish_single_photo_uses_feed_post_id_when_available():
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

    assert result.platform_post_id == "page-1_post-1"
    assert result.url == "https://www.facebook.com/page-1_post-1"
    assert result.extra["id"] == "photo-1"
