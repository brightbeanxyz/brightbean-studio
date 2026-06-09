"""Analytics page views.

A single workspace-scoped page that picks one connected social account at a
time and renders the design's Classic layout. HTMX partials handle range
toggles, sort/filter/page changes on the All-posts table, and the
post-detail drawer fetch.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.composer.models import PlatformPost
from apps.members.models import WorkspaceMembership
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount
from apps.workspaces.models import Workspace

from . import services
from .constants import NO_ANALYTICS_PLATFORMS
from .metrics import PLATFORM_COLOR, PLATFORM_PRIMARY

logger = logging.getLogger(__name__)

RANGE_CHOICES = (7, 30, 90)
DEFAULT_RANGE = 30


def _get_workspace(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id)
    if not WorkspaceMembership.objects.filter(user=request.user, workspace=workspace).exists():
        raise PermissionDenied("You are not a member of this workspace.")
    return workspace


def _enabled_accounts(workspace):
    enabled = AnalyticsPlatformConfig.enabled_platforms()
    return list(
        SocialAccount.objects.filter(
            workspace=workspace,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
            platform__in=enabled,
        ).order_by("platform", "account_name")
    )


def _parse_range(value: str | None) -> int:
    try:
        n = int(value or DEFAULT_RANGE)
    except (TypeError, ValueError):
        return DEFAULT_RANGE
    return n if n in RANGE_CHOICES else DEFAULT_RANGE


def _parse_days_filter(value: str | None) -> int | None:
    """Parse the All-posts table's date filter: 7|30|90 or "all"."""
    if value is None or value in ("", "all"):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n in RANGE_CHOICES else None


def _parse_page(value: str | None) -> int:
    """Coerce ``?page=`` into a positive int, defaulting to 1 on bad input.

    Without this, a request like ``?page=abc`` raises ValueError and 500s
    before ``all_posts_for()`` can clamp it.
    """
    try:
        n = int(value or "1")
    except (TypeError, ValueError):
        return 1
    return max(1, n)


@login_required
def analytics_index(request: HttpRequest, workspace_id) -> HttpResponse:
    """Landing route: redirects to the first enabled connected account."""
    workspace = _get_workspace(request, workspace_id)
    if not AnalyticsPlatformConfig.enabled_platforms():
        raise Http404("Analytics is disabled.")
    accounts = _enabled_accounts(workspace)
    if not accounts:
        return render(
            request,
            "analytics/no_accounts.html",
            {"workspace": workspace},
        )
    from django.urls import reverse

    return redirect(reverse("analytics:account", kwargs={"workspace_id": workspace.id, "account_id": accounts[0].id}))


@login_required
def analytics_account(request: HttpRequest, workspace_id, account_id) -> HttpResponse:
    """Main analytics page for one connected SocialAccount."""
    workspace = _get_workspace(request, workspace_id)
    if not AnalyticsPlatformConfig.enabled_platforms():
        raise Http404("Analytics is disabled.")

    accounts = _enabled_accounts(workspace)
    if not accounts:
        return render(request, "analytics/no_accounts.html", {"workspace": workspace})

    account = next((a for a in accounts if str(a.id) == str(account_id)), None)
    if account is None:
        return redirect("analytics:account", workspace_id=workspace.id, account_id=accounts[0].id)

    days = _parse_range(request.GET.get("range"))
    primary_color = "var(--primary)"  # locked in chat — design's locked accent

    has_any_post = PlatformPost.objects.filter(
        social_account=account,
        status=PlatformPost.Status.PUBLISHED,
    ).exists()

    # Empty / "freshly connected" state: no published posts AND no snapshot rows.
    from .models import AccountInsightsSnapshot

    has_snapshots = AccountInsightsSnapshot.objects.filter(social_account=account).exists()
    is_fresh = not has_any_post and not has_snapshots
    analytics_unavailable = account.platform in NO_ANALYTICS_PLATFORMS

    context: dict = {
        "workspace": workspace,
        "active_account": account,
        "accounts": accounts,
        "days": days,
        "range_choices": RANGE_CHOICES,
        "primary_color": primary_color,
        "platform_color": PLATFORM_COLOR.get(account.platform, "var(--primary)"),
        "is_fresh": is_fresh,
        "analytics_needs_reconnect": account.analytics_needs_reconnect,
        "analytics_unavailable": analytics_unavailable,
        "analytics_unavailable_notice": NO_ANALYTICS_PLATFORMS.get(account.platform, ""),
    }

    if analytics_unavailable:
        table = services.all_posts_for(
            account,
            days_filter=_parse_days_filter(request.GET.get("table_range")),
            sort_key="date",
            sort_dir=request.GET.get("dir", "desc"),
            type_filter=request.GET.get("type", "all"),
            page=_parse_page(request.GET.get("page")),
        )
        # Strip metric columns — they'd all be 0 and contradict the
        # "analytics aren't available" notice above the table.
        table["metric_labels"] = []
        context["table"] = table
        if request.headers.get("HX-Request") and request.GET.get("partial") == "table":
            return render(request, "analytics/_post_table.html", context)
        if request.headers.get("HX-Request") and request.GET.get("partial") == "page":
            return render(request, "analytics/_page.html", context)
        return render(request, "analytics/index.html", context)

    if is_fresh:
        return render(request, "analytics/index.html", context)

    # Compute the bundle once and thread series_map into every consumer —
    # the post-level fallback inside the bundle is the dominant cost, and
    # calling these helpers without ``series_map`` re-runs it 3-4 times per
    # render.
    bundle = services.account_analytics_bundle(account, days)
    series_map = bundle["series_map"]
    follower_g = services.follower_growth(account, days, series_map=series_map)
    hero_cards = services.hero_cards(account, days, series_map=series_map)
    engagement = services.engagement_card(account, days, series_map=series_map)
    chart = services.hero_chart_data(
        account,
        days,
        metric=request.GET.get("chart_metric"),
        series_map=series_map,
    )
    table = services.all_posts_for(
        account,
        days_filter=_parse_days_filter(request.GET.get("table_range", str(days))),
        sort_key=request.GET.get("sort") or PLATFORM_PRIMARY.get(account.platform),
        sort_dir=request.GET.get("dir", "desc"),
        type_filter=request.GET.get("type", "all"),
        page=_parse_page(request.GET.get("page")),
    )

    context.update(
        {
            "follower_growth": follower_g,
            "hero_cards": hero_cards,
            "engagement": engagement,
            "chart": chart,
            "chart_series_json": json.dumps([round(v, 4) for v in chart["derived"].series]),
            "chart_labels_json": json.dumps(chart["labels"]),
            "table": table,
        }
    )

    if request.headers.get("HX-Request") and request.GET.get("partial") == "chart":
        return render(request, "analytics/_hero_chart.html", context)
    if request.headers.get("HX-Request") and request.GET.get("partial") == "table":
        return render(request, "analytics/_post_table.html", context)
    if request.headers.get("HX-Request") and request.GET.get("partial") == "page":
        # Full-page swap when account switcher is clicked via HTMX
        return render(request, "analytics/_page.html", context)

    return render(request, "analytics/index.html", context)


@login_required
def post_detail(request: HttpRequest, workspace_id, post_id) -> HttpResponse:
    """HTMX-loaded payload for the slide-over post-detail drawer."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(
        PlatformPost.objects.select_related("social_account", "post").prefetch_related(
            "post__media_attachments__media_asset"
        ),
        id=post_id,
        social_account__workspace=workspace,
    )
    context = services.post_detail(post)
    context.update({"workspace": workspace})
    return render(request, "analytics/_post_detail.html", context)
