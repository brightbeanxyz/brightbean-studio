from django.urls import path

from . import views

app_name = "client_portal"

urlpatterns = [
    path("expired/", views.magic_link_expired, name="magic_link_expired"),
    path("", views.portal_dashboard, name="dashboard"),
    path("approvals/", views.portal_approval_queue, name="approval_queue"),
    path("approvals/<uuid:post_id>/approve/", views.portal_approve, name="approve"),
    path("approvals/<uuid:post_id>/request-changes/", views.portal_request_changes, name="request_changes"),
    path("approvals/<uuid:post_id>/reject/", views.portal_reject, name="reject"),
    path("approvals/<uuid:post_id>/hold/", views.portal_request_hold, name="request_hold"),
    path("published/", views.portal_published, name="published"),
    path("activity/", views.portal_activity, name="activity"),
    path("reports/", views.portal_reports, name="reports"),
    # Magic link entry must be last (catches any token string)
    path("<str:token>/", views.magic_link_entry, name="magic_link_entry"),
]
