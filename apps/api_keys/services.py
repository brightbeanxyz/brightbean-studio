"""Token generation, hashing, issuance, lookup, and revocation for ApiKey.

Token shape::

    bb_studio_<random32>_<lookup8>
    \\_______/ \\_______/ \\_____/
     prefix     secret     lookup

The secret part is what gets HMAC-hashed at rest. The lookup part is an
indexed plaintext column that makes verification O(1) without revealing
the secret. Verification then constant-time-compares the recomputed HMAC
against the stored hash.

A 30-second in-process revocation cache piggy-backs on Django's cache
framework so the next request after a revocation sees 401 quickly
without paying a DB round-trip on every authenticated call.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.api_keys.models import ApiKey

TOKEN_PREFIX = "bb_studio_"
LOOKUP_LEN = 8
REVOCATION_CACHE_TTL = 30  # seconds


# ---------------------------------------------------------------------------
# HMAC pepper derivation
# ---------------------------------------------------------------------------


def _derive_hmac_pepper() -> bytes:
    """Derive a 256-bit HMAC pepper from SECRET_KEY via HKDF.

    Distinct ``info`` bytes from the field-encryption key derivation in
    ``apps.common.encryption`` so a compromise of one secret never reveals
    the other.
    """
    secret = settings.SECRET_KEY.encode("utf-8")
    salt = getattr(settings, "ENCRYPTION_KEY_SALT", None)
    if not salt:
        raise ValueError(
            "ENCRYPTION_KEY_SALT must be set for ApiKey HMAC peppering. "
            "Generate a random value and add it to your environment."
        )
    if isinstance(salt, str):
        salt = salt.encode("utf-8")
    return HKDF(
        algorithm=SHA256(),
        length=32,
        salt=salt,
        info=b"brightbean-api-key-hmac",
    ).derive(secret)


# ---------------------------------------------------------------------------
# Token format helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedToken:
    """Result of splitting a raw bearer string into its three parts."""

    random_part: str
    lookup_prefix: str


def _hmac_hex(random_part: str) -> str:
    return hmac.new(
        _derive_hmac_pepper(),
        random_part.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _make_lookup(random_part: str) -> str:
    return hashlib.sha256(random_part.encode("utf-8")).hexdigest()[:LOOKUP_LEN]


def parse_token(raw: str) -> ParsedToken | None:
    """Split a raw bearer string into its parts, or None on malformed input.

    Strict: exact prefix match, exact part count, lookup length, and a
    plausible secret length. Anything else is treated as an unparseable
    token (caller turns this into 401).
    """
    if not isinstance(raw, str) or not raw.startswith(TOKEN_PREFIX):
        return None
    body = raw[len(TOKEN_PREFIX) :]
    # secrets.token_urlsafe() emits A-Z, a-z, 0-9, '-' and '_' — so the
    # secret itself may contain underscores. Split only on the LAST '_'
    # so the lookup suffix is always isolated correctly.
    parts = body.rsplit("_", 1)
    if len(parts) != 2:
        return None
    random_part, lookup = parts
    if len(lookup) != LOOKUP_LEN:
        return None
    # token_urlsafe(32) yields ~43 chars; allow a sensible range so a
    # future tweak to the entropy size doesn't break parsing.
    if not (32 <= len(random_part) <= 64):
        return None
    if _make_lookup(random_part) != lookup:
        # The lookup is content-addressed to the random part, so a
        # mismatch is a sure sign of tampering or a typo.
        return None
    return ParsedToken(random_part=random_part, lookup_prefix=lookup)


# ---------------------------------------------------------------------------
# Issuance & revocation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuedKey:
    """Return value of ``issue_api_key`` — the only place plaintext exists."""

    api_key: ApiKey
    plaintext_token: str


def issue_api_key(
    *,
    workspace,
    social_accounts,
    issued_by,
    name: str,
    permissions: list[str],
    expires_at=None,
) -> IssuedKey:
    """Create a new ``ApiKey`` and return the plaintext token alongside.

    The plaintext lives only in the returned ``IssuedKey``. Callers must
    surface it to the user once and never store it.

    Defense-in-depth on the inputs:
      * Issuer must hold the org-level ``manage_api_keys`` permission
        (default-granted to org ``owner`` and ``admin``). The HTTP form view
        also gates on this, but issuance is callable from shells, management
        commands, and future internal paths — re-check here so the contract
        described in the model docstring ("Issue and revoke Agent API keys")
        is enforced regardless of caller.
      * Every ``SocialAccount`` in ``social_accounts`` must belong to
        ``workspace`` (caller's UI form should also enforce this; we re-check
        here so a tampered POST can't slip a foreign account in).
      * ``permissions`` must be a subset of the issuer's current
        effective workspace permissions (so an admin can't grant a
        permission they don't transitively hold).
    """
    from apps.members.models import OrgMembership, WorkspaceMembership, has_org_permission

    sa_list = list(social_accounts)
    if not sa_list:
        raise ValueError("An API key must allowlist at least one connected account.")
    for sa in sa_list:
        if sa.workspace_id != workspace.id:
            raise ValueError(
                f"SocialAccount {sa.id} does not belong to workspace {workspace.id}."
            )

    # Org-level manage_api_keys gate — must be checked before any
    # workspace-permission logic so a non-admin who happens to have rich
    # workspace perms still can't mint a key.
    org_membership = OrgMembership.objects.filter(
        user=issued_by, organization_id=workspace.organization_id
    ).first()
    if not has_org_permission(org_membership, "manage_api_keys"):
        raise ValueError(
            f"User {issued_by} lacks the org-level 'manage_api_keys' permission "
            f"for organization {workspace.organization_id}; cannot issue API keys."
        )

    # Permission intersection check — the issuer can only grant what they hold.
    try:
        membership = WorkspaceMembership.objects.get(user=issued_by, workspace=workspace)
        granter_perms = {k for k, v in membership.effective_permissions.items() if v}
    except WorkspaceMembership.DoesNotExist as exc:
        raise ValueError(
            f"User {issued_by} has no membership in workspace {workspace}; "
            f"cannot issue an API key on their behalf."
        ) from exc

    requested = set(permissions or [])
    ungrantable = requested - granter_perms
    if ungrantable:
        raise ValueError(
            f"Issuer cannot grant permissions they don't hold: {sorted(ungrantable)}"
        )

    random_part = secrets.token_urlsafe(32)
    lookup = _make_lookup(random_part)
    token_hash = _hmac_hex(random_part)
    plaintext = f"{TOKEN_PREFIX}{random_part}_{lookup}"

    api_key = ApiKey.objects.create(
        workspace=workspace,
        issued_by=issued_by,
        name=name,
        lookup_prefix=lookup,
        token_hash=token_hash,
        permissions=sorted(requested),
        expires_at=expires_at,
    )
    api_key.social_accounts.set(sa_list)
    return IssuedKey(api_key=api_key, plaintext_token=plaintext)


def revoke_api_key(api_key: ApiKey) -> None:
    """Mark a key revoked and bust the in-process cache.

    Worst-case revocation propagation after this returns is bounded by
    ``REVOCATION_CACHE_TTL`` (30s) — any cache hit on another worker that
    happened to land before this call will still see the key as active
    until that worker's cache entry expires. Acceptable for v1.
    """
    if api_key.revoked_at is None:
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])
    invalidate_api_key_cache(api_key)


def invalidate_api_key_cache(api_key: ApiKey) -> None:
    """Bust the cached ``ApiKey`` row immediately.

    Used by:
      * ``revoke_api_key`` (manual revocation)
      * The ``m2m_changed`` signal on ``ApiKey.social_accounts`` so an
        admin who removes an allowlisted account via the Django admin
        sees that change reflected at the very next API request, not 30s
        later. Without this, the pickled prefetch cache inside
        ``verify_token``'s cached row keeps serving the pre-removal
        allowlist for ``REVOCATION_CACHE_TTL`` seconds, allowing the
        agent to continue targeting an account the admin just removed.
      * The ``post_save`` signal when ``permissions`` or ``expires_at``
        changes — same reasoning, applied to the permissions intersection
        and expiry check.
    """
    cache.delete(_active_cache_key(api_key.lookup_prefix))


# ---------------------------------------------------------------------------
# Verification (read path) — hot path; gets called on every API request.
# ---------------------------------------------------------------------------


def _active_cache_key(lookup_prefix: str) -> str:
    return f"apikey:active:{lookup_prefix}"


def verify_token(raw: str) -> ApiKey | None:
    """Resolve a raw bearer string to an active ``ApiKey``, or None.

    Returns None for: malformed token, unknown prefix, hash mismatch,
    revoked key, expired key, **issuer no longer a member of the key's
    workspace** (or issuer deleted). The caller turns None into 401.

    Constant-time compare on the hash defends against timing oracles on
    the secret part.
    """
    parsed = parse_token(raw)
    if parsed is None:
        return None

    # Cache miss-or-hit on the *active row*. A short TTL keeps stale
    # revocations from lingering more than ``REVOCATION_CACHE_TTL`` seconds.
    cache_key = _active_cache_key(parsed.lookup_prefix)
    api_key = cache.get(cache_key)
    if api_key is None:
        try:
            api_key = (
                ApiKey.objects
                .select_related("workspace", "issued_by")
                .prefetch_related("social_accounts")
                .get(lookup_prefix=parsed.lookup_prefix)
            )
        except ApiKey.DoesNotExist:
            return None
        # Only cache active rows — revocations should not be paper-tigered
        # by a stale "active" entry.
        if api_key.is_active:
            cache.set(cache_key, api_key, REVOCATION_CACHE_TTL)

    if not api_key.is_active:
        # Re-check (DB-fresh row may have been revoked since cache write)
        cache.delete(cache_key)
        return None

    expected_hash = _hmac_hex(parsed.random_part)
    if not hmac.compare_digest(expected_hash, api_key.token_hash):
        return None

    # Defense in depth: even an unrevoked, unexpired key must die if the
    # issuer was offboarded, deleted, or moved out of the workspace.
    # The model docstring promises this; the model property alone can't
    # express it without a DB hit, so we enforce it here on the auth path.
    # Indexed (user_id, workspace_id) lookup → single cheap query, run on
    # every authentication so a freshly offboarded user's key dies on the
    # very next call regardless of REVOCATION_CACHE_TTL.
    if not _issuer_still_authorized(api_key):
        cache.delete(cache_key)
        return None

    return api_key


def _issuer_still_authorized(api_key: ApiKey) -> bool:
    """True iff ``api_key.issued_by`` still has a WorkspaceMembership in the
    key's workspace.

    Returns False when the issuer was deleted (FK set to NULL by
    ``on_delete=SET_NULL``) or when their workspace membership has been
    removed. Demotion within the workspace is handled separately by the
    per-request permission intersection in the Ninja auth class — this
    function only gates *any* access at all.
    """
    from apps.members.models import WorkspaceMembership

    if api_key.issued_by_id is None:
        return False
    return WorkspaceMembership.objects.filter(
        user_id=api_key.issued_by_id,
        workspace_id=api_key.workspace_id,
    ).exists()


# ---------------------------------------------------------------------------
# Debounced last_used update — fired from the auth layer post-verification.
# ---------------------------------------------------------------------------


_LAST_USED_DEBOUNCE_SECONDS = 60


def _last_touched_cache_key(api_key_pk) -> str:
    return f"apikey:last_touched:{api_key_pk}"


def touch_last_used(api_key: ApiKey, *, ip: str | None) -> None:
    """Update ``last_used_at`` / ``last_used_ip`` at most once per 60s.

    Uses a raw ``UPDATE`` (no signals, no full save).

    The debounce is **cache-keyed**, not state-keyed: we previously gated
    on ``api_key.last_used_at`` but ``verify_token`` caches the row for
    ``REVOCATION_CACHE_TTL`` seconds, so the in-memory ``last_used_at``
    is frozen at cache-set time. Every subsequent request would have seen
    the stale value and re-issued the UPDATE, defeating the debounce
    under active use. The cache key (`apikey:last_touched:<pk>`) sidesteps
    that problem and works correctly across workers, since the cache is
    shared.
    """
    debounce_key = _last_touched_cache_key(api_key.pk)
    # `add` is an atomic set-if-not-exists — only the first caller in the
    # window wins the right to do the UPDATE; everyone else short-circuits.
    if not cache.add(debounce_key, "1", _LAST_USED_DEBOUNCE_SECONDS):
        return
    now = timezone.now()
    ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=now, last_used_ip=ip)
