import json
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.analytics.models import PostSnapshot, RefreshLog
from apps.analytics.services import refresh_metrics
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

logger = logging.getLogger(__name__)

PLATFORM_COLORS = {
    "instagram": "rgba(225, 48, 108, 0.7)",
    "tiktok": "rgba(0, 242, 234, 0.7)",
    "youtube": "rgba(255, 0, 0, 0.7)",
}


def _get_user_workspace(request, workspace_id):
    """Get a workspace that the current user has access to, or 404."""
    return get_object_or_404(
        Workspace,
        id=workspace_id,
        organization__memberships__user=request.user,
        is_archived=False,
    )


def _build_account_sections(workspace):
    """Build account section data including chart data for templates."""
    accounts = SocialAccount.objects.filter(workspace=workspace)
    account_sections = []

    for account in accounts:
        snapshots = list(PostSnapshot.objects.filter(
            social_account=account,
        ).order_by("-posted_at")[:20])

        last_log = RefreshLog.objects.filter(
            social_account=account,
        ).first()

        reversed_snaps = list(reversed(snapshots))
        chart_labels = json.dumps([s.post_text[:20] for s in reversed_snaps])
        chart_data = json.dumps([s.engagements for s in reversed_snaps])
        chart_tooltips = json.dumps([
            [f"Likes: {s.likes}", f"Comments: {s.comments}",
             f"Shares: {s.shares}", f"Saves: {s.saves}"]
            for s in reversed_snaps
        ])
        chart_color = PLATFORM_COLORS.get(account.platform, "rgba(59, 130, 246, 0.7)")

        account_sections.append({
            "account": account,
            "snapshots": snapshots,
            "last_log": last_log,
            "chart_labels": chart_labels,
            "chart_data": chart_data,
            "chart_tooltips": chart_tooltips,
            "chart_color": chart_color,
        })

    return account_sections


def _build_summary(workspace):
    """Build aggregate summary stats."""
    all_snapshots = PostSnapshot.objects.filter(workspace=workspace)
    summary = all_snapshots.aggregate(
        total_likes=Sum("likes"),
        total_comments=Sum("comments"),
        total_shares=Sum("shares"),
        total_saves=Sum("saves"),
    )
    return {
        "likes": summary["total_likes"] or 0,
        "comments": summary["total_comments"] or 0,
        "shares": summary["total_shares"] or 0,
        "saves": summary["total_saves"] or 0,
    }


@login_required
def brand_list(request):
    """Landing page — grid of workspace cards with summary stats."""
    workspaces = Workspace.objects.filter(
        organization__memberships__user=request.user,
        is_archived=False,
    ).distinct()

    workspace_data = []
    for ws in workspaces:
        accounts = SocialAccount.objects.filter(workspace=ws)
        total_engagements = PostSnapshot.objects.filter(
            workspace=ws,
        ).aggregate(total=Sum("engagements"))["total"] or 0

        last_refresh = RefreshLog.objects.filter(
            workspace=ws, status="success",
        ).first()

        workspace_data.append({
            "workspace": ws,
            "accounts": accounts,
            "total_engagements": total_engagements,
            "last_refresh": last_refresh,
        })

    return render(request, "analytics/brand_list.html", {
        "workspace_data": workspace_data,
    })


@login_required
def brand_dashboard(request, workspace_id):
    """Single brand dashboard — stacked platform sections."""
    workspace = _get_user_workspace(request, workspace_id)

    account_sections = _build_account_sections(workspace)
    summary = _build_summary(workspace)

    last_refresh = RefreshLog.objects.filter(
        workspace=workspace, status="success",
    ).first()

    return render(request, "analytics/brand_dashboard.html", {
        "workspace": workspace,
        "account_sections": account_sections,
        "summary": summary,
        "last_refresh": last_refresh,
    })


@login_required
@require_POST
def refresh_metrics_view(request, workspace_id):
    """HTMX endpoint — refresh metrics and return updated dashboard partial."""
    workspace = _get_user_workspace(request, workspace_id)

    results = refresh_metrics(workspace)

    account_sections = _build_account_sections(workspace)
    summary = _build_summary(workspace)

    last_refresh = RefreshLog.objects.filter(
        workspace=workspace, status="success",
    ).first()

    return render(request, "analytics/brand_dashboard.html", {
        "workspace": workspace,
        "account_sections": account_sections,
        "summary": summary,
        "last_refresh": last_refresh,
        "refresh_results": results,
    })
