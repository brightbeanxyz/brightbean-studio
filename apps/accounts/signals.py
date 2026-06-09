from allauth.account.signals import user_signed_up
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


def provision_organization_and_workspace(user):
    """Create a default Organization, Workspace, and memberships for a new user.

    Skips if the user already belongs to an organization (e.g. invited users).
    Safe to call multiple times - the guard is idempotent.
    """
    from apps.members.models import OrgMembership, WorkspaceMembership
    from apps.organizations.models import Organization
    from apps.workspaces.models import Workspace

    # Skip if user was invited to an existing org or already provisioned
    if OrgMembership.objects.filter(user=user).exists():
        return

    org = Organization.objects.create(
        name="My Organization",
        default_timezone="UTC",
    )

    OrgMembership.objects.create(
        user=user,
        organization=org,
        org_role=OrgMembership.OrgRole.OWNER,
    )

    # Create a default workspace so the user can start immediately
    workspace = Workspace.objects.create(
        organization=org,
        name="My Workspace",
        description="Your default workspace. Rename it anytime.",
    )

    WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )

    # Set as last workspace so dashboard redirects here
    user.last_workspace_id = workspace.id
    user.save(update_fields=["last_workspace_id"])


def _set_org_timezone_from_browser(request, user):
    """Update the user's organization timezone from the browser_timezone cookie."""
    from urllib.parse import unquote
    from zoneinfo import available_timezones

    from apps.members.models import OrgMembership

    browser_tz = request.COOKIES.get("browser_timezone", "")
    # Defensive length cap: IANA timezone names are all under 40 chars.
    # Reject anything suspiciously long before decoding/validating.
    if not browser_tz or len(browser_tz) > 64:
        return
    browser_tz = unquote(browser_tz)
    if len(browser_tz) > 64 or browser_tz not in available_timezones():
        return
    membership = OrgMembership.objects.filter(user=user).select_related("organization").first()
    if membership and membership.organization.default_timezone == "UTC":
        membership.organization.default_timezone = browser_tz
        membership.organization.save(update_fields=["default_timezone"])


@receiver(user_signed_up)
def create_organization_on_signup(sender, request, user, **kwargs):
    """Handle allauth signup - create org + workspace.

    If the user signed up via an invitation link, accept the invitation
    instead of creating a default org. The invite token is stored in
    the session by the accept_invite view.

    By this point, post_save has already fired and provisioned a default
    "My Organization". If invite acceptance succeeds, we clean up that
    default org so the user only belongs to the invited org.
    """
    pending_token = request.session.pop("pending_invite_token", None)
    if pending_token:
        from apps.members.models import Invitation, OrgMembership
        from apps.members.services import accept_invitation
        from apps.workspaces.models import Workspace

        try:
            invitation = Invitation.objects.get(
                token=pending_token,
                accepted_at__isnull=True,
            )
            if not invitation.is_expired:
                invited_org_id = invitation.organization_id

                # Accept the invitation (creates OrgMembership + WorkspaceMemberships).
                # Skip the email-match check: the session token is proof of
                # delivery, and social logins return a provider-controlled email
                # that often differs from the invited address.
                accept_invitation(invitation, user, require_email_match=False)

                # Clean up the default org that post_save created, if it's
                # different from the invited org.
                default_memberships = OrgMembership.objects.filter(
                    user=user,
                ).exclude(organization_id=invited_org_id)
                for membership in default_memberships:
                    org = membership.organization
                    membership.delete()
                    # Only delete the org if it's the auto-provisioned one
                    # and has no other members.
                    if org.name == "My Organization" and not org.memberships.exists():
                        Workspace.objects.filter(organization=org).delete()
                        org.delete()

                return  # Done - user is now in the invited org only
        except Invitation.DoesNotExist:
            pass  # Fall through to default provisioning
        except ValueError:
            pass  # Invite acceptance failed (e.g. email mismatch) - keep default org

    # No invite or invite failed - ensure default provisioning happened.
    # post_save already handled this, so this is a no-op (idempotent guard).
    provision_organization_and_workspace(user)

    # Try to set the organization timezone from the browser cookie set during signup.
    _set_org_timezone_from_browser(request, user)

    # Email signups see ToS text on the signup form, so auto-accept.
    # Social signups (Google OAuth) will be redirected to a dedicated ToS page.
    if not kwargs.get("sociallogin"):
        user.tos_accepted_at = timezone.now()
        user.save(update_fields=["tos_accepted_at"])


@receiver(post_save, sender="accounts.User")
def create_organization_on_user_create(sender, instance, created, **kwargs):
    """Handle any user creation path (createsuperuser, admin, shell).

    The allauth signal fires *after* post_save, so for normal signups
    post_save runs first and the allauth handler is a no-op (idempotent guard).
    """
    if created:
        provision_organization_and_workspace(instance)
