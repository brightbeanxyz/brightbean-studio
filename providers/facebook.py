"""Facebook Graph API provider implementation."""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlencode, urlparse

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

# Facebook caps the ``attached_media`` array on a single feed post. Larger sets
# must use the album-creation flow, which this provider does not implement.
FACEBOOK_MAX_ATTACHED_MEDIA = 10
# Extension heuristic for spotting video URLs, mirroring the per-item checks in
# the Instagram / Threads carousel providers.
VIDEO_URL_SUFFIXES = (".mp4", ".mov")


class FacebookProvider(SocialProvider):
    """Facebook Graph API v21.0 provider."""

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
        return "Facebook"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 63206

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.LINK]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4, MediaType.MOV]

    @property
    def required_scopes(self) -> list[str]:
        scopes = [
            "business_management",
            "pages_show_list",
            "pages_manage_posts",
            "pages_read_engagement",
            "pages_read_user_content",
            "pages_manage_metadata",
            "pages_messaging",
        ]
        if self.include_analytics_scopes:
            scopes.extend(self.analytics_only_scopes)
        return scopes

    @property
    def analytics_only_scopes(self) -> list[str]:
        # ``read_insights`` is required for page-level account insights
        # (page_impressions_unique, page_daily_follows). Only requested in
        # OAuth when this platform's analytics is enabled.
        return ["read_insights"]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=4800,
            publish_per_day=4800,
            extra={"posts_per_24h_per_page": 4800},
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
                "Facebook token exchange failed",
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
        """Exchange a short-lived token for a long-lived token.

        Facebook does not use traditional refresh tokens. Instead, you
        exchange a short-lived user token for a long-lived one (valid ~60 days).
        """
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
                "Facebook long-lived token exchange failed",
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
        resp = self._request(
            "GET",
            f"{BASE_URL}/me",
            access_token=access_token,
            params={"fields": "id,name,picture"},
        )
        data = resp.json()
        avatar = None
        if "picture" in data and "data" in data["picture"]:
            avatar = data["picture"]["data"].get("url")
        return AccountProfile(
            platform_id=data["id"],
            name=data.get("name", ""),
            avatar_url=avatar,
            extra=data,
        )

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def get_user_pages(self, access_token: str) -> list[dict]:
        """Fetch the pages that the authenticated user manages.

        Returns a list of dicts each containing id, name, access_token,
        category, and picture.
        """
        resp = self._request(
            "GET",
            f"{BASE_URL}/me/accounts",
            access_token=access_token,
            params={"fields": "id,name,access_token,category,picture"},
        )
        data = resp.json()
        if "error" in data:
            logger.error("Facebook /me/accounts error: %s", data["error"])
            raise APIError(
                f"Failed to fetch pages: {data['error'].get('message', 'Unknown error')}",
                platform=self.platform_name,
                raw_response=data,
            )
        logger.debug("Facebook /me/accounts returned %d pages", len(data.get("data", [])))
        pages: list[dict] = []
        for page in data.get("data", []):
            picture_url = None
            if "picture" in page and "data" in page["picture"]:
                picture_url = page["picture"]["data"].get("url")
            pages.append(
                {
                    "id": page["id"],
                    "name": page.get("name", ""),
                    "access_token": page.get("access_token", ""),
                    "category": page.get("category", ""),
                    "picture": picture_url,
                }
            )
        return pages

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        page_id = content.extra.get("page_id")
        if not page_id:
            raise PublishError(
                "page_id is required in content.extra for Facebook publishing",
                platform=self.platform_name,
            )

        if content.post_type == PostType.IMAGE and content.media_urls:
            return self._publish_photo(access_token, page_id, content)
        if content.post_type == PostType.VIDEO and content.media_urls:
            return self._publish_video(access_token, page_id, content)
        return self._publish_text_or_link(access_token, page_id, content)

    def _publish_text_or_link(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        payload: dict = {"message": content.text}
        if content.link_url:
            payload["link"] = content.link_url
        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/feed",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        return PublishResult(
            platform_post_id=data["id"],
            url=f"https://www.facebook.com/{data['id']}",
            extra=data,
        )

    def _publish_photo(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        if len(content.media_urls) > 1:
            return self._publish_multi_photo(access_token, page_id, content)

        payload: dict = {"url": content.media_urls[0]}
        if content.text:
            payload["message"] = content.text
        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/photos",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        return PublishResult(
            platform_post_id=data["id"],
            url=f"https://www.facebook.com/{data.get('post_id', data['id'])}",
            extra=data,
        )

    def _publish_multi_photo(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        urls = content.media_urls

        # Pre-staging guards: fail before any network call so we never leave
        # orphaned unpublished photos behind for an obviously invalid request.
        if len(urls) > FACEBOOK_MAX_ATTACHED_MEDIA:
            raise PublishError(
                f"Facebook multi-photo posts support at most {FACEBOOK_MAX_ATTACHED_MEDIA} photos (got {len(urls)})",
                platform=self.platform_name,
            )
        if any(self._is_video_url(url) for url in urls):
            raise PublishError(
                "Facebook multi-photo posts support images only; post videos separately",
                platform=self.platform_name,
            )

        photo_ids: list[str] = []
        try:
            for url in urls:
                data = self._request(
                    "POST",
                    f"{BASE_URL}/{page_id}/photos",
                    access_token=access_token,
                    json={"url": url, "published": False},
                ).json()
                photo_id = data.get("id")
                if not photo_id:
                    raise PublishError(
                        "Failed to stage Facebook photo for multi-photo post",
                        platform=self.platform_name,
                        raw_response=data,
                    )
                photo_ids.append(photo_id)

            payload: dict = {
                "attached_media": [{"media_fbid": photo_id} for photo_id in photo_ids],
            }
            if content.text:
                payload["message"] = content.text

            data = self._request(
                "POST",
                f"{BASE_URL}/{page_id}/feed",
                access_token=access_token,
                json=payload,
            ).json()
            post_id = data.get("id")
            if not post_id:
                raise PublishError(
                    "Failed to publish Facebook multi-photo post",
                    platform=self.platform_name,
                    raw_response=data,
                )
        except Exception:
            # Best-effort: remove any photos already staged as unpublished so a
            # partial failure (or a retry by the publisher) doesn't accumulate
            # orphaned media on the page.
            self._delete_staged_photos(access_token, photo_ids)
            raise

        return PublishResult(
            platform_post_id=post_id,
            url=f"https://www.facebook.com/{post_id}",
            extra={**data, "photo_ids": photo_ids},
        )

    @staticmethod
    def _is_video_url(url: str) -> bool:
        """Heuristically detect a video URL by file extension.

        Uses the URL path only so presigned query strings (R2/S3) don't defeat
        the check.
        """
        return urlparse(url).path.lower().endswith(VIDEO_URL_SUFFIXES)

    def _delete_staged_photos(self, access_token: str, photo_ids: list[str]) -> None:
        """Best-effort cleanup of unpublished photos staged for a multi-photo post.

        Swallows errors so cleanup never masks the original publish failure.
        """
        for photo_id in photo_ids:
            try:
                self._request("DELETE", f"{BASE_URL}/{photo_id}", access_token=access_token)
            except Exception:
                logger.warning("Failed to clean up staged Facebook photo %s", photo_id)

    def _publish_video(self, access_token: str, page_id: str, content: PublishContent) -> PublishResult:
        payload: dict = {"file_url": content.media_urls[0]}
        if content.text:
            payload["description"] = content.text
        resp = self._request(
            "POST",
            f"{BASE_URL}/{page_id}/videos",
            access_token=access_token,
            json=payload,
        )
        data = resp.json()
        return PublishResult(
            platform_post_id=data["id"],
            url=f"https://www.facebook.com/{data['id']}",
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
            json={"message": text},
        )
        data = resp.json()
        return CommentResult(platform_comment_id=data["id"], extra=data)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        metrics = [
            "post_impressions",
            "post_engaged_users",
            "post_clicks",
            "post_reactions_by_type_total",
        ]
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

        reactions = values.get("post_reactions_by_type_total", {})
        total_likes = reactions.get("like", 0) + reactions.get("love", 0) if isinstance(reactions, dict) else 0

        return PostMetrics(
            impressions=values.get("post_impressions", 0),
            engagements=values.get("post_engaged_users", 0),
            clicks=values.get("post_clicks", 0),
            likes=total_likes,
            extra={"raw_insights": values},
        )

    def get_account_metrics(self, access_token: str, date_range: tuple[datetime, datetime]) -> AccountMetrics:
        page_id = self.credentials.get("page_id", "me")
        metrics = ["page_impressions", "page_engaged_users", "page_fans"]
        resp = self._request(
            "GET",
            f"{BASE_URL}/{page_id}/insights",
            access_token=access_token,
            params={
                "metric": ",".join(metrics),
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
            impressions=values.get("page_impressions", 0),
            reach=values.get("page_engaged_users", 0),
            followers=values.get("page_fans", 0),
            extra={"raw_insights": values},
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        page_id = self.credentials.get("page_id", "me")
        params: dict = {}
        if since:
            params["since"] = int(since.timestamp())

        resp = self._request(
            "GET",
            f"{BASE_URL}/{page_id}/conversations",
            access_token=access_token,
            params=params,
        )
        conversations = resp.json().get("data", [])

        messages: list[InboxMessage] = []
        for convo in conversations:
            convo_id = convo["id"]
            msg_resp = self._request(
                "GET",
                f"{BASE_URL}/{convo_id}/messages",
                access_token=access_token,
                params={"fields": "id,message,from,created_time"},
            )
            for msg in msg_resp.json().get("data", []):
                sender = msg.get("from", {})
                messages.append(
                    InboxMessage(
                        platform_message_id=msg["id"],
                        sender_id=sender.get("id", ""),
                        sender_name=sender.get("name", ""),
                        text=msg.get("message", ""),
                        timestamp=datetime.fromisoformat(msg["created_time"].replace("+0000", "+00:00")),
                        message_type="dm",
                        extra={"conversation_id": convo_id},
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
    # Token management
    # ------------------------------------------------------------------

    def revoke_token(self, access_token: str) -> bool:
        try:
            self._request(
                "DELETE",
                f"{BASE_URL}/me/permissions",
                access_token=access_token,
            )
            return True
        except APIError:
            logger.warning("Failed to revoke Facebook token")
            return False
