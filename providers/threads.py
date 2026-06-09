"""Threads API provider."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import OAuthError, PublishError
from .types import (
    AccountProfile,
    AuthType,
    CommentResult,
    MediaType,
    OAuthTokens,
    PostMetrics,
    PostType,
    PublishContent,
    PublishResult,
    RateLimitConfig,
)

logger = logging.getLogger(__name__)

AUTH_URL = "https://www.threads.com/oauth/authorize"
TOKEN_URL = "https://graph.threads.net/oauth/access_token"
API_BASE = "https://graph.threads.net/v1.0"


class ThreadsProvider(SocialProvider):
    """Threads API provider using OAuth 2.0."""

    def __init__(self, credentials: dict | None = None):
        creds = dict(credentials or {})
        # Normalize: accept app_id/app_secret as aliases for client_id/client_secret
        if "app_id" in creds and "client_id" not in creds:
            creds["client_id"] = creds.pop("app_id")
        if "app_secret" in creds and "client_secret" not in creds:
            creds["client_secret"] = creds.pop("app_secret")
        super().__init__(creds)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "Threads"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 500

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.CAROUSEL]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.MP4, MediaType.MOV]

    @property
    def required_scopes(self) -> list[str]:
        return [
            "threads_basic",
            "threads_content_publish",
            "threads_manage_insights",
            "threads_manage_replies",
        ]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=5000,
            publish_per_day=250,
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.required_scopes),
            "response_type": "code",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        body = resp.json()
        short_lived_token = body.get("access_token")
        if not short_lived_token:
            raise OAuthError(
                f"Threads token exchange failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )

        # Exchange short-lived token for long-lived token
        long_lived = self._exchange_for_long_lived_token(short_lived_token)
        return long_lived

    def _exchange_for_long_lived_token(self, short_lived_token: str) -> OAuthTokens:
        """Exchange a short-lived token for a long-lived one."""
        resp = self._request(
            "GET",
            f"{API_BASE}/access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_secret": self.credentials["client_secret"],
                "access_token": short_lived_token,
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"Threads long-lived token exchange failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        return OAuthTokens(
            access_token=body["access_token"],
            expires_in=body.get("expires_in"),
            token_type=body.get("token_type", "Bearer"),
            raw_response=body,
        )

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh a long-lived Threads token.

        Note: Threads uses the access token itself for refresh (no separate
        refresh_token). The ``refresh_token`` argument here is the current
        long-lived access token.
        """
        resp = self._request(
            "GET",
            f"{API_BASE}/refresh_access_token",
            params={
                "grant_type": "th_refresh_token",
                "access_token": refresh_token,
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"Threads token refresh failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        return OAuthTokens(
            access_token=body["access_token"],
            expires_in=body.get("expires_in"),
            token_type=body.get("token_type", "Bearer"),
            raw_response=body,
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        resp = self._request(
            "GET",
            f"{API_BASE}/me",
            access_token=access_token,
            params={
                "fields": "id,username,name,threads_profile_picture_url,threads_biography",
            },
        )
        body = resp.json()
        return AccountProfile(
            platform_id=body.get("id", ""),
            name=body.get("name", ""),
            handle=body.get("username"),
            avatar_url=body.get("threads_profile_picture_url"),
            extra={"biography": body.get("threads_biography")},
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        user_id = content.extra.get("user_id")
        if not user_id:
            # Fetch user_id from profile if not provided
            profile = self.get_profile(access_token)
            user_id = profile.platform_id

        if not user_id:
            raise PublishError(
                "Could not determine Threads user_id",
                platform=self.platform_name,
            )

        if content.post_type == PostType.CAROUSEL:
            return self._publish_carousel(access_token, user_id, content)

        return self._publish_single(access_token, user_id, content)

    def _publish_single(
        self,
        access_token: str,
        user_id: str,
        content: PublishContent,
    ) -> PublishResult:
        """Create and publish a single-item thread (TEXT, IMAGE, or VIDEO)."""
        # Step 1: Create container
        container_payload: dict = {
            "text": (content.text or "")[: self.max_caption_length],
        }

        if content.post_type == PostType.IMAGE and content.media_urls:
            container_payload["media_type"] = "IMAGE"
            container_payload["image_url"] = content.media_urls[0]
        elif content.post_type == PostType.VIDEO and content.media_urls:
            container_payload["media_type"] = "VIDEO"
            container_payload["video_url"] = content.media_urls[0]
        else:
            container_payload["media_type"] = "TEXT"

        # Add reply_to_id if this is a reply
        reply_to = content.extra.get("reply_to_id")
        if reply_to:
            container_payload["reply_to_id"] = reply_to

        create_resp = self._request(
            "POST",
            f"{API_BASE}/{user_id}/threads",
            access_token=access_token,
            data=container_payload,
        )
        create_body = create_resp.json()
        creation_id = create_body.get("id")

        if not creation_id:
            raise PublishError(
                f"Threads container creation failed: {create_body}",
                platform=self.platform_name,
                raw_response=create_body,
            )

        # Step 2: Publish the container
        publish_resp = self._request(
            "POST",
            f"{API_BASE}/{user_id}/threads_publish",
            access_token=access_token,
            data={"creation_id": creation_id},
        )
        publish_body = publish_resp.json()
        thread_id = publish_body.get("id", "")
        return PublishResult(
            platform_post_id=thread_id,
            extra=publish_body,
        )

    def _publish_carousel(
        self,
        access_token: str,
        user_id: str,
        content: PublishContent,
    ) -> PublishResult:
        """Create and publish a carousel thread."""
        # Step 1: Create individual item containers
        children_ids: list[str] = []

        for url in content.media_urls:
            # Determine media type by extension heuristic
            lower_url = url.lower()
            if any(lower_url.endswith(ext) for ext in (".mp4", ".mov")):
                media_type = "VIDEO"
                key = "video_url"
            else:
                media_type = "IMAGE"
                key = "image_url"

            item_resp = self._request(
                "POST",
                f"{API_BASE}/{user_id}/threads",
                access_token=access_token,
                data={
                    "media_type": media_type,
                    key: url,
                    "is_carousel_item": "true",
                },
            )
            item_body = item_resp.json()
            item_id = item_body.get("id")
            if not item_id:
                raise PublishError(
                    f"Threads carousel item creation failed: {item_body}",
                    platform=self.platform_name,
                    raw_response=item_body,
                )
            children_ids.append(item_id)

        # Step 2: Create carousel container
        carousel_resp = self._request(
            "POST",
            f"{API_BASE}/{user_id}/threads",
            access_token=access_token,
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(children_ids),
                "text": (content.text or "")[: self.max_caption_length],
            },
        )
        carousel_body = carousel_resp.json()
        creation_id = carousel_body.get("id")
        if not creation_id:
            raise PublishError(
                f"Threads carousel container creation failed: {carousel_body}",
                platform=self.platform_name,
                raw_response=carousel_body,
            )

        # Step 3: Publish
        publish_resp = self._request(
            "POST",
            f"{API_BASE}/{user_id}/threads_publish",
            access_token=access_token,
            data={"creation_id": creation_id},
        )
        publish_body = publish_resp.json()
        thread_id = publish_body.get("id", "")
        return PublishResult(
            platform_post_id=thread_id,
            extra=publish_body,
        )

    # ------------------------------------------------------------------
    # Comments (replies)
    # ------------------------------------------------------------------

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        """Reply to a thread (uses the container flow with reply_to_id)."""
        user_id_resp = self._request(
            "GET",
            f"{API_BASE}/me",
            access_token=access_token,
            params={"fields": "id"},
        )
        user_id = user_id_resp.json().get("id", "")

        # Create reply container
        create_resp = self._request(
            "POST",
            f"{API_BASE}/{user_id}/threads",
            access_token=access_token,
            data={
                "media_type": "TEXT",
                "text": text[: self.max_caption_length],
                "reply_to_id": post_id,
            },
        )
        creation_id = create_resp.json().get("id")
        if not creation_id:
            raise PublishError(
                "Threads reply container creation failed",
                platform=self.platform_name,
                raw_response=create_resp.json(),
            )

        # Publish
        publish_resp = self._request(
            "POST",
            f"{API_BASE}/{user_id}/threads_publish",
            access_token=access_token,
            data={"creation_id": creation_id},
        )
        reply_id = publish_resp.json().get("id", "")
        return CommentResult(
            platform_comment_id=reply_id,
            extra=publish_resp.json(),
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        resp = self._request(
            "GET",
            f"{API_BASE}/{post_id}/insights",
            access_token=access_token,
            params={
                "metric": "views,likes,replies,reposts,quotes",
            },
        )
        body = resp.json()
        data = body.get("data", [])

        metrics: dict[str, int] = {}
        for item in data:
            name = item.get("name", "")
            values = item.get("values", [])
            if values:
                metrics[name] = values[0].get("value", 0)

        return PostMetrics(
            impressions=metrics.get("views", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("replies", 0),
            shares=metrics.get("reposts", 0),
            engagements=(
                metrics.get("likes", 0)
                + metrics.get("replies", 0)
                + metrics.get("reposts", 0)
                + metrics.get("quotes", 0)
            ),
            extra={
                "quotes": metrics.get("quotes", 0),
                "raw": data,
            },
        )
