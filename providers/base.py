"""Abstract base class for social platform providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

import httpx

from .exceptions import APIError, RateLimitError
from .types import (
    AccountMetrics,
    AccountProfile,
    AuthType,
    CommentResult,
    Demographics,
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

REQUEST_TIMEOUT = 30.0


class SocialProvider(ABC):
    """Abstract base class that all social platform providers must implement.

    Each provider is instantiated with app-level credentials (client_id,
    client_secret, etc.) from PlatformCredential or environment variables.
    Per-user OAuth tokens are passed as method arguments.
    """

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    # ------------------------------------------------------------------
    # Class-level metadata (abstract properties)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable platform name (e.g. 'Facebook')."""

    @property
    @abstractmethod
    def auth_type(self) -> AuthType:
        """Authentication type this provider uses."""

    @property
    @abstractmethod
    def max_caption_length(self) -> int:
        """Maximum character length for post text."""

    @property
    @abstractmethod
    def supported_post_types(self) -> list[PostType]:
        """Post types this platform supports."""

    @property
    @abstractmethod
    def supported_media_types(self) -> list[MediaType]:
        """Media types this platform accepts."""

    @property
    @abstractmethod
    def required_scopes(self) -> list[str]:
        """OAuth scopes required for full functionality."""

    @property
    def rate_limits(self) -> RateLimitConfig:
        """Platform rate limit configuration."""
        return RateLimitConfig()

    # ------------------------------------------------------------------
    # OAuth methods (override for OAuth providers)
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Generate the OAuth authorization URL."""
        raise NotImplementedError(f"{self.platform_name} does not implement get_auth_url")

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange an authorization code for access tokens."""
        raise NotImplementedError(f"{self.platform_name} does not implement exchange_code")

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token."""
        raise NotImplementedError(f"{self.platform_name} does not implement refresh_token")

    # ------------------------------------------------------------------
    # Profile (abstract - every provider must implement)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_profile(self, access_token: str) -> AccountProfile:
        """Fetch the authenticated account's profile information."""

    # ------------------------------------------------------------------
    # Publishing (abstract - every provider must implement)
    # ------------------------------------------------------------------

    @abstractmethod
    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        """Publish content to the platform."""

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        """Post a comment on an existing post (e.g. first comment)."""
        raise NotImplementedError(f"{self.platform_name} does not support comments")

    # ------------------------------------------------------------------
    # Analytics (optional - override per provider)
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        """Fetch engagement metrics for a specific post."""
        raise NotImplementedError(f"{self.platform_name} does not support post metrics")

    def get_account_metrics(self, access_token: str, date_range: tuple[datetime, datetime]) -> AccountMetrics:
        """Fetch account-level metrics for a date range."""
        raise NotImplementedError(f"{self.platform_name} does not support account metrics")

    def get_audience_demographics(self, access_token: str) -> Demographics:
        """Fetch audience demographic data."""
        raise NotImplementedError(f"{self.platform_name} does not support demographics")

    def get_recent_post_metrics(
        self, access_token: str, account_platform_id: str, limit: int = 20
    ) -> list[PostMetrics]:
        """Fetch engagement metrics for recent posts.

        Returns a list of PostMetrics. Post identification metadata is carried
        in the extra dict with these required keys:
        - extra["platform_post_id"] — native post ID
        - extra["post_url"] — permalink to the post
        - extra["post_text"] — caption/title text
        - extra["posted_at"] — ISO 8601 timestamp string
        - extra["post_type"] — image, video, reel, carousel, story, short, pin
        """
        raise NotImplementedError(
            f"{self.platform_name} does not support recent post metrics"
        )

    # ------------------------------------------------------------------
    # Inbox (optional - override per provider)
    # ------------------------------------------------------------------

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        """Fetch inbox messages (comments, mentions, DMs)."""
        raise NotImplementedError(f"{self.platform_name} does not support inbox")

    def reply_to_message(self, access_token: str, message_id: str, text: str, extra: dict | None = None) -> ReplyResult:
        """Reply to an inbox message."""
        raise NotImplementedError(f"{self.platform_name} does not support message replies")

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def revoke_token(self, access_token: str) -> bool:
        """Revoke an OAuth token. Returns True if successful."""
        return False

    def validate_token(self, access_token: str) -> bool:
        """Quick health check - try get_profile and see if it works."""
        try:
            self.get_profile(access_token)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        access_token: str | None = None,
        headers: dict | None = None,
        params: dict | None = None,
        json: dict | None = None,
        data: dict | bytes | None = None,
        files: dict | None = None,
        timeout: float = REQUEST_TIMEOUT,
    ) -> httpx.Response:
        """Make an HTTP request with standard error handling.

        Raises APIError on 4xx/5xx, RateLimitError on 429.
        """
        req_headers = {}
        if access_token:
            req_headers["Authorization"] = f"Bearer {access_token}"
        if headers:
            req_headers.update(headers)

        with httpx.Client(timeout=timeout) as client:
            # httpx uses `content` for raw bytes, `data` for form mappings
            request_kwargs: dict = {
                "headers": req_headers,
                "params": params,
                "json": json,
                "files": files,
            }
            if isinstance(data, bytes):
                request_kwargs["content"] = data
            else:
                request_kwargs["data"] = data
            response = client.request(method, url, **request_kwargs)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            logger.error("%s API 429 response: %s", self.platform_name, response.text[:1000])
            raise RateLimitError(
                f"Rate limit exceeded for {self.platform_name}: {response.text[:500]}",
                retry_after=int(retry_after) if retry_after else None,
                platform=self.platform_name,
                raw_response=self._safe_json(response),
            )

        if response.status_code >= 400:
            raise APIError(
                f"{self.platform_name} API error {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
                platform=self.platform_name,
                raw_response=self._safe_json(response),
            )

        return response

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict:
        """Try to parse response as JSON, return empty dict on failure."""
        try:
            return response.json()
        except Exception:
            return {}
