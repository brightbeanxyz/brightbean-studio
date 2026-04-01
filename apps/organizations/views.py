import calendar as cal_mod
from collections import defaultdict
from datetime import date, timedelta
from zoneinfo import available_timezones

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone as django_tz
from django.views.decorators.http import require_http_methods
from apps.composer.models import Post, Tag
from apps.members.decorators import require_org_role
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

COMMON_TIMEZONES = [
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "Canada/Eastern",
    "Canada/Central",
    "Canada/Pacific",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Amsterdam",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Zurich",
    "Europe/Stockholm",
    "Europe/Istanbul",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
]


@login_required
@require_org_role(OrgMembership.OrgRole.ADMIN)
@require_http_methods(["GET", "POST"])
def settings_view(request):
    org = request.org
    is_owner = request.org_membership.org_role == OrgMembership.OrgRole.OWNER

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_name":
            _handle_name_update(request, org)
        elif action == "update_timezone":
            _handle_tz_update(request, org)
        elif action == "delete_organization":
            return _handle_org_deletion(request, org)
        elif action == "cancel_deletion":
            _handle_cancel_deletion(request, org)
        return redirect("organizations:settings")

    context = {
        "organization": org,
        "settings_active": "general",
        "is_owner": is_owner,
        "common_timezones": COMMON_TIMEZONES,
        "all_timezones": sorted(available_timezones()),
    }
    return render(request, "organizations/settings.html", context)


def _handle_name_update(request, org):
    """Handle organization name change."""
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Organization name cannot be empty.")
        return

    org.name = name
    org.save(update_fields=["name"])
    messages.success(request, "Organization name updated.")


def _handle_tz_update(request, org):
    """Handle default timezone change."""
    tz = request.POST.get("timezone", "").strip()
    if tz not in available_timezones():
        messages.error(request, "Invalid timezone.")
        return

    org.default_timezone = tz
    org.save(update_fields=["default_timezone"])
    messages.success(request, "Default timezone updated.")


def _handle_org_deletion(request, org):
    """Handle organization soft-deletion (owner only)."""
    if request.org_membership.org_role != OrgMembership.OrgRole.OWNER:
        raise PermissionDenied

    org.deletion_requested_at = django_tz.now()
    org.deletion_scheduled_for = django_tz.now() + timedelta(days=14)
    org.save(update_fields=["deletion_requested_at", "deletion_scheduled_for"])
    messages.success(request, "Organization scheduled for deletion in 14 days.")
    return redirect("organizations:settings")


def _handle_cancel_deletion(request, org):
    """Cancel a pending organization deletion (owner only)."""
    if request.org_membership.org_role != OrgMembership.OrgRole.OWNER:
        raise PermissionDenied

    org.deletion_requested_at = None
    org.deletion_scheduled_for = None
    org.save(update_fields=["deletion_requested_at", "deletion_scheduled_for"])
    messages.success(request, "Organization deletion cancelled.")


@login_required
def cross_workspace_calendar(request):
    """Org-level calendar showing all workspaces' posts, color-coded by workspace."""
    org = request.org
    if not org:
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("Organization required.")

    # Get workspaces the user has membership in
    user_workspace_ids = set(
        WorkspaceMembership.objects.filter(user=request.user).values_list("workspace_id", flat=True)
    )
    workspaces = Workspace.objects.filter(
        organization=org,
        id__in=user_workspace_ids,
        is_archived=False,
    ).order_by("name")

    # Workspace filter
    selected_ws_ids = request.GET.getlist("workspace")
    filtered_workspaces = workspaces.filter(id__in=selected_ws_ids) if selected_ws_ids else workspaces

    # View type (month/week/day)
    view_type = request.GET.get("view", "month")

    target_date_str = request.GET.get("date")
    if target_date_str:
        try:
            target_date = date.fromisoformat(target_date_str)
        except (ValueError, TypeError):
            target_date = date.today()
    else:
        target_date = date.today()

    # Social accounts across filtered workspaces (for channel filter)
    social_accounts = (
        SocialAccount.objects.filter(
            workspace__in=filtered_workspaces,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        .select_related("workspace")
        .order_by("platform", "account_name")
    )

    # Tags across filtered workspaces
    all_tags = sorted(set(Tag.objects.filter(workspace__in=filtered_workspaces).values_list("name", flat=True)))

    # Base post queryset with filters
    base_posts = (
        Post.objects.filter(workspace__in=filtered_workspaces)
        .select_related("workspace", "author")
        .prefetch_related("platform_posts__social_account", "media_attachments__media_asset")
    )

    # Channel filter
    channel = request.GET.get("channel")
    if channel:
        base_posts = base_posts.filter(platform_posts__social_account_id=channel).distinct()

    # Tag filter
    tag = request.GET.get("tag")
    if tag:
        base_posts = base_posts.filter(tags__contains=[tag])

    # Status filter
    status = request.GET.get("status")
    if status:
        base_posts = base_posts.filter(status=status)

    # Workspace colors for legend
    workspace_colors = {}
    for ws in workspaces:
        workspace_colors[str(ws.id)] = ws.primary_color or "#F97316"

    today = date.today()

    # Build view-specific data
    if view_type == "week":
        context = _build_week_context(base_posts, target_date, today)
    elif view_type == "day":
        context = _build_day_context(base_posts, target_date, today)
    else:
        context = _build_month_context(base_posts, target_date, today)

    context.update(
        {
            "organization": org,
            "workspaces": workspaces,
            "selected_workspace_ids": selected_ws_ids,
            "workspace_colors": workspace_colors,
            "target_date": target_date,
            "default_workspace": workspaces.first(),
            "day_names": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "settings_active": "calendars",
            "view_type": view_type,
            "social_accounts": social_accounts,
            "all_tags": all_tags,
            "status_choices": Post.Status.choices,
        }
    )
    return render(request, "organizations/cross_calendar.html", context)


def _build_month_context(base_posts, target_date, today):
    year, month = target_date.year, target_date.month
    cal = cal_mod.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    first_day = weeks[0][0]
    last_day = weeks[-1][6]

    posts = base_posts.filter(
        scheduled_at__date__gte=first_day,
        scheduled_at__date__lte=last_day,
    ).order_by("scheduled_at")

    posts_by_date = defaultdict(list)
    for post in posts:
        if post.scheduled_at:
            posts_by_date[post.scheduled_at.date()].append(post)

    calendar_weeks = []
    for week in weeks:
        week_data = []
        for day in week:
            day_posts = posts_by_date.get(day, [])
            week_data.append(
                {
                    "date": day,
                    "is_current_month": day.month == month,
                    "is_today": day == today,
                    "is_past": day < today,
                    "posts": day_posts[:5],
                    "total_posts": len(day_posts),
                    "overflow": max(0, len(day_posts) - 5),
                }
            )
        calendar_weeks.append(week_data)

    prev_month = (date(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(year, month, 28) + timedelta(days=4)).replace(day=1)

    return {
        "calendar_weeks": calendar_weeks,
        "period_label": date(year, month, 1).strftime("%B %Y"),
        "prev_date": prev_month.isoformat(),
        "next_date": next_month.isoformat(),
    }


def _build_week_context(base_posts, target_date, today):
    monday = target_date - timedelta(days=target_date.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]

    posts = base_posts.filter(
        scheduled_at__date__gte=week_days[0],
        scheduled_at__date__lte=week_days[6],
    ).order_by("scheduled_at")

    posts_by_slot = defaultdict(list)
    for post in posts:
        if post.scheduled_at:
            key = (post.scheduled_at.date(), post.scheduled_at.hour)
            posts_by_slot[key].append(post)

    hours = list(range(6, 23))

    return {
        "week_days": week_days,
        "hours": hours,
        "posts_by_slot": dict(posts_by_slot),
        "today": today,
        "period_label": f"{week_days[0].strftime('%b %d')} – {week_days[6].strftime('%b %d, %Y')}",
        "prev_date": (monday - timedelta(weeks=1)).isoformat(),
        "next_date": (monday + timedelta(weeks=1)).isoformat(),
    }


def _build_day_context(base_posts, target_date, today):
    posts = base_posts.filter(scheduled_at__date=target_date).order_by("scheduled_at")

    posts_by_hour = defaultdict(list)
    for post in posts:
        if post.scheduled_at:
            posts_by_hour[post.scheduled_at.hour].append(post)

    hours = list(range(0, 24))

    return {
        "posts_by_hour": dict(posts_by_hour),
        "hours": hours,
        "today": today,
        "period_label": target_date.strftime("%A, %B %d, %Y"),
        "prev_date": (target_date - timedelta(days=1)).isoformat(),
        "next_date": (target_date + timedelta(days=1)).isoformat(),
    }
