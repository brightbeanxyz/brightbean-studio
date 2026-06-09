"""LinkedIn provider variant for personal profile posting.

Two OAuth modes, picked automatically by ``settings.py`` based on which env
vars are set (see ``PLATFORM_CREDENTIALS_FROM_ENV``):

* ``oidc`` - the dev app only has "Sign In with LinkedIn using OpenID Connect"
  + "Share on LinkedIn" enabled. Profile is fetched via ``/v2/userinfo``,
  inbox is unsupported (``r_member_social`` is gated on Community Management
  API approval), and first-comment publishing is unsupported for the same
  reason (``/rest/socialActions/.../comments`` is gated on the same approval
  even though ``w_member_social`` is granted). LinkedIn does not issue refresh
  tokens for these scopes; the user reconnects manually every ~60 days.
* ``community_management`` - the dev app has Community Management API
  approval. Falls through to the base provider (``/v2/me``, full inbox,
  first comment, refresh tokens).
"""

from __future__ import annotations

from datetime import datetime

from .linkedin import API_BASE, LinkedInProvider
from .types import AccountProfile, CommentResult, InboxMessage


class LinkedInPersonalProvider(LinkedInProvider):
    """LinkedIn provider scoped to personal member posting."""

    @property
    def platform_name(self) -> str:
        return "LinkedIn (Personal)"

    @property
    def _is_oidc_mode(self) -> bool:
        # `_oauth_mode` is computed in settings.py from which env vars are set;
        # never user-configured. Defaults to OIDC for credentials that don't
        # carry it (e.g. DB-configured per-org PlatformCredential rows).
        return self.credentials.get("_oauth_mode", "oidc") == "oidc"

    @property
    def required_scopes(self) -> list[str]:
        if self._is_oidc_mode:
            return ["openid", "profile", "email", "w_member_social"]
        return ["r_basicprofile", "w_member_social", "r_member_social"]

    def get_profile(self, access_token: str) -> AccountProfile:
        if not self._is_oidc_mode:
            return super().get_profile(access_token)
        # LinkedIn's OIDC discovery declares pairwise subject types, but the
        # `sub` claim is empirically the member's Person ID - `urn:li:person:{sub}`
        # works as the post author URN. Every third-party LinkedIn integration
        # relies on this; if LinkedIn ever enforces pairwise, posting breaks.
        resp = self._request("GET", f"{API_BASE}/v2/userinfo", access_token=access_token)
        data = resp.json()
        return AccountProfile(
            platform_id=data.get("sub", ""),
            name=data.get("name", ""),
            avatar_url=data.get("picture"),
            extra=data,
        )

    def get_messages(self, access_token: str, since: datetime | None = None) -> list[InboxMessage]:
        if not self._is_oidc_mode:
            return super().get_messages(access_token, since)
        return []

    def publish_comment(self, access_token: str, post_id: str, text: str) -> CommentResult:
        if self._is_oidc_mode:
            raise NotImplementedError(
                "First comment is unsupported in OIDC mode: socialActions.CREATE "
                "requires Community Management API approval."
            )
        return super().publish_comment(access_token, post_id, text)

    def get_post_metrics(self, access_token: str, post_id: str):
        raise NotImplementedError(
            "LinkedIn does not expose personal-profile share statistics via the "
            "REST API. Only Company Pages (LinkedIn Company) have analytics."
        )

    def get_account_metrics(self, access_token: str, date_range):
        raise NotImplementedError("LinkedIn does not expose personal-profile account analytics via the REST API.")
