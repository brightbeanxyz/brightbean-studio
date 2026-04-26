from django.urls import path

from . import views
from .views_signup import InvitePrefillSignupView

app_name = "accounts"

urlpatterns = [
    path("signup/", InvitePrefillSignupView.as_view(), name="account_signup"),
    path("accept-terms/", views.accept_terms, name="accept_terms"),
    path("settings/", views.account_settings, name="settings"),
    path("logout/", views.logout_view, name="logout"),
]
