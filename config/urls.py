from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import health_check
from apps.api.api import api as agent_api
from apps.approvals.views import org_approval_queue

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("organizations/", include("apps.organizations.urls")),
    # Org-level Agent API key management (Phase 4 UI). Mounted at
    # /organizations/api-keys/ so the page sits alongside General,
    # Workspaces, Team Members in the settings sidebar.
    path("organizations/api-keys/", include("apps.api_keys.urls")),
    path("workspaces/", include("apps.workspaces.urls")),
    path("members/", include("apps.members.urls")),
    path("settings/", include("apps.settings_manager.urls")),
    path("credentials/", include("apps.credentials.urls")),
    path("social-accounts/", include("apps.social_accounts.urls")),
    # Content Pipeline (Stream A)
    path("workspace/<uuid:workspace_id>/", include("apps.composer.urls")),
    path("workspace/<uuid:workspace_id>/calendar/", include("apps.calendar.urls")),
    path("workspace/<uuid:workspace_id>/inbox/", include("apps.inbox.urls")),
    path("workspace/<uuid:workspace_id>/analytics/", include("apps.analytics.urls")),
    path("webhooks/", include("apps.inbox.webhook_urls")),
    # Agent API (Phase 2) — programmatic access for external AI agents.
    # Authenticated via scoped bearer tokens issued from the Organization
    # → API Keys page. OpenAPI docs at /api/v1/docs. ``agent_api.urls``
    # is Ninja's (patterns, app_namespace, instance_namespace) tuple,
    # which Django's path() handles natively.
    path("api/v1/", agent_api.urls),
    # Approval Workflow (Stream F)
    path("workspace/<uuid:workspace_id>/", include("apps.approvals.urls")),
    # Client Portal Admin (workspace settings)
    path("workspace/<uuid:workspace_id>/settings/clients/", include("apps.client_portal.urls_admin")),
    # Media Library
    path("workspace/<uuid:workspace_id>/media/", include("apps.media_library.urls")),
    path("approvals/org/", org_approval_queue, name="org_approval_queue"),
    # Client Portal (Stream F)
    path("portal/", include("apps.client_portal.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("onboarding/", include("apps.onboarding.urls")),
    path("organizations/media/", include("apps.media_library.urls_org")),
    path("", include("apps.accounts.urls_root")),
]

# ---------------------------------------------------------------------------
# Intelligence integration — mounted only when env vars are set.
# Two prefixes, DIFFERENT namespaces:
#   /orgs/<uuid:org_id>/intelligence/*  — org-scoped surfaces under
#                                          namespace ``intelligence`` (playground,
#                                          subscribe, checkout, tools, …)
#   /intelligence/*                     — non-org-scoped under namespace
#                                          ``intelligence_global`` (Stripe success
#                                          URL + user-scoped finalizing)
#
# Both used to share the namespace ``intelligence`` which caused only the
# first include's names to be reachable via ``reverse()`` — activate,
# finalizing, finalizing-status (in the second include) were orphaned and
# any redirect/url-tag to them blew up with NoReverseMatch.
# ---------------------------------------------------------------------------
if settings.INTELLIGENCE_ENABLED:
    from apps.intelligence import urls as intelligence_urls

    urlpatterns += [
        path(
            "orgs/<uuid:org_id>/intelligence/",
            include((intelligence_urls.org_scoped_patterns, "intelligence")),
        ),
        path(
            "intelligence/",
            include((intelligence_urls.user_scoped_patterns, "intelligence_global")),
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
