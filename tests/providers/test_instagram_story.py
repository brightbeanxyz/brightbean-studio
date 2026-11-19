"""Instagram Stories carry no caption: it is never shown, so it is not sent."""

import pytest

from providers.types import PostType
from tests.providers.test_instagram import IG_PUBLISHERS, IMAGE_URL, VIDEO_URL, _publish


@pytest.mark.parametrize(("make_provider", "create_url"), IG_PUBLISHERS)
@pytest.mark.parametrize(("url", "field"), [(IMAGE_URL, "image_url"), (VIDEO_URL, "video_url")])
def test_a_story_is_sent_without_its_caption(make_provider, create_url, url, field):
    provider = make_provider()

    _publish(provider, text="Only for the feed", media_urls=[url], post_type=PostType.STORY)

    assert provider._request.call_args_list[0].kwargs["json"] == {
        "media_type": "STORIES",
        field: url,
    }
