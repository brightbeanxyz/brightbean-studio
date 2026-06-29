"""Unsplash image search service.

Uses the Unsplash API (free tier: 50 requests/hour) to search for stock photography.
Requires ``UNSPLASH_ACCESS_KEY`` in settings/environment.

API docs: https://unsplash.com/documentation
Guidelines: https://help.unsplash.com/en/articles/2511258-guideline-attribution
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

UNSPLASH_API_BASE = "https://api.unsplash.com"
RATE_LIMIT_CACHE_KEY = "unsplash:rate_limit:remaining"
RATE_LIMIT_RESET_KEY = "unsplash:rate_limit:reset"
FREE_TIER_LIMIT = 50  # requests per hour


class UnsplashError(Exception):
    """Base exception for Unsplash API errors."""


class UnsplashAuthError(UnsplashError):
    """Invalid or missing API key."""


class UnsplashRateLimited(UnsplashError):
    """Rate limit exceeded."""


class UnsplashNotFound(UnsplashError):
    """Photo not found."""


@dataclass
class UnsplashPhoto:
    """Minimal Unsplash photo result."""

    id: str
    description: str | None
    width: int
    height: int
    color: str
    urls: dict[str, str] = field(default_factory=dict)
    photographer: str = ""
    photographer_url: str = ""
    download_url: str = ""


@dataclass
class SearchResults:
    """Paginated search results."""

    results: list[UnsplashPhoto]
    total: int
    total_pages: int
    page: int


class UnsplashClient:
    """Client for the Unsplash API.

    Tracks rate limits via Django cache. Respects the free tier
    50 req/hour limit and surfaces Retry-After to users.

    Key resolution order:
      1. workspace_key (passed per-request from workspace.integration_settings)
      2. settings.UNSPLASH_ACCESS_KEY (env var)
    """

    def __init__(self, access_key: str | None = None, workspace_key: str | None = None):
        self._access_key = access_key or workspace_key or getattr(settings, "UNSPLASH_ACCESS_KEY", "")
        self._session = requests.Session()
        self._session.headers.update({"Accept-Version": "v1"})

    @property
    def is_configured(self) -> bool:
        return bool(self._access_key)

    def _check_rate_limit(self) -> None:
        """Raise UnsplashRateLimited if we've hit the free tier cap."""
        remaining = cache.get(RATE_LIMIT_CACHE_KEY)
        if remaining is not None and remaining <= 0:
            reset_at = cache.get(RATE_LIMIT_RESET_KEY, 0)
            wait = max(0, int(reset_at - time.time()))
            raise UnsplashRateLimited(f"Rate limit reached. Try again in {wait // 60 + 1} minute(s).")

    def _update_rate_limit(self, response: requests.Response) -> None:
        """Update cache from X-RateLimit-* headers."""
        remaining = response.headers.get("X-Ratelimit-Remaining")
        if remaining is not None:
            cache.set(RATE_LIMIT_CACHE_KEY, int(remaining), timeout=3600)
        # Fallback: if headers missing, decrement our own counter
        elif cache.get(RATE_LIMIT_CACHE_KEY) is None:
            cache.set(RATE_LIMIT_CACHE_KEY, FREE_TIER_LIMIT - 1, timeout=3600)
        else:
            cache.decr(RATE_LIMIT_CACHE_KEY)

    def _auth_header(self) -> dict[str, str]:
        if not self._access_key:
            raise UnsplashAuthError("Unsplash API key is not configured. Set UNSPLASH_ACCESS_KEY in your environment.")
        return {"Authorization": f"Client-ID {self._access_key}"}

    def search_photos(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
        orientation: str | None = None,
        color: str | None = None,
    ) -> SearchResults:
        """Search Unsplash for photos matching *query*.

        Args:
            query: Search term.
            page: Page number (1-based).
            per_page: Results per page (max 30).
            orientation: Filter by orientation (landscape, portrait, squarish).
            color: Filter by color (6-char hex without #).

        Returns:
            A ``SearchResults`` with photo list and pagination info.

        Raises:
            UnsplashAuthError: API key missing or invalid.
            UnsplashRateLimited: Rate limit exceeded.
            UnsplashError: Other API errors.
        """
        self._check_rate_limit()

        params: dict[str, Any] = {
            "query": query,
            "page": page,
            "per_page": min(per_page, 30),
        }
        if orientation:
            params["orientation"] = orientation
        if color:
            params["color"] = color

        response = self._session.get(
            f"{UNSPLASH_API_BASE}/search/photos",
            headers=self._auth_header(),
            params=params,
            timeout=15,
        )
        self._update_rate_limit(response)

        if response.status_code == 401:
            raise UnsplashAuthError("Unsplash API key is invalid.")
        if response.status_code == 403:
            raise UnsplashRateLimited("Unsplash API returned 403 (rate limited or permission denied).")
        if not response.ok:
            raise UnsplashError(f"Unsplash API error: {response.status_code} {response.text[:200]}")

        data = response.json()
        photos = [
            UnsplashPhoto(
                id=p["id"],
                description=p.get("description") or p.get("alt_description"),
                width=p["width"],
                height=p["height"],
                color=p.get("color", ""),
                urls={
                    "raw": p["urls"]["raw"],
                    "regular": p["urls"]["regular"],
                    "thumb": p["urls"]["thumb"],
                },
                photographer=p["user"]["name"],
                photographer_url=p["user"]["links"]["html"],
                download_url=p["links"]["download_location"],
            )
            for p in data.get("results", [])
        ]

        return SearchResults(
            results=photos,
            total=data["total"],
            total_pages=data["total_pages"],
            page=page,
        )

    def get_photo(self, photo_id: str) -> UnsplashPhoto:
        """Fetch a single photo by Unsplash ID.

        Raises:
            UnsplashNotFound: Photo not found.
        """
        self._check_rate_limit()

        response = self._session.get(
            f"{UNSPLASH_API_BASE}/photos/{photo_id}",
            headers=self._auth_header(),
            timeout=10,
        )
        self._update_rate_limit(response)

        if response.status_code == 404:
            raise UnsplashNotFound(f"Photo {photo_id} not found on Unsplash.")
        if not response.ok:
            raise UnsplashError(f"Unsplash API error: {response.status_code}")

        p = response.json()
        return UnsplashPhoto(
            id=p["id"],
            description=p.get("description") or p.get("alt_description"),
            width=p["width"],
            height=p["height"],
            color=p.get("color", ""),
            urls={
                "raw": p["urls"]["raw"],
                "regular": p["urls"]["regular"],
                "thumb": p["urls"]["thumb"],
            },
            photographer=p["user"]["name"],
            photographer_url=p["user"]["links"]["html"],
            download_url=p["links"]["download_location"],
        )

    def download_photo(self, photo_id: str) -> bytes:
        """Download image bytes for a photo (regular resolution, 1080px).

        Triggers Unsplash download tracking event as required by API guidelines.
        """
        photo = self.get_photo(photo_id)
        self._trigger_download_event(photo.download_url)

        response = self._session.get(photo.urls["regular"], timeout=30)
        if not response.ok:
            raise UnsplashError(f"Failed to download image: {response.status_code}")
        return response.content

    def _trigger_download_event(self, download_url: str) -> None:
        """POST to Unsplash download endpoint (required by API guidelines).

        This is a fire-and-forget call — failures here should not block
        the import, but we log them for compliance auditing.
        """
        try:
            self._session.get(
                download_url,
                headers=self._auth_header(),
                timeout=10,
            )
        except Exception:
            logger.warning("Failed to trigger Unsplash download event for %s", download_url)


# Module-level convenience functions for backward compatibility

_default_client: UnsplashClient | None = None


def _get_client() -> UnsplashClient:
    global _default_client
    if _default_client is None:
        _default_client = UnsplashClient()
    return _default_client


def search_photos(
    query: str,
    per_page: int = 5,
    page: int = 1,
    orientation: str | None = None,
    color: str | None = None,
) -> list[dict]:
    """Convenience function — returns list of dicts for compatibility.

    New code should use UnsplashClient directly.
    """
    client = _get_client()
    if not client.is_configured:
        return []
    try:
        results = client.search_photos(query, page=page, per_page=per_page, orientation=orientation, color=color)
        return [
            {
                "id": p.id,
                "description": p.description,
                "url_raw": p.urls["raw"],
                "url_regular": p.urls["regular"],
                "url_thumb": p.urls["thumb"],
                "photographer": p.photographer,
                "photographer_url": p.photographer_url,
            }
            for p in results.results
        ]
    except UnsplashError:
        return []
