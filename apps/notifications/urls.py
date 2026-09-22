from django.urls import path

from . import unsubscribe as unsubscribe_views
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("drawer/", views.notification_drawer, name="drawer"),
    path("unread-count/", views.unread_count, name="unread_count"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("<uuid:notification_id>/read/", views.mark_as_read, name="mark_as_read"),
    path("preferences/", views.preferences, name="preferences"),
    path("unsubscribe/<str:token>/", unsubscribe_views.unsubscribe, name="unsubscribe"),
]
