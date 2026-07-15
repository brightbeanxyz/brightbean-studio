"""YouTube Data API v3 provider."""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import OAuthError, PublishError
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

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
API_BASE = "https://www.googleapis.com/youtube/v3"
UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"
ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"

# YouTube Analytics caps a ``filters=video==<id>,<id>,...`` list at 500 IDs
# per request. Larger inputs to :meth:`YouTubeProvider.get_post_analytics`
# are split into multiple requests transparently.
_ANALYTICS_VIDEO_FILTER_CHUNK = 500


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
        scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
        if self.include_analytics_scopes:
            scopes.extend(self.analytics_only_scopes)
        return scopes

    @property
    def analytics_only_scopes(self) -> list[str]:
        # Required for the YouTube Analytics API (watch time, retention,
        # demographics). Only requested when analytics is enabled so the
        # Google OAuth consent screen doesn't list it when not needed.
        return ["https://www.googleapis.com/auth/yt-analytics.readonly"]

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

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
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

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
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
        """Per-video counts from the YouTube Data API ``videos.list?part=statistics``.

        Only the counts the Data API exposes: views, likes, comments. Watch
        time, average view percentage, and shares are intentionally absent
        — those live on the Analytics API and are batched per channel by
        :meth:`get_post_analytics`.
        """
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

    def get_account_metrics(self, access_token: str, date_range: tuple[datetime, datetime]) -> AccountMetrics:
        """Channel-level metrics from the YouTube Analytics API.

        Fetches the metrics the YouTube Data API can't provide per-video:
        watch time, average view %, subscribers gained, and shares.
        Views/likes/comments come from per-post snapshots so the main page
        stays consistent with the per-post drawer; shares is the exception
        because ``videos.list?part=statistics`` exposes no shareCount field.

        Per-video equivalents of the channel-level watch-time / avg-view-% /
        shares triple come from :meth:`get_post_analytics`, which calls the
        same ``/reports`` endpoint with ``dimensions=video`` and the video
        IDs as a filter.

        Callers must pass a single-day ``date_range`` — Analytics returns one
        aggregated row across [startDate, endDate], and the sync layer writes
        it as a single day's snapshot. Larger ranges would silently collapse
        into one cell.

        Requires the ``yt-analytics.readonly`` scope. The YouTube Analytics
        API typically lags 1–2 days behind real-time.
        """
        start_date = date_range[0].date().isoformat()
        end_date = date_range[1].date().isoformat()
        resp = self._request(
            "GET",
            f"{ANALYTICS_BASE}/reports",
            access_token=access_token,
            params={
                "ids": "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": "estimatedMinutesWatched,averageViewPercentage,subscribersGained,shares",
            },
        )
        body = resp.json()
        headers = body.get("columnHeaders", [])
        rows = body.get("rows", [])
        if not rows or not rows[0]:
            return AccountMetrics()

        index = {col.get("name", ""): i for i, col in enumerate(headers)}
        row = rows[0]

        def _value_or_none(name: str) -> float | None:
            """Return float value if Analytics returned the column (even 0), else None.

            Distinguishes "metric not in the response" (None) from "metric
            returned 0" (0.0). Falsy-zero guards downstream incorrectly drop
            real 0-value days otherwise.
            """
            i = index.get(name)
            if i is None or i >= len(row) or row[i] is None:
                return None
            try:
                return float(row[i])
            except (TypeError, ValueError):
                return None

        extra: dict = {}
        for api_key, catalog_key in (
            ("estimatedMinutesWatched", "watch_time"),
            ("averageViewPercentage", "avg_view_pct"),
            ("subscribersGained", "subscribers"),
            ("shares", "shares"),
        ):
            v = _value_or_none(api_key)
            if v is not None:
                extra[catalog_key] = v
        return AccountMetrics(extra=extra)

    def get_post_analytics(
        self,
        access_token: str,
        post_ids: list[str],
        date_range: tuple[datetime, datetime],
    ) -> dict[str, PostMetrics]:
        """Per-video metrics from the YouTube Analytics API, batched.

        Returns ``{video_id: PostMetrics}`` populated with ``extra``:
        ``watch_time`` (estimatedMinutesWatched), ``avg_view_pct``
        (averageViewPercentage), and ``shares``. These are the per-video
        metrics the Data API v3 ``statistics`` part can't provide — the
        catalog keys match the ones :func:`apps.analytics.tasks._post_metrics_to_dict`
        reads from ``PostMetrics.extra`` via ``_GENERIC_POST_EXTRA_KEYS``.

        One ``/reports`` request covers every video in ``post_ids`` via
        ``dimensions=video`` and ``filters=video==<id>,<id>,...``. The
        endpoint caps the filter at 500 IDs per request, so longer inputs
        are split into multiple calls and merged.

        Videos that have no activity in the window are omitted from the
        Analytics response and will be absent from the returned dict —
        callers should treat that as "no data" rather than "all zeros".

        Requires the ``yt-analytics.readonly`` scope (same as
        :meth:`get_account_metrics`). The Analytics API typically lags
        1–2 days behind real-time.
        """
        if not post_ids:
            return {}

        start_date = date_range[0].date().isoformat()
        end_date = date_range[1].date().isoformat()
        result: dict[str, PostMetrics] = {}

        for offset in range(0, len(post_ids), _ANALYTICS_VIDEO_FILTER_CHUNK):
            chunk = post_ids[offset : offset + _ANALYTICS_VIDEO_FILTER_CHUNK]
            resp = self._request(
                "GET",
                f"{ANALYTICS_BASE}/reports",
                access_token=access_token,
                params={
                    "ids": "channel==MINE",
                    "startDate": start_date,
                    "endDate": end_date,
                    "metrics": "estimatedMinutesWatched,averageViewPercentage,shares",
                    "dimensions": "video",
                    "filters": f"video=={','.join(chunk)}",
                },
            )
            body = resp.json()
            headers = body.get("columnHeaders", []) or []
            rows = body.get("rows", []) or []
            index = {col.get("name", ""): i for i, col in enumerate(headers)}
            video_idx = index.get("video")
            if video_idx is None:
                continue

            # API column → indexes used below. Pre-computed once per chunk so
            # the inner row loop is a flat lookup. Same semantics as the
            # closure in ``get_account_metrics``: missing column → key
            # omitted; present column with a 0 → 0 is preserved (not dropped
            # as falsy).
            watch_idx = index.get("estimatedMinutesWatched")
            avp_idx = index.get("averageViewPercentage")
            shares_idx = index.get("shares")

            for row in rows:
                if video_idx >= len(row):
                    continue
                video_id = row[video_idx]
                if not video_id:
                    continue

                extra: dict = {}
                for catalog_key, i in (("watch_time", watch_idx), ("avg_view_pct", avp_idx)):
                    if i is None or i >= len(row) or row[i] is None:
                        continue
                    try:
                        extra[catalog_key] = float(row[i])
                    except (TypeError, ValueError):
                        continue

                # ``shares`` has a dedicated ``PostMetrics`` field; the catalog
                # mapper (``_post_metrics_to_dict``) reads it from there, not
                # from ``extra``. Cast to int to match the field type.
                shares_value: int | None = None
                if shares_idx is not None and shares_idx < len(row) and row[shares_idx] is not None:
                    try:
                        shares_value = int(float(row[shares_idx]))
                    except (TypeError, ValueError):
                        shares_value = None

                if extra or shares_value is not None:
                    result[video_id] = PostMetrics(shares=shares_value or 0, extra=extra)
        return result

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
