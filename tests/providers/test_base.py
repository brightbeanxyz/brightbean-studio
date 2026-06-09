"""Tests for the provider base class and registry."""

import pytest

from providers import PROVIDER_REGISTRY, get_provider
from providers.base import SocialProvider
from providers.types import AuthType, PostType


class TestProviderRegistry:
    """Test provider registry completeness and get_provider()."""

    def test_registry_contains_all_platforms(self):
        expected = {
            "facebook",
            "instagram",
            "instagram_login",
            "linkedin_personal",
            "linkedin_company",
            "tiktok",
            "youtube",
            "pinterest",
            "threads",
            "bluesky",
            "google_business",
            "mastodon",
        }
        assert set(PROVIDER_REGISTRY.keys()) == expected

    def test_all_registry_values_are_provider_subclasses(self):
        for platform, cls in PROVIDER_REGISTRY.items():
            assert issubclass(cls, SocialProvider), f"{platform} -> {cls} is not a SocialProvider subclass"

    def test_get_provider_returns_instance(self):
        provider = get_provider("facebook", {"app_id": "test", "app_secret": "test"})
        assert isinstance(provider, SocialProvider)
        assert provider.platform_name == "Facebook"

    def test_get_provider_raises_on_unknown_platform(self):
        with pytest.raises(ValueError, match="No provider registered"):
            get_provider("twitter")

    def test_get_provider_default_credentials(self):
        provider = get_provider("bluesky")
        assert provider.credentials == {}


class TestSocialProviderInterface:
    """Test that all providers implement required abstract methods."""

    @pytest.mark.parametrize("platform", list(PROVIDER_REGISTRY.keys()))
    def test_provider_has_platform_name(self, platform):
        provider = get_provider(platform)
        assert isinstance(provider.platform_name, str)
        assert len(provider.platform_name) > 0

    @pytest.mark.parametrize("platform", list(PROVIDER_REGISTRY.keys()))
    def test_provider_has_auth_type(self, platform):
        provider = get_provider(platform)
        assert isinstance(provider.auth_type, AuthType)

    @pytest.mark.parametrize("platform", list(PROVIDER_REGISTRY.keys()))
    def test_provider_has_max_caption_length(self, platform):
        provider = get_provider(platform)
        assert isinstance(provider.max_caption_length, int)
        assert provider.max_caption_length > 0

    @pytest.mark.parametrize("platform", list(PROVIDER_REGISTRY.keys()))
    def test_provider_has_supported_post_types(self, platform):
        provider = get_provider(platform)
        post_types = provider.supported_post_types
        assert isinstance(post_types, list)
        assert len(post_types) > 0
        for pt in post_types:
            assert isinstance(pt, PostType)

    @pytest.mark.parametrize("platform", list(PROVIDER_REGISTRY.keys()))
    def test_provider_has_required_scopes(self, platform):
        provider = get_provider(platform)
        scopes = provider.required_scopes
        assert isinstance(scopes, list)

    @pytest.mark.parametrize("platform", list(PROVIDER_REGISTRY.keys()))
    def test_provider_has_rate_limits(self, platform):
        provider = get_provider(platform)
        rl = provider.rate_limits
        assert rl.requests_per_hour > 0

    def test_session_providers_raise_on_get_auth_url(self):
        """Bluesky (session auth) should raise on OAuth methods."""
        provider = get_provider("bluesky")
        with pytest.raises(NotImplementedError):
            provider.get_auth_url("http://localhost/callback", "state123")

    def test_oauth_providers_implement_get_auth_url(self):
        """OAuth providers should return a URL string."""
        provider = get_provider(
            "facebook",
            {"client_id": "test_id", "client_secret": "test_secret"},
        )
        url = provider.get_auth_url("http://localhost/callback", "state123")
        assert url.startswith("https://")
        assert "test_id" in url
        assert "state123" in url

    def test_validate_token_returns_bool(self):
        """validate_token should return False when get_profile fails."""
        provider = get_provider("facebook")
        # With no real token, this should return False (not raise)
        result = provider.validate_token("invalid_token")
        assert result is False


class TestProviderMetadata:
    """Test specific provider metadata values match spec."""

    def test_facebook_max_caption(self):
        p = get_provider("facebook")
        assert p.max_caption_length == 63206

    def test_instagram_max_caption(self):
        p = get_provider("instagram")
        assert p.max_caption_length == 2200

    def test_linkedin_personal_max_caption(self):
        p = get_provider("linkedin_personal")
        assert p.max_caption_length == 3000

    def test_linkedin_company_max_caption(self):
        p = get_provider("linkedin_company")
        assert p.max_caption_length == 3000

    def test_bluesky_max_caption(self):
        p = get_provider("bluesky")
        assert p.max_caption_length == 300

    def test_threads_max_caption(self):
        p = get_provider("threads")
        assert p.max_caption_length == 500

    def test_bluesky_auth_type_is_session(self):
        p = get_provider("bluesky")
        assert p.auth_type == AuthType.SESSION

    def test_mastodon_auth_type_is_instance_oauth(self):
        p = get_provider("mastodon")
        assert p.auth_type == AuthType.INSTANCE_OAUTH

    def test_facebook_auth_type_is_oauth2(self):
        p = get_provider("facebook")
        assert p.auth_type == AuthType.OAUTH2
