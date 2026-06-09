"""Tests for OAuth redirect-URI slug aliases.

TikTok's app review rejects redirect URIs that contain the brand name in
the path, so the redirect URI uses an opaque slug (``social1``). These
tests guard the round-trip so the platform identifier the rest of the
codebase keys on never leaks into the URL.
"""

from apps.social_accounts.oauth_aliases import (
    PLATFORM_TO_URL_ALIAS,
    from_url_slug,
    to_url_slug,
)


def test_tiktok_maps_to_social1():
    assert to_url_slug("tiktok") == "social1"


def test_social1_slug_resolves_back_to_tiktok():
    assert from_url_slug("social1") == "tiktok"


def test_tiktok_slug_still_resolves_for_backwards_compatibility():
    # Legacy redirect URI (``callback/tiktok/``) must keep resolving while
    # the TikTok dev portal transitions to the new ``social1`` slug.
    assert from_url_slug("tiktok") == "tiktok"


def test_unknown_platforms_pass_through_unchanged():
    # Platforms without an alias entry use their own name in the URL.
    for platform in ("instagram", "youtube", "linkedin_company", "facebook"):
        assert to_url_slug(platform) == platform
        assert from_url_slug(platform) == platform


def test_round_trip_for_every_aliased_platform():
    # Every (platform → slug → platform) round trip must be an identity, so
    # callback handlers always resolve back to the right provider keyword.
    for platform, slug in PLATFORM_TO_URL_ALIAS.items():
        assert from_url_slug(to_url_slug(platform)) == platform
        assert from_url_slug(slug) == platform


def test_no_alias_value_collides_with_a_real_platform_name():
    # An alias that matches another platform's identifier would break the
    # reverse lookup. Guard against that as the alias map grows.
    from apps.credentials.models import PlatformCredential

    real_platforms = {value for value, _ in PlatformCredential.Platform.choices}
    for slug in PLATFORM_TO_URL_ALIAS.values():
        assert slug not in real_platforms, f"alias '{slug}' collides with a real platform"
