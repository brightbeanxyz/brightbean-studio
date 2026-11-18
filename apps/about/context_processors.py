"""Studio identity and source-code details for every template."""

from django.conf import settings
from django.urls import reverse

from apps.about.version import source_info


def legal_urls() -> dict[str, str]:
    """The studio's published policies, falling back to the in-app pages."""
    return {
        "terms": settings.TERMS_URL or reverse("about:terms"),
        "privacy": settings.PRIVACY_URL or reverse("about:privacy"),
    }


def site_identity(request):
    urls = legal_urls()
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
        "TERMS_URL": urls["terms"],
        "PRIVACY_URL": urls["privacy"],
        "SOURCE": source_info(),
    }
