"""Instagram Graph API provider implementation.

Instagram's API is accessed through the Facebook Graph API. Authentication
uses the Facebook OAuth flow with Instagram-specific scopes.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import APIError, OAuthError, PublishError
from .types import (
    AccountMetrics,
    AccountProfile,
    AuthType,
    CommentResult,
    InboxMessage,
    MediaType,
    OAuthTokens,
    PostMetrics,
    PostType,
    PublishContent,
    PublishResult,
    RateLimitConfig,
    ReplyResult,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.facebook.com/v21.0"
OAUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
TOKEN_URL = f"{BASE_URL}/oauth/access_token"

# Polling settings for container status checks
CONTAINER_POLL_INTERVAL = 2  # seconds
CONTAINER_POLL_MAX_ATTEMPTS = 60


class InstagramProvider(SocialProvider):
    """Instagram Graph API provider (via Facebook Graph API v21.0)."""

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
        return "Instagram"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 2200

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.IMAGE, PostType.CAROUSEL, PostType.REEL, PostType.STORY]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4, MediaType.MOV]

    @property
    def required_scopes(self) -> list[str]:
        return [
            "instagram_basic",
            "instagram_content_publish",
            "instagram_manage_comments",
            "instagram_manage_insights",
        ]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=5000,
            publish_per_day=100,
            extra={"published_posts_per_24h": 100},
        )

    # ------------------------------------------------------------------
    # OAuth (uses Facebook OAuth flow)
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.required_scopes),
            "response_type": "code",
        }
        return f"{OAUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            params={
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
            },
        )
        data = resp.json()
        if "access_token" not in data:
            raise OAuthError(
                "Instagram token exchange failed",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            raw_response=data,
        )

    def refresh_token(self, short_lived_token: str) -> OAuthTokens:
        """Exchange short-lived token for a long-lived one (same as Facebook)."""
        resp = self._request(
            "GET",
            f"{BASE_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "fb_exchange_token": short_lived_token,
            },
        )
        data = resp.json()
        if "access_token" not in data:
            raise OAuthError(
                "Instagram long-lived token exchange failed",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            raw_response=data,
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        ig_user_id = self._get_ig_user_id(access_token)
        resp = self._request(
            "GET",
            f"{BASE_URL}/{ig_user_id}",
            access_token=access_token,
            params={"fields": "id,username,name,profile_picture_url,followers_count"},
        )
        data = resp.json()
        return AccountProfile(
            platform_id=data["id"],
            name=data.get("name", ""),
            handle=data.get("username"),
            avatar_url=data.get("profile_picture_url"),
            follower_count=data.get("followers_count", 0),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Publishing (two-step container flow)
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        ig_user_id = content.extra.get("ig_user_id") or self._get_ig_user_id(access_token)

        if content.post_type == PostType.CAROUSEL:
            return self._publish_carousel(access_token, ig_user_id, content)
        return self._publish_single(access_token, ig_user_id, content)

    def _publish_single(self, access_token: str, ig_user_id: str, content: PublishContent) -> PublishResult:
        """Publish a single image, reel, or story."""
        payload: dict = {}

        if content.text:
            payload["caption"] = content.text

        if content.post_type == PostType.REEL:
            payload["media_type"] = "REELS"
            payload["video_url"] = content.media_urls[0]
        elif content.post_type == PostType.STORY:
            if content.media_urls and content.media_urls[0].endswith((".mp4", ".mov")):
                payload["media_type"] = "STORIES"
                payload["video_url"] = content.media_urls[0]
            else:
                payload["media_type"] = "STORIES"
                payload["image_url"] = content.media_urls[0]
        else:
            # Default IMAGE
            payload["image_url"] = content.media_urls[0]

        # Step 1: create container
        container_id = self._create_container(access_token, ig_user_id, payload)

        # Step 2: wait for container to be ready
        self._wait_for_container(access_token, container_id)

        # Step 3: publish
        return self._publish_container(access_token, ig_user_id, container_id)

    def _publish_carousel(self, access_token: str, ig_user_id: str, content: PublishContent) -> PublishResult:
        """Publish a carousel post with multiple media items."""
        child_ids: list[str] = []

        for url in content.media_urls:
            is_video = url.lower().endswith((".mp4", ".mov"))
            child_payload: dict = {
                "is_carousel_item": True,
            }
            if is_video:
                child_payload["media_type"] = "VIDEO"
                child_payload["video_url"] = url
            else:
                child_payload["image_url"] = url

            child_id = self._create_container(access_token, ig_user_id, child_payload)
            self._wait_for_container(access_token, child_id)
            child_ids.append(child_id)

        # Create carousel container
        carousel_payload: dict = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
        }
        if content.text:
            carousel_payload["caption"] = content.text

        carousel_id = self._create_container(access_token, ig_user_id, carousel_payload)
        self._wait_for_container(access_token, carousel_id)

        return self._publish_container(access_token, ig_user_id, carousel_id)

    def _create_container(self, access_token: str, ig_user_id: str, payload: dict) -> str:
        resp = self._request(
            "POST",
            f"{BASE_URL}/{ig_user_id}/media",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        container_id = data.get("id")
        if not container_id:
            raise PublishError(
                "Failed to create Instagram media container",
                platform=self.platform_name,
                raw_response=data,
            )
        return container_id

    def _wait_for_container(self, access_token: str, container_id: str) -> None:
        """Poll container status until FINISHED or error."""
        for _ in range(CONTAINER_POLL_MAX_ATTEMPTS):
            resp = self._request(
                "GET",
                f"{BASE_URL}/{container_id}",
                access_token=access_token,
                params={"fields": "status_code,status"},
            )
            data = resp.json()
            status = data.get("status_code", "")

            if status == "FINISHED":
                return
            if status == "ERROR":
                raise PublishError(
                    f"Instagram container failed: {data.get('status', 'unknown error')}",
                    platform=self.platform_name,
                    raw_response=data,
                )

            time.sleep(CONTAINER_POLL_INTERVAL)

        raise PublishError(
            "Instagram container processing timed out",
            platform=self.platform_name,
        )

    def _publish_container(self, access_token: str, ig_user_id: str, container_id: str) -> PublishResult:
        resp = self._request(
            "POST",
            f"{BASE_URL}/{ig_user_id}/media_publish",
            access_token=access_token,
            json={"creation_id": container_id},
        )
        data = resp.json()
        media_id = data.get("id", "")
        return PublishResult(
            platform_post_id=media_id,
            url=f"https://www.instagram.com/p/{media_id}/",
            extra=data,
        )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        resp = self._request(
            "POST",
            f"{BASE_URL}/{post_id}/comments",
            access_token=access_token,
            params={"fields": "id"},
            json={"message": text},
        )
        data = resp.json()
        return CommentResult(platform_comment_id=data["id"], extra=data)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        metrics = ["impressions", "reach", "engagement", "saved"]
        resp = self._request(
            "GET",
            f"{BASE_URL}/{post_id}/insights",
            access_token=access_token,
            params={"metric": ",".join(metrics)},
        )
        data = resp.json()
        values: dict = {}
        for entry in data.get("data", []):
            name = entry.get("name", "")
            val = entry.get("values", [{}])[0].get("value", 0)
            values[name] = val

        return PostMetrics(
            impressions=values.get("impressions", 0),
            reach=values.get("reach", 0),
            engagements=values.get("engagement", 0),
            saves=values.get("saved", 0),
            extra={"raw_insights": values},
        )

    def get_account_metrics(self, access_token: str, date_range: tuple[datetime, datetime]) -> AccountMetrics:
        ig_user_id = self.credentials.get("ig_user_id", "me")
        metrics = ["impressions", "reach", "follower_count", "profile_views"]
        resp = self._request(
            "GET",
            f"{BASE_URL}/{ig_user_id}/insights",
            access_token=access_token,
            params={
                "metric": ",".join(metrics),
                "period": "day",
                "since": int(date_range[0].timestamp()),
                "until": int(date_range[1].timestamp()),
            },
        )
        data = resp.json()
        values: dict = {}
        for entry in data.get("data", []):
            name = entry.get("name", "")
            val = entry.get("values", [{}])[0].get("value", 0)
            values[name] = val

        return AccountMetrics(
            impressions=values.get("impressions", 0),
            reach=values.get("reach", 0),
            followers=values.get("follower_count", 0),
            profile_views=values.get("profile_views", 0),
            extra={"raw_insights": values},
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        ig_user_id = self.credentials.get("ig_user_id", "me")
        params: dict = {"fields": "id,participants,messages{id,message,from,created_time}"}
        if since:
            params["since"] = int(since.timestamp())

        resp = self._request(
            "GET",
            f"{BASE_URL}/{ig_user_id}/conversations",
            access_token=access_token,
            params=params,
        )
        conversations = resp.json().get("data", [])

        messages: list[InboxMessage] = []
        for convo in conversations:
            for msg in convo.get("messages", {}).get("data", []):
                sender = msg.get("from", {})
                messages.append(
                    InboxMessage(
                        platform_message_id=msg["id"],
                        sender_id=sender.get("id", ""),
                        sender_name=sender.get("name", sender.get("username", "")),
                        text=msg.get("message", ""),
                        timestamp=datetime.fromisoformat(msg["created_time"].replace("+0000", "+00:00")),
                        message_type="dm",
                        extra={"conversation_id": convo["id"]},
                    )
                )
        return messages

    def reply_to_message(self, access_token: str, message_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        """Reply to a conversation. message_id should be the conversation ID."""
        resp = self._request(
            "POST",
            f"{BASE_URL}/{message_id}/messages",
            access_token=access_token,
            json={"message": text},
        )
        data = resp.json()
        return ReplyResult(platform_message_id=data.get("id", ""), extra=data)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_ig_user_id(self, access_token: str) -> str:
        """Resolve the Instagram Business Account ID from the connected
        Facebook Page.

        The IG user ID can be stored in credentials to avoid an extra API call.
        """
        if "ig_user_id" in self.credentials:
            return self.credentials["ig_user_id"]

        # Get pages and find the one with an instagram_business_account
        resp = self._request(
            "GET",
            f"{BASE_URL}/me/accounts",
            access_token=access_token,
            params={"fields": "id,instagram_business_account"},
        )
        for page in resp.json().get("data", []):
            ig_account = page.get("instagram_business_account")
            if ig_account:
                return ig_account["id"]

        raise APIError(
            "No Instagram Business Account found linked to any Facebook Page",
            platform=self.platform_name,
        )
