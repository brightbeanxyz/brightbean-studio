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

BASE_URL = "https://graph.facebook.com/v25.0"
OAUTH_URL = "https://www.facebook.com/v25.0/dialog/oauth"
TOKEN_URL = f"{BASE_URL}/oauth/access_token"
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

# Polling settings for container status checks
CONTAINER_POLL_INTERVAL = 2  # seconds
CONTAINER_POLL_MAX_ATTEMPTS = 60


class InstagramProvider(SocialProvider):
    """Instagram Graph API provider (via Facebook Graph API v25.0)."""

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
            "pages_show_list",
            "pages_read_engagement",
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

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": ",".join(self.required_scopes),
            "response_type": "code",
        }
        return f"{OAUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
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
            params={"fields": "id,username,name,profile_picture_url,followers_count,media_count"},
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
    # Accounts
    # ------------------------------------------------------------------

    def get_user_pages(self, access_token: str) -> list[dict]:
        """Fetch linked Instagram Business accounts for Facebook-login OAuth.

        The user authenticates through Facebook, but the connected account in
        Brightbean should be the Instagram Business account selected from the
        Facebook Pages the user manages.
        """
        resp = self._request(
            "GET",
            f"{BASE_URL}/me/accounts",
            access_token=access_token,
            params={
                "fields": (
                    "id,name,access_token,category,picture,"
                    "instagram_business_account{id,username,name,profile_picture_url,followers_count,media_count}"
                ),
            },
        )
        data = resp.json()
        if "error" in data:
            logger.error("Instagram /me/accounts error: %s", data["error"])
            raise APIError(
                f"Failed to fetch Instagram accounts: {data['error'].get('message', 'Unknown error')}",
                platform=self.platform_name,
                raw_response=data,
            )

        accounts: list[dict] = []
        for page in data.get("data", []):
            ig_account = page.get("instagram_business_account")
            if not ig_account:
                continue

            picture_url = ig_account.get("profile_picture_url")
            if not picture_url and "picture" in page and "data" in page["picture"]:
                picture_url = page["picture"]["data"].get("url")

            username = ig_account.get("username", "")
            name = ig_account.get("name") or username or page.get("name", "")
            account = {
                "id": str(ig_account["id"]),
                "name": name,
                "handle": username,
                "category": page.get("category", ""),
                "picture": picture_url,
                "followers_count": ig_account.get("followers_count", 0),
                "page_id": page.get("id"),
                "page_name": page.get("name", ""),
            }
            page_token = page.get("access_token")
            if page_token:
                account["access_token"] = page_token
            accounts.append(account)
        return accounts

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

        if content.post_type in (PostType.REEL, PostType.VIDEO):
            # Instagram no longer supports standalone feed videos: a single
            # video is published as a Reel. PostType.VIDEO (the engine's
            # fallback for a lone video asset) must take the REELS path too,
            # otherwise it falls through to the IMAGE branch and the .mp4 is
            # sent as image_url ("The image format is not supported").
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
        fields = self._get_media_fields(access_token, post_id)
        values, errors = fetch_insights_safe(
            self._request,
            platform=self.platform_name,
            endpoint=f"{BASE_URL}/{post_id}/insights",
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
        ig_user_id = self.credentials.get("ig_user_id", "me")
        since = int(date_range[0].timestamp())
        until = int(date_range[1].timestamp())
        values, errors = fetch_insights_safe(
            self._request,
            platform=self.platform_name,
            endpoint=f"{BASE_URL}/{ig_user_id}/insights",
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
        profile = self._get_profile_fields(access_token, ig_user_id)
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

    def _get_profile_fields(self, access_token: str, ig_user_id: str) -> dict | None:
        # Returns ``None`` on failure so callers can distinguish a failed fetch
        # from a successful one with no data (a genuine 0).
        try:
            return self._request(
                "GET",
                f"{BASE_URL}/{ig_user_id}",
                access_token=access_token,
                params={"fields": "id,username,name,profile_picture_url,followers_count,media_count"},
            ).json()
        except APIError as exc:
            logger.debug("Instagram profile fields unavailable for %s: %s", ig_user_id, exc)
            return None

    def _get_media_fields(self, access_token: str, media_id: str) -> dict:
        try:
            return self._request(
                "GET",
                f"{BASE_URL}/{media_id}",
                access_token=access_token,
                params={"fields": ",".join(INSTAGRAM_MEDIA_FIELDS)},
            ).json()
        except APIError as exc:
            logger.debug("Instagram media fields unavailable for %s: %s", media_id, exc)
            return {}
