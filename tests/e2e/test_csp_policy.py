"""A per-view CSP override must not shrink the policy to a single directive.

`@csp_override` does not override a DIRECTIVE - it replaces the WHOLE policy.
django/middleware/csp.py reads the decorator's dict INSTEAD of SECURE_CSP and
merges nothing:

    if (csp_config := getattr(response, "_csp_config", sentinel)) is sentinel:
        csp_config = settings.SECURE_CSP

So a decorator carrying only `form-action` serves a page with no `script-src`
and no `default-src` - which restricts scripts not at all, on exactly the pages
that hand control to a third party.

Nothing else catches it. The page renders, every static gate passes, the unit
suite passes, and the header is wrong only in the direction of being too
permissive - so no browser complains either.
"""

import urllib.error
import urllib.request

#: django-oauth-toolkit's consent view. It carries a csp_override widening
#: form-action to Claude's callback hosts. Anonymous, so it answers with a
#: redirect to login - and the decorator sets the policy on that response too.
CONSENT_VIEW_PATH = "/oauth/authorize/"

#: Every directive the base policy defines. Losing any of them on an overridden
#: view is the defect.
REQUIRED_DIRECTIVES = ("default-src", "script-src", "style-src", "img-src", "form-action")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Stop at the view's own response; the header we want is on that one."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_without_following_redirects(url):
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(url, timeout=30) as response:
            return response.status, response.headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers


def test_a_csp_override_view_still_serves_the_whole_policy(live_server):
    status, headers = _fetch_without_following_redirects(live_server.url + CONSENT_VIEW_PATH)
    policy = headers.get("Content-Security-Policy", "")

    assert status != 404, f"{CONSENT_VIEW_PATH} did not route to the consent view"
    # Proves the DECORATED view was reached: only its override adds this host,
    # so an undecorated page or a 404 cannot satisfy this and pass vacuously.
    assert "https://claude.ai" in policy, f"not the overridden view, or the widening was lost: {policy}"

    missing = [directive for directive in REQUIRED_DIRECTIVES if directive not in policy]
    assert not missing, f"the override dropped {missing}; this page would restrict scripts not at all: {policy}"
