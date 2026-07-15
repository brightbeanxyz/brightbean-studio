"""Client-side PKCE helpers for outbound OAuth flows.

Some providers (currently TikTok) require PKCE on the authorization request.
These helpers centralise the verifier lifecycle so every OAuth-initiation
site — connect, reconnect, and the connection-link onboarding flow — stays
consistent: generate a verifier when the provider needs one, stash it in the
flow's session payload, then splat it into ``get_auth_url`` / ``exchange_code``.

The ``code_challenge`` derivation itself is provider-specific (TikTok uses a
hex SHA256 digest, not the RFC 7636 base64url encoding) and lives in the
provider, not here.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from providers.base import SocialProvider

# RFC 7636 allows a 43-128 char verifier; token_urlsafe(64) yields ~86 chars
# from the URL-safe alphabet, which is a subset of the unreserved set.
_VERIFIER_NBYTES = 64


def issue_pkce_verifier(provider: SocialProvider) -> str | None:
    """Return a fresh PKCE ``code_verifier`` when ``provider`` requires PKCE, else None.

    Callers store the result in the flow's OAuth session payload and pass it to
    ``get_auth_url`` (via :func:`pkce_kwargs`) so the provider can derive the
    ``code_challenge``; the matching callback replays it on token exchange.
    """
    return secrets.token_urlsafe(_VERIFIER_NBYTES) if provider.uses_pkce else None


def pkce_kwargs(code_verifier: str | None) -> dict[str, str]:
    """kwargs to splat into ``get_auth_url`` / ``exchange_code`` for a PKCE verifier.

    Empty when there is no verifier, so non-PKCE providers are invoked with
    exactly their original argument list.
    """
    return {"code_verifier": code_verifier} if code_verifier else {}
