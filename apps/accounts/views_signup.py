from allauth.account.views import LoginView, SignupView

from .signup_links import custom_signup_url, pending_invite_email


class InvitePrefillSignupView(SignupView):
    """Signup view that pre-fills and locks the email when a pending
    invite token is in the session."""

    def get_initial(self):
        initial = super().get_initial()
        email = pending_invite_email(self.request)
        if email:
            initial["email"] = email
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["invited_email_locked"] = bool(pending_invite_email(self.request))
        return ctx


class SignupLinkLoginView(LoginView):
    """Login view whose "Sign up" link honors ``CUSTOM_SIGNUP_URL``.

    allauth's ``signup_url`` (with its ``?next=`` passthrough) is kept when the
    setting is empty or an invite is pending.
    """

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["signup_url"] = custom_signup_url(self.request) or ctx.get("signup_url")
        return ctx
