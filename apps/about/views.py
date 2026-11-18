"""Public pages: the source page (AGPL-3.0 section 13) and the legal fallbacks.

All three are deliberately public. The source offer has to reach everyone who
uses the service, including a client opening a magic link or a visitor on the
sign-in page, and a user must be able to read the policies before accepting.
"""

from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET


@require_GET
def source(request):
    return render(request, "about/source.html")


@require_GET
def terms(request):
    if settings.TERMS_URL:
        return redirect(settings.TERMS_URL)
    return render(request, "about/legal/unpublished.html", {"document_title": "Terms of service"})


@require_GET
def privacy(request):
    if settings.PRIVACY_URL:
        return redirect(settings.PRIVACY_URL)
    return render(request, "about/legal/unpublished.html", {"document_title": "Privacy policy"})
