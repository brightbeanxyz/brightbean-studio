from django.urls import path

from . import views

app_name = "media_library_org"

urlpatterns = [
    path("shared/", views.shared_library_index, name="shared_index"),
    path("shared/upload/", views.shared_upload, name="shared_upload"),
    path("shared/tags/autocomplete/", views.shared_tag_autocomplete, name="shared_tag_autocomplete"),
    path("shared/<uuid:asset_id>/", views.shared_asset_detail, name="shared_asset_detail"),
    path("shared/<uuid:asset_id>/edit/", views.shared_asset_edit, name="shared_asset_edit"),
    path("shared/<uuid:asset_id>/delete/", views.shared_asset_delete, name="shared_asset_delete"),
    path("shared/<uuid:asset_id>/tags/", views.shared_asset_update_tags, name="shared_asset_tags"),
    path("shared/<uuid:asset_id>/download/", views.shared_asset_download, name="shared_asset_download"),
    path("shared/<uuid:asset_id>/versions/", views.shared_version_list, name="shared_version_list"),
]
