"""Mastodon API v1 provider implementation."""

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

DEFAULT_MAX_CHARS = 500


class MastodonProvider(SocialProvider):
    """Mastodon API v1 provider.

    Uses instance-specific OAuth.  The ``credentials`` dict must contain:

    - ``instance_url`` – e.g. ``https://mastodon.social``
    - ``client_id``    – obtained from app registration
    - ``client_secret``– obtained from app registration
    """

    def __init__(self, credentials: dict | None = None):
        super().__init__(credentials)
        instance = self.credentials.get("instance_url", "")
        self.instance_url: str = instance.rstrip("/")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "Mastodon"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.INSTANCE_OAUTH

    @property
    def max_caption_length(self) -> int:
        return DEFAULT_MAX_CHARS

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.POLL]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [
            MediaType.JPEG,
            MediaType.PNG,
            MediaType.GIF,
            MediaType.MP4,
            MediaType.MOV,
            MediaType.WEBP,
        ]

    @property
    def required_scopes(self) -> list[str]:
        return ["read", "write", "follow"]

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=100,
            requests_per_day=7200,
            publish_per_day=100,
            extra={"publish_per_3h": 300},
        )

    # ------------------------------------------------------------------
    # App registration
    # ------------------------------------------------------------------

    def register_app(self, instance_url: str, redirect_uri: str) -> dict:
        """Register an OAuth application on a Mastodon instance.

        Returns a dict with ``client_id`` and ``client_secret``.
        This only needs to be called once per instance.
        """
        url = f"{instance_url.rstrip('/')}/api/v1/apps"
        resp = self._request(
            "POST",
            url,
            json={
                "client_name": "Brightbean",
                "redirect_uris": redirect_uri,
                "scopes": " ".join(self.required_scopes),
                "website": "https://brightbean.xyz",
            },
        )
        data = resp.json()
        return {
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "instance_url": instance_url,
        }

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        """Build the instance-specific OAuth authorization URL."""
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.required_scopes),
            "response_type": "code",
            "state": state,
        }
        return f"{self.instance_url}/oauth/authorize?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
        """Exchange an authorization code for a Mastodon access token."""
        resp = self._request(
            "POST",
            f"{self.instance_url}/oauth/token",
            data={
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": " ".join(self.required_scopes),
            },
        )
        data = resp.json()
        if "error" in data:
            raise OAuthError(
                f"Token exchange failed: {data.get('error_description', data['error'])}",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            raw_response=data,
        )

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Mastodon tokens do not expire by default - return existing token."""
        return OAuthTokens(access_token=refresh_token)

    def revoke_token(self, access_token: str) -> bool:
        """Revoke a Mastodon OAuth token."""
        try:
            self._request(
                "POST",
                f"{self.instance_url}/oauth/revoke",
                data={
                    "client_id": self.credentials["client_id"],
                    "client_secret": self.credentials["client_secret"],
                    "token": access_token,
                },
            )
            return True
        except Exception:
            logger.exception("Failed to revoke Mastodon token")
            return False

    # ------------------------------------------------------------------
    # Instance info
    # ------------------------------------------------------------------

    def get_instance_max_chars(self, access_token: str) -> int:
        """Retrieve the instance's maximum status character limit."""
        try:
            resp = self._request(
                "GET",
                f"{self.instance_url}/api/v2/instance",
                access_token=access_token,
            )
            data = resp.json()
            return int(data.get("configuration", {}).get("statuses", {}).get("max_characters", DEFAULT_MAX_CHARS))
        except Exception:
            return DEFAULT_MAX_CHARS

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        """Fetch the authenticated user's Mastodon profile."""
        resp = self._request(
            "GET",
            f"{self.instance_url}/api/v1/accounts/verify_credentials",
            access_token=access_token,
        )
        data = resp.json()
        return AccountProfile(
            platform_id=data["id"],
            name=data.get("display_name", data.get("username", "")),
            handle=data.get("acct"),
            avatar_url=data.get("avatar"),
            follower_count=data.get("followers_count", 0),
            extra={"username": data.get("username")},
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        """Publish a status to Mastodon."""
        # Upload media first if present
        media_ids: list[str] = []
        for media_path in content.media_files or []:
            media_id = self._upload_media(access_token, media_path)
            media_ids.append(media_id)

        # Build status params
        params: dict = {}
        if content.text:
            params["status"] = content.text
        if media_ids:
            params["media_ids[]"] = media_ids

        # Visibility
        visibility = content.extra.get("visibility", "public")
        params["visibility"] = visibility

        # Content warning / spoiler text
        if content.extra.get("spoiler_text"):
            params["spoiler_text"] = content.extra["spoiler_text"]

        # Poll
        if content.post_type == PostType.POLL and content.extra.get("poll"):
            poll = content.extra["poll"]
            params["poll[options][]"] = poll.get("options", [])
            params["poll[expires_in]"] = poll.get("expires_in", 86400)
            if poll.get("multiple"):
                params["poll[multiple]"] = "true"
            if poll.get("hide_totals"):
                params["poll[hide_totals]"] = "true"

        # Reply
        if content.extra.get("in_reply_to_id"):
            params["in_reply_to_id"] = content.extra["in_reply_to_id"]

        resp = self._request(
            "POST",
            f"{self.instance_url}/api/v1/statuses",
            access_token=access_token,
            data=params,
        )
        data = resp.json()

        return PublishResult(
            platform_post_id=data["id"],
            url=data.get("url"),
            extra=data,
        )

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        """Reply to an existing Mastodon status."""
        resp = self._request(
            "POST",
            f"{self.instance_url}/api/v1/statuses",
            access_token=access_token,
            data={
                "status": text,
                "in_reply_to_id": post_id,
                "visibility": "public",
            },
        )
        data = resp.json()
        return CommentResult(
            platform_comment_id=data["id"],
            extra=data,
        )

    # ------------------------------------------------------------------
    # Media upload
    # ------------------------------------------------------------------

    def _upload_media(self, access_token: str, file_path: str) -> str:
        """Upload a media file and return its media ID."""
        with open(file_path, "rb") as f:
            resp = self._request(
                "POST",
                f"{self.instance_url}/api/v2/media",
                access_token=access_token,
                files={"file": f},
            )
        data = resp.json()
        return data["id"]

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        """Fetch metrics for a Mastodon status."""
        resp = self._request(
            "GET",
            f"{self.instance_url}/api/v1/statuses/{post_id}",
            access_token=access_token,
        )
        data = resp.json()
        return PostMetrics(
            likes=data.get("favourites_count", 0),
            shares=data.get("reblogs_count", 0),
            comments=data.get("replies_count", 0),
            engagements=(data.get("favourites_count", 0) + data.get("reblogs_count", 0) + data.get("replies_count", 0)),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        """Fetch mentions, favourites, and reblogs from notifications."""
        params: dict = {
            "types[]": ["mention", "favourite", "reblog"],
        }
        if since:
            params["since_id"] = "0"  # Mastodon uses min_id for pagination

        resp = self._request(
            "GET",
            f"{self.instance_url}/api/v1/notifications",
            access_token=access_token,
            params=params,
        )
        data = resp.json()

        messages: list[InboxMessage] = []
        for notif in data:
            account = notif.get("account", {})
            status = notif.get("status", {})
            text = status.get("content", "") if status else ""
            # Strip HTML tags for plain text
            import re

            text = re.sub(r"<[^>]+>", "", text)

            created = notif.get("created_at", "")
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now()

            messages.append(
                InboxMessage(
                    platform_message_id=notif["id"],
                    sender_id=account.get("id", ""),
                    sender_name=account.get("display_name", account.get("acct", "")),
                    text=text,
                    timestamp=ts,
                    message_type=notif.get("type", "mention"),
                    extra=notif,
                )
            )

        return messages

    def reply_to_message(self, access_token: str, message_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        """Reply to a notification's associated status."""
        # Get the notification to find the status ID
        resp = self._request(
            "GET",
            f"{self.instance_url}/api/v1/notifications/{message_id}",
            access_token=access_token,
        )
        notif = resp.json()
        status = notif.get("status", {})
        status_id = status.get("id")

        if not status_id:
            raise PublishError(
                "Cannot reply: notification has no associated status",
                platform=self.platform_name,
            )

        reply_resp = self._request(
            "POST",
            f"{self.instance_url}/api/v1/statuses",
            access_token=access_token,
            data={
                "status": text,
                "in_reply_to_id": status_id,
                "visibility": "public",
            },
        )
        reply_data = reply_resp.json()
        return ReplyResult(
            platform_message_id=reply_data["id"],
            extra=reply_data,
        )
