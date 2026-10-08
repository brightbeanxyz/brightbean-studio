"""Where "Sign up" links send people.

``CUSTOM_SIGNUP_URL`` moves every Studio-generated signup link (the login page,
the unknown-account email, the redirect after an owner deletes their org) to
another page. It only moves the links: ``/accounts/signup/`` stays open, so
that page may send people back to it.
"""

from django.conf import settings

from apps.members.models import Invitation


def pending_invite_email(request):
    """Email of the still-open invite whose token is in the session, else None.

    The accept page stores the token on GET (``apps.members.views.accept_invite``);
    signup accepts the invite from it (``apps.accounts.signals``).
    """
    session = getattr(request, "session", None)
    token = session.get("pending_invite_token") if session is not None else None
    if not token:
        return None
    invitation = Invitation.objects.filter(
        token=token,
        accepted_at__isnull=True,
    ).first()
    if invitation and not invitation.is_expired:
        return invitation.email
    return None


def custom_signup_url(request):
    """``CUSTOM_SIGNUP_URL``, or "" when the built-in signup should be linked.

    An invitee always gets the built-in signup, because only it pre-fills the
    invited email and accepts the invite on signup. Without this, an invitee
    who picks "Log In to Join" and then "Sign up" would lose the invite.
    """
    if not settings.CUSTOM_SIGNUP_URL or pending_invite_email(request):
        return ""
    return settings.CUSTOM_SIGNUP_URL
