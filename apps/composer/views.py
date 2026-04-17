"""Views for the Post Composer (F-2.1)."""

import contextlib
import json
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx
from dateutil import parser as date_parser
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_GET, require_POST

from apps.members.decorators import require_permission
from apps.members.models import WorkspaceMembership
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

from .forms import ContentCategoryForm, PostForm
from .models import (
    ContentCategory,
    Feed,
    Idea,
    IdeaGroup,
    IdeaMedia,
    PlatformPost,
    Post,
    PostMedia,
    PostTemplate,
    PostVersion,
    Tag,
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


def _sync_platform_posts(request, post, workspace, initial_status=None):
    """Sync platform post selections from form data.

    When ``initial_status`` is given, newly-created PlatformPost rows are
    initialised to that status (e.g. ``"draft"``, ``"scheduled"``,
    ``"pending_review"``). Existing rows are not touched here — call
    ``_transition_post_children`` separately if you want to move them.
    """
    selected_ids_str = request.POST.get("selected_accounts", "")
    selected_ids = [s.strip() for s in selected_ids_str.split(",") if s.strip()]
    post.platform_posts.exclude(social_account_id__in=selected_ids).delete()
    for acc_id in selected_ids:
        try:
            account = SocialAccount.objects.get(id=acc_id, workspace=workspace)
        except SocialAccount.DoesNotExist:
            continue
        defaults = {}
        if initial_status:
            defaults["status"] = initial_status
        pp, _created = PlatformPost.objects.get_or_create(
            post=post,
            social_account=account,
            defaults=defaults,
        )
        override_title = request.POST.get(f"override_title_{acc_id}", "").strip()
        override_caption = request.POST.get(f"override_caption_{acc_id}", "").strip()
        override_comment = request.POST.get(f"override_comment_{acc_id}", "").strip()
        pp.platform_specific_title = override_title if override_title else None
        pp.platform_specific_caption = override_caption if override_caption else None
        pp.platform_specific_first_comment = override_comment if override_comment else None

        # Per-platform extras
        if account.platform == "youtube":
            tags_raw = request.POST.get(f"yt_tags_{acc_id}", "")
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
            privacy_status = request.POST.get(f"yt_privacy_status_{acc_id}", "public")
            if privacy_status not in ("public", "unlisted", "private"):
                privacy_status = "public"
            thumb_id = request.POST.get(f"yt_thumbnail_asset_id_{acc_id}", "").strip() or None
            pp.platform_extra = {
                "privacy_status": privacy_status,
                "self_declared_made_for_kids": request.POST.get(f"yt_made_for_kids_{acc_id}") == "true",
                "tags": tags_list,
                "thumbnail_asset_id": thumb_id,
            }

        elif account.platform == "pinterest":
            pp.platform_extra = {
                "board_id": request.POST.get(f"pin_board_id_{acc_id}", "").strip() or None,
                "link_url": request.POST.get(f"pin_link_url_{acc_id}", "").strip() or None,
                "alt_text": request.POST.get(f"pin_alt_text_{acc_id}", "").strip() or None,
                "tag_products": request.POST.get(f"pin_tag_products_{acc_id}", "").strip() or None,
                "allow_comments": request.POST.get(f"pin_allow_comments_{acc_id}") == "true",
                "show_similar_products": request.POST.get(f"pin_show_similar_{acc_id}") == "true",
                "cover_image_asset_id": request.POST.get(f"pin_cover_image_asset_id_{acc_id}", "").strip() or None,
            }

        pp.save()


def _save_version(post, user):
    """Create a PostVersion snapshot."""
    version_number = (post.versions.count()) + 1
    snapshot = {
        "title": post.title,
        "caption": post.caption,
        "first_comment": post.first_comment,
        "internal_notes": post.internal_notes,
        "tags": post.tags,
        "status": post.status,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "platform_posts": [
            {
                "social_account_id": str(pp.social_account_id),
                "platform": pp.social_account.platform,
                "title_override": pp.platform_specific_title,
                "caption_override": pp.platform_specific_caption,
                "first_comment_override": pp.platform_specific_first_comment,
                "platform_extra": pp.platform_extra or {},
            }
            for pp in post.platform_posts.select_related("social_account")
        ],
        "media": [
            {
                "media_asset_id": str(pm.media_asset_id),
                "position": pm.position,
                "alt_text": pm.alt_text,
            }
            for pm in post.media_attachments.all()
        ],
    }
    PostVersion.objects.create(
        post=post,
        version_number=version_number,
        snapshot=snapshot,
        created_by=user,
    )


def _resolve_queues_for_post(queue_id, workspace, post_data):
    """Resolve the Queues to add a post to.

    Returns a list of Queue objects - one per selected social account when
    no explicit ``queue_id`` is supplied by the composer form. If an explicit
    queue_id is provided it is used exclusively.
    """
    from apps.calendar.models import Queue

    if queue_id:
        q = Queue.objects.filter(id=queue_id, workspace=workspace, is_active=True).first()
        return [q] if q else []

    selected_raw = post_data.get("selected_accounts", "") or ""
    account_ids = [a.strip() for a in selected_raw.split(",") if a.strip()]
    if not account_ids:
        return []

    queues = list(
        Queue.objects.filter(workspace=workspace, is_active=True, social_account_id__in=account_ids).order_by(
            "created_at"
        )
    )
    # De-duplicate by social_account (one queue per account)
    seen = set()
    unique = []
    for q in queues:
        if q.social_account_id in seen:
            continue
        seen.add(q.social_account_id)
        unique.append(q)
    return unique


def _reassign_queue_slots_from_floor(queues, post, floor_date, workspace):
    """Override per-platform scheduled_at for *post* with the next posting slot
    on/after *floor_date* for each queue's social account.

    Used when the composer was opened from a specific calendar day - we want
    each platform to pick its earliest available slot starting that day,
    independently.
    """
    from apps.calendar.services import _next_slot_datetimes
    from apps.composer.services import sync_post_scheduled_at

    ws_tz = workspace.effective_timezone or "UTC"
    import zoneinfo

    tz = zoneinfo.ZoneInfo(ws_tz)
    floor_dt = datetime.combine(floor_date, datetime.min.time()).replace(tzinfo=tz)
    floor_dt = max(floor_dt, timezone.now())

    for q in queues:
        slots = _next_slot_datetimes(q.social_account, floor_dt, count=1)
        if not slots:
            continue
        pp = post.platform_posts.filter(social_account=q.social_account).first()
        if pp is None:
            continue
        pp.scheduled_at = slots[0]
        pp.save(update_fields=["scheduled_at", "updated_at"])

    sync_post_scheduled_at(post)


@login_required
@require_permission("create_posts")
def compose(request, workspace_id, post_id=None):
    """Render the full-page composer for creating or editing a post."""
    workspace = _get_workspace(request, workspace_id)

    # Load existing post or prepare a blank one
    if post_id:
        post = get_object_or_404(Post, id=post_id, workspace=workspace)
        # Enforce edit permissions: authors can edit their own posts,
        # but editing another user's post requires edit_others_posts.
        membership = request.workspace_membership
        perms = membership.effective_permissions if membership else {}
        if post.author != request.user and not perms.get("edit_others_posts", False):
            raise PermissionDenied("You do not have permission to edit this post.")
        form = PostForm(instance=post)
        if post.scheduled_at:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(workspace.effective_timezone or "UTC")
            local_dt = post.scheduled_at.astimezone(tz)
            form.initial["scheduled_date"] = local_dt.strftime("%Y-%m-%d")
            form.initial["scheduled_time"] = local_dt.strftime("%H:%M")
        _acct_filter = request.GET.get("account")
        if _acct_filter:
            selected_account_ids = list(
                post.platform_posts.filter(social_account_id=_acct_filter).values_list("social_account_id", flat=True)
            )
        else:
            selected_account_ids = list(post.platform_posts.values_list("social_account_id", flat=True))
        media_attachments = post.media_attachments.select_related("media_asset").all()
        platform_extras = {str(pp.social_account_id): (pp.platform_extra or {}) for pp in post.platform_posts.all()}
    else:
        post = None
        # Pre-fill scheduled date/time from query params (e.g. when coming from calendar "+" CTA)
        initial = {}
        qs_date = request.GET.get("scheduled_date")
        qs_time = request.GET.get("scheduled_time")
        if qs_date:
            with contextlib.suppress(ValueError):
                initial["scheduled_date"] = datetime.strptime(qs_date, "%Y-%m-%d").date().isoformat()
        if qs_time:
            parsed_time = None
            for fmt in ("%H:%M", "%H:%M:%S"):
                try:
                    parsed_time = datetime.strptime(qs_time, fmt).time()
                    break
                except ValueError:
                    continue
            if parsed_time is not None:
                initial["scheduled_time"] = parsed_time.strftime("%H:%M")
        form = PostForm(initial=initial)
        selected_account_ids = []
        media_attachments = []
        platform_extras = {}

    # Clear any stale pending media from previous compose sessions.
    # Each compose page load starts fresh; the upload flow re-populates
    # the session as the user adds files.
    from apps.media_library.models import MediaAsset

    session_key = f"pending_media_{workspace.id}"
    request.session.pop(session_key, None)
    pending_assets = MediaAsset.objects.none()

    # Connected social accounts for this workspace
    social_accounts = (
        SocialAccount.objects.for_workspace(workspace.id)
        .filter(
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        .order_by("platform", "account_name")
    )

    # When opening from calendar with a specific account, show only that account
    account_filter = request.GET.get("account")
    if account_filter and post_id:
        social_accounts = social_accounts.filter(id=account_filter)

    # Platform character limits for JS
    char_limits = {
        str(acc.id): {
            "platform": acc.platform,
            "limit": acc.char_limit,
            "name": acc.account_name,
            **acc.field_config,
        }
        for acc in social_accounts
    }

    # Workspace defaults
    default_first_comment = workspace.default_first_comment
    default_hashtags = workspace.default_hashtags

    # Categories for dropdown
    categories = ContentCategory.objects.for_workspace(workspace.id)

    # Queues for "Add to Queue" action
    from apps.calendar.models import Queue

    queues = (
        Queue.objects.for_workspace(workspace.id).filter(is_active=True).select_related("social_account", "category")
    )

    # Permissions for action buttons
    membership = request.workspace_membership
    perms = membership.effective_permissions if membership else {}
    can_publish = perms.get("publish_directly", False)
    can_approve = perms.get("approve_posts", False)
    ws_role = membership.workspace_role if membership else None
    can_view_internal_notes = ws_role not in ("client", "viewer") if ws_role else True

    # Template data pre-fill (if using a template)
    template_id = request.GET.get("template")
    template_data = None
    if template_id and not post:
        try:
            tpl = PostTemplate.objects.get(id=template_id, workspace=workspace)
            template_data = tpl.template_data
        except (PostTemplate.DoesNotExist, ValidationError):
            # Fall back to built-in template by integer ID
            from apps.composer.builtin_templates import TEMPLATES as BUILTIN_TEMPLATES

            builtin = next((t for t in BUILTIN_TEMPLATES if str(t["id"]) == template_id), None)
            if builtin:
                template_data = {"body": builtin.get("body", ""), "title": builtin.get("title", "")}

    # Pre-fill caption from template data
    if template_data and not post:
        body = template_data.get("body", "")
        if body:
            form.initial["caption"] = body

    # Approval workflow context
    workflow_mode = workspace.approval_workflow_mode
    show_submit_button = workflow_mode != "none"
    show_resubmit_button = (
        post is not None and post.platform_posts.filter(status__in=("changes_requested", "rejected")).exists()
    )

    # Approval history and comments for existing posts
    approval_history = []
    post_comments = []
    if post:
        from apps.approvals.models import ApprovalAction

        approval_history = ApprovalAction.objects.filter(post=post).select_related("user").order_by("-created_at")[:10]
        from apps.approvals.comments import get_comments_for_post

        post_comments = get_comments_for_post(post, request.user)

    # Workspace tags for the tag dropdown
    all_tags = Tag.objects.for_workspace(workspace.id)

    # Build media_items for the initial preview render
    media_items = []
    for att in media_attachments:
        asset = att.media_asset
        media_items.append(
            {
                "url": asset.file.url if asset.file else "",
                "is_video": asset.is_video,
                "filename": asset.filename,
            }
        )
    if not media_items:
        for asset in pending_assets:
            media_items.append(
                {
                    "url": asset.file.url if asset.file else "",
                    "is_video": asset.is_video,
                    "filename": asset.filename,
                }
            )

    # Resolve thumbnail/cover image URLs for per-account assets already saved
    thumb_ids = [
        extra.get("thumbnail_asset_id") for extra in platform_extras.values() if extra.get("thumbnail_asset_id")
    ]
    cover_ids = [
        extra.get("cover_image_asset_id") for extra in platform_extras.values() if extra.get("cover_image_asset_id")
    ]
    all_asset_ids = [aid for aid in thumb_ids + cover_ids if aid]
    asset_url_map = {}
    if all_asset_ids:
        for asset in MediaAsset.objects.filter(id__in=all_asset_ids, workspace=workspace):
            url = ""
            if asset.thumbnail:
                url = asset.thumbnail.url
            elif asset.file:
                url = asset.file.url
            asset_url_map[str(asset.id)] = url
    for _acc_id, extra in platform_extras.items():
        tid = extra.get("thumbnail_asset_id")
        if tid and tid in asset_url_map:
            extra["thumbnail_url"] = asset_url_map[tid]
        cid = extra.get("cover_image_asset_id")
        if cid and cid in asset_url_map:
            extra["cover_image_url"] = asset_url_map[cid]

    context = {
        "workspace": workspace,
        "post": post,
        "form": form,
        "social_accounts": social_accounts,
        "selected_account_ids": [str(aid) for aid in selected_account_ids],
        "platform_extras_json": json.dumps(platform_extras),
        "media_attachments": media_attachments,
        "media_items": media_items,
        "media_items_json": json.dumps(media_items),
        "char_limits_json": json.dumps(char_limits),
        "default_first_comment": default_first_comment,
        "default_hashtags": json.dumps(default_hashtags),
        "can_publish": can_publish,
        "can_approve": can_approve,
        "can_view_internal_notes": can_view_internal_notes,
        "is_edit": post is not None,
        "categories": categories,
        "queues": queues,
        "template_data_json": json.dumps(template_data) if template_data else "null",
        "workflow_mode": workflow_mode,
        "show_submit_button": show_submit_button,
        "show_resubmit_button": show_resubmit_button,
        "approval_history": approval_history,
        "post_comments": post_comments,
        "pending_assets": pending_assets,
        "all_tags": all_tags,
    }
    return render(request, "composer/compose.html", context)


def _transition_post_children(post, target, *, allow_via_draft=True, only=None):
    """Transition every (or selected) PlatformPost child of *post* to *target*.

    Returns ``(moved, skipped)`` lists of PlatformPost instances. Children
    already in the target state are left alone (counted as moved). For states
    that don't allow a direct transition, an intermediate hop through
    ``draft`` is attempted when ``allow_via_draft`` is True.

    ``only`` may be an iterable of PlatformPost IDs to restrict the operation
    to a subset of children.
    """
    children = post.platform_posts.all()
    if only is not None:
        only_ids = {str(x) for x in only}
        children = [pp for pp in children if str(pp.id) in only_ids]
    moved, skipped = [], []
    for pp in children:
        if pp.status == target:
            moved.append(pp)
            continue
        try:
            if pp.can_transition_to(target):
                pp.transition_to(target)
            elif allow_via_draft and pp.can_transition_to("draft") and target != "draft":
                pp.transition_to("draft")
                if pp.can_transition_to(target):
                    pp.transition_to(target)
                else:
                    skipped.append(pp)
                    continue
            else:
                skipped.append(pp)
                continue
            pp.save(update_fields=["status", "published_at", "updated_at"])
            moved.append(pp)
        except ValueError:
            skipped.append(pp)
    return moved, skipped


def _platform_status_map(post):
    """Return ``{platform_post_id: status}`` for HTMX response headers."""
    return {str(pp.id): pp.status for pp in post.platform_posts.all()}


@login_required
@require_permission("create_posts")
@require_POST
def save_post(request, workspace_id, post_id=None):
    """Save or update a post (draft, schedule, or publish action)."""
    workspace = _get_workspace(request, workspace_id)
    action = request.POST.get("action", "save_draft")

    if post_id:
        post = get_object_or_404(Post, id=post_id, workspace=workspace)
        # Enforce edit permissions: authors can edit their own, others need edit_others_posts
        membership = request.workspace_membership
        perms = membership.effective_permissions if membership else {}
        if post.author != request.user and not perms.get("edit_others_posts", False):
            raise PermissionDenied("You do not have permission to edit this post.")
        form = PostForm(request.POST, instance=post)
    else:
        form = PostForm(request.POST)

    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    post = form.save(commit=False)
    post.workspace = workspace
    if not post_id:
        post.author = request.user

    # Handle action — note that Post itself no longer carries an editorial
    # status: every transition below operates on the PlatformPost children,
    # which is why we sync those before/after running it.
    pending_target = None  # what to transition existing children to after sync
    initial_status = "draft"  # default status for newly created PlatformPosts

    if action == "schedule":
        sched_date = form.cleaned_data.get("scheduled_date")
        sched_time = form.cleaned_data.get("scheduled_time")
        if sched_date and sched_time:
            ws_tz = workspace.effective_timezone or "UTC"
            import zoneinfo

            tz = zoneinfo.ZoneInfo(ws_tz)
            naive_dt = datetime.combine(sched_date, sched_time)
            aware_dt = naive_dt.replace(tzinfo=tz)
            if aware_dt <= timezone.now():
                return JsonResponse(
                    {"errors": {"schedule": "Scheduled time must be in the future."}},
                    status=400,
                )
            post.scheduled_at = aware_dt
            # Propagate the manually chosen time to every PlatformPost so all
            # selected platforms publish at the same moment.
            post._schedule_propagate_dt = aware_dt  # handled after post.save()
            pending_target = "scheduled"
            initial_status = "scheduled"
        else:
            return JsonResponse({"errors": {"schedule": "Date and time required."}}, status=400)
    elif action == "publish_now":
        # Server-side permission check - only roles with publish_directly can bypass approval
        membership = request.workspace_membership
        perms = membership.effective_permissions if membership else {}
        if not perms.get("publish_directly", False):
            raise PermissionDenied("You do not have permission to publish directly.")
        now_dt = timezone.now()
        post.scheduled_at = now_dt
        post._schedule_propagate_dt = now_dt  # handled after post.save()
        pending_target = "scheduled"
        initial_status = "scheduled"
    elif action == "add_to_queue":
        from apps.calendar.services import add_to_queue

        queue_id = request.POST.get("queue_id")
        queues = _resolve_queues_for_post(queue_id, workspace, request.POST)
        if not queues:
            return JsonResponse({"errors": {"queue": "No active queue found for the selected channel."}}, status=400)
        post.save()
        # Ensure PlatformPost rows exist for every selected account before the
        # queue service writes per-platform scheduled_at values.
        _sync_platform_posts(request, post, workspace, initial_status="draft")
        for q in queues:
            add_to_queue(post, q)
        # If opened from a specific calendar day (month/week/day "+" CTA), each
        # queue should use that day as its floor - re-assign slots accordingly.
        floor_date = form.cleaned_data.get("scheduled_date")
        if floor_date:
            _reassign_queue_slots_from_floor(queues, post, floor_date, workspace)
        # Transition every child whose scheduled_at was filled in to "scheduled".
        _transition_post_children(post, "scheduled")
        _save_version(post, request.user)
        if request.htmx:
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps({"postSaved": {"postId": str(post.id), "status": post.status}}),
                    "X-Platform-Statuses": json.dumps(_platform_status_map(post)),
                },
            )
        return redirect("composer:compose_edit", workspace_id=workspace.id, post_id=post.id)
    elif action == "add_to_queue_priority":
        from apps.calendar.services import add_to_queue

        queue_id = request.POST.get("queue_id")
        queues = _resolve_queues_for_post(queue_id, workspace, request.POST)
        if not queues:
            return JsonResponse({"errors": {"queue": "No active queue found for the selected channel."}}, status=400)
        post.save()
        _sync_platform_posts(request, post, workspace, initial_status="draft")
        for q in queues:
            add_to_queue(post, q, priority=True)
        _transition_post_children(post, "scheduled")
        _save_version(post, request.user)
        if request.htmx:
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps({"postSaved": {"postId": str(post.id), "status": post.status}}),
                    "X-Platform-Statuses": json.dumps(_platform_status_map(post)),
                },
            )
        return redirect("composer:compose_edit", workspace_id=workspace.id, post_id=post.id)
    elif action == "submit_for_approval":
        # Save post first so it has a PK, then delegate to approval service
        post.save()
        # Sync platform posts before submitting
        _sync_platform_posts(request, post, workspace, initial_status="draft")
        _save_version(post, request.user)
        from apps.approvals.services import submit_for_review

        submit_for_review(post, request.user, workspace)
        if request.htmx:
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps({"postSaved": {"postId": str(post.id), "status": post.status}}),
                    "X-Platform-Statuses": json.dumps(_platform_status_map(post)),
                },
            )
        return redirect("composer:compose_edit", workspace_id=workspace.id, post_id=post.id)
    elif action == "resubmit_for_approval":
        # Resubmit after changes requested or rejection
        post.save()
        _sync_platform_posts(request, post, workspace, initial_status="draft")
        _save_version(post, request.user)
        from apps.approvals.services import resubmit_post

        resubmit_post(post, request.user, workspace)
        if request.htmx:
            return HttpResponse(
                status=204,
                headers={
                    "HX-Trigger": json.dumps({"postSaved": {"postId": str(post.id), "status": post.status}}),
                    "X-Platform-Statuses": json.dumps(_platform_status_map(post)),
                },
            )
        return redirect("composer:compose_edit", workspace_id=workspace.id, post_id=post.id)
    # else: save_draft — leave children as-is for existing posts; new children
    # default to draft via initial_status above.

    post.save()

    # Attach pending session media for new posts
    if not post_id:
        from apps.media_library.models import MediaAsset as _MediaAsset

        session_key = f"pending_media_{workspace.id}"
        pending_ids = request.session.get(session_key, [])
        if pending_ids:
            for idx, asset_id in enumerate(pending_ids):
                try:
                    asset = _MediaAsset.objects.get(id=asset_id, workspace=workspace)
                    PostMedia.objects.get_or_create(
                        post=post,
                        media_asset=asset,
                        defaults={"position": idx},
                    )
                except _MediaAsset.DoesNotExist:
                    continue
            del request.session[session_key]

    # Sync any new tags to the Tag model
    _sync_tags_to_model(workspace, post.tags)

    # Handle recurring post creation
    make_recurring = request.POST.get("make_recurring")
    if make_recurring and action == "schedule" and post.scheduled_at:
        from apps.calendar.models import RecurrenceRule

        frequency = request.POST.get("recurrence_frequency", "weekly")
        interval_str = request.POST.get("recurrence_interval", "1")
        end_date_str = request.POST.get("recurrence_end_date", "")
        try:
            interval_val = int(interval_str)
        except (ValueError, TypeError):
            interval_val = 1
        end_date_val = None
        if end_date_str:
            try:
                from datetime import date as date_cls

                end_date_val = date_cls.fromisoformat(end_date_str)
            except (ValueError, TypeError):
                pass
        RecurrenceRule.objects.update_or_create(
            post=post,
            defaults={
                "frequency": frequency,
                "interval": interval_val,
                "end_date": end_date_val,
                "is_active": True,
            },
        )

    # Sync platform posts (newly-created rows inherit ``initial_status`` for
    # this action — e.g. "scheduled" for schedule/publish_now, "draft" for
    # save_draft).
    _sync_platform_posts(request, post, workspace, initial_status=initial_status)

    # Propagate manually-chosen schedule/publish_now datetimes to every
    # PlatformPost now that they exist.
    propagate_dt = getattr(post, "_schedule_propagate_dt", None)
    if propagate_dt is not None:
        post.platform_posts.update(scheduled_at=propagate_dt)

    # Move existing children to the requested target state (no-op for
    # save_draft — children that are already mid-workflow stay put).
    if pending_target:
        _transition_post_children(post, pending_target)

    # Save version
    _save_version(post, request.user)

    # Return appropriate response
    if request.htmx:
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "postSaved": {
                            "postId": str(post.id),
                            "status": post.status,
                        }
                    }
                ),
                "X-Platform-Statuses": json.dumps(_platform_status_map(post)),
            },
        )

    return redirect("composer:compose_edit", workspace_id=workspace.id, post_id=post.id)


@login_required
@require_POST
def transition_platform_post(request, workspace_id, post_id, platform_post_id):
    """Transition a single PlatformPost to a target editorial status.

    Used by the composer's per-account chip menu so the user can take a single
    social account in/out of draft, schedule, etc. without affecting siblings.
    Permission rules mirror save_post: ``approve_posts`` is required for any
    approval-stage target; ``publish_directly`` is required for scheduled.
    """
    workspace = _get_workspace(request, workspace_id)
    pp = get_object_or_404(
        PlatformPost.objects.select_related("post", "social_account"),
        id=platform_post_id,
        post_id=post_id,
        post__workspace=workspace,
    )
    target = (request.POST.get("target_status") or "").strip()
    if not target:
        return JsonResponse({"error": "target_status required"}, status=400)

    membership = request.workspace_membership
    perms = membership.effective_permissions if membership else {}
    approval_states = {"approved", "pending_review", "pending_client", "changes_requested", "rejected"}
    if target in ("scheduled", "publishing") and not perms.get("publish_directly", False):
        raise PermissionDenied("You do not have permission to schedule this post.")
    if target in approval_states and not perms.get("approve_posts", False) and target != "pending_review":
        raise PermissionDenied("You do not have permission to make approval decisions.")

    if pp.status == target:
        return JsonResponse({"ok": True, "status": pp.status, "noop": True})

    try:
        pp.transition_to(target)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    pp.save(update_fields=["status", "published_at", "updated_at"])
    return JsonResponse({"ok": True, "status": pp.status, "platform_post_id": str(pp.id)})


@login_required
@require_permission("create_posts")
@require_POST
def autosave(request, workspace_id, post_id=None):
    """Auto-save endpoint called every 30 seconds via HTMX.

    On first save for a new post (no post_id), creates the draft and returns
    an HX-Trigger with the new post ID so the client can switch the autosave
    URL to the edit endpoint, preventing duplicate drafts on subsequent ticks.
    """
    workspace = _get_workspace(request, workspace_id)

    is_new = False
    if post_id:
        post = get_object_or_404(Post, id=post_id, workspace=workspace)
        # Enforce edit permissions on existing posts
        membership = request.workspace_membership
        perms = membership.effective_permissions if membership else {}
        if post.author != request.user and not perms.get("edit_others_posts", False):
            raise PermissionDenied("You do not have permission to edit this post.")
    else:
        # Check if a previous autosave already created a draft for this session
        # by looking for the post_id passed from the client
        client_post_id = request.POST.get("_autosave_post_id", "").strip()
        if client_post_id:
            try:
                post = Post.objects.get(id=client_post_id, workspace=workspace)
            except Post.DoesNotExist:
                post = Post(workspace=workspace, author=request.user)
                is_new = True
        else:
            post = Post(workspace=workspace, author=request.user)
            is_new = True

    post.title = request.POST.get("title", "")
    post.caption = request.POST.get("caption", "")
    post.first_comment = request.POST.get("first_comment", "")
    post.internal_notes = request.POST.get("internal_notes", "")

    tags_raw = request.POST.get("tags", "")
    if tags_raw:
        post.tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    post.save()

    # Attach pending session media when creating a new post
    if is_new:
        from apps.media_library.models import MediaAsset

        session_key = f"pending_media_{workspace.id}"
        pending_ids = request.session.get(session_key, [])
        if pending_ids:
            for idx, asset_id in enumerate(pending_ids):
                try:
                    asset = MediaAsset.objects.get(id=asset_id, workspace=workspace)
                    PostMedia.objects.get_or_create(
                        post=post,
                        media_asset=asset,
                        defaults={"position": idx},
                    )
                except MediaAsset.DoesNotExist:
                    continue
            del request.session[session_key]

    # Sync platform selections
    selected_ids_str = request.POST.get("selected_accounts", "")
    selected_ids = [s.strip() for s in selected_ids_str.split(",") if s.strip()]
    post.platform_posts.exclude(social_account_id__in=selected_ids).delete()
    for acc_id in selected_ids:
        PlatformPost.objects.get_or_create(
            post=post,
            social_account_id=acc_id,
        )

    return HttpResponse(
        f'<span class="text-xs text-gray-400">Saved {timezone.now().strftime("%H:%M")}</span>',
        headers={"HX-Trigger": json.dumps({"autosaved": {"postId": str(post.id), "isNew": is_new}})},
    )


@login_required
@require_GET
def preview(request, workspace_id):
    """Live preview endpoint - renders platform-specific preview from form state.

    Called via HTMX with debounced POST from the composer.
    Stateless - no DB queries except social account lookup.
    """
    workspace = _get_workspace(request, workspace_id)
    title = request.GET.get("title", "")
    caption = request.GET.get("caption", "")
    first_comment = request.GET.get("first_comment", "")
    selected_ids_str = request.GET.get("selected_accounts", "")
    selected_ids = [s.strip() for s in selected_ids_str.split(",") if s.strip()]

    # Build preview data per platform
    previews = []
    if selected_ids:
        accounts = SocialAccount.objects.filter(
            id__in=selected_ids,
            workspace=workspace,
        ).order_by("platform")
        for account in accounts:
            override_title_key = f"override_title_{account.id}"
            override_key = f"override_caption_{account.id}"
            effective_title = request.GET.get(override_title_key, "") or title
            effective_caption = request.GET.get(override_key, "") or caption
            char_limit = account.char_limit
            field_config = account.field_config
            previews.append(
                {
                    "account": account,
                    "title": effective_title,
                    "caption": effective_caption,
                    "first_comment": first_comment,
                    "char_count": len(effective_caption),
                    "char_limit": char_limit,
                    "is_over_limit": len(effective_caption) > char_limit,
                    "truncated_caption": effective_caption[:char_limit]
                    if len(effective_caption) > char_limit
                    else effective_caption,
                    "needs_title": field_config["needs_title"],
                }
            )

    # Gather media for preview - check pending session media or post attachments
    from apps.media_library.models import MediaAsset

    media_items = []
    post_id_str = request.GET.get("_autosave_post_id", "")

    if post_id_str:
        try:
            post_obj = Post.objects.get(id=post_id_str, workspace=workspace)
            for att in post_obj.media_attachments.select_related("media_asset").all():
                asset = att.media_asset
                media_items.append(
                    {
                        "url": asset.file.url if asset.file else "",
                        "is_video": asset.is_video,
                        "filename": asset.filename,
                    }
                )
        except Post.DoesNotExist:
            pass

    if not media_items:
        # Check session pending media
        session_key = f"pending_media_{workspace.id}"
        pending_ids = request.session.get(session_key, [])
        if pending_ids:
            for asset in MediaAsset.objects.filter(id__in=pending_ids, workspace=workspace):
                media_items.append(
                    {
                        "url": asset.file.url if asset.file else "",
                        "is_video": asset.is_video,
                        "filename": asset.filename,
                    }
                )

    return render(
        request,
        "composer/partials/preview_panel.html",
        {
            "previews": previews,
            "workspace": workspace,
            "media_items": media_items,
        },
    )


@login_required
@require_GET
def media_picker(request, workspace_id, post_id=None):
    """Modal picker for selecting media from the library."""
    workspace = _get_workspace(request, workspace_id)
    from apps.media_library.models import MediaAsset

    post = None
    if post_id:
        post = get_object_or_404(Post, id=post_id, workspace=workspace)

    assets = MediaAsset.objects.for_workspace(workspace.id).order_by("-created_at")[:50]
    return render(
        request,
        "composer/partials/media_picker.html",
        {
            "assets": assets,
            "workspace": workspace,
            "post": post,
        },
    )


@login_required
@require_GET
def thumbnail_picker(request, workspace_id):
    """Modal picker for selecting an image asset as a YouTube thumbnail.

    Image-only, selection dispatches a client-side event; does not attach
    anything server-side.
    """
    workspace = _get_workspace(request, workspace_id)
    from apps.media_library.models import MediaAsset

    assets = (
        MediaAsset.objects.for_workspace(workspace.id)
        .filter(media_type=MediaAsset.MediaType.IMAGE)
        .order_by("-created_at")[:50]
    )
    return render(
        request,
        "composer/partials/thumbnail_picker.html",
        {"assets": assets, "workspace": workspace},
    )


@login_required
@require_POST
def thumbnail_upload(request, workspace_id):
    """Upload an image from the local machine to the media library and return
    its id + URL so the composer can wire it as a YouTube thumbnail.

    Image-only. Returns JSON with asset_id, url, filename.
    """
    workspace = _get_workspace(request, workspace_id)
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    content_type = uploaded_file.content_type or ""
    if not content_type.startswith("image/"):
        return JsonResponse({"error": "Only image files are allowed"}, status=400)

    from apps.media_library.models import MediaAsset

    asset = MediaAsset.objects.create(
        workspace=workspace,
        uploaded_by=request.user,
        file=uploaded_file,
        filename=uploaded_file.name,
        media_type=MediaAsset.MediaType.IMAGE,
        mime_type=content_type,
        file_size=uploaded_file.size,
        source="upload",
    )

    url = ""
    if asset.thumbnail:
        url = asset.thumbnail.url
    elif asset.file:
        url = asset.file.url

    return JsonResponse(
        {
            "asset_id": str(asset.id),
            "url": url,
            "filename": asset.filename,
        }
    )


@login_required
@require_GET
def pinterest_boards(request, workspace_id, account_id):
    """Fetch Pinterest boards for board selection in the composer."""
    workspace = _get_workspace(request, workspace_id)
    account = get_object_or_404(SocialAccount, id=account_id, workspace=workspace, platform="pinterest")

    from apps.credentials.models import PlatformCredential
    from providers import get_provider

    try:
        cred = PlatformCredential.objects.for_org(workspace.organization_id).get(
            platform="pinterest", is_configured=True
        )
        credentials = cred.credentials
    except PlatformCredential.DoesNotExist:
        from django.conf import settings as django_settings

        env_creds = getattr(django_settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
        credentials = env_creds.get("pinterest", {})

    provider = get_provider("pinterest", credentials)

    # Refresh token if expiring
    access_token = account.oauth_access_token
    if account.token_expires_at and account.is_token_expiring_soon:
        try:
            new_tokens = provider.refresh_token(account.oauth_refresh_token)
            account.oauth_access_token = new_tokens.access_token
            if new_tokens.refresh_token:
                account.oauth_refresh_token = new_tokens.refresh_token
            if new_tokens.expires_in:
                from datetime import timedelta

                account.token_expires_at = timezone.now() + timedelta(seconds=new_tokens.expires_in)
            account.connection_status = account.ConnectionStatus.CONNECTED
            account.save(
                update_fields=[
                    "oauth_access_token",
                    "oauth_refresh_token",
                    "token_expires_at",
                    "connection_status",
                    "updated_at",
                ]
            )
            access_token = new_tokens.access_token
        except Exception:
            return JsonResponse({"error": "Token refresh failed"}, status=502)

    try:
        boards = provider.get_boards(access_token)
    except Exception:
        return JsonResponse({"error": "Failed to fetch boards"}, status=502)

    return JsonResponse({"boards": [{"id": b.get("id"), "name": b.get("name")} for b in boards]})


@login_required
@require_POST
def attach_media(request, workspace_id, post_id):
    """Attach a media asset to a post."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    media_asset_id = request.POST.get("media_asset_id")

    if not media_asset_id:
        return JsonResponse({"error": "media_asset_id required"}, status=400)

    from apps.media_library.models import MediaAsset

    asset = get_object_or_404(MediaAsset, id=media_asset_id, workspace=workspace)

    max_pos = post.media_attachments.aggregate(models.Max("position"))["position__max"]
    position = (max_pos or 0) + 1

    attachment, _ = PostMedia.objects.get_or_create(
        post=post,
        media_asset=asset,
        defaults={"position": position},
    )

    response = render(
        request,
        "composer/partials/media_list.html",
        {
            "media_attachments": [attachment],
            "post": post,
            "workspace": workspace,
        },
    )
    response["HX-Trigger"] = "previewUpdate"
    return response


@login_required
@require_POST
def attach_pending_media(request, workspace_id):
    """Attach a library media asset as pending (before post is saved)."""
    workspace = _get_workspace(request, workspace_id)
    media_asset_id = request.POST.get("media_asset_id")

    if not media_asset_id:
        return JsonResponse({"error": "media_asset_id required"}, status=400)

    from apps.media_library.models import MediaAsset

    asset = get_object_or_404(MediaAsset, id=media_asset_id, workspace=workspace)

    session_key = f"pending_media_{workspace.id}"
    pending = request.session.get(session_key, [])
    asset_id_str = str(asset.id)
    if asset_id_str not in pending:
        pending.append(asset_id_str)
        request.session[session_key] = pending

    response = render(
        request,
        "composer/partials/media_list_pending.html",
        {
            "pending_assets": [asset],
            "workspace": workspace,
        },
    )
    response["HX-Trigger"] = "previewUpdate"
    return response


@login_required
@require_POST
def upload_media(request, workspace_id, post_id=None):
    """Upload a file directly from the composer and optionally attach to a post."""
    workspace = _get_workspace(request, workspace_id)
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    from apps.media_library.models import MediaAsset

    # Determine media type
    content_type = uploaded_file.content_type or ""
    if content_type.startswith("image/"):
        media_type = MediaAsset.MediaType.IMAGE
    elif content_type.startswith("video/"):
        media_type = MediaAsset.MediaType.VIDEO
    elif content_type == "image/gif":
        media_type = MediaAsset.MediaType.GIF
    else:
        media_type = MediaAsset.MediaType.DOCUMENT

    asset = MediaAsset.objects.create(
        workspace=workspace,
        uploaded_by=request.user,
        file=uploaded_file,
        filename=uploaded_file.name,
        media_type=media_type,
        mime_type=content_type,
        file_size=uploaded_file.size,
        source="upload",
    )

    # If a post ID is provided, attach immediately
    if post_id:
        post = get_object_or_404(Post, id=post_id, workspace=workspace)

        # Migrate any session pending media to the post (can happen when the
        # media picker still uses attach_pending_media after autosave created
        # the post and updated the upload URL).
        session_key = f"pending_media_{workspace.id}"
        pending_ids = request.session.get(session_key, [])
        if pending_ids:
            existing_pos = post.media_attachments.aggregate(models.Max("position"))["position__max"] or 0
            for idx, pid in enumerate(pending_ids):
                try:
                    pending_asset = MediaAsset.objects.get(id=pid, workspace=workspace)
                    PostMedia.objects.get_or_create(
                        post=post,
                        media_asset=pending_asset,
                        defaults={"position": existing_pos + idx + 1},
                    )
                except MediaAsset.DoesNotExist:
                    continue
            del request.session[session_key]

        max_pos = post.media_attachments.aggregate(models.Max("position"))["position__max"]
        position = (max_pos or 0) + 1
        attachment = PostMedia.objects.create(post=post, media_asset=asset, position=position)

        response = render(
            request,
            "composer/partials/media_list.html",
            {
                "media_attachments": [attachment],
                "post": post,
                "workspace": workspace,
            },
        )
        response["X-Uploaded-Asset-Id"] = str(asset.id)
        response["X-Uploaded-Asset-Url"] = asset.file.url
        return response

    # No post yet - store pending media IDs in session so they can be
    # attached when the post is eventually saved.
    session_key = f"pending_media_{workspace.id}"
    pending = request.session.get(session_key, [])
    pending.append(str(asset.id))
    request.session[session_key] = pending

    response = render(
        request,
        "composer/partials/media_list_pending.html",
        {
            "pending_assets": [asset],
            "workspace": workspace,
        },
    )
    response["X-Uploaded-Asset-Id"] = str(asset.id)
    response["X-Uploaded-Asset-Url"] = asset.file.url
    return response


@login_required
@require_POST
def remove_media(request, workspace_id, post_id, media_id):
    """Remove a media attachment from a post."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    PostMedia.objects.filter(id=media_id, post=post).delete()

    response = render(
        request,
        "composer/partials/media_list.html",
        {
            "media_attachments": post.media_attachments.select_related("media_asset").all(),
            "post": post,
            "workspace": workspace,
        },
    )
    response["HX-Trigger"] = "previewUpdate"
    return response


@login_required
@require_POST
def remove_pending_media(request, workspace_id, asset_id):
    """Remove a pending media asset (before post is saved)."""
    workspace = _get_workspace(request, workspace_id)

    from apps.media_library.models import MediaAsset
    from apps.media_library.services import delete_asset

    session_key = f"pending_media_{workspace.id}"
    pending = request.session.get(session_key, [])
    asset_id_str = str(asset_id)
    if asset_id_str in pending:
        pending.remove(asset_id_str)
        request.session[session_key] = pending

    # Delete the asset and its files from storage (R2)
    asset = MediaAsset.objects.filter(id=asset_id, workspace=workspace).first()
    if asset:
        with contextlib.suppress(Exception):
            delete_asset(asset)

    # Return updated pending list
    pending_assets = MediaAsset.objects.filter(id__in=pending, workspace=workspace)
    return render(
        request,
        "composer/partials/media_list_pending.html",
        {
            "pending_assets": pending_assets,
            "workspace": workspace,
        },
    )


@login_required
@require_GET
def drafts_list(request, workspace_id):
    """List all drafts for this workspace."""
    workspace = _get_workspace(request, workspace_id)
    # A post is a "draft" when at least one of its PlatformPost children is in
    # the draft state and none have moved into a more advanced workflow stage.
    # Easiest correct query: any post whose only child statuses are "draft".
    drafts = (
        Post.objects.for_workspace(workspace.id)
        .filter(platform_posts__status="draft")
        .exclude(
            platform_posts__status__in=[
                "pending_review",
                "pending_client",
                "approved",
                "scheduled",
                "publishing",
                "published",
            ]
        )
        .distinct()
        .select_related("author")
        .prefetch_related("platform_posts__social_account")
        .order_by("-updated_at")
    )

    return render(
        request,
        "composer/drafts_list.html",
        {
            "workspace": workspace,
            "drafts": drafts,
        },
    )


@login_required
@require_POST
def post_delete(request, workspace_id, post_id):
    """Delete a post or a single platform post via HTMX.

    When an ``account`` query parameter is provided, only the PlatformPost for
    that social account is removed.  If it was the last PlatformPost the parent
    Post is deleted as well.  Without the parameter the entire Post (and all
    its PlatformPosts) is deleted.
    """
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)

    account_id = request.GET.get("account") or request.POST.get("account")
    if account_id:
        pp = get_object_or_404(PlatformPost, post=post, social_account_id=account_id)
        pp.delete()
        # If no platform posts remain, clean up the parent post too.
        if not post.platform_posts.exists():
            post.delete()
    else:
        post.delete()

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "postChanged"},
    )


# ---------------------------------------------------------------------------
# Create landing page & Idea CRUD
# ---------------------------------------------------------------------------


def _idea_columns(workspace, tag=None):
    """Build Kanban columns from IdeaGroup for a workspace, optionally filtered by tag."""
    groups = IdeaGroup.objects.for_workspace(workspace.id).order_by("position", "created_at")

    # Ensure default groups exist for this workspace
    if not groups.exists():
        created_groups = {}
        for name, pos in [("Unassigned", 0), ("To Do", 1), ("In Progress", 2), ("Done", 3)]:
            created_groups[name] = IdeaGroup.objects.create(workspace=workspace, name=name, position=pos)
        # Seed an introductory idea in the Unassigned column
        Idea.objects.create(
            workspace=workspace,
            group=created_groups["Unassigned"],
            title="This is a place to plan \u270d\ufe0f your content",
            description="Save your Ideas before converting them into posts. Brainstorm, plan ahead, and keep everything organized in one place.",
            status=Idea.Status.UNASSIGNED,
            position=0,
        )
        groups = IdeaGroup.objects.for_workspace(workspace.id).order_by("position", "created_at")

    ideas_qs = (
        Idea.objects.for_workspace(workspace.id)
        .select_related("author", "media_asset")
        .prefetch_related("media_attachments__media_asset")
        .order_by("position", "-created_at")
    )
    if tag:
        from apps.utils import json_tag_contains

        ideas_qs = ideas_qs.filter(json_tag_contains("tags", tag))

    grouped_ideas = {str(grp.id): [] for grp in groups}
    for idea in ideas_qs:
        _prepare_idea_for_kanban(idea)

        group_key = str(idea.group_id) if idea.group_id else ""
        if group_key in grouped_ideas:
            grouped_ideas[group_key].append(idea)

    columns = []
    for grp in groups:
        columns.append(
            {
                "id": str(grp.id),
                "key": str(grp.id),
                "label": grp.name,
                "ideas": grouped_ideas.get(str(grp.id), []),
            }
        )

    # All workspace tags from the Tag model
    all_tags = list(Tag.objects.for_workspace(workspace.id).values_list("name", flat=True))

    return columns, all_tags


def _parse_media_asset_ids(raw_ids):
    """Parse ordered media ids from CSV, preserving order and removing duplicates."""
    ordered = []
    seen = set()
    for token in (raw_ids or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            normalized = str(uuid.UUID(token))
        except (ValueError, TypeError, AttributeError):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _build_idea_media_payload(idea):
    """Build ordered media payload and attachment list for Kanban rendering."""
    attachments = [att for att in idea.media_attachments.all() if att.media_asset_id and att.media_asset]
    media_payload = []
    for att in attachments:
        asset = att.media_asset
        media_payload.append(
            {
                "asset_id": str(asset.id),
                "url": asset.file.url if asset.file else "",
                "filename": asset.filename,
                "media_type": asset.media_type,
                "position": att.position,
            }
        )

    # Legacy fallback for ideas that only have the old single media pointer.
    if not media_payload and idea.media_asset_id and idea.media_asset:
        media_payload.append(
            {
                "asset_id": str(idea.media_asset_id),
                "url": idea.media_asset.file.url if idea.media_asset.file else "",
                "filename": idea.media_asset.filename,
                "media_type": idea.media_asset.media_type,
                "position": 0,
            }
        )
    return media_payload, attachments


def _prepare_idea_for_kanban(idea):
    """Attach computed media/tag fields used by Kanban templates."""
    media_payload, attachments = _build_idea_media_payload(idea)
    idea.media_payload_json = json.dumps(media_payload)
    idea.tags_payload_json = json.dumps(idea.tags or [])
    idea.media_count = len(media_payload)
    idea.cover_media = attachments[0].media_asset if attachments else idea.media_asset
    return idea


def _render_idea_card_fragment(request, idea):
    """Render a single Kanban idea card fragment."""
    _prepare_idea_for_kanban(idea)
    return render_to_string(
        "composer/partials/idea_card.html",
        {
            "idea": idea,
            "group_id": str(idea.group_id) if idea.group_id else "",
        },
        request=request,
    )


def _render_kanban_column_fragment(request, group):
    """Render a single Kanban column fragment."""
    return render_to_string(
        "composer/partials/kanban_column.html",
        {
            "col": {
                "id": str(group.id),
                "key": str(group.id),
                "label": group.name,
                "ideas": [],
            },
        },
        request=request,
    )


def _wants_json_response(request):
    """Detect whether mutation endpoint should return JSON payload."""
    accept = request.headers.get("Accept", "")
    return "application/json" in accept.lower()


def _normalize_media_asset_ids(raw_ids="", extra_ids=None):
    """Normalize media IDs from mixed inputs while preserving first-seen order."""
    chunks = []
    if isinstance(raw_ids, str):
        chunks.append(raw_ids)
    elif raw_ids:
        chunks.extend(str(item) for item in raw_ids)
    if extra_ids:
        chunks.extend(str(item) for item in extra_ids)
    return _parse_media_asset_ids(",".join(chunks))


def _sync_idea_media_attachments(idea, workspace, ordered_asset_ids):
    """Synchronize IdeaMedia rows to match ordered ids and keep cover pointer aligned."""
    from apps.media_library.models import MediaAsset

    normalized_ids = _normalize_media_asset_ids(ordered_asset_ids)
    if normalized_ids:
        valid_assets = set(
            str(aid)
            for aid in MediaAsset.objects.filter(workspace=workspace, id__in=normalized_ids).values_list(
                "id", flat=True
            )
        )
        ordered_ids = [aid for aid in normalized_ids if aid in valid_assets]
    else:
        ordered_ids = []

    existing_attachments = list(idea.media_attachments.all())
    existing = {str(att.media_asset_id): att for att in existing_attachments}
    ids_to_keep = set(ordered_ids)
    ids_to_delete = [att.id for att in existing_attachments if str(att.media_asset_id) not in ids_to_keep]
    if ids_to_delete:
        IdeaMedia.objects.filter(id__in=ids_to_delete).delete()

    to_create = []
    to_update = []
    now = timezone.now()
    for position, asset_id in enumerate(ordered_ids):
        attachment = existing.get(asset_id)
        if attachment:
            if attachment.position != position:
                attachment.position = position
                attachment.updated_at = now
                to_update.append(attachment)
            continue
        to_create.append(
            IdeaMedia(
                idea=idea,
                media_asset_id=asset_id,
                position=position,
            )
        )

    if to_create:
        IdeaMedia.objects.bulk_create(to_create)
    if to_update:
        IdeaMedia.objects.bulk_update(to_update, ["position", "updated_at"])

    cover_id = ordered_ids[0] if ordered_ids else None
    current_cover_id = str(idea.media_asset_id) if idea.media_asset_id else None
    if current_cover_id != cover_id:
        idea.media_asset_id = cover_id
        idea.save(update_fields=["media_asset", "updated_at"])


def _create_idea_media_asset(workspace, user, uploaded_file):
    """Create a MediaAsset from an uploaded file for Idea create/edit flows."""
    from apps.media_library.models import MediaAsset

    content_type = uploaded_file.content_type or ""
    if content_type == "image/gif":
        media_type = MediaAsset.MediaType.GIF
    elif content_type.startswith("image/"):
        media_type = MediaAsset.MediaType.IMAGE
    elif content_type.startswith("video/"):
        media_type = MediaAsset.MediaType.VIDEO
    else:
        media_type = MediaAsset.MediaType.DOCUMENT

    return MediaAsset.objects.create(
        organization=workspace.organization,
        workspace=workspace,
        uploaded_by=user,
        file=uploaded_file,
        filename=uploaded_file.name,
        media_type=media_type,
        mime_type=content_type,
        file_size=uploaded_file.size,
        source="upload",
    )


@login_required
@require_permission("create_posts")
def create_landing(request, workspace_id):
    """Render the Create landing page with Ideas Kanban board."""
    from apps.composer.builtin_templates import (
        CATEGORIES,
        get_all_templates,
        get_featured_templates,
    )

    workspace = _get_workspace(request, workspace_id)
    tab = request.GET.get("tab", "ideas")
    tag = request.GET.get("tag")

    columns, all_tags = _idea_columns(workspace, tag)

    feeds = Feed.objects.for_workspace(workspace.id)

    context = {
        "workspace": workspace,
        "tab": tab,
        "columns": columns,
        "all_tags": all_tags,
        "active_tag": tag,
        "featured_templates": get_featured_templates(),
        "builtin_templates": get_all_templates(),
        "template_categories": CATEGORIES,
        "feeds": feeds,
    }
    return render(request, "composer/create_landing.html", context)


@login_required
@require_permission("create_posts")
@require_POST
def idea_upload_media(request, workspace_id):
    """Upload media for Idea modals and return an asset id for reliable save binding."""
    workspace = _get_workspace(request, workspace_id)
    uploaded_file = request.FILES.get("file") or request.FILES.get("media")
    if not uploaded_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    asset = _create_idea_media_asset(workspace, request.user, uploaded_file)
    return JsonResponse(
        {
            "asset_id": str(asset.id),
            "filename": asset.filename,
            "url": asset.file.url if asset.file else "",
            "size": asset.file_size,
            "media_type": asset.media_type,
        }
    )


@login_required
@require_permission("create_posts")
@require_POST
def idea_create(request, workspace_id):
    """Create a new idea via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    tags_raw = request.POST.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    if not title:
        return HttpResponse("Title is required.", status=400)

    # Assign to the specified group or default to the first group
    group_id = request.POST.get("group")
    if group_id:
        group = IdeaGroup.objects.filter(id=group_id, workspace=workspace).first()
    else:
        group = IdeaGroup.objects.for_workspace(workspace.id).order_by("position").first()

    has_multi_media_payload = "media_asset_ids" in request.POST
    media_asset_ids = _normalize_media_asset_ids(request.POST.get("media_asset_ids", ""))

    # Handle media: pre-uploaded IDs (preferred), direct multipart upload fallback,
    # or legacy single pre-uploaded asset id.
    uploaded_file = request.FILES.get("media") or request.FILES.get("file")
    media_asset_id = request.POST.get("media_asset_id", "").strip()
    if uploaded_file:
        uploaded_asset = _create_idea_media_asset(workspace, request.user, uploaded_file)
        media_asset_ids.append(str(uploaded_asset.id))
    elif not media_asset_ids and media_asset_id:
        from apps.media_library.models import MediaAsset

        legacy_asset = MediaAsset.objects.filter(id=media_asset_id, workspace=workspace).first()
        if legacy_asset:
            media_asset_ids.append(str(legacy_asset.id))

    media_asset_ids = _normalize_media_asset_ids(media_asset_ids)

    with transaction.atomic():
        idea = Idea.objects.create(
            workspace=workspace,
            author=request.user,
            title=title,
            description=description,
            tags=tags,
            group=group,
            status=Idea.Status.UNASSIGNED,
            media_asset_id=media_asset_ids[0] if media_asset_ids else None,
        )

        if has_multi_media_payload or media_asset_ids:
            _sync_idea_media_attachments(idea, workspace, media_asset_ids)

    # Sync any new tags to the Tag model
    _sync_tags_to_model(workspace, tags)

    if _wants_json_response(request):
        idea = (
            Idea.objects.for_workspace(workspace.id)
            .select_related("media_asset")
            .prefetch_related("media_attachments__media_asset")
            .get(id=idea.id)
        )
        return JsonResponse(
            {
                "ok": True,
                "idea_id": str(idea.id),
                "group_id": str(idea.group_id) if idea.group_id else "",
                "tags": idea.tags or [],
                "card_html": _render_idea_card_fragment(request, idea),
            }
        )

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "ideaChanged"},
    )


@login_required
@require_permission("create_posts")
@require_POST
def idea_edit(request, workspace_id, idea_id):
    """Edit an existing idea via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    idea = get_object_or_404(Idea, id=idea_id, workspace=workspace)
    previous_group_id = str(idea.group_id) if idea.group_id else ""

    idea.title = request.POST.get("title", idea.title).strip()
    idea.description = request.POST.get("description", idea.description).strip()
    tags_raw = request.POST.get("tags", "")
    idea.tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    group_id = request.POST.get("group", "").strip()
    if group_id:
        group = IdeaGroup.objects.filter(id=group_id, workspace=workspace).first()
        if group:
            idea.group = group

    # Handle media attachments:
    # - preferred: ordered media_asset_ids list
    # - fallback: legacy single media_asset_id + remove_media
    has_multi_media_payload = "media_asset_ids" in request.POST
    media_asset_ids = _normalize_media_asset_ids(request.POST.get("media_asset_ids", ""))
    uploaded_file = request.FILES.get("media") or request.FILES.get("file")
    uploaded_asset = None
    if uploaded_file:
        uploaded_asset = _create_idea_media_asset(workspace, request.user, uploaded_file)
        media_asset_ids.append(str(uploaded_asset.id))
    media_asset_ids = _normalize_media_asset_ids(media_asset_ids)

    with transaction.atomic():
        idea.save(update_fields=["title", "description", "tags", "group", "updated_at"])

        if has_multi_media_payload:
            _sync_idea_media_attachments(idea, workspace, media_asset_ids)
        else:
            media_asset_id = request.POST.get("media_asset_id", "").strip()
            remove_media = request.POST.get("remove_media") == "true"

            if uploaded_asset:
                _sync_idea_media_attachments(idea, workspace, [str(uploaded_asset.id)])
            elif media_asset_id:
                from apps.media_library.models import MediaAsset

                asset = MediaAsset.objects.filter(id=media_asset_id, workspace=workspace).first()
                if asset:
                    _sync_idea_media_attachments(idea, workspace, [str(asset.id)])
            elif remove_media:
                _sync_idea_media_attachments(idea, workspace, [])

    # Sync any new tags to the Tag model
    _sync_tags_to_model(workspace, idea.tags)

    if _wants_json_response(request):
        idea = (
            Idea.objects.for_workspace(workspace.id)
            .select_related("media_asset")
            .prefetch_related("media_attachments__media_asset")
            .get(id=idea.id)
        )
        return JsonResponse(
            {
                "ok": True,
                "idea_id": str(idea.id),
                "previous_group_id": previous_group_id,
                "group_id": str(idea.group_id) if idea.group_id else "",
                "tags": idea.tags or [],
                "card_html": _render_idea_card_fragment(request, idea),
            }
        )

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "ideaChanged"},
    )


@login_required
@require_permission("create_posts")
@require_POST
def idea_create_post(request, workspace_id, idea_id):
    """Create a new draft post from an idea and return composer redirect metadata."""
    workspace = _get_workspace(request, workspace_id)
    idea = get_object_or_404(
        Idea.objects.for_workspace(workspace.id)
        .select_related("media_asset")
        .prefetch_related("media_attachments__media_asset"),
        id=idea_id,
    )

    tags = []
    if isinstance(idea.tags, list):
        tags = [tag.strip() for tag in idea.tags if isinstance(tag, str) and tag.strip()]

    ordered_media_asset_ids = []
    seen_media_ids = set()
    for attachment in idea.media_attachments.all():
        if not attachment.media_asset_id:
            continue
        media_id = str(attachment.media_asset_id)
        if media_id in seen_media_ids:
            continue
        seen_media_ids.add(media_id)
        ordered_media_asset_ids.append(media_id)

    # Legacy fallback: old ideas may only have the single media pointer set.
    if not ordered_media_asset_ids and idea.media_asset_id:
        ordered_media_asset_ids.append(str(idea.media_asset_id))

    connected_accounts = list(
        SocialAccount.objects.for_workspace(workspace.id)
        .filter(connection_status=SocialAccount.ConnectionStatus.CONNECTED)
        .order_by("platform", "account_name", "id")
    )

    with transaction.atomic():
        post = Post.objects.create(
            workspace=workspace,
            author=request.user,
            title=idea.title or "",
            caption=idea.description or "",
            tags=tags,
        )

        if ordered_media_asset_ids:
            PostMedia.objects.bulk_create(
                [
                    PostMedia(
                        post=post,
                        media_asset_id=asset_id,
                        position=index,
                    )
                    for index, asset_id in enumerate(ordered_media_asset_ids)
                ]
            )

        if connected_accounts:
            PlatformPost.objects.bulk_create(
                [
                    PlatformPost(
                        post=post,
                        social_account=account,
                    )
                    for account in connected_accounts
                ]
            )

        idea.post = post
        idea.save(update_fields=["post", "updated_at"])

    from django.urls import reverse

    compose_url = reverse("composer:compose_edit", kwargs={"workspace_id": workspace.id, "post_id": post.id})
    return JsonResponse(
        {
            "ok": True,
            "post_id": str(post.id),
            "compose_url": compose_url,
        }
    )


@login_required
@require_permission("create_posts")
@require_POST
def idea_delete(request, workspace_id, idea_id):
    """Delete an idea via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    idea = get_object_or_404(Idea, id=idea_id, workspace=workspace)
    group_id = str(idea.group_id) if idea.group_id else ""
    idea.delete()

    if _wants_json_response(request):
        return JsonResponse(
            {
                "ok": True,
                "idea_id": str(idea_id),
                "group_id": group_id,
            }
        )

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "ideaChanged"},
    )


@login_required
@require_permission("create_posts")
@require_POST
def idea_move(request, workspace_id, idea_id):
    """Move an idea to a new column/position via HTMX (drag-and-drop)."""
    workspace = _get_workspace(request, workspace_id)
    idea = get_object_or_404(Idea, id=idea_id, workspace=workspace)
    new_group_id = request.POST.get("group")
    new_position = request.POST.get("position")

    # Support both group-based and legacy status-based moves
    if new_group_id:
        group = IdeaGroup.objects.filter(id=new_group_id, workspace=workspace).first()
        if group:
            idea.group = group
    else:
        new_status = request.POST.get("status")
        if new_status and new_status in dict(Idea.Status.choices):
            idea.status = new_status
    if new_position is not None:
        with contextlib.suppress(ValueError, TypeError):
            idea.position = int(new_position)
    idea.save()

    # No HX-Trigger here - the frontend handles the move optimistically
    return HttpResponse(status=204)


@login_required
@require_permission("create_posts")
@require_GET
def idea_board(request, workspace_id):
    """Return the Kanban board partial for HTMX refresh."""
    workspace = _get_workspace(request, workspace_id)
    tag = request.GET.get("tag")
    columns, all_tags = _idea_columns(workspace, tag)

    return render(
        request,
        "composer/partials/kanban_board.html",
        {
            "workspace": workspace,
            "columns": columns,
            "all_tags": all_tags,
            "active_tag": tag,
        },
    )


# ---------------------------------------------------------------------------
# Idea Group CRUD (Kanban columns)
# ---------------------------------------------------------------------------


@login_required
@require_permission("create_posts")
@require_POST
def idea_group_create(request, workspace_id):
    """Create a new Kanban column via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    name = request.POST.get("name", "").strip()
    if not name:
        if _wants_json_response(request):
            return JsonResponse({"error": "Name is required."}, status=400)
        return HttpResponse("Name is required.", status=400)

    max_pos = IdeaGroup.objects.for_workspace(workspace.id).aggregate(models.Max("position"))["position__max"] or 0
    group = IdeaGroup.objects.create(workspace=workspace, name=name, position=max_pos + 1)

    if _wants_json_response(request):
        return JsonResponse(
            {
                "ok": True,
                "group_id": str(group.id),
                "group_name": group.name,
                "column_html": _render_kanban_column_fragment(request, group),
            }
        )

    return HttpResponse(status=204, headers={"HX-Trigger": "ideaChanged"})


@login_required
@require_permission("create_posts")
@require_POST
def idea_group_delete(request, workspace_id, group_id):
    """Delete an empty Kanban column via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    group = get_object_or_404(IdeaGroup, id=group_id, workspace=workspace)

    if group.ideas.exists():
        if _wants_json_response(request):
            return JsonResponse({"error": "Column must be empty before deleting."}, status=400)
        return HttpResponse("Column must be empty before deleting.", status=400)

    deleted_group_id = str(group.id)
    group.delete()
    if _wants_json_response(request):
        return JsonResponse({"ok": True, "group_id": deleted_group_id})
    return HttpResponse(status=204, headers={"HX-Trigger": "ideaChanged"})


@login_required
@require_permission("create_posts")
@require_POST
def idea_group_reorder(request, workspace_id):
    """Reorder Kanban columns. Expects JSON body: {"order": ["uuid1", "uuid2", ...]}."""
    workspace = _get_workspace(request, workspace_id)
    try:
        data = json.loads(request.body)
        order = data.get("order", [])
    except (json.JSONDecodeError, AttributeError):
        return HttpResponse("Invalid JSON.", status=400)

    if not order:
        return HttpResponse(status=204)

    groups = {str(g.id): g for g in IdeaGroup.objects.for_workspace(workspace.id)}
    for position, group_id in enumerate(order):
        group = groups.get(group_id)
        if group and group.position != position:
            group.position = position
            group.save(update_fields=["position"])

    return HttpResponse(status=204)


# ---------------------------------------------------------------------------
# Content Categories CRUD
# ---------------------------------------------------------------------------


@login_required
def category_list(request, workspace_id):
    """Settings page for managing content categories."""
    workspace = _get_workspace(request, workspace_id)
    categories = ContentCategory.objects.for_workspace(workspace.id)
    form = ContentCategoryForm()

    return render(
        request,
        "composer/categories.html",
        {
            "workspace": workspace,
            "categories": categories,
            "form": form,
        },
    )


@login_required
@require_POST
def category_create(request, workspace_id):
    """Create a new content category via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    form = ContentCategoryForm(request.POST)

    if not form.is_valid():
        return HttpResponse("Invalid data.", status=400)

    category = form.save(commit=False)
    category.workspace = workspace
    max_pos = ContentCategory.objects.for_workspace(workspace.id).aggregate(models.Max("position"))["position__max"]
    category.position = (max_pos or 0) + 1
    category.save()

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "categoryChanged"},
    )


@login_required
@require_POST
def category_edit(request, workspace_id, category_id):
    """Edit a content category via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    category = get_object_or_404(ContentCategory, id=category_id, workspace=workspace)
    form = ContentCategoryForm(request.POST, instance=category)

    if not form.is_valid():
        return HttpResponse("Invalid data.", status=400)

    form.save()
    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "categoryChanged"},
    )


@login_required
@require_POST
def category_delete(request, workspace_id, category_id):
    """Delete a content category via HTMX."""
    workspace = _get_workspace(request, workspace_id)
    category = get_object_or_404(ContentCategory, id=category_id, workspace=workspace)
    category.delete()

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "categoryChanged"},
    )


# ---------------------------------------------------------------------------
# Post Templates
# ---------------------------------------------------------------------------


@login_required
def template_list(request, workspace_id):
    """Settings page for managing post templates."""
    workspace = _get_workspace(request, workspace_id)
    templates = PostTemplate.objects.for_workspace(workspace.id).select_related("created_by")

    return render(
        request,
        "composer/templates_list.html",
        {
            "workspace": workspace,
            "templates": templates,
        },
    )


@login_required
@require_POST
def save_as_template(request, workspace_id, post_id):
    """Save the current post as a reusable template."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)

    name = request.POST.get("template_name", "").strip()
    if not name:
        name = f"Template from {post.caption_snippet or 'post'}"

    description = request.POST.get("template_description", "").strip()

    template_data = {
        "caption": post.caption,
        "first_comment": post.first_comment,
        "category_id": str(post.category_id) if post.category_id else None,
        "tags": post.tags,
        "platform_account_ids": [str(pp.social_account_id) for pp in post.platform_posts.all()],
        "media_asset_ids": [str(pm.media_asset_id) for pm in post.media_attachments.all()],
    }

    PostTemplate.objects.create(
        workspace=workspace,
        name=name,
        description=description,
        template_data=template_data,
        created_by=request.user,
    )

    if request.htmx:
        return HttpResponse(
            status=204,
            headers={"HX-Trigger": "templateSaved"},
        )
    return redirect("composer:compose_edit", workspace_id=workspace.id, post_id=post.id)


@login_required
@require_POST
def template_delete(request, workspace_id, template_id):
    """Delete a post template."""
    workspace = _get_workspace(request, workspace_id)
    tpl = get_object_or_404(PostTemplate, id=template_id, workspace=workspace)
    tpl.delete()

    return HttpResponse(
        status=204,
        headers={"HX-Trigger": "templateChanged"},
    )


@login_required
@require_GET
def template_picker(request, workspace_id):
    """HTMX partial returning list of templates for the picker modal."""
    workspace = _get_workspace(request, workspace_id)
    templates = PostTemplate.objects.for_workspace(workspace.id).select_related("created_by")

    return render(
        request,
        "composer/partials/template_picker.html",
        {
            "workspace": workspace,
            "templates": templates,
        },
    )


@login_required
@require_GET
def use_template(request, workspace_id, template_id):
    """Redirect to composer with template data pre-filled."""
    workspace = _get_workspace(request, workspace_id)
    get_object_or_404(PostTemplate, id=template_id, workspace=workspace)

    from django.urls import reverse

    compose_url = reverse("composer:compose", kwargs={"workspace_id": workspace.id})
    return redirect(f"{compose_url}?template={template_id}")


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------


@login_required
@require_permission("create_posts")
def csv_upload(request, workspace_id):
    """Render CSV upload page or handle file upload and show column mapping."""
    workspace = _get_workspace(request, workspace_id)

    if request.method == "POST" and request.FILES.get("csv_file"):
        import csv
        import io

        csv_file = request.FILES["csv_file"]
        decoded = csv_file.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(decoded))
        rows = list(reader)

        if not rows:
            return render(
                request,
                "composer/csv_import.html",
                {"workspace": workspace, "error": "CSV file is empty."},
            )

        headers = rows[0]
        preview_rows = rows[1:6]  # First 5 data rows

        # Auto-detect column mapping
        field_map = {
            "date": ["date", "publish_date", "scheduled_date"],
            "time": ["time", "publish_time", "scheduled_time"],
            "platforms": ["platform", "platforms", "channel", "channels"],
            "caption": ["caption", "text", "content", "message", "body"],
            "media_url": ["media_url", "media", "image_url", "image", "video_url"],
            "category": ["category", "content_category", "type"],
            "tags": ["tags", "labels", "tag"],
            "first_comment": ["first_comment", "comment"],
        }

        auto_mapping = {}
        for col_idx, header in enumerate(headers):
            header_lower = header.strip().lower().replace(" ", "_")
            for field, aliases in field_map.items():
                if header_lower in aliases:
                    auto_mapping[field] = col_idx
                    break

        # Store CSV in session for the next step
        request.session[f"csv_import_{workspace.id}"] = {
            "headers": headers,
            "rows": rows[1:],  # Exclude header
            "filename": csv_file.name,
        }

        import json as json_mod

        return render(
            request,
            "composer/partials/csv_mapping.html",
            {
                "workspace": workspace,
                "headers": headers,
                "preview_rows": preview_rows,
                "auto_mapping": auto_mapping,
                "auto_mapping_json": json_mod.dumps(auto_mapping),
                "field_choices": list(field_map.keys()),
            },
        )

    return render(
        request,
        "composer/csv_import.html",
        {"workspace": workspace},
    )


@login_required
@require_permission("create_posts")
@require_POST
def csv_preview(request, workspace_id):
    """Validate CSV rows with the selected column mapping and show preview."""
    workspace = _get_workspace(request, workspace_id)
    csv_data = request.session.get(f"csv_import_{workspace.id}")

    if not csv_data:
        return HttpResponse("No CSV data found. Please upload again.", status=400)

    # Parse column mapping from POST
    mapping = {}
    for field in ["date", "time", "platforms", "caption", "media_url", "category", "tags", "first_comment"]:
        col_idx = request.POST.get(f"map_{field}", "")
        if col_idx != "":
            import contextlib

            with contextlib.suppress(ValueError, TypeError):
                mapping[field] = int(col_idx)

    rows = csv_data["rows"]
    errors = []
    valid_count = 0

    from apps.social_accounts.models import SocialAccount

    valid_platforms = {p[0].lower() for p in SocialAccount.Platform.choices}
    connected_accounts = set(
        SocialAccount.objects.for_workspace(workspace.id)
        .filter(connection_status=SocialAccount.ConnectionStatus.CONNECTED)
        .values_list("platform", flat=True)
    )

    for row_idx, row in enumerate(rows, start=2):  # Row 2 = first data row
        row_errors = []

        # Validate date
        if "date" in mapping:
            date_val = row[mapping["date"]].strip() if mapping["date"] < len(row) else ""
            if date_val:
                try:
                    from datetime import date as date_cls

                    date_cls.fromisoformat(date_val)
                except ValueError:
                    row_errors.append(f"Invalid date format '{date_val}' (expected YYYY-MM-DD)")
            else:
                row_errors.append("Date is empty")

        # Validate platforms
        if "platforms" in mapping:
            platforms_val = row[mapping["platforms"]].strip() if mapping["platforms"] < len(row) else ""
            if platforms_val:
                for p in platforms_val.split(","):
                    p = p.strip().lower()
                    if p and p not in valid_platforms:
                        row_errors.append(f"Unknown platform '{p}'")
                    elif p and p not in connected_accounts:
                        row_errors.append(f"Platform '{p}' is not connected")

        # Validate caption
        if "caption" in mapping:
            caption_val = row[mapping["caption"]].strip() if mapping["caption"] < len(row) else ""
            if not caption_val:
                row_errors.append("Caption is empty")

        if row_errors:
            errors.append({"row": row_idx, "errors": row_errors})
        else:
            valid_count += 1

    # Store mapping in session
    request.session[f"csv_mapping_{workspace.id}"] = mapping

    return render(
        request,
        "composer/partials/csv_validation.html",
        {
            "workspace": workspace,
            "total_rows": len(rows),
            "valid_count": valid_count,
            "errors": errors[:50],  # Show max 50 errors
            "has_more_errors": len(errors) > 50,
        },
    )


@login_required
@require_permission("create_posts")
@require_POST
def csv_confirm_import(request, workspace_id):
    """Kick off the CSV import as a background job."""
    workspace = _get_workspace(request, workspace_id)
    csv_data = request.session.get(f"csv_import_{workspace.id}")
    mapping = request.session.get(f"csv_mapping_{workspace.id}")

    if not csv_data or not mapping:
        return HttpResponse("No CSV data found. Please upload again.", status=400)

    from apps.social_accounts.models import SocialAccount

    rows = csv_data["rows"]
    created_count = 0
    error_count = 0

    for row in rows:
        try:
            caption = row[mapping["caption"]].strip() if "caption" in mapping and mapping["caption"] < len(row) else ""
            if not caption:
                error_count += 1
                continue

            post = Post(
                workspace=workspace,
                author=request.user,
                caption=caption,
            )
            initial_pp_status = "draft"

            # Date + time
            if "date" in mapping and mapping["date"] < len(row):
                date_str = row[mapping["date"]].strip()
                time_str = ""
                if "time" in mapping and mapping["time"] < len(row):
                    time_str = row[mapping["time"]].strip()

                if date_str:
                    import zoneinfo

                    ws_tz = workspace.effective_timezone or "UTC"
                    tz = zoneinfo.ZoneInfo(ws_tz)
                    from datetime import time as time_cls

                    d = datetime.strptime(date_str, "%Y-%m-%d").date()
                    t = datetime.strptime(time_str, "%H:%M").time() if time_str else time_cls(9, 0)
                    naive_dt = datetime.combine(d, t)
                    post.scheduled_at = naive_dt.replace(tzinfo=tz)
                    initial_pp_status = "scheduled"

            # First comment
            if "first_comment" in mapping and mapping["first_comment"] < len(row):
                post.first_comment = row[mapping["first_comment"]].strip()

            # Tags
            if "tags" in mapping and mapping["tags"] < len(row):
                tags_raw = row[mapping["tags"]].strip()
                if tags_raw:
                    post.tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

            # Category
            if "category" in mapping and mapping["category"] < len(row):
                cat_name = row[mapping["category"]].strip()
                if cat_name:
                    cat, _ = ContentCategory.objects.get_or_create(
                        workspace=workspace,
                        name=cat_name,
                        defaults={"color": "#3B82F6"},
                    )
                    post.category = cat

            post.save()

            # Platforms
            if "platforms" in mapping and mapping["platforms"] < len(row):
                platforms_str = row[mapping["platforms"]].strip()
                if platforms_str:
                    for p in platforms_str.split(","):
                        p = p.strip().lower()
                        accounts = SocialAccount.objects.filter(
                            workspace=workspace,
                            platform=p,
                            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
                        )
                        for acc in accounts:
                            PlatformPost.objects.get_or_create(
                                post=post,
                                social_account=acc,
                                defaults={
                                    "status": initial_pp_status,
                                    "scheduled_at": post.scheduled_at,
                                },
                            )

            created_count += 1
        except Exception:
            error_count += 1

    # Clean up session data
    request.session.pop(f"csv_import_{workspace.id}", None)
    request.session.pop(f"csv_mapping_{workspace.id}", None)

    return render(
        request,
        "composer/partials/csv_progress.html",
        {
            "workspace": workspace,
            "created_count": created_count,
            "error_count": error_count,
            "total_rows": len(rows),
        },
    )


# ---------------------------------------------------------------------------
# Tag CRUD (JSON API endpoints)
# ---------------------------------------------------------------------------


def _sync_tags_to_model(workspace, tag_names):
    """Ensure Tag records exist for all given tag names in a workspace."""
    if not tag_names:
        return
    existing = set(Tag.objects.for_workspace(workspace.id).filter(name__in=tag_names).values_list("name", flat=True))
    new_tags = [Tag(workspace=workspace, name=name) for name in tag_names if name not in existing]
    if new_tags:
        Tag.objects.bulk_create(new_tags, ignore_conflicts=True)


@login_required
@require_GET
def tag_list(request, workspace_id):
    """Return workspace tags as JSON, optionally filtered by search query."""
    workspace = _get_workspace(request, workspace_id)
    q = request.GET.get("q", "").strip().lower()
    tags = Tag.objects.for_workspace(workspace.id)
    if q:
        tags = tags.filter(name__icontains=q)
    tag_data = [{"id": str(t.id), "name": t.name} for t in tags[:50]]
    return JsonResponse(tag_data, safe=False)


@login_required
@require_POST
def tag_create(request, workspace_id):
    """Create a new tag and return it as JSON."""
    workspace = _get_workspace(request, workspace_id)
    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Tag name is required."}, status=400)
    tag, created = Tag.objects.get_or_create(workspace=workspace, name=name)
    return JsonResponse({"id": str(tag.id), "name": tag.name, "created": created})


# ── Feeds ──────────────────────────────────────────────────────────────────


FEED_EVENTS_PAGE_SIZE = 15
FEED_EVENTS_CACHE_TTL_SECONDS = 10 * 60
_IMG_SRC_RE = re.compile(r"""<img[^>]+src=["']([^"']+)["']""", re.IGNORECASE)


def _feed_events_cache_key(workspace_id):
    return f"composer:feed-events:{workspace_id}"


def _normalize_selected_feed_id(selected_feed_id, feeds):
    valid_feed_ids = {str(feed.id) for feed in feeds}
    if selected_feed_id in valid_feed_ids:
        return selected_feed_id
    return "all"


def _coerce_positive_int(value, default=0):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _xml_local_name(tag):
    """Return local XML tag name without namespace."""
    if not tag:
        return ""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1].lower()
    if ":" in tag:
        return tag.split(":", 1)[-1].lower()
    return tag.lower()


def _first_child(element, *names):
    wanted = {name.lower() for name in names}
    for child in element:
        if _xml_local_name(child.tag) in wanted:
            return child
    return None


def _first_child_text(element, *names):
    child = _first_child(element, *names)
    if child is None:
        return ""
    return (child.text or "").strip()


def _extract_atom_link(entry):
    for child in entry:
        if _xml_local_name(child.tag) != "link":
            continue
        href = (child.attrib.get("href") or "").strip()
        rel = (child.attrib.get("rel") or "").strip().lower()
        if href and rel in ("", "alternate"):
            return href
    for child in entry:
        if _xml_local_name(child.tag) != "link":
            continue
        href = (child.attrib.get("href") or "").strip()
        if href:
            return href
    return ""


def _extract_image_url(entry, summary_raw):
    for node in entry.iter():
        name = _xml_local_name(node.tag)
        if name not in {"thumbnail", "content", "enclosure"}:
            continue
        url = (node.attrib.get("url") or node.attrib.get("href") or node.attrib.get("src") or "").strip()
        media_type = (node.attrib.get("type") or "").lower()
        medium = (node.attrib.get("medium") or "").lower()
        if url and (name == "thumbnail" or medium == "image" or media_type.startswith("image/") or not media_type):
            return url

    if summary_raw:
        match = _IMG_SRC_RE.search(summary_raw)
        if match:
            return match.group(1)
    return ""


def _clean_summary(raw_summary):
    if not raw_summary:
        return ""
    return re.sub(r"\s+", " ", strip_tags(raw_summary)).strip()


def _parse_published_at(raw_value):
    if not raw_value:
        return None
    with contextlib.suppress(ValueError, TypeError, OverflowError):
        parsed = date_parser.parse(raw_value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def _parse_feed_document(xml_content):
    """Parse RSS/Atom document into metadata and raw entries."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    root_name = _xml_local_name(root.tag)
    if root_name == "rss":
        channel = _first_child(root, "channel")
        if channel is None:
            return None
        entries = [child for child in channel if _xml_local_name(child.tag) == "item"]
        return {
            "title": _first_child_text(channel, "title"),
            "website_url": _first_child_text(channel, "link"),
            "entries": entries,
            "entry_kind": "rss",
        }

    if root_name == "feed":
        entries = [child for child in root if _xml_local_name(child.tag) == "entry"]
        return {
            "title": _first_child_text(root, "title"),
            "website_url": _extract_atom_link(root),
            "entries": entries,
            "entry_kind": "atom",
        }

    if root_name == "rdf":
        channel = _first_child(root, "channel")
        entries = [child for child in root if _xml_local_name(child.tag) == "item"]
        return {
            "title": _first_child_text(channel, "title") if channel is not None else "",
            "website_url": _first_child_text(channel, "link") if channel is not None else "",
            "entries": entries,
            "entry_kind": "rss",
        }

    return None


def _build_event_from_entry(feed, parsed_feed, entry):
    kind = parsed_feed["entry_kind"]
    if kind == "atom":
        raw_title = _first_child_text(entry, "title")
        raw_link = _extract_atom_link(entry)
        raw_summary = _first_child_text(entry, "summary") or _first_child_text(entry, "content")
        raw_published = (
            _first_child_text(entry, "published")
            or _first_child_text(entry, "updated")
            or _first_child_text(entry, "issued")
        )
    else:
        raw_title = _first_child_text(entry, "title")
        raw_link = _first_child_text(entry, "link")
        raw_summary = (
            _first_child_text(entry, "description")
            or _first_child_text(entry, "summary")
            or _first_child_text(entry, "content")
        )
        raw_published = (
            _first_child_text(entry, "pubDate")
            or _first_child_text(entry, "published")
            or _first_child_text(entry, "updated")
            or _first_child_text(entry, "date")
        )

    title = raw_title or parsed_feed["title"] or feed.name or "Untitled"
    link = raw_link or parsed_feed["website_url"] or feed.website_url
    summary = _clean_summary(raw_summary)
    image_url = _extract_image_url(entry, raw_summary)
    published_at = _parse_published_at(raw_published)
    event_id = (link or f"{feed.id}:{title}:{raw_published}").strip()
    return {
        "event_id": event_id,
        "feed_id": str(feed.id),
        "feed_name": feed.name,
        "feed_favicon_url": feed.favicon_url,
        "feed_website_url": feed.website_url or parsed_feed["website_url"],
        "title": title,
        "link": link,
        "summary": summary,
        "image_url": image_url,
        "published_at": published_at,
    }


def _fetch_feed_events_for_workspace(feeds):
    """Fetch and aggregate recent events across all workspace feeds."""
    if not feeds:
        return []

    headers = {
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
        "User-Agent": "Brightbean RSS Reader/1.0",
    }
    all_events = []
    with httpx.Client(headers=headers, timeout=8.0, follow_redirects=True) as client:
        for feed in feeds:
            with contextlib.suppress(httpx.RequestError):
                response = client.get(feed.url)
                if response.status_code >= 400:
                    continue
                parsed_feed = _parse_feed_document(response.content)
                if not parsed_feed:
                    continue
                for entry in parsed_feed["entries"][:50]:
                    all_events.append(_build_event_from_entry(feed, parsed_feed, entry))

    deduped_events = []
    seen = set()
    for event in all_events:
        dedupe_key = (event["feed_id"], event["event_id"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped_events.append(event)

    deduped_events.sort(
        key=lambda event: event["published_at"] or datetime(1970, 1, 1, tzinfo=UTC),
        reverse=True,
    )
    return deduped_events


def _get_cached_workspace_feed_events(workspace, feeds, force_refresh=False):
    """Return cached feed events and last refresh time for workspace feeds."""
    cache_key = _feed_events_cache_key(workspace.id)
    signature = tuple((str(feed.id), feed.url, feed.name, feed.website_url) for feed in feeds)
    cached = cache.get(cache_key)
    if cached and not force_refresh and cached.get("signature") == signature:
        return cached.get("events", []), cached.get("fetched_at")

    events = _fetch_feed_events_for_workspace(feeds)
    fetched_at = timezone.now()
    cache.set(
        cache_key,
        {
            "signature": signature,
            "events": events,
            "fetched_at": fetched_at,
        },
        FEED_EVENTS_CACHE_TTL_SECONDS,
    )
    return events, fetched_at


def _filter_events_for_feed(events, selected_feed_id):
    if selected_feed_id == "all":
        return events
    return [event for event in events if event["feed_id"] == selected_feed_id]


def _build_feed_events_context(workspace, selected_feed_id="all", offset=0):
    feeds = list(Feed.objects.for_workspace(workspace.id))
    selected_feed_id = _normalize_selected_feed_id(selected_feed_id, feeds)
    selected_feed = next((feed for feed in feeds if str(feed.id) == selected_feed_id), None)
    events, last_refreshed_at = _get_cached_workspace_feed_events(workspace, feeds)
    filtered_events = _filter_events_for_feed(events, selected_feed_id)
    page_events = filtered_events[offset : offset + FEED_EVENTS_PAGE_SIZE]
    next_offset = offset + FEED_EVENTS_PAGE_SIZE
    has_more = len(filtered_events) > next_offset
    return {
        "feeds": feeds,
        "selected_feed_id": selected_feed_id,
        "selected_feed": selected_feed,
        "events": page_events,
        "next_offset": next_offset,
        "has_more": has_more,
        "last_refreshed_at": last_refreshed_at,
        "total_event_count": len(filtered_events),
    }


def _render_feeds_tab(
    request,
    workspace,
    *,
    show_add_modal=False,
    add_rss_url="",
    add_error="",
    selected_feed_id="all",
):
    """Render the feeds tab partial with modal state and first event page."""
    context = _build_feed_events_context(workspace, selected_feed_id=selected_feed_id, offset=0)
    context.update(
        {
            "workspace": workspace,
            "show_add_modal": show_add_modal,
            "add_rss_url": add_rss_url,
            "add_error": add_error,
        }
    )
    return render(request, "composer/partials/feeds_tab.html", context)


def _validate_rss_url(rss_url):
    """Validate that a URL points to a reachable RSS/Atom XML feed."""
    headers = {
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
        "User-Agent": "Brightbean RSS Validator/1.0",
    }
    try:
        response = httpx.get(rss_url, headers=headers, timeout=8.0, follow_redirects=True)
    except httpx.RequestError:
        return False, "Could not reach this URL. Please check the link and try again.", {}

    if response.status_code >= 400:
        return False, "This URL could not be loaded as a feed.", {}

    parsed_feed = _parse_feed_document(response.content)
    if not parsed_feed:
        return False, "This URL is reachable, but it does not appear to be a valid RSS/Atom feed.", {}

    return (
        True,
        "",
        {
            "title": parsed_feed.get("title", "").strip(),
            "website_url": parsed_feed.get("website_url", "").strip(),
        },
    )


@login_required
@require_permission("create_posts")
@require_GET
def feed_list(request, workspace_id):
    """Return the feeds tab partial (empty state or feed list)."""
    workspace = _get_workspace(request, workspace_id)
    selected_feed_id = request.GET.get("feed_id", "all")
    is_append = request.GET.get("append") == "1"
    offset = _coerce_positive_int(request.GET.get("offset"), default=0)

    if is_append:
        context = _build_feed_events_context(workspace, selected_feed_id=selected_feed_id, offset=offset)
        context.update(
            {
                "workspace": workspace,
                "show_empty": False,
            }
        )
        return render(request, "composer/partials/feed_events_batch.html", context)

    return _render_feeds_tab(request, workspace, selected_feed_id=selected_feed_id)


@login_required
@require_permission("create_posts")
@require_POST
def feed_add(request, workspace_id):
    """Add a feed subscription to the workspace."""
    from django.core.exceptions import ValidationError
    from django.core.validators import URLValidator

    workspace = _get_workspace(request, workspace_id)
    rss_url = request.POST.get("rss_url", "").strip()
    name = request.POST.get("name", "").strip()
    website_url = request.POST.get("website_url", "").strip()
    source = request.POST.get("source", "")
    category = request.POST.get("category", "brightbean-favorites")
    selected_feed_id = request.POST.get("feed_id", "all")
    derived_metadata = {}

    if not rss_url:
        if source == "explore":
            return HttpResponse("Feed URL is required.", status=400)
        return _render_feeds_tab(
            request,
            workspace,
            show_add_modal=True,
            add_rss_url=rss_url,
            add_error="Feed URL is required.",
            selected_feed_id=selected_feed_id,
        )

    validator = URLValidator()
    try:
        validator(rss_url)
    except ValidationError:
        if source == "explore":
            return HttpResponse("Invalid URL.", status=400)
        return _render_feeds_tab(
            request,
            workspace,
            show_add_modal=True,
            add_rss_url=rss_url,
            add_error="Invalid URL.",
            selected_feed_id=selected_feed_id,
        )

    if source != "explore":
        is_valid_rss, validation_error, derived_metadata = _validate_rss_url(rss_url)
        if not is_valid_rss:
            return _render_feeds_tab(
                request,
                workspace,
                show_add_modal=True,
                add_rss_url=rss_url,
                add_error=validation_error,
                selected_feed_id=selected_feed_id,
            )

    if Feed.objects.for_workspace(workspace.id).filter(url=rss_url).exists():
        # Already subscribed - if from explore, just re-render explore view
        if source == "explore":
            return _render_explore(request, workspace, category)
        return _render_feeds_tab(
            request,
            workspace,
            show_add_modal=True,
            add_rss_url=rss_url,
            add_error="Already subscribed to this feed.",
            selected_feed_id=selected_feed_id,
        )

    resolved_name = name or derived_metadata.get("title") or rss_url
    resolved_website_url = website_url or derived_metadata.get("website_url", "")
    Feed.objects.create(
        workspace=workspace,
        name=resolved_name,
        url=rss_url,
        website_url=resolved_website_url,
        added_by=request.user,
    )
    cache.delete(_feed_events_cache_key(workspace.id))

    if source == "explore":
        response = _render_explore(request, workspace, category)
        response["HX-Trigger"] = "feedsUpdated"
        return response

    return _render_feeds_tab(request, workspace, selected_feed_id=selected_feed_id)


@login_required
@require_permission("create_posts")
@require_POST
def feed_delete(request, workspace_id, feed_id):
    """Remove a feed subscription."""
    workspace = _get_workspace(request, workspace_id)
    selected_feed_id = request.POST.get("feed_id", "all")
    feed = get_object_or_404(Feed, id=feed_id, workspace=workspace)
    feed.delete()
    cache.delete(_feed_events_cache_key(workspace.id))

    return _render_feeds_tab(request, workspace, selected_feed_id=selected_feed_id)


@login_required
@require_permission("create_posts")
@require_GET
def feed_explore(request, workspace_id):
    """Return the explore feeds modal content for a given category."""
    workspace = _get_workspace(request, workspace_id)
    category = request.GET.get("category", "brightbean-favorites")
    return _render_explore(request, workspace, category)


def _render_explore(request, workspace, category):
    """Shared helper to render the explore feeds partial."""
    from .curated_feeds import get_feed_categories, get_feeds_for_category

    subscribed_urls = set(Feed.objects.for_workspace(workspace.id).values_list("url", flat=True))
    curated = get_feeds_for_category(category)
    for feed in curated:
        feed["subscribed"] = feed["rss"] in subscribed_urls

    return render(
        request,
        "composer/partials/feeds_explore.html",
        {
            "workspace": workspace,
            "categories": get_feed_categories(),
            "active_category": category,
            "curated_feeds": curated,
        },
    )
