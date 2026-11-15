from unittest.mock import MagicMock

import pytest

from providers.exceptions import PublishError
from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider
from providers.types import PostType, PublishContent


@pytest.fixture(params=[InstagramProvider, InstagramLoginProvider])
def provider(request):
    p = request.param({"client_id": "id", "client_secret": "secret"})
    p._get_ig_user_id = MagicMock(return_value="ig-id")
    p._create_container = MagicMock(return_value="container")
    p._wait_for_container = MagicMock()
    p._publish_container = MagicMock(return_value="published")
    return p


@pytest.mark.parametrize("strategy", ["MANUAL", "SS_PERFORMANCE"])
@pytest.mark.parametrize("post_type", [PostType.REEL, PostType.VIDEO, PostType.TEXT])
def test_trial_reaches_container_for_single_video(provider, strategy, post_type):
    content = PublishContent(
        post_type=post_type,
        media_urls=["https://example.com/signed?x=1"],
        media_types=["video"],
        extra={"trial_reel_graduation_strategy": strategy},
    )
    assert provider.publish_post("token", content) == "published"
    payload = provider._create_container.call_args.args[-1]
    assert payload["media_type"] == "REELS"
    assert payload["trial_params"] == {"graduation_strategy": strategy}
    provider._create_container.assert_called_once()


def test_regular_reel_has_no_trial_params(provider):
    provider.publish_post("token", PublishContent(post_type=PostType.REEL, media_urls=["https://example.com/v.mp4"]))
    assert "trial_params" not in provider._create_container.call_args.args[-1]


@pytest.mark.parametrize("strategy", ["invalid", "", False, {"MANUAL": True}])
def test_invalid_strategy_fails_before_network(provider, strategy):
    with pytest.raises(PublishError) as error:
        provider.publish_post(
            "token",
            PublishContent(
                media_urls=["https://example.com/v.mp4"],
                extra={"trial_reel_graduation_strategy": strategy},
            ),
        )
    assert error.value.retryable is False
    provider._create_container.assert_not_called()
    provider._get_ig_user_id.assert_not_called()


@pytest.mark.parametrize(
    "kind,urls",
    [
        (PostType.IMAGE, ["https://example.com/p.jpg"]),
        (PostType.STORY, ["https://example.com/v.mp4"]),
        (PostType.CAROUSEL, ["https://example.com/a.mp4", "https://example.com/b.mp4"]),
        (PostType.REEL, []),
    ],
)
def test_trial_never_falls_back_to_other_media(provider, kind, urls):
    with pytest.raises(PublishError):
        provider.publish_post(
            "token",
            PublishContent(
                post_type=kind,
                media_urls=urls,
                extra={"trial_reel_graduation_strategy": "MANUAL"},
            ),
        )
    provider._create_container.assert_not_called()
    provider._get_ig_user_id.assert_not_called()


def test_meta_rejection_does_not_retry_without_trial(provider):
    provider._create_container.side_effect = PublishError("Account not eligible", retryable=False)
    with pytest.raises(PublishError, match="not eligible"):
        provider.publish_post(
            "token",
            PublishContent(
                post_type=PostType.REEL,
                media_urls=["https://example.com/v.mp4"],
                extra={"trial_reel_graduation_strategy": "MANUAL"},
            ),
        )
    provider._create_container.assert_called_once()
    provider._publish_container.assert_not_called()
