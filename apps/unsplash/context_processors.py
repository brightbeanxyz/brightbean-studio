"""Context processors for the Unsplash plugin.

Injects the Unsplash modal HTML and DRF auth token into every page
so the modal can be triggered from anywhere without template changes.
"""

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


def unsplash_modal(request):
    """Inject Unsplash modal HTML + DRF token into template context.

    Only injects when user is authenticated. The modal is hidden by
    default (Alpine `x-show="show"`) — it only appears when a component
    calls `$dispatch('open-unsplash-modal', params)`.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {}

    token = _get_drf_token(request.user)

    # Render modal HTML from the plugin's template directory
    try:
        modal_html = render_to_string(
            "integrations/unsplash_modal.html",
            {},
            request=request,
        )
    except Exception:
        modal_html = ""

    # Inject window.drfToken so the Unsplash JS can auth API calls
    token_script = ""
    if token:
        token_script = f"<script>window.drfToken = '{token}';</script>"

    return {
        "unsplash_modal_html": mark_safe(modal_html + token_script),
        "unsplash_drf_token": token,
    }


def _get_drf_token(user):
    """Get or create a DRF auth token for the user."""
    try:
        from rest_framework.authtoken.models import Token

        token, _created = Token.objects.get_or_create(user=user)
        return token.key
    except Exception:
        return ""
