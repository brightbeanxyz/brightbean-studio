"""Org-level API key management views.

Three responsibilities:

1. **List** every ``ApiKey`` in the org with enough metadata that an
   admin can decide which to revoke.
2. **Issue** a new key via a two-step HTMX-driven modal: workspace
   dropdown → (cascading) social-account multi-select + permission
   checkboxes scoped to what the issuer can grant in that workspace.
3. **Revoke** an existing key.

Every mutation re-validates inputs server-side against the same
``services.issue_api_key`` enforcement layer the Phase 1 service tests
exercise — a tampered form post that names a foreign workspace, an
out-of-org account, or an unbacked permission gets the same
``ValueError`` an out-of-process caller would.
"""

from __future__ import annotations

import functools

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import (
    PermissionDenied,
)
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.api_keys import services
from apps.api_keys.models import ApiKey
from apps.members.models import (
    PERMISSION_KEYS,
    WorkspaceMembership,
    has_org_permission,
)
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

# Permission keys defined in the registry but intentionally hidden from
# API-key issuance until the feature they gate ships. Stored API keys may
# still carry these strings; they just don't appear in the picker.
_HIDDEN_FROM_ISSUANCE = {"view_analytics"}

# ---------------------------------------------------------------------------
# Authorization decorator
# ---------------------------------------------------------------------------


def _require_manage_api_keys(view_func):
    """Gate a view on the org-level ``manage_api_keys`` permission.

    Reuses ``request.org_membership`` populated by the existing
    ``apps.members.middleware.RBACMiddleware``, so the URL doesn't have
    to carry an ``org_id`` and the sidebar link can be a plain
    ``{% url 'api_keys:list' %}``. Members lacking the permission get a
    403; users with no org membership at all get the same 403 (so the
    page never accidentally leaks that the URL exists).
    """

    @functools.wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        org_membership = getattr(request, "org_membership", None)
        if not has_org_permission(org_membership, "manage_api_keys"):
            raise PermissionDenied("You need the manage_api_keys org permission to use this page.")
        return view_func(request, *args, **kwargs)

    return login_required(_wrapped)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@_require_manage_api_keys
def list_keys(request):
    """Render the API-keys list page for the current org.

    Prefetches every relation the list template uses so the page renders
    in a constant number of queries regardless of key count. Status is
    a computed property — keys can be in one of three buckets:
    ``active``, ``revoked``, ``expired`` — so the template can chip them
    consistently.
    """
    org = request.org
    keys = (
        ApiKey.objects.filter(workspace__organization=org)
        .select_related("workspace", "issued_by")
        .prefetch_related("social_accounts")
        .order_by("-created_at")
    )
    rows = [_row_context(k) for k in keys]
    context = {
        "settings_active": "api_keys",
        "rows": rows,
        # Empty issuance form context — the modal renders inside the
        # same page so we don't need a separate route.
        "issuance": _initial_issuance_context(org, request.user),
    }
    return render(request, "api_keys/list.html", context)


def _row_context(api_key: ApiKey) -> dict:
    """Adapt an ``ApiKey`` row into the dict the list template expects."""
    if api_key.revoked_at is not None:
        status = "revoked"
    elif api_key.expires_at and api_key.expires_at <= timezone.now():
        status = "expired"
    else:
        status = "active"
    return {
        "id": api_key.id,
        "name": api_key.name,
        "workspace_name": api_key.workspace.name,
        "accounts": list(api_key.social_accounts.all()),
        "permissions": list(api_key.permissions or []),
        "last_used_at": api_key.last_used_at,
        "issued_by": api_key.issued_by,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at,
        "status": status,
    }


def _initial_issuance_context(org, user) -> dict:
    """Build the initial state for the issuance modal.

    The workspace dropdown is rendered server-side from the org's
    workspaces; everything downstream (accounts, permissions) loads via
    the HTMX partial on workspace change.
    """
    workspaces = Workspace.objects.filter(organization=org, is_archived=False).order_by("name")
    return {"workspaces": workspaces}


# ---------------------------------------------------------------------------
# HTMX partial — workspace → accounts + permissions
# ---------------------------------------------------------------------------


@_require_manage_api_keys
def workspace_options_partial(request):
    """Return a partial with the social-account checkboxes and grantable
    permission catalog for the selected workspace.

    Triggered by ``hx-trigger="change"`` on the workspace ``<select>``.
    The permission set is intersected with what the issuer (the logged-in
    user) actually holds in this workspace — an admin without
    ``publish_directly`` in workspace X cannot tick the
    ``publish_directly`` checkbox for a key in workspace X, even via a
    tampered form post (which ``services.issue_api_key`` re-validates).
    """
    workspace_id = request.GET.get("workspace_id")
    if not workspace_id:
        return HttpResponse("")
    try:
        workspace = Workspace.objects.get(id=workspace_id, organization=request.org)
    except (Workspace.DoesNotExist, ValueError, DjangoValidationError):
        # Django's UUIDField raises ``django.core.exceptions.ValidationError``
        # (not ``ValueError``) when the input doesn't parse as a UUID,
        # so a tampered HTMX trigger like ``workspace_id=not-a-uuid``
        # used to escape this handler and 500. Catch all three exception
        # types and don't differentiate a bad UUID from a foreign-org
        # workspace — the empty response is identical to "no workspace
        # picked", which is what the cascade UI expects.
        return HttpResponse("")

    # Show all connected accounts; the issue endpoint re-checks the
    # account → workspace mapping before persisting.
    accounts = SocialAccount.objects.filter(
        workspace=workspace,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    ).order_by("platform", "account_name")

    # Permission catalog scoped to what THIS issuer can grant in THIS
    # workspace — see ``_grantable_permissions`` for the rule.
    grantable = _grantable_permissions(request.user, workspace)

    context = {
        "workspace": workspace,
        "accounts": accounts,
        "grantable_permissions": grantable,
    }
    return render(request, "api_keys/_workspace_options.html", context)


def _grantable_permissions(user, workspace) -> list[tuple[str, str]]:
    """Return ``[(perm_key, label), ...]`` of permissions the user can
    grant in ``workspace``.

    The rule mirrors what ``services.issue_api_key`` will enforce
    server-side: an issuer can only grant a permission they themselves
    hold via their workspace membership. This way the UI doesn't offer
    permissions the user can't actually issue.

    Labels are derived from the permission key — ``PERMISSION_KEYS`` is
    a flat list of slugs in ``apps.members.models``, with no
    human-readable label dict alongside it. Titlecasing the underscored
    slug ("create_posts" → "Create posts") gives a friendly-enough
    label for the modal without us having to maintain a parallel dict.
    """
    try:
        membership = WorkspaceMembership.objects.select_related("custom_role").get(user=user, workspace=workspace)
    except WorkspaceMembership.DoesNotExist:
        return []
    held = {k for k, v in membership.effective_permissions.items() if v}
    return [
        (k, k.replace("_", " ").capitalize())
        for k in PERMISSION_KEYS
        if k in held and k not in _HIDDEN_FROM_ISSUANCE
    ]


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


@_require_manage_api_keys
@require_http_methods(["POST"])
def issue_key(request):
    """Issue a new key, then render the one-time-reveal modal.

    The plaintext token is shown to the user **once** in this response;
    we never store it. Subsequent requests can see the key in the list,
    but never see the token.
    """
    name = (request.POST.get("name") or "").strip()
    workspace_id = request.POST.get("workspace_id") or ""
    account_ids = request.POST.getlist("social_account_ids")
    permission_keys = request.POST.getlist("permissions")
    expires_at_str = (request.POST.get("expires_at") or "").strip()

    errors: list[str] = []
    if not name:
        errors.append("Name is required.")
    if not workspace_id:
        errors.append("Workspace is required.")
    if not account_ids:
        errors.append("Select at least one connected account.")

    workspace = None
    if workspace_id and not errors:
        try:
            workspace = Workspace.objects.get(id=workspace_id, organization=request.org)
        except (Workspace.DoesNotExist, ValueError, DjangoValidationError):
            # ``ValidationError`` covers the malformed-UUID path; see the
            # corresponding catch in ``workspace_options_partial`` for
            # the full rationale.
            errors.append("Selected workspace is not in this organisation.")

    accounts: list[SocialAccount] = []
    if workspace is not None:
        accounts = list(SocialAccount.objects.filter(id__in=account_ids, workspace=workspace))
        if len(accounts) != len(set(account_ids)):
            errors.append("Some selected accounts do not belong to that workspace.")

    expires_at = None
    if expires_at_str:
        from django.utils.dateparse import parse_datetime

        # Accept either a full ISO timestamp or a date-only value from
        # ``<input type="date">``.
        expires_at = parse_datetime(expires_at_str)
        if expires_at is None:
            from datetime import datetime, time

            try:
                d = datetime.fromisoformat(expires_at_str).date()
                expires_at = datetime.combine(d, time.max).replace(tzinfo=timezone.get_current_timezone())
            except ValueError:
                errors.append("Could not parse expires_at.")

    if errors:
        for e in errors:
            messages.error(request, e)
        return redirect("api_keys:list")

    try:
        issued = services.issue_api_key(
            workspace=workspace,
            social_accounts=accounts,
            issued_by=request.user,
            name=name,
            permissions=permission_keys,
            expires_at=expires_at,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("api_keys:list")

    # Render the one-time-reveal modal on top of the list page. We
    # deliberately do NOT redirect — a redirect (PRG) would drop the
    # plaintext token via Location header round-trip and break the
    # "shown exactly once" contract.
    org = request.org
    keys = (
        ApiKey.objects.filter(workspace__organization=org)
        .select_related("workspace", "issued_by")
        .prefetch_related("social_accounts")
        .order_by("-created_at")
    )
    context = {
        "settings_active": "api_keys",
        "rows": [_row_context(k) for k in keys],
        "issuance": _initial_issuance_context(org, request.user),
        "reveal_token": issued.plaintext_token,
        "reveal_key_name": issued.api_key.name,
    }
    return render(request, "api_keys/list.html", context)


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------


@_require_manage_api_keys
@require_http_methods(["POST"])
def revoke_key(request, key_id):
    """Soft-revoke a key.

    The actual delete is deferred to the background sweep (or a future
    admin action) — we only set ``revoked_at`` so the verify_token path
    rejects subsequent uses immediately. The cache is busted inside
    ``services.revoke_api_key`` via the signal handler, so propagation
    is immediate even across workers.
    """
    key = get_object_or_404(
        ApiKey.objects.select_related("workspace", "workspace__organization"),
        id=key_id,
    )
    # Defence in depth — never revoke a key outside the current org.
    if key.workspace.organization_id != request.org.id:
        raise Http404()
    if key.revoked_at is None:
        services.revoke_api_key(key)
        messages.success(request, f"Revoked key “{key.name}”.")
    else:
        messages.info(request, f"Key “{key.name}” was already revoked.")
    return redirect("api_keys:list")
