"""URL patterns for the org-level API key management UI.

Mounted at ``/organizations/api-keys/`` by ``config/urls.py``. Lives at
org scope (not workspace scope) per the plan — an org admin gets a
unified view of every key across every workspace, with one issuance
flow.
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "api_keys"

urlpatterns = [
    path("", views.list_keys, name="list"),
    path("issue/", views.issue_key, name="issue"),
    path("<uuid:key_id>/revoke/", views.revoke_key, name="revoke"),
    # HTMX partial — cascades the workspace dropdown into a list of
    # connected SocialAccounts + the permission catalog grantable to
    # the issuer in that workspace.
    path("_workspace-options/", views.workspace_options_partial, name="workspace_options"),
]
