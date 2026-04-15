"""TikTok Content Posting API provider."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import OAuthError, PublishError
from .types import (
    AccountProfile,
    AuthType,
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

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
API_BASE = "https://open.tiktokapis.com/v2"

DEFAULT_PRIVACY_LEVEL = "PUBLIC_TO_EVERYONE"
VALID_PRIVACY_LEVELS = frozenset(
    {
        "PUBLIC_TO_EVERYONE",
        "MUTUAL_FOLLOW_FRIENDS",
        "FOLLOWER_OF_CREATOR",
        "SELF_ONLY",
    }
)


class TikTokProvider(SocialProvider):
    """TikTok Content Posting API provider using OAuth 2.0."""

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "TikTok"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 2200

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.VIDEO]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.MP4, MediaType.MOV]

    @property
    def required_scopes(self) -> list[str]:
        return ["user.info.basic", "video.publish", "video.upload", "comment.list", "comment.list.manage"]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=5000,
            publish_per_day=5,
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_key": self.credentials["client_key"],
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
                "client_key": self.credentials["client_key"],
                "client_secret": self.credentials["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"TikTok token exchange failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        return OAuthTokens(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            expires_in=body.get("expires_in"),
            scope=body.get("scope"),
            raw_response=body,
        )

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_key": self.credentials["client_key"],
                "client_secret": self.credentials["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"TikTok token refresh failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        return OAuthTokens(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            expires_in=body.get("expires_in"),
            scope=body.get("scope"),
            raw_response=body,
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        resp = self._request(
            "GET",
            f"{API_BASE}/user/info/",
            access_token=access_token,
            params={
                "fields": "open_id,union_id,avatar_url,display_name,follower_count",
            },
        )
        body = resp.json()
        user = body.get("data", {}).get("user", {})
        return AccountProfile(
            platform_id=user.get("open_id", ""),
            name=user.get("display_name", ""),
            avatar_url=user.get("avatar_url"),
            follower_count=user.get("follower_count", 0),
            extra={"union_id": user.get("union_id")},
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        if content.post_type != PostType.VIDEO:
            raise PublishError(
                "TikTok only supports VIDEO posts",
                platform=self.platform_name,
            )

        privacy_level = content.extra.get("privacy_level", DEFAULT_PRIVACY_LEVEL)
        if privacy_level not in VALID_PRIVACY_LEVELS:
            raise PublishError(
                f"Invalid privacy_level '{privacy_level}'. Must be one of {sorted(VALID_PRIVACY_LEVELS)}",
                platform=self.platform_name,
            )

        # Determine upload source strategy
        if content.media_urls:
            return self._publish_pull_from_url(access_token, content, privacy_level)
        if content.media_files:
            return self._publish_file_upload(access_token, content, privacy_level)
        raise PublishError(
            "No video source provided (media_urls or media_files required)",
            platform=self.platform_name,
        )

    def _publish_pull_from_url(
        self,
        access_token: str,
        content: PublishContent,
        privacy_level: str,
    ) -> PublishResult:
        """Publish using PULL_FROM_URL source."""
        payload = {
            "post_info": {
                "title": (content.title or content.text or "")[: self.max_caption_length],
                "privacy_level": privacy_level,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": content.media_urls[0],
            },
        }
        resp = self._request(
            "POST",
            f"{API_BASE}/post/publish/video/init/",
            access_token=access_token,
            json=payload,
        )
        body = resp.json()
        publish_id = body.get("data", {}).get("publish_id", "")
        return PublishResult(
            platform_post_id=publish_id,
            extra=body.get("data", {}),
        )

    def _publish_file_upload(
        self,
        access_token: str,
        content: PublishContent,
        privacy_level: str,
    ) -> PublishResult:
        """Publish using FILE_UPLOAD source (two-step)."""
        # Step 1: Initialize upload
        payload = {
            "post_info": {
                "title": (content.title or content.text or "")[: self.max_caption_length],
                "privacy_level": privacy_level,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
            },
        }
        init_resp = self._request(
            "POST",
            f"{API_BASE}/post/publish/video/init/",
            access_token=access_token,
            json=payload,
        )
        init_body = init_resp.json()
        upload_url = init_body.get("data", {}).get("upload_url")
        publish_id = init_body.get("data", {}).get("publish_id", "")

        if not upload_url:
            raise PublishError(
                "TikTok did not return an upload_url",
                platform=self.platform_name,
                raw_response=init_body,
            )

        # Step 2: Upload video binary
        video_path = content.media_files[0]
        with open(video_path, "rb") as f:
            video_data = f.read()

        self._request(
            "PUT",
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(video_data)),
            },
            data=video_data,
            timeout=120.0,
        )

        return PublishResult(
            platform_post_id=publish_id,
            extra=init_body.get("data", {}),
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        # Fetch recent videos
        resp = self._request(
            "POST",
            f"{API_BASE}/video/list/",
            access_token=access_token,
            json={"max_count": 20},
        )
        videos = resp.json().get("data", {}).get("videos", [])

        messages: list[InboxMessage] = []

        for video in videos:
            video_id = video.get("id", "")
            if not video_id:
                continue

            cursor = 0
            while True:
                c_resp = self._request(
                    "POST",
                    f"{API_BASE}/comment/list/",
                    access_token=access_token,
                    json={"video_id": video_id, "max_count": 50, "cursor": cursor},
                )
                c_data = c_resp.json().get("data", {})
                comments = c_data.get("comments", [])
                if not comments:
                    break

                for comment in comments:
                    created = datetime.fromtimestamp(comment.get("create_time", 0), tz=UTC)
                    if since and created < since:
                        continue

                    user = comment.get("user", {})
                    comment_id = comment.get("id", "")

                    messages.append(
                        InboxMessage(
                            platform_message_id=comment_id,
                            sender_id=user.get("open_id", user.get("unique_id", "")),
                            sender_name=user.get("display_name", ""),
                            text=comment.get("text", ""),
                            timestamp=created,
                            message_type="comment",
                            extra={
                                "video_id": video_id,
                                "comment_id": comment_id,
                                "sender_avatar_url": user.get("avatar_url", ""),
                            },
                        )
                    )

                if not c_data.get("has_more", False):
                    break
                cursor = c_data.get("cursor", 0)

        return messages

    def reply_to_message(self, access_token: str, message_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        extra = extra or {}
        video_id = extra.get("video_id", "")
        if not video_id:
            raise PublishError(
                "video_id required in extra for TikTok reply",
                platform=self.platform_name,
            )

        resp = self._request(
            "POST",
            f"{API_BASE}/comment/reply/create/",
            access_token=access_token,
            json={
                "video_id": video_id,
                "comment_id": message_id,
                "text": text,
            },
        )
        data = resp.json().get("data", {})
        return ReplyResult(
            platform_message_id=data.get("comment_id", ""),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Analytics — recent post metrics
    # ------------------------------------------------------------------

    def get_recent_post_metrics(
        self, access_token: str, account_platform_id: str, limit: int = 20
    ) -> list[PostMetrics]:
        resp = self._request(
            "POST",
            f"{API_BASE}/video/list/",
            access_token=access_token,
            json={
                "max_count": limit,
            },
        )
        body = resp.json()
        videos = body.get("data", {}).get("videos", [])

        results = []
        for video in videos:
            likes = video.get("like_count", 0)
            comments_count = video.get("comment_count", 0)
            shares = video.get("share_count", 0)
            views = video.get("view_count", 0)

            # Convert Unix timestamp to ISO 8601
            create_time = video.get("create_time", 0)
            posted_at = datetime.fromtimestamp(create_time, tz=UTC).isoformat()

            results.append(PostMetrics(
                likes=likes,
                comments=comments_count,
                shares=shares,
                video_views=views,
                engagements=likes + comments_count + shares,
                impressions=views,
                extra={
                    "platform_post_id": video.get("id", ""),
                    "post_url": video.get("share_url", ""),
                    "post_text": video.get("title", ""),
                    "posted_at": posted_at,
                    "post_type": "video",
                },
            ))

        return results

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def revoke_token(self, access_token: str) -> bool:
        try:
            self._request(
                "POST",
                f"{API_BASE}/oauth/revoke/",
                data={
                    "client_key": self.credentials["client_key"],
                    "token": access_token,
                },
            )
            return True
        except Exception:
            logger.exception("Failed to revoke TikTok token")
            return False
