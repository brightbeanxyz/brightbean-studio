import calendar as cal_mod
from collections import defaultdict
from datetime import date, timedelta
from zoneinfo import available_timezones

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone as django_tz
from django.views.decorators.http import require_http_methods

from apps.composer.models import PlatformPost, Post, Tag
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
        elif action == "delete_organization_now":
            return _handle_immediate_org_deletion(request, org)
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


@login_required
@require_org_role(OrgMembership.OrgRole.MEMBER)
def workspaces_view(request):
    org = request.org
    workspaces = (
        Workspace.objects.filter(organization=org).prefetch_related("memberships__user").order_by("is_archived", "name")
    )

    # Build workspace data with members and current user's role
    workspace_data = []
    archived_data = []
    for ws in workspaces:
        members = list(ws.memberships.all())
        user_membership = next((m for m in members if m.user_id == request.user.id), None)
        can_manage = user_membership and user_membership.workspace_role in (
            WorkspaceMembership.WorkspaceRole.OWNER,
            WorkspaceMembership.WorkspaceRole.MANAGER,
        )
        entry = {
            "workspace": ws,
            "members": members,
            "member_count": len(members),
            "can_manage": can_manage,
        }
        if ws.is_archived:
            archived_data.append(entry)
        else:
            workspace_data.append(entry)

    context = {
        "workspace_data": workspace_data,
        "archived_data": archived_data,
        "settings_active": "workspaces",
    }
    return render(request, "organizations/workspaces.html", context)


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
    """Schedule organization deletion for 14 days from now (owner only)."""
    if request.org_membership.org_role != OrgMembership.OrgRole.OWNER:
        raise PermissionDenied

    from apps.organizations.tasks import execute_scheduled_org_deletion

    grace = timedelta(days=14)
    org.deletion_requested_at = django_tz.now()
    org.deletion_scheduled_for = django_tz.now() + grace
    org.save(update_fields=["deletion_requested_at", "deletion_scheduled_for"])

    execute_scheduled_org_deletion(str(org.id), schedule=grace)

    messages.success(request, "Organization scheduled for deletion in 14 days.")
    return redirect("organizations:settings")


def _handle_immediate_org_deletion(request, org):
    """Permanently delete an organization right now (owner only).

    Since v1 is one-org-per-user, deleting the org leaves the user with no
    workspace/org context. Log them out and send them to signup so they can
    start fresh.
    """
    if request.org_membership.org_role != OrgMembership.OrgRole.OWNER:
        raise PermissionDenied

    from background_task.models import Task

    Task.objects.filter(
        task_name="apps.organizations.tasks.execute_scheduled_org_deletion",
        task_params__contains=str(org.id),
    ).delete()

    org.hard_delete(requesting_user=request.user)
    logout(request)
    return redirect("account_signup")


def _handle_cancel_deletion(request, org):
    """Cancel a pending organization deletion (owner only).

    Also removes the queued background-task row so the worker isn't holding
    a no-op scheduled for 14 days out.
    """
    if request.org_membership.org_role != OrgMembership.OrgRole.OWNER:
        raise PermissionDenied

    from background_task.models import Task

    Task.objects.filter(
        task_name="apps.organizations.tasks.execute_scheduled_org_deletion",
        task_params__contains=str(org.id),
    ).delete()

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

    # Base PlatformPost queryset with filters - each chip is one PP.
    from django.db.models.functions import Coalesce

    base_pps = (
        PlatformPost.objects.filter(post__workspace__in=filtered_workspaces)
        .select_related("post__workspace", "post__author", "social_account")
        .prefetch_related("post__media_attachments__media_asset")
        .annotate(effective_at=Coalesce("scheduled_at", "post__scheduled_at"))
    )

    # Channel filter
    channel = request.GET.get("channel")
    if channel:
        base_pps = base_pps.filter(social_account_id=channel)

    # Tag filter
    tag = request.GET.get("tag")
    if tag:
        base_pps = base_pps.filter(post__tags__contains=[tag])

    # Status filter — editorial status now lives on the PlatformPost itself.
    status = request.GET.get("status")
    if status:
        base_pps = base_pps.filter(status=status)

    # Workspace colors for legend
    workspace_colors = {}
    for ws in workspaces:
        workspace_colors[str(ws.id)] = ws.primary_color or "#F97316"

    today = date.today()

    # Build view-specific data
    if view_type == "week":
        context = _build_week_context(base_pps, target_date, today)
    elif view_type == "day":
        context = _build_day_context(base_pps, target_date, today)
    else:
        context = _build_month_context(base_pps, target_date, today)

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


def _build_month_context(base_pps, target_date, today):
    year, month = target_date.year, target_date.month
    cal = cal_mod.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    first_day = weeks[0][0]
    last_day = weeks[-1][6]

    platform_posts = base_pps.filter(
        effective_at__date__gte=first_day,
        effective_at__date__lte=last_day,
    ).order_by("effective_at")

    posts_by_date = defaultdict(list)
    for pp in platform_posts:
        if pp.effective_at:
            posts_by_date[pp.effective_at.date()].append(pp)

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


def _build_week_context(base_pps, target_date, today):
    monday = target_date - timedelta(days=target_date.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]

    platform_posts = base_pps.filter(
        effective_at__date__gte=week_days[0],
        effective_at__date__lte=week_days[6],
    ).order_by("effective_at")

    posts_by_slot = defaultdict(list)
    for pp in platform_posts:
        if pp.effective_at:
            key = (pp.effective_at.date(), pp.effective_at.hour)
            posts_by_slot[key].append(pp)

    hours = list(range(0, 24))

    week_slots = []
    for hour in hours:
        day_slots = []
        for day in week_days:
            key = (day, hour)
            day_slots.append((day, posts_by_slot.get(key, [])))
        week_slots.append((hour, day_slots))

    from django.utils import timezone as _tz

    return {
        "week_days": week_days,
        "hours": hours,
        "week_slots": week_slots,
        "today": today,
        "current_hour": _tz.now().hour,
        "period_label": f"{week_days[0].strftime('%b %d')} – {week_days[6].strftime('%b %d, %Y')}",
        "prev_date": (monday - timedelta(weeks=1)).isoformat(),
        "next_date": (monday + timedelta(weeks=1)).isoformat(),
    }


def _build_day_context(base_pps, target_date, today):
    platform_posts = base_pps.filter(effective_at__date=target_date).order_by("effective_at")

    posts_by_hour = defaultdict(list)
    for pp in platform_posts:
        if pp.effective_at:
            posts_by_hour[pp.effective_at.hour].append(pp)

    hours = list(range(0, 24))

    day_slots = [(hour, posts_by_hour.get(hour, [])) for hour in hours]

    now = django_tz.now()

    return {
        "day_slots": day_slots,
        "hours": hours,
        "today": today,
        "is_today": target_date == today,
        "is_past_day": target_date < today,
        "current_hour": now.hour,
        "period_label": target_date.strftime("%A, %B %d, %Y"),
        "prev_date": (target_date - timedelta(days=1)).isoformat(),
        "next_date": (target_date + timedelta(days=1)).isoformat(),
    }
