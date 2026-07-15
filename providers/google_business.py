"""Google Business Profile API provider implementation."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from .base import SocialProvider
from .exceptions import OAuthError, PublishError
from .types import (
    AccountProfile,
    AuthType,
    MediaType,
    OAuthTokens,
    PostMetrics,
    PostType,
    PublishContent,
    PublishResult,
)

logger = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
ACCOUNTS_API = "https://mybusinessaccountmanagement.googleapis.com/v1"
BUSINESS_INFO_API = "https://mybusinessbusinessinformation.googleapis.com/v1"
POSTS_API = "https://mybusiness.googleapis.com/v4"


class GoogleBusinessProvider(SocialProvider):
    """Google Business Profile provider.

    Uses Google OAuth 2.0.  The ``credentials`` dict must contain:

    - ``client_id``
    - ``client_secret``

    Optional:
    - ``account_id`` – Google Business account ID
    - ``location_id`` – Google Business location ID
    """

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "Google Business"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.OAUTH2

    @property
    def max_caption_length(self) -> int:
        return 1500

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.TEXT, PostType.IMAGE]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG]

    @property
    def required_scopes(self) -> list[str]:
        return ["https://www.googleapis.com/auth/business.manage"]

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        """Build the Google OAuth 2.0 authorization URL."""
        params = {
            "client_id": self.credentials["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.required_scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
        """Exchange an authorization code for Google access/refresh tokens."""
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
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
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            raw_response=data,
        )

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired Google access token."""
        resp = self._request(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.credentials["client_id"],
                "client_secret": self.credentials["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        data = resp.json()
        if "error" in data:
            raise OAuthError(
                f"Token refresh failed: {data.get('error_description', data['error'])}",
                platform=self.platform_name,
                raw_response=data,
            )
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=refresh_token,  # Google doesn't rotate refresh tokens
            expires_in=data.get("expires_in"),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            raw_response=data,
        )

    def revoke_token(self, access_token: str) -> bool:
        """Revoke a Google OAuth token."""
        try:
            self._request(
                "POST",
                REVOKE_URL,
                params={"token": access_token},
            )
            return True
        except Exception:
            logger.exception("Failed to revoke Google token")
            return False

    # ------------------------------------------------------------------
    # Account / location helpers
    # ------------------------------------------------------------------

    def _get_account_id(self, access_token: str) -> str:
        """Return the account ID from credentials or by listing accounts."""
        if self.credentials.get("account_id"):
            return self.credentials["account_id"]

        resp = self._request(
            "GET",
            f"{ACCOUNTS_API}/accounts",
            access_token=access_token,
        )
        data = resp.json()
        accounts = data.get("accounts", [])
        if not accounts:
            raise PublishError(
                "No Google Business accounts found",
                platform=self.platform_name,
            )
        # Return the first account's resource name (e.g. "accounts/123")
        return accounts[0]["name"]

    def _get_location_id(self, access_token: str, account_id: str) -> str:
        """Return the location ID from credentials or by listing locations."""
        if self.credentials.get("location_id"):
            return self.credentials["location_id"]

        resp = self._request(
            "GET",
            f"{BUSINESS_INFO_API}/{account_id}/locations",
            access_token=access_token,
        )
        data = resp.json()
        locations = data.get("locations", [])
        if not locations:
            raise PublishError(
                "No locations found for Google Business account",
                platform=self.platform_name,
            )
        return locations[0]["name"]

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        """Fetch the Google Business account and primary location info."""
        account_id = self._get_account_id(access_token)

        resp = self._request(
            "GET",
            f"{BUSINESS_INFO_API}/{account_id}/locations",
            access_token=access_token,
        )
        data = resp.json()
        locations = data.get("locations", [])

        if locations:
            loc = locations[0]
            name = loc.get("title", loc.get("name", ""))
            address_obj = loc.get("storefrontAddress", {})
            address_lines = address_obj.get("addressLines", [])
            address = ", ".join(address_lines) if address_lines else ""
            phone = loc.get("phoneNumbers", {}).get("primaryPhone", "")
            return AccountProfile(
                platform_id=loc.get("name", account_id),
                name=name,
                handle=None,
                extra={"address": address, "phone": phone},
            )

        return AccountProfile(
            platform_id=account_id,
            name=account_id,
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        """Publish a local post to Google Business Profile."""
        if content.text and len(content.text) > self.max_caption_length:
            raise PublishError(
                f"Post text exceeds {self.max_caption_length} characters (got {len(content.text)})",
                platform=self.platform_name,
            )

        account_id = self._get_account_id(access_token)
        location_id = self._get_location_id(access_token, account_id)

        # Determine topic type
        topic_type = content.extra.get("topic_type", "STANDARD")

        body: dict = {
            "languageCode": content.extra.get("language_code", "en"),
            "summary": content.text or "",
            "topicType": topic_type,
        }

        # Attach media
        if content.media_urls:
            body["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": url} for url in content.media_urls]

        # EVENT type extras
        if topic_type == "EVENT" and content.extra.get("event"):
            body["event"] = content.extra["event"]

        # OFFER type extras
        if topic_type == "OFFER" and content.extra.get("offer"):
            body["offer"] = content.extra["offer"]

        resp = self._request(
            "POST",
            f"{POSTS_API}/{location_id}/localPosts",
            access_token=access_token,
            json=body,
        )
        data = resp.json()

        post_name = data.get("name", "")
        return PublishResult(
            platform_post_id=post_name,
            url=data.get("searchUrl"),
            extra=data,
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_metrics(self, access_token: str, post_id: str) -> PostMetrics:
        """Fetch metrics for a Google Business local post."""
        resp = self._request(
            "GET",
            f"{POSTS_API}/{post_id}",
            access_token=access_token,
        )
        data = resp.json()
        search_views = 0
        maps_views = 0
        for metric in data.get("searchActionMetrics", []):
            if metric.get("metricType") == "QUERIES_DIRECT":
                search_views += metric.get("value", 0)
        return PostMetrics(
            impressions=search_views + maps_views,
            extra={
                "search_views": search_views,
                "maps_views": maps_views,
                "raw": data,
            },
        )
