"""Social platform provider registry.

Maps PlatformCredential.Platform enum values to provider classes.
Use get_provider() to instantiate a provider with app credentials.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .bluesky import BlueskyProvider
from .facebook import FacebookProvider
from .google_business import GoogleBusinessProvider
from .instagram import InstagramProvider
from .instagram_login import InstagramLoginProvider
from .linkedin_company import LinkedInCompanyProvider
from .linkedin_personal import LinkedInPersonalProvider
from .mastodon import MastodonProvider
from .pinterest import PinterestProvider
from .threads import ThreadsProvider
from .tiktok import TikTokProvider
from .youtube import YouTubeProvider

if TYPE_CHECKING:
    from .base import SocialProvider

PROVIDER_REGISTRY: dict[str, type[SocialProvider]] = {
    "facebook": FacebookProvider,
    "instagram": InstagramProvider,
    "instagram_login": InstagramLoginProvider,
    "linkedin_personal": LinkedInPersonalProvider,
    "linkedin_company": LinkedInCompanyProvider,
    "tiktok": TikTokProvider,
    "youtube": YouTubeProvider,
    "pinterest": PinterestProvider,
    "threads": ThreadsProvider,
    "bluesky": BlueskyProvider,
    "google_business": GoogleBusinessProvider,
    "mastodon": MastodonProvider,
}


def get_provider(platform: str, credentials: dict | None = None) -> SocialProvider:
    """Instantiate and return a provider for the given platform.

    Args:
        platform: A PlatformCredential.Platform value (e.g. "facebook").
        credentials: Platform app credentials (client_id, client_secret, etc.)
                     from PlatformCredential or settings.PLATFORM_CREDENTIALS_FROM_ENV.
                     If None, falls back to env credentials from
                     ``settings.PLATFORM_CREDENTIALS_FROM_ENV``.

    Raises:
        ValueError: If no provider is registered for the given platform.
    """
    provider_cls = PROVIDER_REGISTRY.get(platform)
    if provider_cls is None:
        raise ValueError(f"No provider registered for platform: {platform}")
    if credentials is None:
        from django.conf import settings

        env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
        credentials = env_creds.get(platform, {})
    return provider_cls(credentials=credentials)
