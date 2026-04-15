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
