"""Views for managing client portal access from workspace settings."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from apps.members import services as member_services
from apps.members.decorators import require_workspace_role
from apps.members.models import Invitation, OrgMembership, WorkspaceMembership

from . import services as portal_services
from .models import MagicLinkToken

# ---------------------------------------------------------------------------
# Client List
# ---------------------------------------------------------------------------


@login_required
@require_workspace_role("manager")
@require_GET
def client_list(request, workspace_id):
    """List all clients and pending client invitations for this workspace."""
    workspace = request.workspace

    # Active clients (users with CLIENT role in this workspace)
    client_memberships = (
        WorkspaceMembership.objects.filter(
            workspace=workspace,
            workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
        )
        .select_related("user")
        .order_by("user__email")
    )

    # Get latest magic link token per client for status display
    now = timezone.now()
    active_tokens = MagicLinkToken.objects.filter(
        workspace=workspace,
        expires_at__gt=now,
    ).select_related("user")
    token_map = {}
    for t in active_tokens:
        # Keep the most recent token per user
        existing = token_map.get(t.user_id)
        if not existing or t.created_at > existing.created_at:
            token_map[t.user_id] = t

    clients_data = []
    for membership in client_memberships:
        token = token_map.get(membership.user_id)
        clients_data.append(
            {
                "membership": membership,
                "user": membership.user,
                "token": token,
            }
        )

    # Pending invitations with CLIENT role for this workspace
    pending_invites = _get_pending_client_invites(request.org, workspace)

    return render(
        request,
        "client_portal/admin/client_list.html",
        {
            "settings_active": "clients",
            "clients_data": clients_data,
            "pending_invites": pending_invites,
        },
    )


# ---------------------------------------------------------------------------
# Invite Client
# ---------------------------------------------------------------------------


@login_required
@require_workspace_role("manager")
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def invite_client(request, workspace_id):
    """Invite a new client to this workspace."""
    workspace = request.workspace
    email = request.POST.get("email", "").strip()

    if not email:
        return HttpResponse(
            '<div class="text-red-600 text-sm p-3">Email address is required.</div>',
            status=422,
        )

    workspace_assignments = [
        {
            "workspace_id": str(workspace.id),
            "role": WorkspaceMembership.WorkspaceRole.CLIENT,
        }
    ]

    try:
        member_services.create_invitation(
            org=request.org,
            email=email,
            org_role=OrgMembership.OrgRole.MEMBER,
            workspace_assignments=workspace_assignments,
            invited_by=request.user,
        )
    except ValueError as e:
        return HttpResponse(
            f'<div class="text-red-600 text-sm p-3">{e}</div>',
            status=422,
        )

    if request.headers.get("HX-Request"):
        pending_invites = _get_pending_client_invites(request.org, workspace)
        return render(
            request,
            "client_portal/admin/partials/pending_invites_section.html",
            {"pending_invites": pending_invites},
        )
    return redirect("client_portal_admin:client_list", workspace_id=workspace.id)


# ---------------------------------------------------------------------------
# Send Magic Link
# ---------------------------------------------------------------------------


@login_required
@require_workspace_role("manager")
@require_POST
@ratelimit(key="user", rate="10/m", method="POST", block=True)
def send_magic_link(request, workspace_id, membership_id):
    """Generate and send a portal magic link to a client."""
    workspace = request.workspace
    membership = get_object_or_404(
        WorkspaceMembership,
        id=membership_id,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
    )

    try:
        portal_services.generate_magic_link(
            workspace=workspace,
            client_user=membership.user,
            created_by=request.user,
        )
    except ValueError as e:
        return HttpResponse(
            f'<div class="text-red-600 text-sm p-3">{e}</div>',
            status=422,
        )

    if request.headers.get("HX-Request"):
        # Re-fetch the token for status display
        now = timezone.now()
        token = (
            MagicLinkToken.objects.filter(
                user=membership.user,
                workspace=workspace,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )
        return render(
            request,
            "client_portal/admin/partials/client_row.html",
            {
                "client": {
                    "membership": membership,
                    "user": membership.user,
                    "token": token,
                },
            },
        )
    return redirect("client_portal_admin:client_list", workspace_id=workspace.id)


# ---------------------------------------------------------------------------
# Remove Client
# ---------------------------------------------------------------------------


@login_required
@require_workspace_role("manager")
@require_POST
def remove_client(request, workspace_id, membership_id):
    """Remove a client from this workspace."""
    workspace = request.workspace
    membership = get_object_or_404(
        WorkspaceMembership,
        id=membership_id,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
    )

    # Invalidate any active magic links for this client
    MagicLinkToken.objects.filter(
        user=membership.user,
        workspace=workspace,
        expires_at__gt=timezone.now(),
    ).update(expires_at=timezone.now())

    membership.delete()

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200, headers={"HX-Trigger": "clientRemoved"})
    return redirect("client_portal_admin:client_list", workspace_id=workspace.id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pending_client_invites(org, workspace):
    """Get pending invitations that assign CLIENT role to this workspace."""
    now = timezone.now()
    all_pending = (
        Invitation.objects.filter(
            organization=org,
            accepted_at__isnull=True,
            expires_at__gt=now,
        )
        .select_related("invited_by")
        .order_by("-created_at")
    )

    # Filter for invitations that include this workspace with CLIENT role
    ws_id_str = str(workspace.id)
    client_invites = []
    for invite in all_pending:
        for assignment in invite.workspace_assignments:
            if (
                str(assignment.get("workspace_id")) == ws_id_str
                and assignment.get("role") == WorkspaceMembership.WorkspaceRole.CLIENT
            ):
                client_invites.append(invite)
                break

    return client_invites
