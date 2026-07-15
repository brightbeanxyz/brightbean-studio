"""LinkedIn Marketing API v2 provider implementation."""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import time
from datetime import UTC, datetime
from urllib.parse import quote, urlencode

import httpx

from .base import SocialProvider
from .exceptions import APIError, OAuthError, PublishError
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

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
REVOKE_URL = "https://www.linkedin.com/oauth/v2/revoke"
API_BASE = "https://api.linkedin.com"

# Required headers for LinkedIn REST API.
# LinkedIn sunsets versioned APIs after ~1 year; bump LinkedIn-Version
# to the latest YYYYMM at https://learn.microsoft.com/en-us/linkedin/marketing/versioning
# before the current value falls out of support.
LINKEDIN_HEADERS = {
    "LinkedIn-Version": "202604",
    "X-Restli-Protocol-Version": "2.0.0",
}


def _encode_urn(urn: str) -> str:
    """Percent-encode a LinkedIn URN for use as a URL path segment.

    LinkedIn rejects path-variable URNs unless their colons (and parens/commas
    in composite comment URNs) are percent-encoded. Per the Posts API docs:
    "urn:li:ugcPost:12345 becomes urn%3Ali%3AugcPost%3A12345."
    """
    return quote(urn, safe="")


class LinkedInProvider(SocialProvider):
    """LinkedIn Marketing API v2 provider."""

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "LinkedIn"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 3000

    @property
    def supported_post_types(self) -> list[PostType]:
        return [
            PostType.TEXT,
            PostType.IMAGE,
            PostType.VIDEO,
            PostType.LINK,
            PostType.ARTICLE,
            PostType.POLL,
        ]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4]

    @property
    def required_scopes(self) -> list[str]:
        return [
            "w_member_social",
            "r_member_social",
            "w_organization_social",
            "r_organization_social",
        ]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=200,
            requests_per_day=100,
            publish_per_day=100,
            extra={
                "member_posts_per_day": 100,
                "company_shares_per_day": 100,
            },
        )

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        params = {
            "response_type": "code",
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(self.required_scopes),
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
        if "access_token" not in data:
            raise OAuthError(
                "LinkedIn token exchange failed",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            raw_response=data,
        )

    def refresh_token(self, refresh_token_value: str) -> OAuthTokens:
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_value,
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = resp.json()
        if "access_token" not in data:
            raise OAuthError(
                "LinkedIn token refresh failed",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            raw_response=data,
        )

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        resp = self._request(
            "GET",
            f"{API_BASE}/v2/me",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
        )
        data = resp.json()
        first = data.get("localizedFirstName", "")
        last = data.get("localizedLastName", "")
        name = f"{first} {last}".strip() or data.get("vanityName", "")
        return AccountProfile(
            platform_id=data.get("id", ""),
            name=name,
            avatar_url=data.get("profilePicture", {}).get("displayImage"),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        author = content.extra.get("author")
        if not author:
            # Derive from profile
            profile = self.get_profile(access_token)
            author = f"urn:li:person:{profile.platform_id}"

        if content.post_type == PostType.IMAGE and (content.media_files or content.media_urls):
            return self._publish_image_post(access_token, author, content)
        if content.post_type == PostType.VIDEO and (content.media_files or content.media_urls):
            return self._publish_video_post(access_token, author, content)
        if content.post_type == PostType.ARTICLE:
            return self._publish_article_post(access_token, author, content)
        if content.post_type == PostType.POLL:
            return self._publish_poll_post(access_token, author, content)
        return self._publish_text_post(access_token, author, content)

    def _build_post_body(self, author: str, commentary: str) -> dict:
        return {
            "author": author,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
        }

    def _publish_text_post(self, access_token: str, author: str, content: PublishContent) -> PublishResult:
        body = self._build_post_body(author, content.text)

        if content.link_url:
            body["content"] = {
                "article": {
                    "source": content.link_url,
                    "title": content.title or "",
                    "description": content.description or "",
                }
            }

        resp = self._request(
            "POST",
            f"{API_BASE}/rest/posts",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json=body,
        )
        post_urn = resp.headers.get("x-restli-id", "")
        return PublishResult(
            platform_post_id=post_urn,
            url=self._post_urn_to_url(post_urn),
            extra={"urn": post_urn},
        )

    def _publish_image_post(self, access_token: str, author: str, content: PublishContent) -> PublishResult:
        # Step 1: initialize upload
        init_resp = self._request(
            "POST",
            f"{API_BASE}/rest/images",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            params={"action": "initializeUpload"},
            json={
                "initializeUploadRequest": {
                    "owner": author,
                }
            },
        )
        init_data = init_resp.json().get("value", {})
        upload_url = init_data.get("uploadUrl", "")
        image_urn = init_data.get("image", "")

        if not upload_url or not image_urn:
            raise PublishError(
                "Failed to initialize LinkedIn image upload",
                platform=self.platform_name,
                raw_response=init_data,
            )

        # Step 2: upload image binary (prefer local file to avoid extra network hop)
        image_source = content.media_files[0] if content.media_files else content.media_urls[0]
        self._upload_binary(access_token, upload_url, image_source)

        # Step 3: create post with image
        body = self._build_post_body(author, content.text)
        body["content"] = {
            "media": {
                "id": image_urn,
            }
        }

        resp = self._request(
            "POST",
            f"{API_BASE}/rest/posts",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json=body,
        )
        post_urn = resp.headers.get("x-restli-id", "")
        return PublishResult(
            platform_post_id=post_urn,
            url=self._post_urn_to_url(post_urn),
            extra={"urn": post_urn, "image_urn": image_urn},
        )

    def _publish_video_post(self, access_token: str, author: str, content: PublishContent) -> PublishResult:
        # LinkedIn's Videos REST API: init with fileSizeBytes -> PUT each chunk from
        # uploadInstructions (collecting ETags) -> finalizeUpload -> poll until
        # status=AVAILABLE -> create post. Chunks are streamed from disk to avoid
        # loading multi-GB videos into memory.
        video_path, cleanup_path = self._materialize_video_to_disk(content)
        try:
            file_size = os.path.getsize(video_path)

            # Step 1: initialize upload
            init_resp = self._request(
                "POST",
                f"{API_BASE}/rest/videos",
                access_token=access_token,
                headers=LINKEDIN_HEADERS,
                params={"action": "initializeUpload"},
                json={
                    "initializeUploadRequest": {
                        "owner": author,
                        "fileSizeBytes": file_size,
                    }
                },
            )
            init_data = init_resp.json().get("value", {})
            video_urn = init_data.get("video", "")
            upload_instructions = init_data.get("uploadInstructions") or []
            # uploadToken can legitimately be empty per LinkedIn's docs samples;
            # we forward whatever the init returned to finalizeUpload as-is.
            upload_token = init_data.get("uploadToken", "")

            if not video_urn or not upload_instructions:
                raise PublishError(
                    "Failed to initialize LinkedIn video upload",
                    platform=self.platform_name,
                    raw_response=init_data,
                )

            # Step 2: stream each chunk from disk to its assigned upload URL
            uploaded_part_ids: list[str] = []
            with open(video_path, "rb") as f:
                for index, instruction in enumerate(upload_instructions):
                    chunk_url = instruction.get("uploadUrl")
                    first_byte = instruction.get("firstByte")
                    last_byte = instruction.get("lastByte")
                    if not chunk_url or first_byte is None or last_byte is None:
                        raise PublishError(
                            f"LinkedIn upload instruction {index} is missing required fields",
                            platform=self.platform_name,
                            raw_response=instruction,
                        )
                    f.seek(first_byte)
                    chunk = f.read(last_byte - first_byte + 1)
                    etag = self._upload_video_chunk(chunk_url, chunk)
                    uploaded_part_ids.append(etag)

            # Step 3: finalize — LinkedIn assembles chunks and starts processing
            self._request(
                "POST",
                f"{API_BASE}/rest/videos",
                access_token=access_token,
                headers=LINKEDIN_HEADERS,
                params={"action": "finalizeUpload"},
                json={
                    "finalizeUploadRequest": {
                        "video": video_urn,
                        "uploadToken": upload_token,
                        "uploadedPartIds": uploaded_part_ids,
                    }
                },
            )

            # Step 4: wait for processing — posting before status=AVAILABLE returns
            # 400 MEDIA_ASSET_WAITING_UPLOAD / MEDIA_ASSET_PROCESSING_FAILED.
            self._wait_for_video_available(access_token, video_urn)
        finally:
            if cleanup_path:
                with contextlib.suppress(OSError):
                    os.unlink(video_path)

        # Step 5: create post with video
        body = self._build_post_body(author, content.text)
        body["content"] = {
            "media": {
                "id": video_urn,
            }
        }

        resp = self._request(
            "POST",
            f"{API_BASE}/rest/posts",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json=body,
        )
        post_urn = resp.headers.get("x-restli-id", "")
        return PublishResult(
            platform_post_id=post_urn,
            url=self._post_urn_to_url(post_urn),
            extra={"urn": post_urn, "video_urn": video_urn},
        )

    def _publish_article_post(self, access_token: str, author: str, content: PublishContent) -> PublishResult:
        body = self._build_post_body(author, content.text)
        body["content"] = {
            "article": {
                "source": content.link_url or "",
                "title": content.title or "",
                "description": content.description or "",
            }
        }
        resp = self._request(
            "POST",
            f"{API_BASE}/rest/posts",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json=body,
        )
        post_urn = resp.headers.get("x-restli-id", "")
        return PublishResult(
            platform_post_id=post_urn,
            url=self._post_urn_to_url(post_urn),
            extra={"urn": post_urn},
        )

    def _publish_poll_post(self, access_token: str, author: str, content: PublishContent) -> PublishResult:
        poll_question = content.extra.get("poll_question", content.text)
        poll_options = content.extra.get("poll_options", [])
        poll_duration = content.extra.get("poll_duration", "THREE_DAYS")

        if not poll_options:
            raise PublishError(
                "poll_options required in content.extra for LinkedIn poll posts",
                platform=self.platform_name,
            )

        body = self._build_post_body(author, content.text)
        body["content"] = {
            "poll": {
                "question": poll_question,
                "options": [{"text": opt} for opt in poll_options],
                "settings": {
                    "duration": poll_duration,
                },
            }
        }
        resp = self._request(
            "POST",
            f"{API_BASE}/rest/posts",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json=body,
        )
        post_urn = resp.headers.get("x-restli-id", "")
        return PublishResult(
            platform_post_id=post_urn,
            url=self._post_urn_to_url(post_urn),
            extra={"urn": post_urn},
        )

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        """Post a comment on a LinkedIn post.

        post_id should be the post URN (e.g. urn:li:share:123456).
        """
        profile = self.get_profile(access_token)
        actor = f"urn:li:person:{profile.platform_id}"

        resp = self._request(
            "POST",
            f"{API_BASE}/rest/socialActions/{_encode_urn(post_id)}/comments",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json={
                "actor": actor,
                "message": {"text": text},
            },
        )
        data = resp.json()
        comment_urn = resp.headers.get("x-restli-id", data.get("id", ""))
        return CommentResult(platform_comment_id=comment_urn, extra=data)

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        # Determine author URN
        profile = self.get_profile(access_token)
        author = f"urn:li:person:{profile.platform_id}"

        # Fetch recent posts by this author
        params: dict = {"q": "author", "author": author, "count": 20}
        resp = self._request(
            "GET",
            f"{API_BASE}/rest/posts",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            params=params,
        )
        posts = resp.json().get("elements", [])

        messages: list[InboxMessage] = []

        for post in posts:
            post_urn = post.get("id", "")
            if not post_urn:
                continue

            # Fetch comments on this post
            start = 0
            while True:
                c_resp = self._request(
                    "GET",
                    f"{API_BASE}/rest/socialActions/{_encode_urn(post_urn)}/comments",
                    access_token=access_token,
                    headers=LINKEDIN_HEADERS,
                    params={"start": start, "count": 100},
                )
                c_data = c_resp.json()
                elements = c_data.get("elements", [])
                if not elements:
                    break

                for comment in elements:
                    created_at_ms = comment.get("created", {}).get("time", 0)
                    created_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)

                    if since and created_at < since:
                        continue

                    actor_urn = comment.get("actor", "")
                    comment_urn = comment.get("$URN", comment.get("id", ""))
                    comment_text = comment.get("message", {}).get("text", "")

                    # Use actor~ expansion if available, otherwise fall back to URN
                    actor_info = comment.get("actor~", {})
                    sender_name = actor_info.get("name") or actor_info.get("localizedFirstName", "") or actor_urn

                    messages.append(
                        InboxMessage(
                            platform_message_id=comment_urn,
                            sender_id=actor_urn,
                            sender_name=sender_name,
                            text=comment_text,
                            timestamp=created_at,
                            message_type="comment",
                            extra={
                                "post_urn": post_urn,
                                "comment_urn": comment_urn,
                                "actor_urn": actor_urn,
                            },
                        )
                    )

                # Check if there are more comments
                if len(elements) < 100:
                    break
                start += 100

        return messages

    def reply_to_message(self, access_token: str, message_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        extra = extra or {}
        post_urn = extra.get("post_urn", "")
        if not post_urn:
            raise APIError(
                "post_urn required in extra for LinkedIn reply",
                platform=self.platform_name,
            )

        profile = self.get_profile(access_token)
        actor = f"urn:li:person:{profile.platform_id}"

        resp = self._request(
            "POST",
            f"{API_BASE}/rest/socialActions/{_encode_urn(post_urn)}/comments",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            json={
                "actor": actor,
                "message": {"text": text},
                "parentComment": message_id,
            },
        )
        data = resp.json()
        comment_urn = resp.headers.get("x-restli-id", data.get("id", ""))
        return ReplyResult(platform_message_id=comment_urn, extra=data)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        """Fetch metrics for a specific post.

        post_id should be the post URN.
        """
        resp = self._request(
            "GET",
            f"{API_BASE}/rest/organizationalEntityShareStatistics",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            params={"q": "organizationalEntity", "shares[0]": post_id},
        )
        data = resp.json()
        elements = data.get("elements", [])
        if not elements:
            return PostMetrics(extra={"raw": data})

        stats = elements[0].get("totalShareStatistics", {})
        return PostMetrics(
            impressions=stats.get("impressionCount", 0),
            engagements=stats.get("engagementCount", 0),
            likes=stats.get("likeCount", 0),
            comments=stats.get("commentCount", 0),
            shares=stats.get("shareCount", 0),
            clicks=stats.get("clickCount", 0),
            extra={"raw_statistics": stats},
        )

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def revoke_token(self, access_token: str) -> bool:
        try:
            self._request(
                "POST",
                REVOKE_URL,
                data={
                    "client_id": self.credentials["client_id"],
                    "client_secret": self.credentials["client_secret"],
                    "token": access_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            return True
        except APIError:
            logger.warning("Failed to revoke LinkedIn token")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _upload_binary(self, access_token: str, upload_url: str, source: str) -> None:
        """Read media from a local file path or URL and upload to LinkedIn.

        Args:
            source: A local file path or an HTTP(S) URL to download from.
        """
        media_bytes = self._read_media_bytes(source)

        with httpx.Client(timeout=120.0) as client:
            upload_resp = client.put(
                upload_url,
                content=media_bytes,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/octet-stream",
                    **LINKEDIN_HEADERS,
                },
            )
            if upload_resp.status_code >= 400:
                raise PublishError(
                    f"LinkedIn media upload failed: {upload_resp.status_code}",
                    platform=self.platform_name,
                    raw_response=self._safe_json(upload_resp),
                )

    @staticmethod
    def _read_media_bytes(source: str) -> bytes:
        """Load media into memory from a local file path or HTTP(S) URL."""
        if source.startswith(("http://", "https://")):
            with httpx.Client(timeout=120.0) as client:
                resp = client.get(source)
                resp.raise_for_status()
                return resp.content
        with open(source, "rb") as f:
            return f.read()

    def _upload_video_chunk(self, upload_url: str, chunk: bytes) -> str:
        """PUT a single video chunk and return its ETag for finalizeUpload.

        Per LinkedIn's Videos API docs, the chunk upload URL is pre-authenticated
        via the `?sau=...` query param — only Content-Type should be sent. Adding
        an Authorization header or LinkedIn-Version can confuse the upload edge.
        """
        with httpx.Client(timeout=120.0) as client:
            resp = client.put(
                upload_url,
                content=chunk,
                headers={"Content-Type": "application/octet-stream"},
            )
            if resp.status_code >= 400:
                raise PublishError(
                    f"LinkedIn video chunk upload failed: {resp.status_code}",
                    platform=self.platform_name,
                    raw_response=self._safe_json(resp),
                )
            # httpx Headers is case-insensitive, so a single .get covers all casings.
            etag = resp.headers.get("etag", "")
            if not etag:
                raise PublishError(
                    "LinkedIn video chunk upload succeeded but returned no ETag",
                    platform=self.platform_name,
                )
            # LinkedIn's docs show two ETag formats: HTTP-spec hex like `"abc"` and
            # long opaque tokens like `/ambry-videoei/signedId/...bin` (no quotes).
            # finalizeUpload wants the unquoted value in both cases.
            if len(etag) >= 2 and etag[0] == '"' and etag[-1] == '"':
                etag = etag[1:-1]
            return etag

    def _materialize_video_to_disk(self, content: PublishContent) -> tuple[str, bool]:
        """Return a local path for the video plus whether the caller owns cleanup.

        The publisher engine downloads media to a temp file before invoking the
        provider, so `media_files[0]` is the normal path. The `media_urls` branch
        exists only for direct-API callers; it downloads once to a temp file so
        the chunk loop can seek/read instead of holding the full bytes in memory.
        """
        if content.media_files:
            return content.media_files[0], False
        if not content.media_urls:
            raise PublishError(
                "No video source provided",
                platform=self.platform_name,
            )

        url = content.media_urls[0]
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)  # noqa: SIM115
        try:
            with httpx.stream("GET", url, timeout=300.0) as resp:
                resp.raise_for_status()
                for buf in resp.iter_bytes():
                    tmp.write(buf)
        except Exception:
            tmp.close()
            with contextlib.suppress(OSError):
                os.unlink(tmp.name)
            raise
        tmp.close()
        return tmp.name, True

    def _wait_for_video_available(
        self,
        access_token: str,
        video_urn: str,
        *,
        timeout_seconds: float = 180.0,
        poll_interval: float = 3.0,
    ) -> None:
        """Poll until the video reaches AVAILABLE status (or fail fast on terminal errors).

        Posting against a video that is still WAITING_UPLOAD / PROCESSING returns
        400 MEDIA_ASSET_WAITING_UPLOAD or MEDIA_ASSET_PROCESSING_FAILED — see
        https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api#api-error-details
        """
        deadline = time.monotonic() + timeout_seconds
        last_status: str | None = None
        while True:
            resp = self._request(
                "GET",
                f"{API_BASE}/rest/videos/{_encode_urn(video_urn)}",
                access_token=access_token,
                headers=LINKEDIN_HEADERS,
            )
            data = resp.json()
            status = data.get("status")
            if status == "AVAILABLE":
                return
            if status == "PROCESSING_FAILED":
                raise PublishError(
                    f"LinkedIn rejected the video during processing: "
                    f"{data.get('processingFailureReason', 'unknown reason')}",
                    platform=self.platform_name,
                    raw_response=data,
                )
            last_status = status
            if time.monotonic() >= deadline:
                raise PublishError(
                    f"Timed out waiting for LinkedIn video to become AVAILABLE (last status: {last_status})",
                    platform=self.platform_name,
                )
            time.sleep(poll_interval)

    @staticmethod
    def _post_urn_to_url(urn: str) -> str | None:
        """Convert a LinkedIn post URN to a web URL.

        URN format: urn:li:share:123456 or urn:li:ugcPost:123456
        """
        if not urn:
            return None
        # Extract the numeric ID from the URN
        parts = urn.split(":")
        if len(parts) >= 4:
            return f"https://www.linkedin.com/feed/update/{urn}/"
        return None
