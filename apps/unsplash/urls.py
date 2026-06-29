"""URL routing for the Unsplash integration plugin.

All routes live under /api/v1/ (included from the project's config/urls.py).
"""

from django.urls import path

from . import views

app_name = "apps.unsplash"

urlpatterns = [
    path("media/unsplash/search/", views.UnsplashSearchView.as_view(), name="unsplash_search"),
    path("media/unsplash/import/", views.UnsplashImportView.as_view(), name="unsplash_import"),
    path("media/folders/", views.FolderListCreateView.as_view(), name="folder_list"),
    path("media/folders/<uuid:id>/", views.FolderDetailView.as_view(), name="folder_detail"),
]
