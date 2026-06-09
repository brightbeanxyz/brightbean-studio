"""Template context for the Intelligence integration.

Exposes the feature flag + the org's intelligence subscription state so
templates (notably the left-nav and any cross-app banners) can render
correctly without each view manually populating the context.
"""

from __future__ import annotations

from django.conf import settings


def intelligence_flag(request):
    """Add ``INTELLIGENCE_ENABLED`` to template context.

    Wrapped in a function (not just a settings-direct lookup) so we
    don't accidentally leak any settings beyond what we explicitly
    intend templates to see.
    """
    return {
        "INTELLIGENCE_ENABLED": getattr(settings, "INTELLIGENCE_ENABLED", False),
    }
