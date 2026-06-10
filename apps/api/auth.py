"""Django Ninja bearer-token auth class for the Agent API.

Resolves an ``Authorization: Bearer bb_studio_…`` header to an active
``ApiKey``, then duck-types a ``request.workspace_membership`` shim so the
existing ``@require_permission`` decorator from
``apps.members.decorators`` works unchanged when called from within a
Ninja route — same protocol (``effective_permissions`` dict), no DB rows
created, no signals fired.

Defense-in-depth checks on every request:

* HMAC compare on the secret part (constant-time)
* Key not revoked, not expired
* Issuer still has a ``WorkspaceMembership`` in the key's workspace
* Per-request permission intersection of (key.permissions) ∩
  (issuer's current effective workspace permissions) — silently shrinks
  the key's grants if the issuer is demoted, with no scheduled job
* Per-IP failed-auth throttle on the 401 path (brute-force defense on
  the ``lookup_prefix`` + secret)

We deliberately keep the shim cheap (one dataclass instance, no save())
and never write a synthetic ``WorkspaceMembership`` row.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from ninja.security import HttpBearer

from apps.api.limits import is_failed_auth_ip_blocked, record_failed_auth
from apps.api_keys.models import ApiKey
from apps.api_keys.services import TOKEN_PREFIX, touch_last_used, verify_token

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class VirtualMembership:
    """Duck-typed stand-in for ``apps.members.models.WorkspaceMembership``.

    The only attribute ``@require_permission`` reads is
    ``effective_permissions`` — a dict mapping permission_key → bool.
    Keeping the shim narrow means we never have to chase additional
    properties (custom roles, signals, save()) when the membership model
    grows new fields.
    """

    effective_permissions: dict[str, bool]
    workspace: Any
    user: Any  # ``api_key.issued_by`` or AnonymousUser if the user was deleted


def _resolve_effective_permissions(api_key: ApiKey) -> dict[str, bool]:
    """Intersection of (key.permissions) ∩ (issuer's current perms).

    The issuer-membership existence check has already happened inside
    ``verify_token``; this lookup just fetches their *current* effective
    permissions and intersects with what was granted at key-issuance time.
    Demoting the issuer mid-life therefore shrinks the key silently,
    which is the documented contract.
    """
    from apps.members.models import WorkspaceMembership

    granted = set(api_key.permissions or [])
    if not granted or api_key.issued_by_id is None:
        return {k: False for k in granted}
    try:
        membership = WorkspaceMembership.objects.select_related("custom_role").get(
            user_id=api_key.issued_by_id, workspace_id=api_key.workspace_id
        )
    except WorkspaceMembership.DoesNotExist:
        # verify_token already rejects this path, but defend in depth.
        return {k: False for k in granted}
    issuer_perms = {k for k, v in membership.effective_permissions.items() if v}
    effective = granted & issuer_perms
    # Return a complete dict so ``perms.get(key, False)`` works for every
    # originally granted key even when the intersection is empty.
    return {k: (k in effective) for k in granted}


class ApiKeyAuth(HttpBearer):
    """Ninja ``HttpBearer`` that authenticates Agent API requests.

    The Ninja contract is: return a truthy value on success (becomes
    ``request.auth``); return ``None`` on failure to get a 401. We also
    attach extra context to the request so route bodies can call
    ``@require_permission`` unchanged.
    """

    def _pre_auth_reject(self, request: HttpRequest) -> bool:
        """Pre-auth defenses shared by every bearer (API key OR OAuth token).

        Returns True if the request must be refused — the caller returns
        ``None`` for a uniform 401. Logs the reason (never the credential) so
        an otherwise-opaque 401 is diagnosable from the server logs.
        """
        # Pre-auth IP throttle — short-circuit if this IP has already burned
        # through its failed-auth budget. We do this FIRST so a brute-force
        # script doesn't get to pay only the HMAC cost per attempt past the
        # threshold, AND so plain-HTTP probes (which also feed the counter,
        # see below) can't escape it by hitting the HTTPS guard first.
        # Returning None (→ uniform 401) means an attacker can't tell the
        # throttle exists; they just see their attempts continuing to fail
        # with the same response shape they were already seeing.
        if is_failed_auth_ip_blocked(request):
            # DEBUG, not WARNING: this fires on every request from an
            # already-blocked IP, so a louder level would let an attacker
            # inflate our log volume — the opposite of the throttle's intent.
            LOG.debug("Bearer auth rejected: client IP is throttled after repeated failed auth.")
            return True

        # HTTPS guard — block plaintext bearer transmission in prod.
        # ``settings.DEBUG`` lets local development over http://127.0.0.1
        # work without TLS termination. Anything else: refuse, AND count
        # the attempt toward the IP throttle so plain-HTTP brute-forcing
        # is also rate-limited (the previous behaviour leaked free 400s
        # forever, undercutting the throttle).
        if not request.is_secure() and not settings.DEBUG:
            # WARNING: in prod, SecurityMiddleware's SSL redirect means real
            # plain-HTTP traffic never reaches here, so a False is_secure()
            # signals a misconfigured proxy (missing X-Forwarded-Proto) worth
            # surfacing, not a probe.
            LOG.warning(
                "Bearer auth rejected: request.is_secure() is False. Behind a TLS-terminating "
                "proxy, forward X-Forwarded-Proto: https (see SECURE_PROXY_SSL_HEADER)."
            )
            record_failed_auth(request)
            # Generic 401 instead of a product-fingerprinting "Agent API
            # requires HTTPS" string: an attacker probing for our endpoint
            # over plain HTTP gets the same opaque response as any other
            # failed auth, denying them a pre-auth product fingerprint.
            return True

        return False

    def authenticate(self, request: HttpRequest, token: str) -> ApiKey | None:
        if self._pre_auth_reject(request):
            return None

        api_key = verify_token(token)
        if api_key is None:
            # Record this attempt against the IP so the next request can be
            # short-circuited by the throttle. INFO (not WARNING): an
            # unrecognised key is the expected, adversarial-probe path.
            LOG.info("Bearer auth rejected: API key not recognised, revoked, or expired.")
            record_failed_auth(request)
            return None

        # Resolve effective permissions and attach the membership shim.
        effective = _resolve_effective_permissions(api_key)
        user = api_key.issued_by if api_key.issued_by_id is not None else AnonymousUser()
        request.api_key = api_key  # type: ignore[attr-defined]
        request.workspace = api_key.workspace  # type: ignore[attr-defined]
        request.workspace_membership = VirtualMembership(  # type: ignore[attr-defined]
            effective_permissions=effective,
            workspace=api_key.workspace,
            user=user,
        )
        # ``request.user`` lets downstream code (e.g. audit logging,
        # author attribution on Post) treat the issuer as the actor.
        # ``user`` is ``User | AnonymousUser`` (never None — the
        # ``api_key.issued_by_id is None`` branch above produced an
        # AnonymousUser), but mypy can't narrow that across the ternary.
        request.user = user  # type: ignore[assignment]

        # Best-effort, debounced, single raw UPDATE; safe to run after
        # the response is built but doing it inline keeps the auth path
        # synchronous and easy to reason about.
        touch_last_used(api_key, ip=_client_ip(request))

        return api_key


def _client_ip(request: HttpRequest) -> str | None:
    """Delegate to the canonical, proxy-trust-aware implementation in limits.

    Same rationale as ``apps/api/middleware.py::_client_ip`` — exactly
    one IP-derivation policy across the throttle, the audit log, and
    ``ApiKey.last_used_ip``.
    """
    from apps.api.limits import _client_ip as _canonical

    return _canonical(request)


# ---------------------------------------------------------------------------
# MCP auth — bb_studio_ API keys OR OAuth 2.1 access tokens
# ---------------------------------------------------------------------------
#
# The /api/v1/mcp endpoint accepts a second credential type beyond the
# bb_studio_ key: an OAuth 2.1 access token issued by the BrightBean Studio
# Authorization Server (apps.oauth_server), which is what Claude Desktop's
# native connector flow obtains. OAuth authenticates a *person* rather than a
# minted credential, so we map the token's user to their active workspace and
# expose an ApiKey-shaped shim — the MCP handlers, throttle, and audit log all
# read an ``ApiKey``-like object off the request and run unchanged.

_MCP_OAUTH_SCOPE = "mcp"


class _AllWorkspaceAccounts:
    """Duck-types ``ApiKey.social_accounts`` for an OAuth caller.

    A scoped API key carries an explicit account allowlist; an OAuth caller
    acts as *themselves*, so their effective allowlist is every connected
    account in the workspace they're operating in. Only ``.all()`` is consumed
    by the MCP handlers (apps/mcp/handlers.py), so that's all we implement.
    """

    def __init__(self, workspace_id: Any) -> None:
        self._workspace_id = workspace_id

    def all(self):  # noqa: A003 — mirrors the Django manager method name.
        from apps.social_accounts.models import SocialAccount

        return SocialAccount.objects.for_workspace(self._workspace_id)


class OAuthMcpActor:
    """ApiKey-shaped stand-in for an OAuth-authenticated MCP caller.

    Exposes exactly the ``ApiKey`` attributes the MCP path touches — the
    handlers' ``workspace`` / ``social_accounts`` / ``issued_by``, the
    throttle's ``id`` / ``workspace_id`` / ``rate_override_*``, and the audit
    log's ``is_oauth`` discriminator — without creating a DB row. The caller's
    permissions are carried via the ``VirtualMembership`` attached separately
    to the request, so no key-style permission intersection applies here.
    """

    is_oauth = True
    # No per-key rate overrides — OAuth callers use the default tiers.
    rate_override_writes = None
    rate_override_reads = None

    def __init__(self, *, user: Any, membership: Any) -> None:
        self.issued_by = user
        self.issued_by_id = user.id
        self.workspace = membership.workspace
        self.workspace_id = membership.workspace_id
        # Namespaced id so the per-actor rate-limit cache key
        # (``apikey:<id>:w``) can't collide with a real ApiKey UUID.
        self.id = f"oauth:{user.id}"
        self.social_accounts = _AllWorkspaceAccounts(membership.workspace_id)
        # Read by ``McpAuth`` to build the request's ``VirtualMembership`` — the
        # single source of truth for this caller's permissions.
        self.effective_permissions = membership.effective_permissions


def _resolve_active_membership(user: Any):
    """Pick the workspace an OAuth caller operates in.

    Mirrors the dashboard's "current workspace" notion (see
    ``apps.members.middleware.RBACMiddleware``): the user's
    ``last_workspace_id`` when they still have a non-archived membership
    there, else their earliest-joined non-archived membership. Returns None
    when the user has no usable workspace — the caller refuses the auth.
    """
    from apps.members.models import WorkspaceMembership

    base = WorkspaceMembership.objects.select_related("workspace", "custom_role").filter(
        user=user, workspace__is_archived=False
    )
    if getattr(user, "last_workspace_id", None):
        current = base.filter(workspace_id=user.last_workspace_id).first()
        if current is not None:
            return current
    return base.order_by("added_at").first()


def _resolve_oauth_actor(token: str) -> OAuthMcpActor | None:
    """Resolve a non-bb_studio_ bearer as a django-oauth-toolkit access token.

    Looks the token up by its indexed ``token_checksum`` (the path DOT's own
    bearer validation uses; a plain ``token=`` filter scans an unindexed
    column and degrades as tokens accumulate). Returns None for any missing /
    invalid / expired / wrong-scope token, or when the user has no usable
    workspace.

    Each rejection is logged with its specific reason (never the token value)
    so an opaque 401 from an MCP client is diagnosable from the server logs.
    """
    from oauth2_provider.models import get_access_token_model

    access_token_model = get_access_token_model()
    token_checksum = hashlib.sha256(token.encode("utf-8")).hexdigest()
    tok = access_token_model.objects.select_related("user").filter(token_checksum=token_checksum).first()
    if tok is None:
        # INFO (not WARNING): an unknown bearer is the expected probe path,
        # bounded by the IP throttle; logging it louder invites flooding.
        LOG.info("Bearer auth rejected: no OAuth access token matches the presented bearer.")
        return None
    if tok.user_id is None:
        # WARNING: a token row with no user is a data anomaly, not normal traffic.
        LOG.warning("Bearer auth rejected: OAuth access token %s is not bound to a user.", tok.pk)
        return None
    # is_valid([scope]) == (not is_expired()) and allow_scopes([scope]); split so the
    # log names whether expiry or scope was the cause.
    if tok.is_expired():
        # INFO: token expiry is a normal, recurring condition (clients refresh hourly).
        LOG.info("Bearer auth rejected: OAuth access token for user %s has expired.", tok.user_id)
        return None
    if not tok.allow_scopes([_MCP_OAUTH_SCOPE]):
        # INFO: a wrong-scope token is a client-side issue, not a server alarm.
        LOG.info(
            "Bearer auth rejected: OAuth token for user %s is missing the %r scope (granted: %r).",
            tok.user_id,
            _MCP_OAUTH_SCOPE,
            tok.scope,
        )
        return None
    membership = _resolve_active_membership(tok.user)
    if membership is None:
        # WARNING: a valid, scoped, unexpired token whose user maps to no
        # workspace is the genuinely anomalous case operators want to see.
        LOG.warning(
            "Bearer auth rejected: user %s has a valid OAuth token but no active (non-archived) workspace membership.",
            tok.user_id,
        )
        return None
    return OAuthMcpActor(user=tok.user, membership=membership)


class McpAuth(ApiKeyAuth):
    """Bearer auth for the MCP router: bb_studio_ keys OR OAuth 2.1 tokens.

    A ``bb_studio_`` token reuses the parent ``ApiKeyAuth`` path verbatim —
    same IP throttle, HTTPS guard, permission intersection, and audit. Any
    other bearer is resolved as an OAuth access token issued by the BrightBean
    Studio Authorization Server (apps.oauth_server) and mapped to the user's
    active workspace via an ``OAuthMcpActor`` shim.
    """

    def authenticate(self, request: HttpRequest, token: str):  # type: ignore[override]
        if token.startswith(TOKEN_PREFIX):
            return super().authenticate(request, token)

        # OAuth path — reuse the key path's pre-auth defenses (IP throttle +
        # HTTPS guard) so both credential types share one implementation and
        # one set of rejection logs.
        if self._pre_auth_reject(request):
            return None

        actor = _resolve_oauth_actor(token)
        if actor is None:
            # _resolve_oauth_actor has already logged the specific reason.
            record_failed_auth(request)
            return None

        request.api_key = actor  # type: ignore[attr-defined]
        request.workspace = actor.workspace  # type: ignore[attr-defined]
        request.workspace_membership = VirtualMembership(  # type: ignore[attr-defined]
            effective_permissions=actor.effective_permissions,
            workspace=actor.workspace,
            user=actor.issued_by,
        )
        # Lets audit logging / author attribution treat the OAuth user as the
        # actor, exactly as the key path treats ``api_key.issued_by``.
        request.user = actor.issued_by  # type: ignore[assignment]
        return actor
