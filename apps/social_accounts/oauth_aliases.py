"""URL-slug aliases for OAuth callback paths.

TikTok's app review rejects redirect URIs that contain the string "tiktok"
in the path. To satisfy that policy without renaming the platform identifier
throughout the codebase, the redirect URI uses an opaque slug (``social1``)
while every other layer (DB, providers, signed OAuth state, models) keeps
using ``tiktok``.

The mapping is one-way per platform: callers that build the redirect URI
call :func:`to_url_slug`; the callback view normalises the incoming path
parameter with :func:`from_url_slug` before any platform-keyed lookup.

Platforms without an entry pass through unchanged, so existing routes
(``callback/instagram/``, ``callback/youtube/`` …) keep working.
"""

from __future__ import annotations

PLATFORM_TO_URL_ALIAS: dict[str, str] = {
    "tiktok": "social1",
}

URL_ALIAS_TO_PLATFORM: dict[str, str] = {v: k for k, v in PLATFORM_TO_URL_ALIAS.items()}


def to_url_slug(platform: str) -> str:
    """Return the URL-path slug for ``platform`` (e.g. ``tiktok`` → ``social1``)."""
    return PLATFORM_TO_URL_ALIAS.get(platform, platform)


def from_url_slug(slug: str) -> str:
    """Return the platform identifier for a URL slug (e.g. ``social1`` → ``tiktok``).

    Unrecognised slugs pass through so the legacy ``callback/tiktok/`` route
    still resolves during the transition window.
    """
    return URL_ALIAS_TO_PLATFORM.get(slug, slug)


def redirect_uri_from_request(request) -> str:
    """Rebuild the OAuth redirect URI from the incoming callback request.

    OAuth token exchange requires the ``redirect_uri`` parameter to match
    the URL used at authorization EXACTLY. Reconstructing from
    ``request.path`` (instead of ``reverse()``-ing the current canonical
    URL) preserves whatever path the platform actually called back to —
    important during transitions where the canonical slug changes (e.g.
    TikTok's ``tiktok`` → ``social1`` rename) and any auth started before
    the deploy would otherwise rebuild to the new path and fail TikTok's
    exact-match check.
    """
    return request.build_absolute_uri(request.path)
