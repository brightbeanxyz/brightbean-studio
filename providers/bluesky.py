"""Bluesky / AT Protocol provider implementation."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlparse

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
PLC_DIRECTORY_URL = "https://plc.directory"

# The DIDs the PDS lookup follows: a did:plc is 24 base32 characters, a did:web
# a bare hostname (atproto allows no port or path on it).
_PLC_DID_RE = re.compile(r"^did:plc:[a-z2-7]{24}$")
_WEB_DID_RE = re.compile(r"^did:web:[A-Za-z0-9.-]+$")


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


def _pds_endpoint(did_document: dict) -> str | None:
    """Return the ``#atproto_pds`` service endpoint of a DID document, if any."""
    for service in did_document.get("service") or []:
        if not isinstance(service, dict):
            continue
        if not str(service.get("id", "")).endswith("#atproto_pds"):
            continue
        if service.get("type") != "AtprotoPersonalDataServer":
            continue
        endpoint = service.get("serviceEndpoint")
        if isinstance(endpoint, str) and endpoint.startswith("https://"):
            return endpoint.rstrip("/")
    return None


def _is_bluesky_hosted(pds_url: str) -> bool:
    """True for bsky.social and the PDS fleet Bluesky runs behind it."""
    host = (urlparse(pds_url).hostname or "").lower()
    return host == "bsky.social" or host.endswith(".bsky.network")


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

    def get_auth_url(self, redirect_uri: str, state: str, code_verifier: str | None = None) -> str:
        raise NotImplementedError("Bluesky uses session-based auth, not OAuth. Use create_session() instead.")

    def exchange_code(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokens:
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

    def resolve_pds(self, identifier: str, *, is_safe_url: Callable[[str], bool]) -> str | None:
        """Return the base URL of the PDS hosting ``identifier``, a handle or a DID.

        Follows the account's DID document: plc.directory for a did:plc, the
        domain's ``/.well-known/did.json`` for a did:web. A DID document can
        name any server, so ``is_safe_url`` vets every host that comes from it
        before it is contacted. Returns None for an email address (createSession
        accepts one, but it resolves to nothing), a DID or document this cannot
        follow, and a URL ``is_safe_url`` rejects.
        """
        identifier = identifier.strip().lstrip("@")
        if "@" in identifier:
            return None
        did = identifier if identifier.startswith("did:") else self.resolve_handle(identifier)
        if _PLC_DID_RE.match(did):
            document_url = f"{PLC_DIRECTORY_URL}/{did}"
        elif _WEB_DID_RE.match(did):
            document_url = f"https://{did.removeprefix('did:web:')}/.well-known/did.json"
            if not is_safe_url(document_url):
                return None
        else:
            return None
        endpoint = _pds_endpoint(self._request("GET", document_url).json())
        if endpoint and is_safe_url(endpoint):
            return endpoint
        return None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        handle: str,
        app_password: str,
        *,
        is_safe_url: Callable[[str], bool] | None = None,
    ) -> OAuthTokens:
        """Create an AT Protocol session using handle and app password.

        Returns an ``OAuthTokens`` with *accessJwt* as ``access_token`` and
        *refreshJwt* as ``refresh_token``.

        With ``is_safe_url``, the session is opened on the PDS hosting the
        account and ``pds_url`` is updated to it, for the caller to store on the
        account. bsky.social only knows the accounts on Bluesky's own PDS fleet:
        a handle on eurosky.social or on a self-hosted PDS cannot log in through
        it. Bluesky-hosted accounts, and any lookup that fails, keep bsky.social.
        """
        if is_safe_url is not None:
            self.pds_url = self._session_host(handle, is_safe_url)
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

    def _session_host(self, identifier: str, is_safe_url: Callable[[str], bool]) -> str:
        """Pick where a new session is opened: the account's own PDS, else bsky.social."""
        try:
            pds_url = self.resolve_pds(identifier, is_safe_url=is_safe_url)
        except Exception:
            logger.warning(
                "Could not resolve the PDS hosting %s, using %s",
                identifier,
                DEFAULT_PDS_URL,
                exc_info=True,
            )
            return DEFAULT_PDS_URL
        if pds_url is None or _is_bluesky_hosted(pds_url):
            return DEFAULT_PDS_URL
        return pds_url

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
                retryable=False,
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
        """Upload a blob to the PDS and return the blob reference.

        The file object is handed to httpx as-is so it is read in chunks off
        disk. Reading it into a bytes object first put the whole file in RSS,
        and this is reached for VIDEO too (see :meth:`_build_embed`) where
        ``MEDIA_LIBRARY_MAX_VIDEO_SIZE`` allows up to 1 GB — on a 512 MB worker
        that is not a slow leak, it is an immediate OOM kill.
        """
        import mimetypes

        mime_type, _ = mimetypes.guess_type(media_path)
        mime_type = mime_type or "application/octet-stream"

        with open(media_path, "rb") as f:
            resp = self._request(
                "POST",
                f"{self.pds_url}/xrpc/com.atproto.repo.uploadBlob",
                access_token=access_token,
                headers={
                    "Content-Type": mime_type,
                    # Explicit so httpx doesn't fall back to chunked transfer
                    # encoding, which some PDS deployments reject.
                    "Content-Length": str(os.path.getsize(media_path)),
                },
                data=f,
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
