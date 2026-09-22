"""Team member invite and management services."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils import timezone

from apps.common.mail import EmailNotSentError, send_or_raise, transactional
from apps.workspaces.models import Workspace

from .models import Invitation, OrgMembership, WorkspaceMembership

logger = logging.getLogger(__name__)

INVITE_EXPIRY_DAYS = 7

# Role hierarchies (must match decorators.py).
ORG_ROLE_LEVEL = {
    OrgMembership.OrgRole.OWNER: 3,
    OrgMembership.OrgRole.ADMIN: 2,
    OrgMembership.OrgRole.MEMBER: 1,
}
WS_ROLE_LEVEL = {
    WorkspaceMembership.WorkspaceRole.OWNER: 6,
    WorkspaceMembership.WorkspaceRole.MANAGER: 5,
    WorkspaceMembership.WorkspaceRole.EDITOR: 4,
    WorkspaceMembership.WorkspaceRole.CONTRIBUTOR: 3,
    WorkspaceMembership.WorkspaceRole.CLIENT: 2,
    WorkspaceMembership.WorkspaceRole.VIEWER: 1,
}


def _inviter_org_level(inviter, org):
    membership = OrgMembership.objects.filter(user=inviter, organization=org).first()
    if not membership:
        return 0
    return ORG_ROLE_LEVEL.get(membership.org_role, 0)


def _inviter_workspace_level(inviter, org, workspace_id):
    """Return inviter's effective workspace role level in *workspace_id*.

    Org owners are treated as workspace owners across every workspace in their
    org (matches the spirit of `@require_org_role("owner")` gating org-wide
    actions). Org admins are bounded by their actual workspace membership; if
    they aren't a member, they have zero authority on that workspace.
    """
    if _inviter_org_level(inviter, org) >= ORG_ROLE_LEVEL[OrgMembership.OrgRole.OWNER]:
        return WS_ROLE_LEVEL[WorkspaceMembership.WorkspaceRole.OWNER]
    ws_membership = WorkspaceMembership.objects.filter(user=inviter, workspace_id=workspace_id).first()
    if not ws_membership:
        return 0
    return WS_ROLE_LEVEL.get(ws_membership.workspace_role, 0)


def create_invitation(org, email, org_role, workspace_assignments, invited_by, *, inviter=None):
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

    # Don't allow inviting as owner (use ownership transfer instead).
    if org_role == OrgMembership.OrgRole.OWNER:
        raise ValueError("Cannot invite someone as an organization owner.")

    # Enforce org-role hierarchy: inviter cannot grant a role above their own.
    # Default `inviter` to `invited_by` so legacy callers without the kwarg
    # still get an enforced check (no silent bypass).
    effective_inviter = inviter or invited_by
    inviter_org_level = _inviter_org_level(effective_inviter, org)
    requested_org_level = ORG_ROLE_LEVEL.get(org_role, 0)
    if requested_org_level == 0:
        raise ValueError(f"Unknown org role: {org_role!r}.")
    # Strict inequality on org-role, but ONLY for the admin/owner tier:
    # blocks lateral admin grants (a compromised admin shouldn't be able to
    # clone their privileges) while still permitting member-tier invites —
    # which the workspace-manager → client-invite flow relies on, since
    # those managers are themselves only org-role=member.
    admin_level = ORG_ROLE_LEVEL[OrgMembership.OrgRole.ADMIN]
    if requested_org_level >= admin_level and requested_org_level >= inviter_org_level:
        raise ValueError("Only organization owners can invite someone as an admin.")

    # Validate workspace assignments belong to org AND don't exceed inviter's
    # workspace role in that specific workspace.
    org_workspace_ids = set(Workspace.objects.filter(organization=org, is_archived=False).values_list("id", flat=True))
    for assignment in workspace_assignments:
        import uuid as uuid_mod

        ws_id = uuid_mod.UUID(str(assignment["workspace_id"]))
        if ws_id not in org_workspace_ids:
            raise ValueError(f"Workspace {ws_id} does not belong to this organization.")

        requested_ws_role = assignment.get("role", WorkspaceMembership.WorkspaceRole.VIEWER)
        requested_ws_level = WS_ROLE_LEVEL.get(requested_ws_role, 0)
        if requested_ws_level == 0:
            raise ValueError(f"Unknown workspace role: {requested_ws_role!r}.")
        inviter_ws_level = _inviter_workspace_level(effective_inviter, org, ws_id)
        if requested_ws_level > inviter_ws_level:
            raise ValueError("You cannot grant a workspace role higher than your own in that workspace.")

    # Revoking an invitation sets expires_at to now, which clears the "already
    # pending" guard above — so revoke-then-reinvite was a loop that handed out
    # a fresh send budget every time round. Carrying the count forward and
    # refusing at the cap closes it; the window keeps a genuinely stale
    # invitation from blocking the address for good.
    already_sent = _recent_send_count(org, email)
    max_sends = getattr(settings, "INVITE_MAX_SENDS", 3)
    if already_sent >= max_sends:
        raise ValueError(
            f"This address has already been emailed {already_sent} times about joining "
            f"this organization. Check the address with them directly rather than sending it again."
        )

    _check_org_invite_budget(org)

    invitation = Invitation.objects.create(
        organization=org,
        email=email,
        org_role=org_role,
        workspace_assignments=workspace_assignments,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS),
        send_count=already_sent,
    )

    if not _send_invite_email(invitation):
        # The invitation row is kept on purpose: it is valid, it shows up in the
        # pending list, and Resend is right there. What must not happen is the
        # caller being told the email went out. ``last_sent_at`` stays null,
        # which is the signal the views use.
        logger.warning("Invitation %s created but the email was not sent", invitation.pk)

    return invitation


def _recent_send_count(org, email) -> int:
    """How many times this address has been mailed about this org lately.

    Bounded by the invitation lifetime rather than counting forever: the loop
    worth stopping happens in minutes, while an invitation that quietly expired
    months ago should not bar someone from being invited today.
    """
    since = timezone.now() - timedelta(days=INVITE_EXPIRY_DAYS)
    return (
        Invitation.objects.filter(
            organization=org,
            email=email,
            accepted_at__isnull=True,
            created_at__gte=since,
        )
        .order_by("-created_at")
        .values_list("send_count", flat=True)
        .first()
        or 0
    )


def _check_org_invite_budget(org) -> None:
    """Stop one organization inviting the world in a day.

    A new signup owns an organization one request after registering, with no
    verified address behind it — which is what the run of "My Organization"
    invitations to unrelated strangers in the Resend log looks like. A daily
    ceiling is the cheapest control that a real team growing quickly will never
    notice.
    """
    from apps.common.mail import reserve_budget

    limit = getattr(settings, "INVITE_MAX_PER_ORG_PER_DAY", 25)
    day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not reserve_budget("invite_org_day", str(org.id), day_start, limit, fail_open=False):
        logger.warning("Organization %s hit the daily invitation cap of %d", org.id, limit)
        raise ValueError(
            f"This organization has sent its {limit} invitation emails for today. You can send more tomorrow."
        )


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

    Throttled two ways, because this had neither and it showed: the Resend log
    has the same address invited four times in thirteen seconds and another
    twelve times in five minutes. A cooldown stops the button being leaned on;
    the total cap stops a genuine "they never got it" turning into a campaign.

    The checks below exist to produce a message worth reading; the cap and the
    cooldown are actually *enforced* atomically in ``_reserve_invite_send``,
    which is the only place that can be sure two requests are not deciding at
    the same moment.

    Raises:
        ValueError: If the invitation is already accepted, is inside its
            cooldown, has been sent as many times as it is allowed, or the
            email could not be sent.
    """
    if invitation.is_accepted:
        raise ValueError("This invitation has already been accepted.")

    max_sends = getattr(settings, "INVITE_MAX_SENDS", 3)
    if invitation.send_count >= max_sends:
        raise ValueError(
            f"This invitation has already been sent {invitation.send_count} times. "
            "Check the address with them directly rather than sending it again."
        )

    cooldown = timedelta(seconds=getattr(settings, "INVITE_RESEND_COOLDOWN_SECONDS", 300))
    if invitation.last_sent_at and timezone.now() - invitation.last_sent_at < cooldown:
        wait = cooldown - (timezone.now() - invitation.last_sent_at)
        raise ValueError(
            f"This invitation was just sent. You can send it again in {int(wait.total_seconds() // 60) + 1} minute(s)."
        )

    # A resend is an invitation email like any other, so it comes out of the
    # same daily allowance. Charging only ``create`` would have made the cap a
    # third of what it claims: 25 invitations each resent twice is 75 emails
    # from an organization told it had spent its 25.
    _check_org_invite_budget(invitation.organization)

    import secrets

    invitation.token = secrets.token_urlsafe(32)
    invitation.expires_at = timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS)
    invitation.save(update_fields=["token", "expires_at"])

    if not _send_invite_email(invitation):
        # Either a competing request took the slot between the checks above and
        # the atomic reservation, or the send itself was refused. Reporting
        # success would leave someone waiting for an email that is not coming.
        raise ValueError("We could not send that invitation right now. Please try again shortly.")

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


def update_member_org_role(org, membership, new_role, *, caller=None):
    """Update a member's organization role.

    Raises:
        ValueError: If demoting the last owner, or if `caller` lacks authority
            to either remove the existing role or set the requested one.
    """
    if new_role == OrgMembership.OrgRole.OWNER:
        raise ValueError("Cannot promote to owner. Transfer ownership instead.")

    new_level = ORG_ROLE_LEVEL.get(new_role, 0)
    if new_level == 0:
        raise ValueError(f"Unknown org role: {new_role!r}.")

    # Caller hierarchy: must be at least as senior as both the existing role
    # and the requested role. Blocks an admin demoting an owner (existing
    # role outranks them) or escalating someone above their own tier.
    if caller is not None:
        caller_level = _inviter_org_level(caller, org)
        existing_level = ORG_ROLE_LEVEL.get(membership.org_role, 0)
        if caller_level < existing_level:
            raise ValueError("You cannot change a member whose role is higher than your own.")
        admin_level = ORG_ROLE_LEVEL[OrgMembership.OrgRole.ADMIN]
        if new_level >= admin_level and new_level >= caller_level:
            raise ValueError("Only organization owners can promote someone to admin.")

    if membership.org_role == OrgMembership.OrgRole.OWNER:
        owner_count = OrgMembership.objects.filter(organization=org, org_role=OrgMembership.OrgRole.OWNER).count()
        if owner_count <= 1:
            raise ValueError("Cannot change the role of the last organization owner.")

    membership.org_role = new_role
    membership.save(update_fields=["org_role"])
    return membership


def update_workspace_assignments(org, user, assignments, *, inviter=None):
    """Update workspace assignments for a member.

    Args:
        org: Organization.
        user: The user whose assignments to update.
        assignments: list of {"workspace_id": "...", "role": "..."}.
        inviter: The user performing the change (for role-hierarchy enforcement).
            When None, no caller-level check is applied (used only by tests or
            internal admin scripts).
    """
    import uuid as uuid_mod

    org_workspace_ids = set(Workspace.objects.filter(organization=org, is_archived=False).values_list("id", flat=True))

    desired = {}
    for a in assignments:
        ws_id = uuid_mod.UUID(str(a["workspace_id"]))
        if ws_id not in org_workspace_ids:
            raise ValueError(f"Workspace {ws_id} does not belong to this organization.")
        requested_role = a.get("role", WorkspaceMembership.WorkspaceRole.VIEWER)
        requested_level = WS_ROLE_LEVEL.get(requested_role, 0)
        if requested_level == 0:
            raise ValueError(f"Unknown workspace role: {requested_role!r}.")
        if inviter is not None:
            inviter_level = _inviter_workspace_level(inviter, org, ws_id)
            if requested_level > inviter_level:
                raise ValueError("You cannot grant a workspace role higher than your own in that workspace.")
        desired[ws_id] = requested_role

    # Current assignments in this org
    current = WorkspaceMembership.objects.filter(
        user=user,
        workspace_id__in=org_workspace_ids,
    )
    current_map = {m.workspace_id: m for m in current}

    # The inviter must also have authority over the *existing* role. Without
    # this check, a viewer-level admin could silently downgrade an owner by
    # submitting the form with role="viewer" (request_level <= inviter_level
    # passes the earlier check; the actual demotion of the owner row is the
    # privilege violation). Apply to both removal and role-change paths.
    if inviter is not None:
        for ws_id, m in current_map.items():
            existing_level = WS_ROLE_LEVEL.get(m.workspace_role, 0)
            inviter_level = _inviter_workspace_level(inviter, org, ws_id)
            if ws_id not in desired:
                # About to delete this membership entirely.
                if existing_level > inviter_level:
                    raise ValueError(
                        "You cannot remove a workspace membership whose current role is higher than your own."
                    )
            elif desired[ws_id] != m.workspace_role and existing_level > inviter_level:
                # About to change this membership's role.
                raise ValueError("You cannot modify a workspace membership whose current role is higher than your own.")

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


def _reserve_invite_send(invitation):
    """Claim this invitation's next send slot, atomically.

    Both the cap and the cooldown are expressed as conditions on the UPDATE
    rather than as an if-statement over values read a moment earlier. Two
    resend requests arriving together would otherwise both read send_count=2
    against a maximum of 3, both decide they were fine, and both send.

    Returns a receipt to hand to ``_release_invite_send`` if the email does not
    go out, or None when the slot was already taken — by the cap, by the
    cooldown, or by a competing request that got there first.
    """
    max_sends = getattr(settings, "INVITE_MAX_SENDS", 3)
    cooldown = timedelta(seconds=getattr(settings, "INVITE_RESEND_COOLDOWN_SECONDS", 300))
    now = timezone.now()
    previous_last_sent_at = invitation.last_sent_at

    claimed = (
        Invitation.objects.filter(pk=invitation.pk, send_count__lt=max_sends)
        .filter(Q(last_sent_at__isnull=True) | Q(last_sent_at__lte=now - cooldown))
        .update(send_count=F("send_count") + 1, last_sent_at=now)
    )
    if not claimed:
        return None

    invitation.send_count += 1
    invitation.last_sent_at = now
    return {"previous_last_sent_at": previous_last_sent_at}


def _release_invite_send(invitation, receipt) -> None:
    """Give the slot back when the email did not actually go out.

    A misconfigured mail server, or a send the outbound budget declined, must
    not cost the recipient one of the few invitations they are allowed — and it
    must not start the cooldown either, or a failed send would make the person
    trying to help wait five minutes to try again. So ``last_sent_at`` is put
    back to what it was, not merely left where the reservation set it.
    """
    Invitation.objects.filter(pk=invitation.pk, send_count__gt=0).update(
        send_count=F("send_count") - 1,
        last_sent_at=receipt["previous_last_sent_at"],
    )
    invitation.send_count = max(0, invitation.send_count - 1)
    invitation.last_sent_at = receipt["previous_last_sent_at"]


def _send_invite_email(invitation) -> bool:
    """Send the invite email for an invitation. Returns whether it went out.

    The slot is reserved before the send and released if the send fails, so the
    accounting is atomic without charging for mail nobody received.
    """
    receipt = _reserve_invite_send(invitation)
    if receipt is None:
        logger.info("Invitation %s has no send slot available", invitation.pk)
        return False

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
        # Someone is waiting on this to get into the product, so it is exempt
        # from the per-recipient cap (never the global one). The invite flood in
        # the Resend log is held back by the resend cooldown and the per-org
        # daily cap, not by the notification cap.
        headers=transactional(),
    )
    msg.attach_alternative(html_content, "text/html")

    try:
        send_or_raise(msg)
    except EmailNotSentError:
        logger.warning("Invite email to %s was not sent", invitation.email)
        _release_invite_send(invitation, receipt)
        return False
    except Exception:
        logger.exception("Failed to send invite email to %s", invitation.email)
        _release_invite_send(invitation, receipt)
        return False

    return True
