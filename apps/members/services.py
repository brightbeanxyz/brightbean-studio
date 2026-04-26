"""Team member invite and management services."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.workspaces.models import Workspace

from .models import Invitation, OrgMembership, WorkspaceMembership

logger = logging.getLogger(__name__)

INVITE_EXPIRY_DAYS = 7


def create_invitation(org, email, org_role, workspace_assignments, invited_by):
    """Create an invitation and send the invite email.

    Args:
        org: Organization to invite into.
        email: Invitee email address.
        org_role: "member" or "admin".
        workspace_assignments: list of {"workspace_id": "...", "role": "..."}.
        invited_by: User who is sending the invite.

    Returns:
        The created Invitation.

    Raises:
        ValueError: If the email already belongs to a member or has a pending invite.
    """
    email = email.strip().lower()

    # Check if already a member
    if OrgMembership.objects.filter(organization=org, user__email=email).exists():
        raise ValueError("This person is already a member of your organization.")

    # Check for pending invite
    pending = Invitation.objects.filter(
        organization=org,
        email=email,
        accepted_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()
    if pending:
        raise ValueError("An invitation is already pending for this email. You can resend it instead.")

    # Validate workspace assignments belong to org
    org_workspace_ids = set(Workspace.objects.filter(organization=org, is_archived=False).values_list("id", flat=True))
    for assignment in workspace_assignments:
        import uuid as uuid_mod

        ws_id = uuid_mod.UUID(str(assignment["workspace_id"]))
        if ws_id not in org_workspace_ids:
            raise ValueError(f"Workspace {ws_id} does not belong to this organization.")

    # Don't allow inviting as owner
    if org_role == OrgMembership.OrgRole.OWNER:
        raise ValueError("Cannot invite someone as an organization owner.")

    invitation = Invitation.objects.create(
        organization=org,
        email=email,
        org_role=org_role,
        workspace_assignments=workspace_assignments,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS),
    )

    _send_invite_email(invitation)
    return invitation


def accept_invitation(invitation, user, *, require_email_match=True):
    """Accept an invitation: create org + workspace memberships.

    Args:
        invitation: The Invitation to accept.
        user: The User accepting.
        require_email_match: When True (default), reject if the user's email
            differs from the invitation's. The signup signal path passes
            False because the session-bound token is itself proof of email
            delivery (and social logins return whatever email the provider
            owns, which often differs from the invited address).

    Raises:
        ValueError: If the invitation is expired, already accepted, or the
            user's email does not match (when require_email_match is True).
    """
    if invitation.is_expired:
        raise ValueError("This invitation has expired.")
    if invitation.is_accepted:
        raise ValueError("This invitation has already been accepted.")

    if require_email_match and user.email.lower() != invitation.email.lower():
        raise ValueError("This invitation was sent to a different email address.")

    # Create org membership (skip if exists, e.g. user was already added)
    org_membership, created = OrgMembership.objects.get_or_create(
        user=user,
        organization=invitation.organization,
        defaults={"org_role": invitation.org_role},
    )

    # Create workspace memberships
    for assignment in invitation.workspace_assignments:
        import uuid as uuid_mod

        ws_id = uuid_mod.UUID(str(assignment["workspace_id"]))
        role = assignment.get("role", WorkspaceMembership.WorkspaceRole.VIEWER)
        WorkspaceMembership.objects.get_or_create(
            user=user,
            workspace_id=ws_id,
            defaults={"workspace_role": role},
        )

    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])

    # Set last workspace for dashboard redirect
    if invitation.workspace_assignments:
        import uuid as uuid_mod

        first_ws_id = uuid_mod.UUID(str(invitation.workspace_assignments[0]["workspace_id"]))
        user.last_workspace_id = first_ws_id
        user.save(update_fields=["last_workspace_id"])

    return org_membership


def resend_invitation(invitation):
    """Resend an invitation with a fresh token and expiry.

    Raises:
        ValueError: If the invitation is already accepted.
    """
    if invitation.is_accepted:
        raise ValueError("This invitation has already been accepted.")

    import secrets

    invitation.token = secrets.token_urlsafe(32)
    invitation.expires_at = timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS)
    invitation.save(update_fields=["token", "expires_at"])

    _send_invite_email(invitation)
    return invitation


def revoke_invitation(invitation):
    """Revoke an invitation by expiring it immediately."""
    if invitation.is_accepted:
        raise ValueError("Cannot revoke an already accepted invitation.")
    invitation.expires_at = timezone.now()
    invitation.save(update_fields=["expires_at"])


def remove_member(org, membership, removed_by):
    """Remove a member from the organization and all its workspaces.

    Args:
        org: Organization.
        membership: The OrgMembership to remove.
        removed_by: User performing the removal.

    Raises:
        ValueError: If trying to remove the last owner or yourself.
    """
    if membership.user_id == removed_by.id:
        raise ValueError("You cannot remove yourself from the organization.")

    if membership.org_role == OrgMembership.OrgRole.OWNER:
        owner_count = OrgMembership.objects.filter(organization=org, org_role=OrgMembership.OrgRole.OWNER).count()
        if owner_count <= 1:
            raise ValueError("Cannot remove the last organization owner.")

    # Delete workspace memberships in this org's workspaces
    org_workspace_ids = Workspace.objects.filter(organization=org).values_list("id", flat=True)
    WorkspaceMembership.objects.filter(
        user=membership.user,
        workspace_id__in=org_workspace_ids,
    ).delete()

    membership.delete()


def update_member_org_role(org, membership, new_role):
    """Update a member's organization role.

    Raises:
        ValueError: If demoting the last owner.
    """
    if new_role == OrgMembership.OrgRole.OWNER:
        raise ValueError("Cannot promote to owner. Transfer ownership instead.")

    if membership.org_role == OrgMembership.OrgRole.OWNER:
        owner_count = OrgMembership.objects.filter(organization=org, org_role=OrgMembership.OrgRole.OWNER).count()
        if owner_count <= 1:
            raise ValueError("Cannot change the role of the last organization owner.")

    membership.org_role = new_role
    membership.save(update_fields=["org_role"])
    return membership


def update_workspace_assignments(org, user, assignments):
    """Update workspace assignments for a member.

    Args:
        org: Organization.
        user: The user whose assignments to update.
        assignments: list of {"workspace_id": "...", "role": "..."}.
    """
    import uuid as uuid_mod

    org_workspace_ids = set(Workspace.objects.filter(organization=org, is_archived=False).values_list("id", flat=True))

    desired = {}
    for a in assignments:
        ws_id = uuid_mod.UUID(str(a["workspace_id"]))
        if ws_id not in org_workspace_ids:
            raise ValueError(f"Workspace {ws_id} does not belong to this organization.")
        desired[ws_id] = a.get("role", WorkspaceMembership.WorkspaceRole.VIEWER)

    # Current assignments in this org
    current = WorkspaceMembership.objects.filter(
        user=user,
        workspace_id__in=org_workspace_ids,
    )
    current_map = {m.workspace_id: m for m in current}

    # Remove memberships not in desired
    for ws_id, m in current_map.items():
        if ws_id not in desired:
            m.delete()

    # Create or update
    for ws_id, role in desired.items():
        if ws_id in current_map:
            m = current_map[ws_id]
            if m.workspace_role != role:
                m.workspace_role = role
                m.save(update_fields=["workspace_role"])
        else:
            WorkspaceMembership.objects.create(
                user=user,
                workspace_id=ws_id,
                workspace_role=role,
            )


def _send_invite_email(invitation):
    """Send the invite email for an invitation."""
    app_url = getattr(settings, "APP_URL", "http://localhost:8000").rstrip("/")
    accept_url = f"{app_url}/members/invite/{invitation.token}/accept/"

    context = {
        "invitation": invitation,
        "accept_url": accept_url,
        "org_name": invitation.organization.name,
        "invited_by": invitation.invited_by,
        "app_url": app_url,
    }

    subject = f"You've been invited to join {invitation.organization.name} on Brightbean"
    text_content = render_to_string("members/email/invite.txt", context)
    html_content = render_to_string("members/email/invite.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
        to=[invitation.email],
    )
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send invite email to %s", invitation.email)
