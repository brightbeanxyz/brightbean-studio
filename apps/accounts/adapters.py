from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

from apps.accounts.models import OAuthConnection


def pending_invitation(request):
    """The unaccepted, unexpired Invitation this visitor arrived with, if any.

    The token is put into the session by the invitation link (see
    apps.members.views) and consumed after signup by apps.accounts.signals.
    """
    if request is None:
        return None
    session = getattr(request, "session", None)
    if session is None:
        return None
    token = session.get("pending_invite_token")
    if not token:
        return None

    from apps.members.models import Invitation

    invitation = Invitation.objects.filter(token=token, accepted_at__isnull=True).first()
    if invitation is None or invitation.is_expired:
        return None
    return invitation


def signup_allowed(request):
    """Whether a brand-new account may be created for this request.

    Only ever asked when an account would actually be created. Signing in
    with an existing account — including a social login that connects to an
    existing user by email — does not pass through here.
    """
    mode = getattr(settings, "SIGNUP_MODE", "open")
    if mode == "open":
        return True
    if mode == "closed":
        return False
    return pending_invitation(request) is not None


class AccountAdapter(DefaultAccountAdapter):
    """Applies SIGNUP_MODE to the email/password signup form."""

    def is_open_for_signup(self, request):
        return signup_allowed(request)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom adapter that syncs Google social logins to OAuthConnection."""

    def is_open_for_signup(self, request, sociallogin):
        """Applies SIGNUP_MODE to social signups.

        Without this, closing the email form would achieve nothing:
        SOCIALACCOUNT_AUTO_SIGNUP creates the account during the provider
        callback, so a new Google user never visits the signup page at all.
        """
        return signup_allowed(request)

    def populate_user(self, request, sociallogin, data):
        """Set user.name from Google profile (custom User model has 'name', not first/last)."""
        user = super().populate_user(request, sociallogin, data)
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()
        if full_name and not user.name:
            user.name = full_name
        return user

    def save_user(self, request, sociallogin, form=None):
        """Create OAuthConnection after saving a new social signup."""
        user = super().save_user(request, sociallogin, form)
        self._sync_oauth_connection(user, sociallogin)
        return user

    def pre_social_login(self, request, sociallogin):
        """Sync OAuthConnection for returning users and auto-connected accounts."""
        super().pre_social_login(request, sociallogin)
        if sociallogin.is_existing:
            self._sync_oauth_connection(sociallogin.user, sociallogin)

    def _sync_oauth_connection(self, user, sociallogin):
        account = sociallogin.account
        if account.provider != "google":
            return
        provider_email = ""
        for ea in sociallogin.email_addresses:
            provider_email = ea.email
            break
        OAuthConnection.objects.update_or_create(
            provider=OAuthConnection.Provider.GOOGLE,
            provider_user_id=account.uid,
            defaults={"user": user, "provider_email": provider_email},
        )
