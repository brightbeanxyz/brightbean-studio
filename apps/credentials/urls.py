from django.urls import path

from . import views

app_name = "credentials"

urlpatterns = [
    path("", views.credentials_list, name="list"),
    path("<str:platform>/save/", views.credentials_save, name="save"),
    path("<str:platform>/remove/", views.credentials_remove, name="remove"),
]
