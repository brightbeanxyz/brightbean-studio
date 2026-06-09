"""Webhook URL patterns - not auth-protected, CSRF-exempt."""

from django.urls import path

from . import webhooks

app_name = "inbox_webhooks"

urlpatterns = [
    path("facebook/", webhooks.facebook_webhook, name="webhook_facebook"),
    path("instagram_login/", webhooks.instagram_login_webhook, name="webhook_instagram_login"),
    path("youtube/", webhooks.youtube_webhook, name="webhook_youtube"),
]
