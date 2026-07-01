"""DEV.to (Forem) provider implementation.

DEV.to is an article platform. Authentication is a single per-account API key
(Settings → Account → DEV Community API Keys), sent in the ``api-key`` header —
there is no OAuth flow, so this provider uses ``AuthType.SESSION`` and stores the
API key as the account's access token.
"""

from __future__ import annotations

import logging
import re

from .base import SocialProvider
from .exceptions import PublishError
from .types import (
    AccountProfile,
    AuthType,
    MediaType,
    OAuthTokens,
    PostType,
    PublishContent,
    PublishResult,
    RateLimitConfig,
)

logger = logging.getLogger(__name__)

API_BASE = "https://dev.to/api"
API_ACCEPT = "application/vnd.forem.api-v1+json"

# DEV.to allows at most 4 tags, each lowercase alphanumeric.
MAX_TAGS = 4
# Article titles are capped at 128 characters by Forem.
MAX_TITLE_LENGTH = 128


class DevtoProvider(SocialProvider):
    """DEV.to / Forem provider using a personal API key (no OAuth)."""

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "DEV.to"

    @property
    def auth_type(self) -> AuthType:
        # API-key based; treated like a session credential (the key IS the token).
        return AuthType.SESSION

    @property
    def max_caption_length(self) -> int:
        # Article body (Markdown) — Forem has no hard cap; keep it generous.
        return 25000

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.ARTICLE, PostType.TEXT, PostType.LINK]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.WEBP]

    @property
    def required_scopes(self) -> list[str]:
        return []  # API-key based, no scopes

    @property
    def rate_limits(self) -> RateLimitConfig:
        # Forem's documented limit for article creation is ~10 per 30s.
        return RateLimitConfig(requests_per_hour=1000, requests_per_day=10000, publish_per_day=100)

    # ------------------------------------------------------------------
    # OAuth stubs (not applicable for API-key auth)
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        raise NotImplementedError("DEV.to uses an API key, not OAuth. Use connect_devto instead.")

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
        raise NotImplementedError("DEV.to uses an API key, not OAuth. Use connect_devto instead.")

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        """Validate the API key and return the authenticated user's profile."""
        resp = self._request(
            "GET",
            f"{API_BASE}/users/me",
            headers=self._auth_headers(access_token),
        )
        data = resp.json()
        username = data.get("username", "")
        return AccountProfile(
            platform_id=str(data.get("id", username)),
            name=data.get("name") or username,
            handle=username,
            avatar_url=data.get("profile_image_90") or data.get("profile_image"),
            follower_count=0,  # not exposed by the /users/me endpoint
            extra=data,
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        """Publish an article to DEV.to via POST /articles."""
        title = (content.title or "").strip()
        if not title:
            raise PublishError(
                "DEV.to requires a title. Set the post title before publishing.",
                platform=self.platform_name,
            )

        body = content.description or content.text or ""
        article: dict = {
            "title": title[:MAX_TITLE_LENGTH],
            "body_markdown": body,
            "published": True,
        }

        tags = self._extract_tags(content)
        if tags:
            article["tags"] = tags

        if content.link_url:
            article["canonical_url"] = content.link_url

        main_image = self._first_image_url(content)
        if main_image:
            article["main_image"] = main_image

        resp = self._request(
            "POST",
            f"{API_BASE}/articles",
            headers=self._auth_headers(access_token),
            json={"article": article},
        )
        data = resp.json()
        article_id = data.get("id")
        if not article_id:
            raise PublishError(
                f"DEV.to article creation returned no id: {data}",
                platform=self.platform_name,
                raw_response=data,
            )
        return PublishResult(
            platform_post_id=str(article_id),
            url=data.get("url"),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _auth_headers(access_token: str) -> dict:
        # DEV.to authenticates with the ``api-key`` header, not Bearer, so the
        # header is passed explicitly rather than via ``_request(access_token=...)``.
        return {
            "api-key": access_token,
            "accept": API_ACCEPT,
            "content-type": "application/json",
        }

    @staticmethod
    def _extract_tags(content: PublishContent) -> list[str]:
        """Resolve up to 4 Forem-valid tags from an explicit hint or #hashtags."""
        raw = content.extra.get("tags") if isinstance(content.extra, dict) else None
        if not raw:
            raw = re.findall(r"(?<!\w)#(\w+)", content.text or "")
        tags: list[str] = []
        for tag in raw:
            clean = re.sub(r"[^a-z0-9]", "", str(tag).lower())
            if clean and clean not in tags:
                tags.append(clean)
            if len(tags) >= MAX_TAGS:
                break
        return tags

    @staticmethod
    def _first_image_url(content: PublishContent) -> str | None:
        """Use the first image media URL as the article cover, if any."""
        for url in content.media_urls or []:
            path = url.split("?", 1)[0].lower()
            if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                return url
        return None
