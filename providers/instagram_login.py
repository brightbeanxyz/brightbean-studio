"""Instagram API with Instagram Login provider.

Supports Professional Instagram accounts (Business or Creator) via the
Instagram Login OAuth flow — distinct from the Facebook-Login path used by
``InstagramProvider``. No linked Facebook Page is required.

Personal (non-Professional) Instagram accounts have no API access since
the Basic Display API was retired on 2024-12-04. Users must convert their
account to Professional before connecting.

Docs: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import APIError, OAuthError, PublishError
from .meta_insights import fetch_insights_safe
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

AUTH_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH_HOST = "https://graph.instagram.com"
API_BASE = f"{GRAPH_HOST}/v25.0"
INSTAGRAM_ACCOUNT_INSIGHTS = [
    "reach",
    "views",
    "accounts_engaged",
    "total_interactions",
]
INSTAGRAM_MEDIA_INSIGHTS = [
    "reach",
    "views",
    "likes",
    "comments",
    "saved",
    "shares",
    "total_interactions",
]
INSTAGRAM_MEDIA_FIELDS = [
    "id",
    "caption",
    "media_type",
    "media_product_type",
    "media_url",
    "thumbnail_url",
    "permalink",
    "timestamp",
    "like_count",
    "comments_count",
]

# Container polling
CONTAINER_POLL_INTERVAL = 2  # seconds
CONTAINER_POLL_MAX_ATTEMPTS = 60  # ~2 minutes max


class InstagramLoginProvider(SocialProvider):
    """Instagram API provider using Instagram Login (OAuth 2.0).

    Authenticates Professional (Business or Creator) Instagram accounts
    directly through Instagram, without requiring a linked Facebook Page.
    """

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
        return "Instagram (Direct)"

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
        scopes = [
            "instagram_business_basic",
            "instagram_business_content_publish",
            "instagram_business_manage_comments",
            "instagram_business_manage_messages",
        ]
        if self.include_analytics_scopes:
            scopes.extend(self.analytics_only_scopes)
        return scopes

    @property
    def analytics_only_scopes(self) -> list[str]:
        # Required for `/insights` endpoints on the IG-Login OAuth path.
        # Only requested when analytics is enabled in AnalyticsPlatformConfig.
        return ["instagram_business_manage_insights"]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=5000,
            publish_per_day=100,
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.required_scopes),
            "response_type": "code",
            "enable_fb_login": "0",
            "force_authentication": "1",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
        # Instagram Login requires multipart/form-data, not urlencoded.
        fields = {
            "client_id": self.credentials["client_id"],
            "client_secret": self.credentials["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        resp = self._request(
            "POST",
            TOKEN_URL,
            files={k: (None, v) for k, v in fields.items()},
        )
        body = resp.json()
        short_lived_token = body.get("access_token")
        logger.info(
            "IG-Login step 1: status=%s keys=%s user_id=%s token=%s len=%d",
            resp.status_code,
            sorted(body.keys()),
            body.get("user_id"),
            (short_lived_token[:6] + "...") if short_lived_token else None,
            len(short_lived_token) if short_lived_token else 0,
        )
        if not short_lived_token:
            raise OAuthError(
                f"Instagram token exchange failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )

        # Exchange short-lived token (~1 hour) for long-lived token (~60 days)
        return self._exchange_for_long_lived_token(short_lived_token)

    def _exchange_for_long_lived_token(self, short_lived_token: str) -> OAuthTokens:
        url = f"{GRAPH_HOST}/access_token"
        logger.info(
            "IG-Login step 2: GET %s client_id=%s token=%s",
            url,
            self.credentials.get("client_id"),
            short_lived_token[:6] + "...",
        )
        resp = self._request(
            "GET",
            url,
            params={
                "grant_type": "ig_exchange_token",
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "access_token": short_lived_token,
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"Instagram long-lived token exchange failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        token = body["access_token"]
        return OAuthTokens(
            access_token=token,
            # Instagram Login uses the access token itself for refresh
            refresh_token=token,
            expires_in=body.get("expires_in"),
            token_type=body.get("token_type", "Bearer"),
            raw_response=body,
        )

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh a long-lived Instagram token.

        Instagram Login uses the access token itself for refresh - there is
        no separate refresh token.
        """
        resp = self._request(
            "GET",
            f"{GRAPH_HOST}/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": refresh_token,
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"Instagram token refresh failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        token = body["access_token"]
        return OAuthTokens(
            access_token=token,
            refresh_token=token,
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
                "fields": "user_id,username,name,profile_picture_url,followers_count,media_count,biography",
            },
        )
        data = resp.json()
        return AccountProfile(
            platform_id=str(data.get("user_id", data.get("id", ""))),
            name=data.get("name", data.get("username", "")),
            handle=data.get("username"),
            avatar_url=data.get("profile_picture_url"),
            follower_count=data.get("followers_count", 0),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        if not content.media_urls:
            raise PublishError(
                "Instagram requires at least one media item",
                platform=self.platform_name,
            )

        if content.post_type == PostType.CAROUSEL and len(content.media_urls) > 1:
            return self._publish_carousel(access_token, content)
        return self._publish_single(access_token, content)

    def _publish_single(self, access_token: str, content: PublishContent) -> PublishResult:
        payload: dict = {}
        if content.text:
            payload["caption"] = content.text

        if content.post_type == PostType.REEL:
            payload["media_type"] = "REELS"
            payload["video_url"] = content.media_urls[0]
        elif content.post_type == PostType.STORY:
            url = content.media_urls[0]
            payload["media_type"] = "STORIES"
            if url.lower().endswith((".mp4", ".mov")):
                payload["video_url"] = url
            else:
                payload["image_url"] = url
        else:
            # Default IMAGE
            payload["image_url"] = content.media_urls[0]

        container_id = self._create_container(access_token, payload)
        self._wait_for_container(access_token, container_id)
        return self._publish_container(access_token, container_id)

    def _publish_carousel(self, access_token: str, content: PublishContent) -> PublishResult:
        child_ids: list[str] = []

        for url in content.media_urls:
            is_video = url.lower().endswith((".mp4", ".mov"))
            child_payload: dict = {"is_carousel_item": True}
            if is_video:
                child_payload["media_type"] = "VIDEO"
                child_payload["video_url"] = url
            else:
                child_payload["image_url"] = url

            child_id = self._create_container(access_token, child_payload)
            self._wait_for_container(access_token, child_id)
            child_ids.append(child_id)

        carousel_payload: dict = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
        }
        if content.text:
            carousel_payload["caption"] = content.text

        carousel_id = self._create_container(access_token, carousel_payload)
        self._wait_for_container(access_token, carousel_id)
        return self._publish_container(access_token, carousel_id)

    def _create_container(self, access_token: str, payload: dict) -> str:
        resp = self._request(
            "POST",
            f"{API_BASE}/me/media",
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
                f"{API_BASE}/{container_id}",
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

    def _publish_container(self, access_token: str, container_id: str) -> PublishResult:
        resp = self._request(
            "POST",
            f"{API_BASE}/me/media_publish",
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
            f"{API_BASE}/{post_id}/comments",
            access_token=access_token,
            json={"message": text},
        )
        data = resp.json()
        return CommentResult(platform_comment_id=data["id"], extra=data)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        fields = self._get_media_fields(access_token, post_id)
        values, errors = fetch_insights_safe(
            self._request,
            platform=self.platform_name,
            endpoint=f"{API_BASE}/{post_id}/insights",
            access_token=access_token,
            metrics=INSTAGRAM_MEDIA_INSIGHTS,
            endpoint_type="media",
        )
        likes = values.get("likes", fields.get("like_count", 0))
        comments = values.get("comments", fields.get("comments_count", 0))

        return PostMetrics(
            reach=values.get("reach", 0),
            likes=likes,
            comments=comments,
            saves=values.get("saved", 0),
            shares=values.get("shares", 0),
            video_views=values.get("views", 0),
            extra={
                "total_interactions": values.get("total_interactions", 0),
                "raw_fields": fields,
                "raw_insights": values,
                "insight_errors": errors,
            },
        )

    def get_account_metrics(self, access_token: str, date_range: tuple[datetime, datetime]) -> AccountMetrics:
        since = int(date_range[0].timestamp())
        until = int(date_range[1].timestamp())
        values, errors = fetch_insights_safe(
            self._request,
            platform=self.platform_name,
            endpoint=f"{API_BASE}/me/insights",
            access_token=access_token,
            metrics=INSTAGRAM_ACCOUNT_INSIGHTS,
            base_params={
                "period": "day",
                "since": since,
                "until": until,
            },
            metric_params={
                "views": {"metric_type": "total_value"},
                "accounts_engaged": {"metric_type": "total_value"},
                "total_interactions": {"metric_type": "total_value"},
            },
            endpoint_type="account",
        )
        profile = self._get_profile_fields(access_token)
        # ``None`` means the fetch FAILED (vs a real 0): leave followers unset so
        # _account_metrics_to_dict skips it and we don't poison the snapshot with 0.
        followers = profile.get("followers_count", 0) if profile is not None else None

        return AccountMetrics(
            reach=values.get("reach", 0),
            followers=followers,
            extra={
                "views": values.get("views", 0),
                "accounts_engaged": values.get("accounts_engaged", 0),
                "total_interactions": values.get("total_interactions", 0),
                "raw_insights": values,
                "insight_errors": errors,
            },
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        params: dict = {"fields": "id,participants,messages{id,message,from,created_time}"}
        if since:
            params["since"] = int(since.timestamp())

        resp = self._request(
            "GET",
            f"{API_BASE}/me/conversations",
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
            f"{API_BASE}/{message_id}/messages",
            access_token=access_token,
            json={"message": text},
        )
        data = resp.json()
        return ReplyResult(platform_message_id=data.get("id", ""), extra=data)

    def _get_profile_fields(self, access_token: str) -> dict | None:
        # Returns ``None`` on failure so callers can distinguish a failed fetch
        # from a successful one with no data (a genuine 0).
        try:
            return self._request(
                "GET",
                f"{API_BASE}/me",
                access_token=access_token,
                params={"fields": "user_id,username,name,profile_picture_url,followers_count,media_count"},
            ).json()
        except APIError as exc:
            logger.debug("Instagram Login profile fields unavailable: %s", exc)
            return None

    def _get_media_fields(self, access_token: str, media_id: str) -> dict:
        try:
            return self._request(
                "GET",
                f"{API_BASE}/{media_id}",
                access_token=access_token,
                params={"fields": ",".join(INSTAGRAM_MEDIA_FIELDS)},
            ).json()
        except APIError as exc:
            logger.debug("Instagram Login media fields unavailable for %s: %s", media_id, exc)
            return {}

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def revoke_token(self, access_token: str) -> bool:
        try:
            self._request(
                "DELETE",
                f"{API_BASE}/me/permissions",
                access_token=access_token,
            )
            return True
        except APIError:
            logger.warning("Failed to revoke Instagram token")
            return False
