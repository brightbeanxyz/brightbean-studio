"""Views for the Content Calendar (F-2.3) and Publish page."""

import calendar as cal_mod
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.composer.models import ContentCategory, PlatformPost, Post
from apps.members.models import WorkspaceMembership
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

from .holidays import get_holidays_for_range
from .models import CustomCalendarEvent, PostingSlot, Queue

# Common timezones for the publish page timezone dropdown
COMMON_TIMEZONES = [
    "US/Eastern",
    "US/Central",
    "US/Mountain",
    "US/Pacific",
    "UTC",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Amsterdam",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "Asia/Dubai",
    "Australia/Sydney",
    "Pacific/Auckland",
    "America/Sao_Paulo",
    "America/Toronto",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/New_York",
]


def _slots_updated_response(account_id):
    """Return a 204 response with an HX-Trigger header for slot grid refresh."""
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": json.dumps({"slotsUpdated": {"accountId": str(account_id)}})},
    )


def _get_workspace(request, workspace_id):
    """Resolve workspace and enforce membership check."""
    workspace = get_object_or_404(Workspace, id=workspace_id)
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    has_membership = WorkspaceMembership.objects.filter(
        user=request.user,
        workspace=workspace,
    ).exists()
    if not has_membership:
        raise PermissionDenied("You are not a member of this workspace.")
    return workspace


def _parse_date(date_str, default=None):
    """Parse a YYYY-MM-DD date string."""
    if date_str:
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass
    return default or date.today()


def _get_filtered_posts(workspace, request):
    """Apply calendar filters from query params."""
    qs = (
        Post.objects.for_workspace(workspace.id)
        .select_related("author")
        .prefetch_related("platform_posts__social_account", "media_attachments__media_asset")
    )

    # Status filter — editorial status now lives on PlatformPost, so match
    # posts that have at least one child carrying the target state.
    statuses = request.GET.getlist("status")
    if statuses:
        qs = qs.filter(platform_posts__status__in=statuses).distinct()

    # Platform filter
    platforms = request.GET.getlist("platform")
    if platforms:
        qs = qs.filter(platform_posts__social_account__platform__in=platforms).distinct()

    # Author filter
    authors = request.GET.getlist("author")
    if authors:
        qs = qs.filter(author_id__in=authors)

    # Category filter
    categories = request.GET.getlist("category")
    if categories:
        qs = qs.filter(category_id__in=categories)

    # Tag filter (OR - match posts containing any selected tag)
    tags = request.GET.getlist("tag")
    if tags:
        from django.db.models import Q

        tag_q = Q()
        for tag in tags:
            tag_q |= Q(tags__contains=[tag])
        qs = qs.filter(tag_q)

    # Date range
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    if start_date:
        qs = qs.filter(scheduled_at__date__gte=_parse_date(start_date))
    if end_date:
        qs = qs.filter(scheduled_at__date__lte=_parse_date(end_date))

    return qs


def _get_filtered_platform_posts(workspace, request):
    """Return a PlatformPost queryset filtered by calendar query params.

    Each row carries an ``effective_at`` annotation that falls back to
    ``post.scheduled_at`` when the PlatformPost has no per-platform override.
    """
    from django.db.models.functions import Coalesce

    qs = (
        PlatformPost.objects.filter(post__workspace_id=workspace.id)
        .select_related("post", "post__author", "post__category", "social_account")
        .annotate(effective_at=Coalesce("scheduled_at", "post__scheduled_at"))
    )

    # Status filter — editorial status now lives on the PlatformPost itself,
    # so each chip can stand on its own per-account state.
    statuses = request.GET.getlist("status")
    if statuses:
        qs = qs.filter(status__in=statuses)

    # Platform filter
    platforms = request.GET.getlist("platform")
    if platforms:
        qs = qs.filter(social_account__platform__in=platforms)

    # Author filter
    authors = request.GET.getlist("author")
    if authors:
        qs = qs.filter(post__author_id__in=authors)

    # Category filter
    categories = request.GET.getlist("category")
    if categories:
        qs = qs.filter(post__category_id__in=categories)

    # Tag filter (OR)
    tags = request.GET.getlist("tag")
    if tags:
        from django.db.models import Q

        tag_q = Q()
        for tag in tags:
            tag_q |= Q(post__tags__contains=[tag])
        qs = qs.filter(tag_q)

    return qs


def _get_publish_context(workspace, request):
    """Build shared context for the publish page (channels, tags, timezone)."""
    # Channels that have posts in this workspace
    channels_with_posts = (
        SocialAccount.objects.filter(
            platform_posts__post__workspace=workspace,
        )
        .distinct()
        .order_by("platform", "account_name")
    )

    # All workspace tags from the Tag model
    from apps.composer.models import Tag

    all_tags = set(Tag.objects.for_workspace(workspace.id).values_list("name", flat=True))

    # Display timezone
    ws_tz = workspace.effective_timezone or "UTC"
    display_timezone = request.GET.get("tz", ws_tz)

    # Build ordered timezone list (workspace default first, then common ones)
    tz_list = [ws_tz]
    for tz in COMMON_TIMEZONES:
        if tz not in tz_list:
            tz_list.append(tz)

    return {
        "channels_with_posts": channels_with_posts,
        "all_tags": sorted(all_tags),
        "display_timezone": display_timezone,
        "timezone_choices": tz_list,
        "workspace_timezone": ws_tz,
        "queue_count": PlatformPost.objects.filter(post__workspace_id=workspace.id, status="scheduled").count(),
        "drafts_count": PlatformPost.objects.filter(post__workspace_id=workspace.id, status="draft").count(),
        "approvals_count": PlatformPost.objects.filter(
            post__workspace_id=workspace.id,
            status__in=["pending_review", "pending_client", "approved", "rejected", "changes_requested"],
        ).count(),
        "sent_count": PlatformPost.objects.filter(
            post__workspace_id=workspace.id,
            status__in=["published", "failed"],
        ).count(),
    }


def _apply_publish_filters(qs, request):
    """Apply channel and tag filters from publish page dropdowns."""
    channel = request.GET.get("channel")
    if channel:
        qs = qs.filter(platform_posts__social_account_id=channel).distinct()

    tag = request.GET.get("tag")
    if tag:
        qs = qs.filter(tags__contains=[tag])

    return qs


def _apply_pp_publish_filters(qs, request):
    """Apply channel and tag filters to a PlatformPost queryset."""
    channel = request.GET.get("channel")
    if channel:
        qs = qs.filter(social_account_id=channel)

    tag = request.GET.get("tag")
    if tag:
        qs = qs.filter(post__tags__contains=[tag])

    return qs


_TAB_TEMPLATES = {
    "queue": "calendar/partials/publish_queue.html",
    "drafts": "calendar/partials/publish_drafts.html",
    "approvals": "calendar/partials/publish_approvals.html",
    "sent": "calendar/partials/publish_sent.html",
}


def _get_tab_context(request, workspace, tab: str) -> dict:
    """Build the template context for one publish tab partial.

    Used both by `calendar_view` (initial server render) and the four
    `publish_tab_*` HTMX endpoints so the rendering paths stay in sync.
    """
    from django.db.models.functions import Coalesce

    if tab not in _TAB_TEMPLATES:
        tab = "queue"

    display_tz = request.GET.get("tz", workspace.effective_timezone or "UTC")
    has_connected_accounts = SocialAccount.objects.filter(
        workspace=workspace,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    ).exists()
    base_ctx = {
        "workspace": workspace,
        "display_timezone": display_tz,
        "has_connected_accounts": has_connected_accounts,
    }

    platform_posts: QuerySet[PlatformPost]
    if tab == "queue":
        platform_posts = (
            PlatformPost.objects.filter(post__workspace_id=workspace.id, status="scheduled")
            .select_related("post__author", "social_account")
            .prefetch_related("post__media_attachments__media_asset")
            .annotate(effective_at=Coalesce("scheduled_at", "post__scheduled_at"))
            .order_by("effective_at", "-post__created_at")
        )
        platform_posts = _apply_pp_publish_filters(platform_posts, request)
        return {**base_ctx, "platform_posts": platform_posts[:200]}

    if tab == "drafts":
        platform_posts = (
            PlatformPost.objects.filter(post__workspace_id=workspace.id, status="draft")
            .select_related("post__author", "social_account")
            .prefetch_related("post__media_attachments__media_asset")
            .order_by("-post__updated_at")
        )
        platform_posts = _apply_pp_publish_filters(platform_posts, request)
        return {**base_ctx, "platform_posts": platform_posts[:200]}

    if tab == "sent":
        platform_posts = (
            PlatformPost.objects.filter(
                post__workspace_id=workspace.id,
                status__in=["published", "failed"],
            )
            .select_related("post__author", "social_account")
            .prefetch_related("post__media_attachments__media_asset")
            .order_by("-post__scheduled_at", "-post__created_at")
        )
        platform_posts = _apply_pp_publish_filters(platform_posts, request)
        return {**base_ctx, "platform_posts": platform_posts[:200]}

    # approvals
    approval_statuses = ["pending_review", "pending_client", "approved", "rejected", "changes_requested"]
    status_filter = request.GET.get("approval_status", "all")
    platform_posts = (
        PlatformPost.objects.filter(
            post__workspace_id=workspace.id,
            status__in=approval_statuses,
        )
        .select_related("post__author", "social_account")
        .prefetch_related("post__media_attachments__media_asset")
        .order_by("post__scheduled_at", "-post__created_at")
    )
    platform_posts = _apply_pp_publish_filters(platform_posts, request)
    if status_filter != "all" and status_filter in approval_statuses:
        platform_posts = platform_posts.filter(status=status_filter)

    membership = getattr(request, "workspace_membership", None)
    perms = membership.effective_permissions if membership else {}
    can_approve = perms.get("approve_posts", False)

    def _count(status):
        return PlatformPost.objects.filter(post__workspace_id=workspace.id, status=status).count()

    return {
        **base_ctx,
        "platform_posts": platform_posts,
        "status_filter": status_filter,
        "can_approve": can_approve,
        "pending_review_count": _count("pending_review"),
        "pending_client_count": _count("pending_client"),
        "approved_count": _count("approved"),
        "rejected_count": _count("rejected"),
        "changes_requested_count": _count("changes_requested"),
    }


@login_required
def calendar_view(request, workspace_id):
    """Main publish page - renders calendar or list mode."""
    workspace = _get_workspace(request, workspace_id)
    has_connected_accounts = SocialAccount.objects.filter(
        workspace=workspace,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    ).exists()
    default_mode = "calendar" if has_connected_accounts else "list"
    mode = request.GET.get("mode", default_mode)
    active_tab = request.GET.get("tab", "queue")
    view_type = request.GET.get("view", "month")
    target_date = _parse_date(request.GET.get("date"))

    # Connected accounts for calendar filter UI
    social_accounts = (
        SocialAccount.objects.for_workspace(workspace.id)
        .filter(
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        .order_by("platform")
    )

    # Authors for filter
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    authors = (
        user_model.objects.filter(
            authored_posts__workspace=workspace,
        )
        .distinct()
        .values("id", "name", "email")
    )

    # Categories for filter
    categories = ContentCategory.objects.for_workspace(workspace.id)

    # Active filters
    active_filters = {
        "statuses": request.GET.getlist("status"),
        "platforms": request.GET.getlist("platform"),
        "authors": request.GET.getlist("author"),
        "categories": request.GET.getlist("category"),
        "tags": request.GET.getlist("tag"),
    }

    show_holidays = request.GET.get("holidays") == "1"

    # Publish page context (channels, tags, timezone dropdowns)
    publish_ctx = _get_publish_context(workspace, request)

    context = {
        "workspace": workspace,
        "mode": mode,
        "active_tab": active_tab,
        "view_type": view_type,
        "target_date": target_date,
        "social_accounts": social_accounts,
        "authors": authors,
        "categories": categories,
        "active_filters": active_filters,
        "status_choices": Post.Status.choices,
        "show_holidays": show_holidays,
        **publish_ctx,
    }

    # For list mode: fetch the active tab's data so the shell can render the
    # initial tab inline server-side (avoids a JS-triggered HTMX waterfall and
    # the resulting content shift).
    if mode == "list":
        context.update(_get_tab_context(request, workspace, active_tab))
        context["initial_tab_template"] = _TAB_TEMPLATES.get(active_tab, _TAB_TEMPLATES["queue"])
        context["is_htmx"] = False

    # HTMX partial: switching between list and calendar mode
    # Only intercept when the toggle buttons explicitly request a mode switch
    is_htmx = getattr(request, "htmx", False)
    if is_htmx and request.GET.get("_switch_mode"):
        if mode == "list":
            return render(request, "calendar/partials/publish_list_shell.html", context)
        else:
            # Render the full calendar shell (toolbar + grid) for mode switch.
            # We still need the calendar data populated in context first.
            _populate_calendar_context(request, workspace, view_type, target_date, context)
            return render(request, "calendar/partials/publish_calendar_shell.html", context)

    # Full page or calendar HTMX partial (sub-view switching within calendar)
    if mode == "calendar":
        return _render_calendar_partial(request, workspace, view_type, target_date, context)

    # Full page in list mode
    return render(request, "calendar/calendar.html", context)


def _populate_calendar_context(request, workspace, view_type, target_date, context):
    """Populate context with calendar data without rendering.

    Used when we need the calendar data (period_label, prev/next dates, etc.)
    but want to render a different template (e.g., the calendar shell on mode switch).
    """
    if view_type == "month":
        _month_view_data(request, workspace, target_date, context)
    elif view_type == "week":
        _week_view_data(request, workspace, target_date, context)
    elif view_type == "day":
        _day_view_data(request, workspace, target_date, context)
    else:
        _month_view_data(request, workspace, target_date, context)


def _render_calendar_partial(request, workspace, view_type, target_date, context):
    """Render the appropriate calendar partial based on view type."""
    if view_type == "month":
        return _month_view(request, workspace, target_date, context)
    elif view_type == "week":
        return _week_view(request, workspace, target_date, context)
    elif view_type == "day":
        return _day_view(request, workspace, target_date, context)
    elif view_type == "list":
        return _list_view(request, workspace, target_date, context)
    return _month_view(request, workspace, target_date, context)


def _month_view_data(request, workspace, target_date, context):
    """Populate context with month view data (no rendering)."""
    import zoneinfo

    display_tz = zoneinfo.ZoneInfo(context.get("display_timezone", "UTC"))

    year, month = target_date.year, target_date.month
    cal = cal_mod.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdatescalendar(year, month)

    # Get all platform posts for this month range (one chip per PlatformPost)
    # Widen by ±1 day to handle timezone boundary shifts
    first_day = weeks[0][0] - timedelta(days=1)
    last_day = weeks[-1][6] + timedelta(days=1)
    platform_posts = (
        _get_filtered_platform_posts(workspace, request)
        .filter(
            effective_at__date__gte=first_day,
            effective_at__date__lte=last_day,
        )
        .order_by("effective_at")
    )

    # Also include drafts without scheduled_at for the current month
    drafts = (
        _get_filtered_posts(workspace, request)
        .filter(
            platform_posts__status="draft",
            scheduled_at__isnull=True,
        )
        .distinct()
        .order_by("-updated_at")[:10]
    )

    # Group PlatformPosts by date in the display timezone
    posts_by_date = defaultdict(list)
    for pp in platform_posts:
        if pp.effective_at:
            posts_by_date[pp.effective_at.astimezone(display_tz).date()].append(pp)

    # Holiday overlay
    holidays_by_date = {}
    if context.get("show_holidays"):
        holidays_by_date = get_holidays_for_range(weeks[0][0], weeks[-1][6])

    # Custom calendar events
    custom_events = (
        CustomCalendarEvent.objects.for_workspace(workspace.id)
        .filter(start_date__lte=weeks[-1][6], end_date__gte=weeks[0][0])
        .order_by("start_date")
    )

    # Build weeks data
    from django.utils import timezone as _tz

    today = _tz.now().astimezone(display_tz).date()
    calendar_weeks = []
    for week in weeks:
        week_data = []
        for day in week:
            day_posts = posts_by_date.get(day, [])
            day_holidays = holidays_by_date.get(day.isoformat(), [])
            day_events = [e for e in custom_events if e.start_date <= day <= e.end_date]
            week_data.append(
                {
                    "date": day,
                    "is_current_month": day.month == month,
                    "is_today": day == today,
                    "is_past": day < today,
                    "posts": day_posts[:3],
                    "total_posts": len(day_posts),
                    "overflow": max(0, len(day_posts) - 3),
                    "holidays": day_holidays,
                    "events": day_events,
                }
            )
        calendar_weeks.append(week_data)

    # Navigation
    prev_month = (date(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(year, month, 28) + timedelta(days=4)).replace(day=1)

    context.update(
        {
            "calendar_weeks": calendar_weeks,
            "period_label": date(year, month, 1).strftime("%B %Y"),
            "prev_date": prev_month.isoformat(),
            "next_date": next_month.isoformat(),
            "unscheduled_drafts": drafts,
            "day_names": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        }
    )


def _month_view(request, workspace, target_date, context):
    """Render month view calendar grid."""
    _month_view_data(request, workspace, target_date, context)
    template = "calendar/partials/month_grid.html" if request.htmx else "calendar/calendar.html"
    return render(request, template, context)


def _week_view_data(request, workspace, target_date, context):
    """Populate context with week view data (no rendering)."""
    import zoneinfo

    display_tz = zoneinfo.ZoneInfo(context.get("display_timezone", "UTC"))

    # Find Monday of the target week
    monday = target_date - timedelta(days=target_date.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]

    # Widen query by ±1 day to handle timezone boundary shifts
    platform_posts = (
        _get_filtered_platform_posts(workspace, request)
        .filter(
            effective_at__date__gte=week_days[0] - timedelta(days=1),
            effective_at__date__lte=week_days[6] + timedelta(days=1),
        )
        .order_by("effective_at")
    )

    # Group PlatformPosts by (date, hour) in the display timezone
    week_days_set = set(week_days)
    posts_by_slot = defaultdict(list)
    for pp in platform_posts:
        if pp.effective_at:
            local_dt = pp.effective_at.astimezone(display_tz)
            if local_dt.date() in week_days_set:
                key = (local_dt.date(), local_dt.hour)
                posts_by_slot[key].append(pp)

    hours = list(range(0, 24))

    # Build a grid structure the template can iterate:
    # week_slots = [(hour, [(day, posts), ...]), ...]
    week_slots = []
    for hour in hours:
        day_slots = []
        for day in week_days:
            key = (day, hour)
            day_slots.append((day, posts_by_slot.get(key, [])))
        week_slots.append((hour, day_slots))

    from django.utils import timezone as _tz

    now = _tz.now().astimezone(display_tz)
    context.update(
        {
            "week_days": week_days,
            "hours": hours,
            "week_slots": week_slots,
            "today": now.date(),
            "current_hour": now.hour,
            "prev_date": (monday - timedelta(weeks=1)).isoformat(),
            "next_date": (monday + timedelta(weeks=1)).isoformat(),
            "period_label": f"{week_days[0].strftime('%b %d')} – {week_days[6].strftime('%b %d, %Y')}",
        }
    )


def _week_view(request, workspace, target_date, context):
    """Render week view with hourly rows."""
    _week_view_data(request, workspace, target_date, context)
    template = "calendar/partials/week_grid.html" if request.htmx else "calendar/calendar.html"
    return render(request, template, context)


def _day_view_data(request, workspace, target_date, context):
    """Populate context with day view data (no rendering)."""
    import zoneinfo

    display_tz = zoneinfo.ZoneInfo(context.get("display_timezone", "UTC"))

    # Widen query by ±1 day to handle timezone boundary shifts
    platform_posts = (
        _get_filtered_platform_posts(workspace, request)
        .filter(
            effective_at__date__gte=target_date - timedelta(days=1),
            effective_at__date__lte=target_date + timedelta(days=1),
        )
        .order_by("effective_at")
    )

    # Group by hour in the display timezone, filtering to the target date
    posts_by_hour = defaultdict(list)
    for pp in platform_posts:
        if pp.effective_at:
            local_dt = pp.effective_at.astimezone(display_tz)
            if local_dt.date() == target_date:
                posts_by_hour[local_dt.hour].append(pp)

    hours = list(range(0, 24))

    # Build a list of (hour, posts) tuples for easy template iteration
    day_slots = [(hour, posts_by_hour.get(hour, [])) for hour in hours]

    from django.utils import timezone as _tz

    now = _tz.now().astimezone(display_tz)
    context.update(
        {
            "day_slots": day_slots,
            "hours": hours,
            "target_date": target_date,
            "is_today": target_date == now.date(),
            "is_past_day": target_date < now.date(),
            "current_hour": now.hour,
            "prev_date": (target_date - timedelta(days=1)).isoformat(),
            "next_date": (target_date + timedelta(days=1)).isoformat(),
            "period_label": target_date.strftime("%A, %B %d, %Y"),
        }
    )


def _day_view(request, workspace, target_date, context):
    """Render day view with detailed hour timeline."""
    _day_view_data(request, workspace, target_date, context)
    template = "calendar/partials/day_grid.html" if request.htmx else "calendar/calendar.html"
    return render(request, template, context)


def _list_view(request, workspace, target_date, context):
    """Render list/table view of posts."""
    posts = _get_filtered_posts(workspace, request).order_by("-scheduled_at", "-created_at")[:200]

    has_connected_accounts = SocialAccount.objects.filter(
        workspace=workspace,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    ).exists()

    context.update(
        {
            "posts": posts,
            "period_label": "All Posts",
            "prev_date": target_date.isoformat(),
            "next_date": target_date.isoformat(),
            "has_connected_accounts": has_connected_accounts,
        }
    )

    template = "calendar/partials/list_view.html" if request.htmx else "calendar/calendar.html"
    return render(request, template, context)


# ---------------------------------------------------------------------------
# Publish page tab views (HTMX partials)
# ---------------------------------------------------------------------------


def _render_tab(request, workspace, tab):
    """Shared HTMX-tab renderer used by the four `publish_tab_*` endpoints."""
    ctx = _get_tab_context(request, workspace, tab)
    ctx["is_htmx"] = True
    return render(request, _TAB_TEMPLATES[tab], ctx)


@login_required
def publish_tab_queue(request, workspace_id):
    """HTMX partial: Queue tab content - shows all scheduled platform posts."""
    workspace = _get_workspace(request, workspace_id)
    return _render_tab(request, workspace, "queue")


@login_required
def publish_tab_drafts(request, workspace_id):
    """HTMX partial: Drafts tab content for the publish page."""
    workspace = _get_workspace(request, workspace_id)
    return _render_tab(request, workspace, "drafts")


@login_required
def publish_tab_approvals(request, workspace_id):
    """HTMX partial: Approvals tab content for the publish page."""
    workspace = _get_workspace(request, workspace_id)
    return _render_tab(request, workspace, "approvals")


@login_required
def publish_tab_sent(request, workspace_id):
    """HTMX partial: Sent tab content for the publish page."""
    workspace = _get_workspace(request, workspace_id)
    return _render_tab(request, workspace, "sent")


@login_required
@require_POST
def reschedule_post(request, workspace_id):
    """HTMX endpoint for drag-and-drop rescheduling of a single PlatformPost."""
    from apps.composer.services import sync_post_scheduled_at

    workspace = _get_workspace(request, workspace_id)
    platform_post_id = request.POST.get("platform_post_id") or request.POST.get("post_id")
    new_datetime_str = request.POST.get("new_datetime")

    if not platform_post_id or not new_datetime_str:
        return JsonResponse({"error": "platform_post_id and new_datetime required"}, status=400)

    pp = get_object_or_404(
        PlatformPost.objects.select_related("post__workspace", "post__author"),
        id=platform_post_id,
        post__workspace=workspace,
    )
    post = pp.post

    # Check permissions - only editable statuses can be rescheduled
    if pp.status not in ("draft", "approved", "scheduled"):
        return JsonResponse({"error": "Post cannot be rescheduled in its current status."}, status=400)

    # Check RBAC
    membership = request.workspace_membership
    perms = membership.effective_permissions if membership else {}
    is_own_post = post.author_id == request.user.id
    can_edit = (is_own_post and perms.get("edit_own_posts")) or perms.get("edit_others_posts")
    if not can_edit:
        return JsonResponse({"error": "Permission denied."}, status=403)

    try:
        import zoneinfo

        ws_tz = workspace.effective_timezone or "UTC"
        tz = zoneinfo.ZoneInfo(ws_tz)
        new_dt = datetime.fromisoformat(new_datetime_str)
        if new_dt.tzinfo is None:
            new_dt = new_dt.replace(tzinfo=tz)
        pp.scheduled_at = new_dt
        # Drop into "scheduled" so the publisher picks it up. Drag-drop on a
        # draft chip is treated as an implicit schedule action.
        if pp.status == "draft" and pp.can_transition_to("scheduled"):
            pp.transition_to("scheduled")
        pp.save(update_fields=["status", "scheduled_at", "updated_at"])
        sync_post_scheduled_at(post)
    except (ValueError, TypeError) as e:
        return JsonResponse({"error": f"Invalid datetime: {e}"}, status=400)

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": json.dumps({"postRescheduled": {"platformPostId": str(pp.id), "postId": str(post.id)}})},
    )


@login_required
def posting_slots(request, workspace_id):
    """Manage posting slots for a workspace's social accounts."""
    workspace = _get_workspace(request, workspace_id)
    accounts = SocialAccount.objects.for_workspace(workspace.id).filter(
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )

    slots = (
        PostingSlot.objects.filter(
            social_account__in=accounts,
        )
        .select_related("social_account")
        .order_by("social_account", "day_of_week", "time")
    )

    # Group by account
    slots_by_account = defaultdict(list)
    for slot in slots:
        slots_by_account[slot.social_account_id].append(slot)

    context = {
        "workspace": workspace,
        "accounts": accounts,
        "slots_by_account": dict(slots_by_account),
        "day_choices": PostingSlot.DayOfWeek.choices,
    }
    return render(request, "calendar/posting_slots.html", context)


@login_required
@require_POST
def save_posting_slot(request, workspace_id):
    """Create or update a posting slot."""
    workspace = _get_workspace(request, workspace_id)
    account_id = request.POST.get("social_account_id")
    day = request.POST.get("day_of_week")
    time_str = request.POST.get("time")

    if not all([account_id, day, time_str]):
        return JsonResponse({"error": "All fields required."}, status=400)

    account = get_object_or_404(
        SocialAccount,
        id=account_id,
        workspace=workspace,
    )

    try:
        slot_time = time.fromisoformat(time_str)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid time format."}, status=400)

    slot, created = PostingSlot.objects.get_or_create(
        social_account=account,
        day_of_week=int(day),
        time=slot_time,
        defaults={"is_active": True},
    )

    if request.htmx:
        return _slots_updated_response(account.id)
    return JsonResponse({"id": str(slot.id), "created": created})


@login_required
@require_POST
def delete_posting_slot(request, workspace_id, slot_id):
    """Delete a posting slot."""
    workspace = _get_workspace(request, workspace_id)
    slot = get_object_or_404(PostingSlot, id=slot_id)
    # Verify the slot belongs to this workspace
    if slot.social_account.workspace_id != workspace.id:
        return JsonResponse({"error": "Not found."}, status=404)

    account_id = str(slot.social_account_id)
    slot.delete()
    if request.htmx:
        return _slots_updated_response(account_id)
    return JsonResponse({"deleted": True})


@login_required
def account_posting_slots_partial(request, workspace_id):
    """Return the posting slots grid partial for a single account (HTMX)."""
    workspace = _get_workspace(request, workspace_id)
    account_id = request.GET.get("social_account_id")
    account = get_object_or_404(
        SocialAccount.objects.prefetch_related("posting_slots"),
        id=account_id,
        workspace=workspace,
    )
    return render(
        request,
        "social_accounts/partials/_posting_slots_grid.html",
        {"account": account, "workspace_id": workspace_id},
    )


@login_required
@require_POST
def toggle_posting_slot_day(request, workspace_id):
    """Toggle is_active for all posting slots of an account on a given day."""
    workspace = _get_workspace(request, workspace_id)
    account_id = request.POST.get("social_account_id")
    day = request.POST.get("day_of_week")

    if not account_id or day is None:
        return JsonResponse({"error": "Missing fields."}, status=400)

    account = get_object_or_404(SocialAccount, id=account_id, workspace=workspace)
    try:
        day_int = int(day)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid day_of_week."}, status=400)
    slots = PostingSlot.objects.filter(social_account=account, day_of_week=day_int)

    if not slots.exists():
        return HttpResponse(status=204)

    # If all active → deactivate; otherwise → activate all
    all_active = not slots.filter(is_active=False).exists()
    slots.update(is_active=not all_active)

    if request.htmx:
        return _slots_updated_response(account_id)
    return JsonResponse({"toggled": True})


@login_required
@require_POST
def update_posting_slot(request, workspace_id, slot_id):
    """Update a posting slot's time."""
    workspace = _get_workspace(request, workspace_id)
    slot = get_object_or_404(PostingSlot, id=slot_id)
    if slot.social_account.workspace_id != workspace.id:
        return JsonResponse({"error": "Not found."}, status=404)

    time_str = request.POST.get("time")
    if not time_str:
        return JsonResponse({"error": "Time is required."}, status=400)

    try:
        new_time = time.fromisoformat(time_str)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid time format."}, status=400)

    # Check for duplicate
    if (
        PostingSlot.objects.filter(
            social_account=slot.social_account,
            day_of_week=slot.day_of_week,
            time=new_time,
        )
        .exclude(id=slot.id)
        .exists()
    ):
        return JsonResponse({"error": "A slot at that time already exists."}, status=409)

    slot.time = new_time
    slot.save(update_fields=["time", "updated_at"])

    account_id = str(slot.social_account_id)
    if request.htmx:
        return _slots_updated_response(account_id)
    return JsonResponse({"updated": True})


# ---------------------------------------------------------------------------
# Queue CRUD
# ---------------------------------------------------------------------------


@login_required
def queue_list(request, workspace_id):
    """List all queues for this workspace."""
    workspace = _get_workspace(request, workspace_id)
    queues = Queue.objects.for_workspace(workspace.id).select_related("social_account", "category")
    accounts = SocialAccount.objects.for_workspace(workspace.id).filter(
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    categories = ContentCategory.objects.for_workspace(workspace.id)

    return render(
        request,
        "calendar/queues.html",
        {
            "workspace": workspace,
            "queues": queues,
            "accounts": accounts,
            "categories": categories,
        },
    )


@login_required
@require_POST
def queue_create(request, workspace_id):
    """Create a new queue."""
    workspace = _get_workspace(request, workspace_id)
    name = request.POST.get("name", "").strip()
    account_id = request.POST.get("social_account_id")
    category_id = request.POST.get("category_id") or None

    if not name or not account_id:
        return JsonResponse({"error": "Name and account required."}, status=400)

    account = get_object_or_404(SocialAccount, id=account_id, workspace=workspace)

    Queue.objects.create(
        workspace=workspace,
        name=name,
        social_account=account,
        category_id=category_id,
    )

    if request.htmx:
        return HttpResponse(status=204, headers={"HX-Trigger": "queueChanged"})
    return redirect("calendar:queue_list", workspace_id=workspace.id)


@login_required
def queue_detail(request, workspace_id, queue_id):
    """Show queue entries in order with drag-to-reorder."""
    workspace = _get_workspace(request, workspace_id)
    queue = get_object_or_404(Queue, id=queue_id, workspace=workspace)
    entries = (
        queue.entries.select_related("post__author")
        .prefetch_related("post__platform_posts__social_account")
        .order_by("position")
    )

    return render(
        request,
        "calendar/queue_detail.html",
        {
            "workspace": workspace,
            "queue": queue,
            "entries": entries,
        },
    )


@login_required
@require_POST
def queue_delete(request, workspace_id, queue_id):
    """Delete a queue."""
    workspace = _get_workspace(request, workspace_id)
    queue = get_object_or_404(Queue, id=queue_id, workspace=workspace)
    queue.delete()

    if request.htmx:
        return HttpResponse(status=204, headers={"HX-Trigger": "queueChanged"})
    return redirect("calendar:queue_list", workspace_id=workspace.id)


@login_required
@require_POST
def queue_reorder(request, workspace_id, queue_id):
    """Reorder queue entries via HTMX drag-and-drop."""
    workspace = _get_workspace(request, workspace_id)
    queue = get_object_or_404(Queue, id=queue_id, workspace=workspace)

    entry_ids_str = request.POST.get("entry_ids", "")
    entry_ids = [s.strip() for s in entry_ids_str.split(",") if s.strip()]

    from .services import reorder_queue

    reorder_queue(queue, entry_ids)

    if request.htmx:
        return HttpResponse(status=204, headers={"HX-Trigger": "queueReordered"})
    return JsonResponse({"reordered": True})


# ---------------------------------------------------------------------------
# Custom Calendar Events CRUD
# ---------------------------------------------------------------------------


@login_required
@require_POST
def event_create(request, workspace_id):
    """Create a custom calendar event via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    title = request.POST.get("title", "").strip()
    start_date_str = request.POST.get("start_date", "")
    end_date_str = request.POST.get("end_date", "")
    color = request.POST.get("color", "#3B82F6")
    description = request.POST.get("description", "").strip()

    if not title or not start_date_str or not end_date_str:
        return JsonResponse({"error": "Title, start date, and end date required."}, status=400)

    try:
        start = date.fromisoformat(start_date_str)
        end = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid date format."}, status=400)

    if end < start:
        end = start

    CustomCalendarEvent.objects.create(
        workspace=workspace,
        title=title,
        description=description,
        start_date=start,
        end_date=end,
        color=color,
        created_by=request.user,
    )

    if request.htmx:
        return HttpResponse(status=204, headers={"HX-Trigger": "calendarRefresh"})
    return JsonResponse({"created": True})


@login_required
@require_POST
def event_edit(request, workspace_id, event_id):
    """Edit a custom calendar event."""
    workspace = _get_workspace(request, workspace_id)
    event = get_object_or_404(CustomCalendarEvent, id=event_id, workspace=workspace)

    event.title = request.POST.get("title", event.title).strip()
    event.description = request.POST.get("description", event.description).strip()
    event.color = request.POST.get("color", event.color)

    import contextlib

    start_str = request.POST.get("start_date")
    end_str = request.POST.get("end_date")
    if start_str:
        with contextlib.suppress(ValueError, TypeError):
            event.start_date = date.fromisoformat(start_str)
    if end_str:
        with contextlib.suppress(ValueError, TypeError):
            event.end_date = date.fromisoformat(end_str)

    event.save()

    if request.htmx:
        return HttpResponse(status=204, headers={"HX-Trigger": "calendarRefresh"})
    return JsonResponse({"updated": True})


@login_required
@require_POST
def event_delete(request, workspace_id, event_id):
    """Delete a custom calendar event."""
    workspace = _get_workspace(request, workspace_id)
    event = get_object_or_404(CustomCalendarEvent, id=event_id, workspace=workspace)
    event.delete()

    if request.htmx:
        return HttpResponse(status=204, headers={"HX-Trigger": "calendarRefresh"})
    return JsonResponse({"deleted": True})
