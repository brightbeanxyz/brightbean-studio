from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import health_check
from apps.approvals.views import org_approval_queue

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("organizations/", include("apps.organizations.urls")),
    path("workspaces/", include("apps.workspaces.urls")),
    path("members/", include("apps.members.urls")),
    path("settings/", include("apps.settings_manager.urls")),
    path("credentials/", include("apps.credentials.urls")),
    path("social-accounts/", include("apps.social_accounts.urls")),
    # Content Pipeline (Stream A)
    path("workspace/<uuid:workspace_id>/", include("apps.composer.urls")),
    path("workspace/<uuid:workspace_id>/calendar/", include("apps.calendar.urls")),
    path("workspace/<uuid:workspace_id>/inbox/", include("apps.inbox.urls")),
    path("webhooks/", include("apps.inbox.webhook_urls")),
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
    path("analytics/", include("apps.analytics.urls")),
    path("", include("apps.accounts.urls_root")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
