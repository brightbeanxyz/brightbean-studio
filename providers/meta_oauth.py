"""Shared Login-dialog parameters for the Facebook-hosted Meta providers.

``FacebookProvider`` and ``InstagramProvider`` both drive the same dialog at
facebook.com; ``InstagramLoginProvider`` drives Instagram's own, which has a
different vocabulary and deliberately does not use any of this.
"""

from __future__ import annotations

# Lets us re-ask for a permission the user previously *declined*. Without it
# Meta skips the dialog entirely on a reconnect, so a declined scope could
# never be requested again and the connection silently lacked an ability it
# advertises.
#
# It does NOT force the full permission list for someone who already granted
# everything — they still see the short "continue sharing?" confirmation. Only
# the user removing the app (Facebook → Settings → Apps and Websites) restores
# the first-time dialog.
FACEBOOK_LOGIN_EXTRA_PARAMS: dict[str, str] = {"auth_type": "rerequest"}


def facebook_login_params(
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: list[str],
    config_id: str = "",
) -> dict[str, str]:
    """Build the query parameters for the facebook.com Login dialog.

    ``config_id`` selects a Facebook *Login for Business* configuration. Meta
    then owns the permission and business-asset selection, so the configured
    scopes replace the ad-hoc ``scope`` list classic Facebook Login sends —
    passing both would have Meta ignore one of them without saying which.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        **FACEBOOK_LOGIN_EXTRA_PARAMS,
    }
    if config_id:
        params["config_id"] = config_id
        # Login for Business defaults to the token response type; this keeps
        # the code flow the callback is built around.
        params["override_default_response_type"] = "true"
    else:
        params["scope"] = ",".join(scopes)
    return params
