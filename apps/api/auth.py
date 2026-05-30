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

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from ninja.security import HttpBearer

from apps.api_keys.models import ApiKey
from apps.api_keys.services import touch_last_used, verify_token
from apps.api.limits import is_failed_auth_ip_blocked, record_failed_auth


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
        membership = (
            WorkspaceMembership.objects
            .select_related("custom_role")
            .get(user_id=api_key.issued_by_id, workspace_id=api_key.workspace_id)
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

    def authenticate(self, request: HttpRequest, token: str) -> ApiKey | None:
        # Pre-auth IP throttle — short-circuit if this IP has already burned
        # through its failed-auth budget. We do this FIRST so a brute-force
        # script doesn't get to pay only the HMAC cost per attempt past the
        # threshold, AND so plain-HTTP probes (which also feed the counter,
        # see below) can't escape it by hitting the HTTPS guard first.
        # Returning None (→ uniform 401) means an attacker can't tell the
        # throttle exists; they just see their attempts continuing to fail
        # with the same response shape they were already seeing.
        if is_failed_auth_ip_blocked(request):
            return None

        # HTTPS guard — block plaintext bearer transmission in prod.
        # ``settings.DEBUG`` lets local development over http://127.0.0.1
        # work without TLS termination. Anything else: refuse, AND count
        # the attempt toward the IP throttle so plain-HTTP brute-forcing
        # is also rate-limited (the previous behaviour leaked free 400s
        # forever, undercutting the throttle).
        if not request.is_secure() and not settings.DEBUG:
            record_failed_auth(request)
            # Generic 401 instead of a product-fingerprinting "Agent API
            # requires HTTPS" string: an attacker probing for our endpoint
            # over plain HTTP gets the same opaque response as any other
            # failed auth, denying them a pre-auth product fingerprint.
            return None

        api_key = verify_token(token)
        if api_key is None:
            # Record this attempt against the IP so the next request can
            # be short-circuited by the check above.
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
        request.user = user  # type: ignore[attr-defined]

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
