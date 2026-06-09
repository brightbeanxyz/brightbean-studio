"""Custom OAuth2 validator that restricts PKCE to S256 only.

django-oauth-toolkit's default validator (and oauthlib under it) accepts both
``S256`` and ``plain`` for ``code_challenge_method``. RFC 7636 §4.2 marks
``plain`` as insecure unless the channel is fully secure end-to-end — which
defeats the entire point of PKCE for the kind of MCP-client scenarios we
support. The protected-resource metadata document advertises ``S256`` as the
only supported method (see ``apps.oauth_server.metadata``); this validator
enforces that contract at the authorize endpoint, blocking authorization
requests with a missing or ``plain`` method early — before any Grant row is
written.
"""

from __future__ import annotations

from oauth2_provider.oauth2_validators import OAuth2Validator
from oauthlib.oauth2.rfc6749 import errors as oauthlib_errors


class S256OnlyOAuth2Validator(OAuth2Validator):
    """OAuth2Validator subclass that requires ``code_challenge_method=S256``.

    Hooks ``is_pkce_required`` because it is the earliest validator method
    oauthlib invokes while ``request.code_challenge_method`` is still the
    raw client-supplied value (oauthlib later defaults a missing method to
    ``"plain"`` at ``authorization_code.py``; we reject before that lands).
    """

    def is_pkce_required(self, client_id, request):
        code_challenge = getattr(request, "code_challenge", None)
        method = getattr(request, "code_challenge_method", None)
        if code_challenge and method != "S256":
            raise oauthlib_errors.InvalidRequestError(
                description="code_challenge_method must be S256",
                request=request,
            )
        return super().is_pkce_required(client_id, request)
