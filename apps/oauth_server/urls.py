"""URL routes for the OAuth Authorization Server (MCP connector flow).

``app_name`` is "oauth2_provider" so any internal ``reverse()`` performed by
django-oauth-toolkit resolves against these routes. Only the routes the MCP
flow needs are exposed — DOT's application-management UI is left unmounted.
"""

from csp.decorators import csp_update
from django.urls import path
from oauth2_provider import views as oauth2_views

from . import views

app_name = "oauth2_provider"

# The consent form POSTs to /oauth/authorize/ ('self'), then 302-redirects to the
# client's redirect_uri (Claude: https://claude.ai|claude.com/api/mcp/auth_callback).
# Chromium enforces form-action across the whole redirect chain, so the redirect
# target must be allowlisted on the consent page or the flow dies silently there.
# csp_update appends to the global CSP_FORM_ACTION, scoping the relaxation here only.
#
# NOTE: every origin a client can redirect back to must be listed here. Adding a
# client whose redirect_uri is not on this list produces a silent browser-side
# failure (the consent form POSTs, then Chromium refuses the redirect).
#   - claude.ai / claude.com      : Claude custom connector
#   - oauth-redirect.googleusercontent.com : Google custom-MCP connector (Gemini)
#   - chatgpt.com / chat.openai.com        : ChatGPT custom connector
authorize_view = csp_update(
    FORM_ACTION=(
        "https://claude.ai https://claude.com "
        "https://oauth-redirect.googleusercontent.com "
        "https://chatgpt.com https://chat.openai.com"
    )
)(oauth2_views.AuthorizationView.as_view())

urlpatterns = [
    path("authorize/", authorize_view, name="authorize"),
    path("token/", oauth2_views.TokenView.as_view(), name="token"),
    path("revoke_token/", oauth2_views.RevokeTokenView.as_view(), name="revoke-token"),
    path("register", views.RegisterView.as_view(), name="register"),
]
