from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.brand_list, name="brand_list"),
    path("<uuid:workspace_id>/", views.brand_dashboard, name="brand_dashboard"),
    path("<uuid:workspace_id>/refresh/", views.refresh_metrics_view, name="refresh_metrics"),
]
