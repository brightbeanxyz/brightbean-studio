"""Views for team member management."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.workspaces.models import Workspace

from . import services
from .decorators import require_org_role
from .models import Invitation, OrgMembership, WorkspaceMembership

# ---------------------------------------------------------------------------
# Team Members List
# ---------------------------------------------------------------------------


@login_required
@require_org_role("member")
@require_GET
def member_list(request):
    """Show all org members and pending invitations."""
    org = request.org
    is_admin = request.org_membership.org_role in (
        OrgMembership.OrgRole.OWNER,
        OrgMembership.OrgRole.ADMIN,
    )

    # Active members with their workspace memberships
    memberships = OrgMembership.objects.filter(organization=org).select_related("user").order_by("invited_at")

    org_workspaces = Workspace.objects.filter(organization=org, is_archived=False).order_by("name")
    org_workspace_ids = [ws.id for ws in org_workspaces]

    # Prefetch workspace memberships for all org members
    members_data = []
    user_ids = [m.user_id for m in memberships]
    ws_memberships = WorkspaceMembership.objects.filter(
        user_id__in=user_ids,
        workspace_id__in=org_workspace_ids,
    ).select_related("workspace")
    ws_map = {}
    for wm in ws_memberships:
        ws_map.setdefault(wm.user_id, []).append(wm)

    for m in memberships:
        members_data.append(
            {
                "membership": m,
                "user": m.user,
                "workspace_memberships": ws_map.get(m.user_id, []),
            }
        )

    # Pending invitations
    pending_invites = []
    if is_admin:
        pending_invites = (
            Invitation.objects.filter(
                organization=org,
                accepted_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .select_related("invited_by")
            .order_by("-created_at")
        )

    # Role choices for forms (exclude owner)
    org_role_choices = [
        (OrgMembership.OrgRole.ADMIN, "Admin"),
        (OrgMembership.OrgRole.MEMBER, "Member"),
    ]
    workspace_role_choices = WorkspaceMembership.WorkspaceRole.choices

    return render(
        request,
        "members/list.html",
        {
            "settings_active": "members",
            "members_data": members_data,
            "pending_invites": pending_invites,
            "is_admin": is_admin,
            "org_workspaces": org_workspaces,
            "org_role_choices": org_role_choices,
            "workspace_role_choices": workspace_role_choices,
            "current_user": request.user,
        },
    )


# ---------------------------------------------------------------------------
# Invite Member
# ---------------------------------------------------------------------------


@login_required
@require_org_role("admin")
@require_POST
def invite_member(request):
    """Create and send a team member invitation."""
    org = request.org
    email = request.POST.get("email", "").strip()
    org_role = request.POST.get("org_role", OrgMembership.OrgRole.MEMBER)

    # Parse workspace assignments from form
    workspace_assignments = []
    org_workspaces = Workspace.objects.filter(organization=org, is_archived=False)
    for ws in org_workspaces:
        ws_key = f"ws_{ws.id}"
        if request.POST.get(ws_key):
            role = request.POST.get(f"ws_role_{ws.id}", WorkspaceMembership.WorkspaceRole.VIEWER)
            workspace_assignments.append(
                {
                    "workspace_id": str(ws.id),
                    "role": role,
                }
            )

    try:
        invitation = services.create_invitation(
            org=org,
            email=email,
            org_role=org_role,
            workspace_assignments=workspace_assignments,
            invited_by=request.user,
            inviter=request.user,
        )
    except ValueError as e:
        return HttpResponse(
            f'<div class="text-red-600 text-sm p-3">{e}</div>',
            status=422,
        )

    if request.headers.get("HX-Request"):
        return render(
            request,
            "members/partials/invitation_row.html",
            {
                "invite": invitation,
                "is_admin": True,
            },
        )
    return redirect("members:list")


# ---------------------------------------------------------------------------
# Resend / Revoke Invite
# ---------------------------------------------------------------------------


@login_required
@require_org_role("admin")
@require_POST
def resend_invite(request, invitation_id):
    """Resend an invitation email with a fresh token."""
    invitation = get_object_or_404(Invitation, id=invitation_id, organization=request.org)
    try:
        services.resend_invitation(invitation)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "members/partials/invitation_row.html",
            {
                "invite": invitation,
                "is_admin": True,
            },
        )
    return redirect("members:list")


@login_required
@require_org_role("admin")
@require_POST
def revoke_invite(request, invitation_id):
    """Revoke a pending invitation."""
    invitation = get_object_or_404(Invitation, id=invitation_id, organization=request.org)
    try:
        services.revoke_invitation(invitation)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200, headers={"HX-Trigger": "inviteRevoked"})
    return redirect("members:list")


# ---------------------------------------------------------------------------
# Accept Invite
# ---------------------------------------------------------------------------


def accept_invite(request, token):
    """Accept an invitation (public - no login required for GET)."""
    try:
        invitation = Invitation.objects.select_related("organization", "invited_by").get(token=token)
    except Invitation.DoesNotExist:
        return render(request, "members/invite_expired.html", status=404)

    if invitation.is_expired or invitation.is_accepted:
        return render(request, "members/invite_expired.html")

    # Resolve workspace names for display
    ws_display = []
    for a in invitation.workspace_assignments:
        try:
            ws = Workspace.objects.get(id=a["workspace_id"])
            ws_display.append({"name": ws.name, "role": a.get("role", "viewer")})
        except Workspace.DoesNotExist:
            pass

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next=/members/invite/{token}/accept/")

        try:
            services.accept_invitation(invitation, request.user)
        except ValueError as e:
            return render(
                request,
                "members/accept_invite.html",
                {
                    "invitation": invitation,
                    "ws_display": ws_display,
                    "error": str(e),
                },
            )

        # Redirect to first assigned workspace or home
        if request.user.last_workspace_id:
            return redirect("calendar:calendar", workspace_id=request.user.last_workspace_id)
        return redirect("/")

    # GET - store token in session for signup flow
    request.session["pending_invite_token"] = token

    return render(
        request,
        "members/accept_invite.html",
        {
            "invitation": invitation,
            "ws_display": ws_display,
            "accept_url": f"/members/invite/{token}/accept/",
        },
    )


# ---------------------------------------------------------------------------
# Update Member Role
# ---------------------------------------------------------------------------


@login_required
@require_org_role("admin")
@require_POST
def update_member_role(request, membership_id):
    """Update a member's organization role."""
    membership = get_object_or_404(OrgMembership, id=membership_id, organization=request.org)
    new_role = request.POST.get("org_role")

    try:
        services.update_member_org_role(request.org, membership, new_role, caller=request.user)
    except ValueError as e:
        return HttpResponse(
            f'<div class="text-red-600 text-sm">{e}</div>',
            status=422,
        )

    if request.headers.get("HX-Request"):
        # Refetch workspace memberships for this member
        org_workspace_ids = Workspace.objects.filter(organization=request.org, is_archived=False).values_list(
            "id", flat=True
        )
        ws_memberships = WorkspaceMembership.objects.filter(
            user=membership.user,
            workspace_id__in=org_workspace_ids,
        ).select_related("workspace")

        return render(
            request,
            "members/partials/member_row.html",
            {
                "member": {
                    "membership": membership,
                    "user": membership.user,
                    "workspace_memberships": list(ws_memberships),
                },
                "is_admin": True,
                "current_user": request.user,
                "workspace_role_choices": WorkspaceMembership.WorkspaceRole.choices,
            },
        )
    return redirect("members:list")


# ---------------------------------------------------------------------------
# Remove Member
# ---------------------------------------------------------------------------


@login_required
@require_org_role("admin")
@require_POST
def remove_member(request, membership_id):
    """Remove a member from the organization."""
    membership = get_object_or_404(OrgMembership, id=membership_id, organization=request.org)

    try:
        services.remove_member(request.org, membership, request.user)
    except ValueError as e:
        return HttpResponse(
            f'<div class="text-red-600 text-sm">{e}</div>',
            status=422,
        )

    if request.headers.get("HX-Request"):
        return HttpResponse(status=200, headers={"HX-Trigger": "memberRemoved"})
    return redirect("members:list")


# ---------------------------------------------------------------------------
# Manage Workspace Assignments
# ---------------------------------------------------------------------------


@login_required
@require_org_role("admin")
def manage_workspaces(request, membership_id):
    """GET: show workspace assignment form. POST: update assignments."""
    membership = get_object_or_404(OrgMembership, id=membership_id, organization=request.org)
    org = request.org
    org_workspaces = Workspace.objects.filter(organization=org, is_archived=False).order_by("name")

    if request.method == "POST":
        assignments = []
        for ws in org_workspaces:
            ws_key = f"ws_{ws.id}"
            if request.POST.get(ws_key):
                role = request.POST.get(
                    f"ws_role_{ws.id}",
                    WorkspaceMembership.WorkspaceRole.VIEWER,
                )
                assignments.append(
                    {
                        "workspace_id": str(ws.id),
                        "role": role,
                    }
                )

        try:
            services.update_workspace_assignments(org, membership.user, assignments, inviter=request.user)
        except ValueError as e:
            return HttpResponse(str(e), status=422)

        if request.headers.get("HX-Request"):
            # Return updated member row
            ws_memberships = WorkspaceMembership.objects.filter(
                user=membership.user,
                workspace_id__in=[ws.id for ws in org_workspaces],
            ).select_related("workspace")
            return render(
                request,
                "members/partials/member_row.html",
                {
                    "member": {
                        "membership": membership,
                        "user": membership.user,
                        "workspace_memberships": list(ws_memberships),
                    },
                    "is_admin": True,
                    "current_user": request.user,
                    "workspace_role_choices": WorkspaceMembership.WorkspaceRole.choices,
                },
            )
        return redirect("members:list")

    # GET - render assignment form
    current_ws_memberships = WorkspaceMembership.objects.filter(
        user=membership.user,
        workspace_id__in=[ws.id for ws in org_workspaces],
    ).select_related("workspace")
    current_map = {wm.workspace_id: wm for wm in current_ws_memberships}

    workspace_data = []
    for ws in org_workspaces:
        wm = current_map.get(ws.id)
        workspace_data.append(
            {
                "workspace": ws,
                "assigned": wm is not None,
                "current_role": wm.workspace_role if wm else WorkspaceMembership.WorkspaceRole.VIEWER,
            }
        )

    return render(
        request,
        "members/partials/workspace_assignments.html",
        {
            "membership": membership,
            "workspace_data": workspace_data,
            "workspace_role_choices": WorkspaceMembership.WorkspaceRole.choices,
        },
    )
