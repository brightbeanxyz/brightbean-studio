"""Mastodon API v1 provider implementation."""

from __future__ import annotations

import logging
import time
import uuid
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

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
    PublishContext,
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
        """Upload once; yield instead of waiting for asynchronous processing."""
        context = content.publish_context
        if context is None:
            # Standalone callers can still publish text and ready images. The
            # studio supplies durable progress before entering this method.
            context = PublishContext(
                checkpoint={
                    "attempt_id": str(uuid.uuid4()),
                    "phase": "uploading",
                    "params": self.status_parameters(content),
                    "media": [
                        {"source": str(i), "media_id": "", "ready": False} for i in range(len(content.media_files))
                    ],
                },
                save_checkpoint=lambda _: None,
            )
        checkpoint = context.checkpoint
        for index, attachment in enumerate(checkpoint["media"]):
            if attachment["media_id"]:
                continue
            # Check ownership before each external side effect, as well as
            # after it. A lost response may orphan an attachment, never a post.
            context.save()
            media_id, ready = self._upload_media(access_token, content.media_files[index])
            attachment.update(media_id=media_id, ready=ready)
            checkpoint.setdefault("processing_started_at", datetime.now(UTC).isoformat())
            context.save()

        if not all(item["ready"] for item in checkpoint["media"]):
            checkpoint["phase"] = "processing"
            context.save()
            return PublishResult(platform_post_id="", deferred=True)
        return self._submit_status(access_token, context)

    @staticmethod
    def status_parameters(content: PublishContent) -> dict:
        """Freeze only authored status parameters, never runtime metadata."""

        # Build status params
        params: dict = {}
        if content.text:
            params["status"] = content.text

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

        return deepcopy(params)

    def resume_publish(self, access_token: str, context: PublishContext) -> PublishResult:
        """Check each pending attachment once, then submit when all are ready."""
        checkpoint = context.checkpoint
        if checkpoint.get("status_id"):
            return self._completed_result(checkpoint)
        if checkpoint["phase"] != "submitting":
            for attachment in checkpoint["media"]:
                if attachment["ready"]:
                    continue
                timeout = self._resume_timeout(context)
                if timeout is None:
                    return PublishResult(platform_post_id="", deferred=True)
                context.save()
                try:
                    response = self._request(
                        "GET",
                        f"{self.instance_url}/api/v1/media/{attachment['media_id']}",
                        access_token=access_token,
                        timeout=timeout,
                    )
                except APIError as exc:
                    if exc.status_code in (400, 401, 403, 404, 413, 415, 422):
                        exc.retryable = False
                    raise
                # 206 can have no body at all. A thumbnail is not proof that
                # the full-sized upload has finished processing.
                if response.status_code == 200 and response.json().get("url"):
                    attachment["ready"] = True
                    context.save()
            if not all(item["ready"] for item in checkpoint["media"]):
                return PublishResult(platform_post_id="", deferred=True)
        return self._submit_status(access_token, context)

    @staticmethod
    def _resume_timeout(context: PublishContext) -> float | None:
        remaining = 5.0 if context.deadline is None else min(5.0, context.deadline - time.monotonic())
        return remaining if remaining > 0 else None

    def _submit_status(self, access_token: str, context: PublishContext) -> PublishResult:
        checkpoint = context.checkpoint
        if checkpoint.get("status_id"):
            return self._completed_result(checkpoint)
        started = checkpoint.get("first_submission_at") or checkpoint.get("processing_started_at")
        if started and datetime.now(UTC) - datetime.fromisoformat(started) >= timedelta(minutes=30):
            # Readiness may have changed just as the durable deadline expired.
            # Yield so the coordinator settles the timeout without posting.
            return PublishResult(platform_post_id="", deferred=True)
        timeout = self._resume_timeout(context)
        if timeout is None:
            return PublishResult(platform_post_id="", deferred=True)
        params = deepcopy(checkpoint["params"])
        if checkpoint["media"]:
            params["media_ids[]"] = [item["media_id"] for item in checkpoint["media"]]
        checkpoint["phase"] = "submitting"
        checkpoint.setdefault("first_submission_at", datetime.now(UTC).isoformat())
        context.save()

        try:
            response = self._request(
                "POST",
                f"{self.instance_url}/api/v1/statuses",
                access_token=access_token,
                headers={"Idempotency-Key": f"studio-mastodon-{checkpoint['attempt_id']}"},
                data=params,
                timeout=timeout,
            )
        except APIError as exc:
            if (
                exc.status_code == 422
                and not checkpoint.get("submission_uncertain")
                and "not finished processing" in str(exc.raw_response.get("error", "")).lower()
            ):
                checkpoint["phase"] = "processing"
                checkpoint.pop("first_submission_at", None)
                for item in checkpoint["media"]:
                    item["ready"] = False
                context.save()
                return PublishResult(platform_post_id="", deferred=True)
            if exc.status_code in (400, 401, 403, 404, 413, 415, 422):
                exc.retryable = False
            raise
        data = response.json()
        status_id = data.get("id")
        if not isinstance(status_id, (str, int)) or isinstance(status_id, bool) or not str(status_id):
            raise PublishError("Mastodon did not return a valid status ID", platform=self.platform_name)
        checkpoint.update(phase="complete", status_id=str(status_id), status_url=data.get("url"))
        context.save()
        return self._completed_result(checkpoint)

    @staticmethod
    def _completed_result(checkpoint: dict) -> PublishResult:
        return PublishResult(
            platform_post_id=checkpoint["status_id"],
            url=checkpoint.get("status_url"),
            extra={"id": checkpoint["status_id"], "url": checkpoint.get("status_url")},
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

    def _upload_media(self, access_token: str, file_path: str) -> tuple[str, bool]:
        """Return an accepted ID and whether the full upload is already ready."""
        try:
            with open(file_path, "rb") as f:
                resp = self._request(
                    "POST",
                    f"{self.instance_url}/api/v2/media",
                    access_token=access_token,
                    files={"file": f},
                )
        except APIError as exc:
            if exc.status_code in (400, 401, 403, 404, 413, 415, 422):
                exc.retryable = False
            raise
        data = resp.json()
        return str(data["id"]), resp.status_code == 200 and bool(data.get("url"))

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

    def reply_to_comment(self, access_token: str, comment_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        """Reply to a mention. Mastodon answers a notification's status, so this is the same call."""
        return self.reply_to_message(access_token, comment_id, text, extra)

    def reply_to_message(
        self,
        access_token: str,
        message_id: str,
        text: str,
        extra: dict | None = None,
        *,
        human_agent: bool = False,
    ) -> ReplyResult:
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
