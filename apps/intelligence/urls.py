"""URL routes for the Studio side of the Intelligence integration.

Mounted by ``config/urls.py`` only when ``settings.INTELLIGENCE_ENABLED``
is True (next milestone). The activate/finalizing routes are NOT
org-scoped because Stripe's success URL is configured at the Dashboard
level and can't carry a per-org UUID; the org is resolved from the
session metadata after Stripe redirects back.
"""

from django.urls import path

from . import views

app_name = "intelligence"


org_scoped_patterns = [
    path("", views.playground, name="playground"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("checkout/", views.checkout, name="checkout"),
    path("discard-checkout/", views.discard_checkout, name="discard-checkout"),
    path("recover/", views.recover, name="recover"),
    path("portal/", views.portal, name="portal"),
    path("billing-settings/", views.billing_settings, name="billing-settings"),
    path("billing-contact/", views.update_billing_contact, name="update-billing-contact"),
    path("status/", views.status_fragment, name="status"),
    # Tool endpoints.
    path("score-packaging/", views.score_packaging, name="score-packaging"),
    path("score-video-hook/", views.score_video_hook, name="score-video-hook"),
    path("benchmark-channel/", views.benchmark_channel, name="benchmark-channel"),
    path("benchmark-video/", views.benchmark_video, name="benchmark-video"),
    path("research-content-gaps/", views.research_content_gaps, name="research-content-gaps"),
    path("list-niches/", views.list_niches, name="list-niches"),
]


# Non-org-scoped surfaces (mounted at /intelligence/ in config/urls.py).
user_scoped_patterns = [
    path("activate/", views.activate, name="activate"),
    path("finalizing/", views.finalizing, name="finalizing"),
    path("finalizing/status/", views.finalizing_status, name="finalizing-status"),
]


# Re-exported so config/urls.py can mount both prefixes from one place.
urlpatterns = org_scoped_patterns + user_scoped_patterns
