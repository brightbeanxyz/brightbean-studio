from django.urls import path

from . import views

app_name = "brands"

urlpatterns = [
    path("", views.brand_list, name="list"),
    path("new/", views.brand_create, name="create"),
    path("<uuid:brand_id>/edit/", views.brand_edit, name="edit"),
]
