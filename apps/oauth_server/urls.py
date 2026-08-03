"""URL routes for the OAuth Authorization Server (MCP connector flow).

``app_name`` is "oauth2_provider" so any internal ``reverse()`` performed by
django-oauth-toolkit resolves against these routes. Only the routes the MCP
flow needs are exposed — DOT's application-management UI is left unmounted.
"""

from django.conf import settings
from django.urls import path
from django.views.decorators.csp import csp_override
from oauth2_provider import views as oauth2_views

from . import views

app_name = "oauth2_provider"

# The consent form POSTs to /oauth/authorize/ ('self'), then 302-redirects to the
# client's redirect_uri (Claude: https://claude.ai|claude.com/api/mcp/auth_callback).
# Chromium enforces form-action across the whole redirect chain, so the redirect
# target must be allowlisted on the consent page or the flow dies silently there.
# csp_override replaces the WHOLE policy, not one directive, so the base policy
# is splatted back in - without that this view would serve form-action and
# nothing else, losing script-src entirely. The relaxation stays scoped here.
_AUTHORIZE_CSP = {
    **settings.CSP_POLICY,
    "form-action": [*settings.CSP_POLICY["form-action"], "https://claude.ai", "https://claude.com"],
}

authorize_view = csp_override(_AUTHORIZE_CSP)(oauth2_views.AuthorizationView.as_view())

urlpatterns = [
    path("authorize/", authorize_view, name="authorize"),
    path("token/", oauth2_views.TokenView.as_view(), name="token"),
    path("revoke_token/", oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
    path("register", views.RegisterView.as_view(), name="register"),
]
