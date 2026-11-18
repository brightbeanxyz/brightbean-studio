from django.urls import path

from . import views

app_name = "about"

urlpatterns = [
    path("about/source/", views.source, name="source"),
    path("legal/terms/", views.terms, name="terms"),
    path("legal/privacy/", views.privacy, name="privacy"),
]
