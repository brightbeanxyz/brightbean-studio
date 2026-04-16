from unittest.mock import MagicMock, patch

import httpx
import pytest

from providers.base import SocialProvider
from providers.types import PostMetrics


class TestGetRecentPostMetrics:
    def test_base_raises_not_implemented(self):
        """Base provider should raise NotImplementedError for unsupported platforms."""

        class StubProvider(SocialProvider):
            platform_name = "stub"
            auth_type = "oauth2"
            max_caption_length = 280
            supported_post_types = []
            supported_media_types = []
            required_scopes = []

            def get_profile(self, access_token):
                pass

            def publish_post(self, access_token, content):
                pass

        provider = StubProvider()
        with pytest.raises(NotImplementedError, match="stub"):
            provider.get_recent_post_metrics("token", "account_id")


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    resp.headers = {}
    return resp


class TestInstagramRecentPostMetrics:
    @patch.object(
        __import__("providers.instagram", fromlist=["InstagramProvider"]).InstagramProvider,
        "_request",
    )
    def test_returns_post_metrics(self, mock_request):
        from providers.instagram import InstagramProvider

        media_response = _mock_response({
            "data": [
                {
                    "id": "media_1",
                    "caption": "New drop preview for the season",
                    "media_type": "IMAGE",
                    "timestamp": "2026-04-10T12:00:00+0000",
                    "permalink": "https://www.instagram.com/p/ABC123/",
                },
                {
                    "id": "media_2",
                    "caption": "Behind the scenes shoot",
                    "media_type": "VIDEO",
                    "timestamp": "2026-04-08T15:30:00+0000",
                    "permalink": "https://www.instagram.com/p/DEF456/",
                },
            ]
        })

        insights_1 = _mock_response({
            "data": [
                {"name": "impressions", "values": [{"value": 5000}]},
                {"name": "reach", "values": [{"value": 3000}]},
                {"name": "likes", "values": [{"value": 200}]},
                {"name": "comments", "values": [{"value": 30}]},
                {"name": "shares", "values": [{"value": 15}]},
                {"name": "saved", "values": [{"value": 50}]},
            ]
        })

        insights_2 = _mock_response({
            "data": [
                {"name": "impressions", "values": [{"value": 8000}]},
                {"name": "reach", "values": [{"value": 5000}]},
                {"name": "likes", "values": [{"value": 400}]},
                {"name": "comments", "values": [{"value": 60}]},
                {"name": "shares", "values": [{"value": 25}]},
                {"name": "saved", "values": [{"value": 100}]},
            ]
        })

        mock_request.side_effect = [media_response, insights_1, insights_2]

        provider = InstagramProvider()
        results = provider.get_recent_post_metrics("token", "ig_user_123", limit=10)

        assert len(results) == 2
        assert results[0].likes == 200
        assert results[0].comments == 30
        assert results[0].shares == 15
        assert results[0].saves == 50
        assert results[0].impressions == 5000
        assert results[0].engagements == 295  # 200+30+15+50
        assert results[0].extra["platform_post_id"] == "media_1"
        assert results[0].extra["post_url"] == "https://www.instagram.com/p/ABC123/"
        assert results[0].extra["post_type"] == "image"


class TestTikTokRecentPostMetrics:
    @patch.object(
        __import__("providers.tiktok", fromlist=["TikTokProvider"]).TikTokProvider,
        "_request",
    )
    def test_returns_post_metrics(self, mock_request):
        from providers.tiktok import TikTokProvider

        list_response = _mock_response({
            "data": {
                "videos": [
                    {
                        "id": "vid_001",
                        "title": "Dance challenge collab",
                        "create_time": 1744300800,
                        "share_url": "https://www.tiktok.com/@nike/video/vid_001",
                        "like_count": 5000,
                        "comment_count": 300,
                        "share_count": 150,
                        "view_count": 80000,
                    },
                ],
                "has_more": False,
            }
        })
        mock_request.return_value = list_response

        provider = TikTokProvider()
        results = provider.get_recent_post_metrics("token", "tiktok_user_1", limit=10)

        assert len(results) == 1
        assert results[0].likes == 5000
        assert results[0].comments == 300
        assert results[0].shares == 150
        assert results[0].video_views == 80000
        assert results[0].engagements == 5450  # 5000+300+150
        assert results[0].extra["platform_post_id"] == "vid_001"
        assert results[0].extra["post_type"] == "video"


class TestYouTubeRecentPostMetrics:
    @patch.object(
        __import__("providers.youtube", fromlist=["YouTubeProvider"]).YouTubeProvider,
        "_request",
    )
    def test_returns_post_metrics(self, mock_request):
        from providers.youtube import YouTubeProvider

        search_response = _mock_response({
            "items": [
                {"id": {"videoId": "yt_vid_1"}},
                {"id": {"videoId": "yt_vid_2"}},
            ]
        })

        videos_response = _mock_response({
            "items": [
                {
                    "id": "yt_vid_1",
                    "snippet": {
                        "title": "Product Review: Nike Air Max",
                        "publishedAt": "2026-04-12T10:00:00Z",
                    },
                    "statistics": {
                        "viewCount": "15000",
                        "likeCount": "800",
                        "commentCount": "120",
                    },
                },
                {
                    "id": "yt_vid_2",
                    "snippet": {
                        "title": "Unboxing the new collection",
                        "publishedAt": "2026-04-09T14:00:00Z",
                    },
                    "statistics": {
                        "viewCount": "9000",
                        "likeCount": "450",
                        "commentCount": "65",
                    },
                },
            ]
        })

        mock_request.side_effect = [search_response, videos_response]

        provider = YouTubeProvider()
        results = provider.get_recent_post_metrics("token", "yt_channel_1", limit=10)

        assert len(results) == 2
        assert results[0].likes == 800
        assert results[0].comments == 120
        assert results[0].video_views == 15000
        assert results[0].engagements == 920  # 800+120
        assert results[0].extra["platform_post_id"] == "yt_vid_1"
        assert results[0].extra["post_type"] == "video"
        assert results[0].extra["post_url"] == "https://www.youtube.com/watch?v=yt_vid_1"
