"""Bluesky / AT Protocol provider implementation."""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from datetime import UTC, datetime

from .base import SocialProvider
from .exceptions import PublishError
from .types import (
    AccountProfile,
    AuthType,
    MediaType,
    OAuthTokens,
    PostType,
    PublishContent,
    PublishResult,
    RateLimitConfig,
)

logger = logging.getLogger(__name__)

DEFAULT_PDS_URL = "https://bsky.social"


def _access_jwt_expires_in(access_jwt: str) -> int | None:
    """Return seconds until an AT Protocol access JWT expires, or None if unknown.

    The createSession / refreshSession responses don't include an expiry field;
    the only source of truth is the JWT's own `exp` claim. We decode the payload
    without verifying the signature — we're reading metadata from a token the
    server just minted over TLS, not making an authorization decision.
    """
    try:
        _, payload_b64, _ = access_jwt.split(".")
        padding = "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        exp = int(payload["exp"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    return max(0, exp - int(time.time()))


class BlueskyProvider(SocialProvider):
    """AT Protocol / Bluesky provider.

    Uses session-based authentication (app passwords), not OAuth.
    The ``credentials`` dict may contain:

    - ``pds_url`` – PDS base URL (defaults to ``https://bsky.social``)
    """

    def __init__(self, credentials: dict | None = None):
        super().__init__(credentials)
        self.pds_url: str = self.credentials.get("pds_url", DEFAULT_PDS_URL).rstrip("/")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "Bluesky"

    @property
    def auth_type(self) -> AuthType:
        return AuthType.SESSION

    @property
    def max_caption_length(self) -> int:
        return 300

    @property
    def supported_post_types(self) -> list[PostType]:
        return [PostType.TEXT, PostType.IMAGE, PostType.VIDEO]

    @property
    def supported_media_types(self) -> list[MediaType]:
        return [MediaType.JPEG, MediaType.PNG, MediaType.MP4]

    @property
    def required_scopes(self) -> list[str]:
        return []  # session-based, no scopes

    @property
    def rate_limits(self) -> RateLimitConfig:
        return RateLimitConfig(
            requests_per_hour=5000,
            requests_per_day=35000,
        )

    # ------------------------------------------------------------------
    # OAuth stubs (not applicable for session auth)
    # ------------------------------------------------------------------

    def get_auth_url(self, redirect_uri: str, state: str) -> str:
        raise NotImplementedError("Bluesky uses session-based auth, not OAuth. Use create_session() instead.")

    def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        raise NotImplementedError("Bluesky uses session-based auth, not OAuth. Use create_session() instead.")

    # ------------------------------------------------------------------
    # Handle resolution
    # ------------------------------------------------------------------

    def resolve_handle(self, handle: str) -> str:
        """Resolve a Bluesky handle to a DID.

        Uses bsky.social for resolution regardless of PDS URL.
        """
        resp = self._request(
            "GET",
            f"{DEFAULT_PDS_URL}/xrpc/com.atproto.identity.resolveHandle",
            params={"handle": handle},
        )
        data = resp.json()
        return data["did"]

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(self, handle: str, app_password: str) -> OAuthTokens:
        """Create an AT Protocol session using handle and app password.

        Returns an ``OAuthTokens`` with *accessJwt* as ``access_token`` and
        *refreshJwt* as ``refresh_token``.
        """
        resp = self._request(
            "POST",
            f"{self.pds_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": app_password},
        )
        data = resp.json()
        return OAuthTokens(
            access_token=data["accessJwt"],
            refresh_token=data["refreshJwt"],
            expires_in=_access_jwt_expires_in(data["accessJwt"]),
            raw_response=data,
        )

    def refresh_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an AT Protocol session using the refresh JWT."""
        resp = self._request(
            "POST",
            f"{self.pds_url}/xrpc/com.atproto.server.refreshSession",
            access_token=refresh_token,
        )
        data = resp.json()
        return OAuthTokens(
            access_token=data["accessJwt"],
            refresh_token=data["refreshJwt"],
            expires_in=_access_jwt_expires_in(data["accessJwt"]),
            raw_response=data,
        )

    # ------------------------------------------------------------------
    # Token revocation
    # ------------------------------------------------------------------

    def revoke_token(self, access_token: str) -> bool:
        """Delete the AT Protocol session (logout)."""
        try:
            self._request(
                "POST",
                f"{self.pds_url}/xrpc/com.atproto.server.deleteSession",
                access_token=access_token,
            )
            return True
        except Exception:
            logger.exception("Failed to delete Bluesky session")
            return False

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self, access_token: str) -> AccountProfile:
        """Fetch the authenticated user's Bluesky profile."""
        # Decode the DID from the JWT payload (middle segment) or use the
        # actor param. We call getProfile with the session's own DID stored
        # in the JWT.  Easier: use "actor=did:..." but we need the DID.
        # We can call getSession to retrieve the DID.
        session = self._request(
            "GET",
            f"{self.pds_url}/xrpc/com.atproto.server.getSession",
            access_token=access_token,
        ).json()
        did = session["did"]

        resp = self._request(
            "GET",
            f"{self.pds_url}/xrpc/app.bsky.actor.getProfile",
            params={"actor": did},
            access_token=access_token,
        )
        data = resp.json()
        handle = data.get("handle") or ""
        return AccountProfile(
            platform_id=data.get("did", did),
            name=data.get("displayName") or handle,
            handle=handle,
            avatar_url=data.get("avatar"),
            follower_count=data.get("followersCount", 0),
        )

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish_post(self, access_token: str, content: PublishContent) -> PublishResult:
        """Publish a post to Bluesky via com.atproto.repo.createRecord."""
        # Validate grapheme length
        grapheme_count = len(content.text) if content.text else 0
        if grapheme_count > self.max_caption_length:
            raise PublishError(
                f"Post text exceeds {self.max_caption_length} graphemes (got {grapheme_count})",
                platform=self.platform_name,
            )

        # Get session DID
        session = self._request(
            "GET",
            f"{self.pds_url}/xrpc/com.atproto.server.getSession",
            access_token=access_token,
        ).json()
        did = session["did"]

        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        record: dict = {
            "$type": "app.bsky.feed.post",
            "text": content.text or "",
            "createdAt": now,
        }

        # Parse facets (links, mentions, hashtags)
        facets = self._parse_facets(content.text or "", access_token)
        if facets:
            record["facets"] = facets

        # Handle media uploads
        embed = self._build_embed(access_token, content)
        if embed:
            record["embed"] = embed

        resp = self._request(
            "POST",
            f"{self.pds_url}/xrpc/com.atproto.repo.createRecord",
            access_token=access_token,
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )
        data = resp.json()

        # Build the web URL from the handle and rkey
        uri = data.get("uri", "")
        rkey = uri.split("/")[-1] if uri else ""
        handle = session.get("handle", "")
        post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else None

        return PublishResult(
            platform_post_id=uri,
            url=post_url,
            extra=data,
        )

    # ------------------------------------------------------------------
    # Rich text facet parsing
    # ------------------------------------------------------------------

    def _parse_facets(self, text: str, access_token: str) -> list[dict]:
        """Parse links, mentions, and hashtags into Bluesky facet objects.

        Byte offsets are computed over the UTF-8 encoding of the text.
        """
        facets: list[dict] = []
        text.encode("utf-8")

        # Links
        link_pattern = re.compile(r"https?://[^\s\)\]>]+")
        for match in link_pattern.finditer(text):
            url = match.group(0)
            byte_start = len(text[: match.start()].encode("utf-8"))
            byte_end = len(text[: match.end()].encode("utf-8"))
            facets.append(
                {
                    "index": {"byteStart": byte_start, "byteEnd": byte_end},
                    "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
                }
            )

        # Mentions (@handle.bsky.social)
        mention_pattern = re.compile(r"(?<!\w)@([\w.-]+(?:\.[\w.-]+)+)")
        for match in mention_pattern.finditer(text):
            handle = match.group(1)
            byte_start = len(text[: match.start()].encode("utf-8"))
            byte_end = len(text[: match.end()].encode("utf-8"))
            try:
                did = self.resolve_handle(handle)
            except Exception:
                logger.warning("Could not resolve handle @%s, skipping facet", handle)
                continue
            facets.append(
                {
                    "index": {"byteStart": byte_start, "byteEnd": byte_end},
                    "features": [{"$type": "app.bsky.richtext.facet#mention", "did": did}],
                }
            )

        # Hashtags
        hashtag_pattern = re.compile(r"(?<!\w)#(\w+)")
        for match in hashtag_pattern.finditer(text):
            tag = match.group(1)
            byte_start = len(text[: match.start()].encode("utf-8"))
            byte_end = len(text[: match.end()].encode("utf-8"))
            facets.append(
                {
                    "index": {"byteStart": byte_start, "byteEnd": byte_end},
                    "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": tag}],
                }
            )

        return facets

    # ------------------------------------------------------------------
    # Media helpers
    # ------------------------------------------------------------------

    def _upload_blob(self, access_token: str, media_path: str) -> dict:
        """Upload a blob to the PDS and return the blob reference."""
        import mimetypes

        mime_type, _ = mimetypes.guess_type(media_path)
        mime_type = mime_type or "application/octet-stream"

        with open(media_path, "rb") as f:
            file_bytes = f.read()

        resp = self._request(
            "POST",
            f"{self.pds_url}/xrpc/com.atproto.repo.uploadBlob",
            access_token=access_token,
            headers={"Content-Type": mime_type},
            data=file_bytes,
        )
        data = resp.json()
        return data.get("blob", data)

    def _build_embed(self, access_token: str, content: PublishContent) -> dict | None:
        """Build the embed object for images or video."""
        media_files = content.media_files or []
        if not media_files:
            return None

        if content.post_type == PostType.VIDEO:
            blob_ref = self._upload_blob(access_token, media_files[0])
            return {
                "$type": "app.bsky.embed.video",
                "video": blob_ref,
            }

        if content.post_type == PostType.IMAGE:
            images = []
            for path in media_files[:4]:  # max 4 images
                blob_ref = self._upload_blob(access_token, path)
                alt_text = content.extra.get("alt_text", "")
                images.append({"alt": alt_text, "image": blob_ref})
            return {
                "$type": "app.bsky.embed.images",
                "images": images,
            }

        return None
