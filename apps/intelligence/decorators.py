"""View decorators for the Intelligence integration.

``@intelligence_subscription_required`` is layered on top of
``@require_org_permission("use_intelligence")`` for tool endpoints,
it ensures the org's ``IntelligenceSubscription`` is in ``status='active'``
before letting the call hit Intelligence. Non-active states render an
inline HTMX partial (or a full-page redirect) rather than a hard 4xx,
because the user is allowed to BE here, just not to call tools yet.
"""

from __future__ import annotations

import functools

from django.shortcuts import redirect, render


def intelligence_subscription_required(view_func):
    """Guards tool endpoints (six HTMX POSTs) with the live subscription
    status. Composes after ``@require_org_permission`` so ``request.org``
    is already populated.

    Status → response mapping:

    - ``active``    : view runs.
    - ``finalizing``: ``_provisioning_in_progress.html`` partial (HTMX) or
                      redirect to the playground (full-page).
    - others / no sub: ``_subscribe_required.html`` partial or redirect.
    """

    @functools.wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        org = getattr(request, "org", None)
        sub = getattr(org, "intelligence_subscription", None) if org else None

        if sub is not None and sub.status == "active":
            return view_func(request, *args, **kwargs)

        is_htmx = bool(request.headers.get("HX-Request"))
        if sub is not None and sub.status == "finalizing":
            if is_htmx:
                return render(
                    request,
                    "intelligence/_provisioning_in_progress.html",
                    {"organization": org},
                    status=409,
                )
            return redirect("intelligence:playground", org_id=org.id)

        # No sub / canceled / past_due / failed.
        if is_htmx:
            return render(
                request,
                "intelligence/_subscribe_required.html",
                {"organization": org, "subscription": sub},
                status=402,
            )
        return redirect("intelligence:playground", org_id=org.id)

    return _wrapped
