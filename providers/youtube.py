"""YouTube Data API v3 provider."""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import OAuthError, PublishError
from .types import (
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

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://www.googleapis.com/youtube/v3"
UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"


class YouTubeProvider(SocialProvider):
    """YouTube Data API v3 provider using Google OAuth 2.0."""

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "YouTube"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 5000

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.VIDEO, PostType.SHORT]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.MP4, MediaType.MOV]

    @property
    def required_scopes(self) -> list[str]:
        return [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=600,
            requests_per_day=10000,
            publish_per_day=6,
            extra={"quota_units_per_day": 10000, "upload_cost_units": 1600},
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(self.required_scopes),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "code": code,
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"YouTube token exchange failed: {body}",
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
                "refresh_token": refresh_token,
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "grant_type": "refresh_token",
            },
        )
        body = resp.json()
        if "access_token" not in body:
            raise OAuthError(
                f"YouTube token refresh failed: {body}",
                platform=self.platform_name,
                raw_response=body,
            )
        return OAuthTokens(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token", refresh_token),
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
            f"{API_BASE}/channels",
            access_token=access_token,
            params={"part": "snippet,statistics", "mine": "true"},
        )
        body = resp.json()
        items = body.get("items", [])
        if not items:
            return AccountProfile(platform_id="", name="Unknown")

        channel = items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})
        thumbnails = snippet.get("thumbnails", {})
        avatar = thumbnails.get("default", {}).get("url") or thumbnails.get("medium", {}).get("url")
        return AccountProfile(
            platform_id=channel["id"],
            name=snippet.get("title", ""),
            handle=snippet.get("customUrl"),
            avatar_url=avatar,
            follower_count=int(stats.get("subscriberCount", 0)),
            extra={
                "view_count": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            },
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        if content.post_type not in (PostType.VIDEO, PostType.SHORT):
            raise PublishError(
                "YouTube only supports VIDEO and SHORT post types",
                platform=self.platform_name,
            )

        title = content.title or content.text or ""
        description = content.description or content.text or ""

        # Shorts: add #Shorts tag if not already present
        if content.post_type == PostType.SHORT and "#Shorts" not in title:
            title = f"{title} #Shorts".strip()

        privacy_status = content.extra.get("privacy_status", "public")
        made_for_kids = content.extra.get("self_declared_made_for_kids", False)
        category_id = content.extra.get("category_id", "22")  # 22 = People & Blogs
        tags = content.extra.get("tags", [])

        metadata = {
            "snippet": {
                "title": title[:100],
                "description": description[: self.max_caption_length],
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Step 1: Initiate resumable upload
        init_resp = self._request(
            "POST",
            f"{UPLOAD_BASE}/videos",
            access_token=access_token,
            params={"uploadType": "resumable", "part": "snippet,status"},
            json=metadata,
        )
        upload_uri = init_resp.headers.get("Location")
        if not upload_uri:
            raise PublishError(
                "YouTube did not return a resumable upload URI",
                platform=self.platform_name,
            )

        # Step 2: Upload video binary
        if content.media_files:
            video_path = content.media_files[0]
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_resp = self._request(
                "PUT",
                upload_uri,
                headers={
                    "Content-Type": "video/*",
                    "Content-Length": str(len(video_data)),
                },
                data=video_data,
                timeout=300.0,
            )
            upload_body = upload_resp.json()
            video_id = upload_body.get("id", "")

            # Step 3 (optional): upload custom thumbnail
            thumbnail_path = content.extra.get("thumbnail_file")
            if video_id and thumbnail_path:
                try:
                    with open(thumbnail_path, "rb") as tf:
                        thumb_data = tf.read()
                    # Guess content type from extension
                    ext = thumbnail_path.lower().rsplit(".", 1)[-1]
                    thumb_ct = "image/png" if ext == "png" else "image/jpeg"
                    self._request(
                        "POST",
                        f"{UPLOAD_BASE}/thumbnails/set",
                        access_token=access_token,
                        params={"videoId": video_id, "uploadType": "media"},
                        headers={
                            "Content-Type": thumb_ct,
                            "Content-Length": str(len(thumb_data)),
                        },
                        data=thumb_data,
                        timeout=60.0,
                    )
                except Exception:
                    logger.exception("Custom thumbnail upload failed for video %s", video_id)

            return PublishResult(
                platform_post_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
                extra=upload_body,
            )

        raise PublishError(
            "No video file provided (media_files required)",
            platform=self.platform_name,
        )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        resp = self._request(
            "POST",
            f"{API_BASE}/commentThreads",
            access_token=access_token,
            params={"part": "snippet"},
            json={
                "snippet": {
                    "videoId": post_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": text,
                        }
                    },
                }
            },
        )
        body = resp.json()
        comment_id = body.get("id", "")
        return CommentResult(
            platform_comment_id=comment_id,
            extra=body,
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        # Resolve channel ID
        ch_resp = self._request(
            "GET",
            f"{API_BASE}/channels",
            access_token=access_token,
            params={"part": "id", "mine": "true"},
        )
        ch_items = ch_resp.json().get("items", [])
        if not ch_items:
            return []
        channel_id = ch_items[0]["id"]

        messages: list[InboxMessage] = []
        page_token: str | None = None

        while True:
            params: dict = {
                "part": "snippet,replies",
                "allThreadsRelatedToChannelId": channel_id,
                "maxResults": 100,
                "order": "time",
            }
            if page_token:
                params["pageToken"] = page_token

            resp = self._request(
                "GET",
                f"{API_BASE}/commentThreads",
                access_token=access_token,
                params=params,
            )
            body = resp.json()

            for thread in body.get("items", []):
                top_snippet = thread["snippet"]["topLevelComment"]["snippet"]
                published = datetime.fromisoformat(top_snippet["publishedAt"].replace("Z", "+00:00"))

                if since and published < since:
                    continue

                top_comment_id = thread["snippet"]["topLevelComment"]["id"]
                video_id = top_snippet["videoId"]

                messages.append(
                    InboxMessage(
                        platform_message_id=top_comment_id,
                        sender_id=top_snippet.get("authorChannelId", {}).get("value", ""),
                        sender_name=top_snippet.get("authorDisplayName", ""),
                        text=top_snippet.get("textDisplay", ""),
                        timestamp=published,
                        message_type="comment",
                        extra={
                            "video_id": video_id,
                            "comment_id": top_comment_id,
                            "sender_avatar_url": top_snippet.get("authorProfileImageUrl", ""),
                        },
                    )
                )

                # Include reply comments in the thread
                for reply in thread.get("replies", {}).get("comments", []):
                    r_snippet = reply["snippet"]
                    r_published = datetime.fromisoformat(r_snippet["publishedAt"].replace("Z", "+00:00"))
                    if since and r_published < since:
                        continue
                    messages.append(
                        InboxMessage(
                            platform_message_id=reply["id"],
                            sender_id=r_snippet.get("authorChannelId", {}).get("value", ""),
                            sender_name=r_snippet.get("authorDisplayName", ""),
                            text=r_snippet.get("textDisplay", ""),
                            timestamp=r_published,
                            message_type="comment",
                            extra={
                                "video_id": video_id,
                                "comment_id": reply["id"],
                                "parent_id": top_comment_id,
                                "sender_avatar_url": r_snippet.get("authorProfileImageUrl", ""),
                            },
                        )
                    )

            page_token = body.get("nextPageToken")
            if not page_token:
                break

        return messages

    def reply_to_message(self, access_token: str, message_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        resp = self._request(
            "POST",
            f"{API_BASE}/comments",
            access_token=access_token,
            params={"part": "snippet"},
            json={
                "snippet": {
                    "parentId": message_id,
                    "textOriginal": text,
                }
            },
        )
        body = resp.json()
        return ReplyResult(platform_message_id=body.get("id", ""), extra=body)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        resp = self._request(
            "GET",
            f"{API_BASE}/videos",
            access_token=access_token,
            params={"part": "statistics", "id": post_id},
        )
        body = resp.json()
        items = body.get("items", [])
        if not items:
            return PostMetrics()

        stats = items[0].get("statistics", {})
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))
        return PostMetrics(
            video_views=views,
            likes=likes,
            comments=comments,
            engagements=likes + comments,
            extra={
                "favorite_count": int(stats.get("favoriteCount", 0)),
            },
        )

    def get_recent_post_metrics(
        self, access_token: str, account_platform_id: str, limit: int = 20
    ) -> list[PostMetrics]:
        # Step 1: Search for the user's recent videos
        search_resp = self._request(
            "GET",
            f"{API_BASE}/search",
            access_token=access_token,
            params={
                "forMine": "true",
                "type": "video",
                "order": "date",
                "maxResults": limit,
                "part": "id",
            },
        )
        video_ids = [
            item["id"]["videoId"]
            for item in search_resp.json().get("items", [])
            if "videoId" in item.get("id", {})
        ]

        if not video_ids:
            return []

        # Step 2: Batch fetch statistics and snippets
        videos_resp = self._request(
            "GET",
            f"{API_BASE}/videos",
            access_token=access_token,
            params={
                "id": ",".join(video_ids),
                "part": "statistics,snippet",
            },
        )

        results = []
        for item in videos_resp.json().get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            video_id = item["id"]

            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))
            comments_count = int(stats.get("commentCount", 0))

            results.append(PostMetrics(
                video_views=views,
                likes=likes,
                comments=comments_count,
                engagements=likes + comments_count,
                impressions=views,
                extra={
                    "platform_post_id": video_id,
                    "post_url": f"https://www.youtube.com/watch?v={video_id}",
                    "post_text": snippet.get("title", ""),
                    "posted_at": snippet.get("publishedAt", ""),
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
                REVOKE_URL,
                params={"token": access_token},
            )
            return True
        except Exception:
            logger.exception("Failed to revoke YouTube token")
            return False
