"""Views for the Approval Workflow (F-2.2)."""

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from apps.composer.models import Post, PostVersion
from apps.members.decorators import require_permission, require_workspace_role
from apps.workspaces.models import Workspace

from . import comments as comment_service
from . import services
from .models import PostComment


def _get_workspace(request, workspace_id):
    from django.core.exceptions import PermissionDenied

    from apps.members.models import WorkspaceMembership

    workspace = get_object_or_404(Workspace, id=workspace_id)
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    if not WorkspaceMembership.objects.filter(user=request.user, workspace=workspace).exists():
        raise PermissionDenied("You do not have access to this workspace.")
    return workspace


# ---------------------------------------------------------------------------
# Approval Queue
# ---------------------------------------------------------------------------


@login_required
@require_permission("approve_posts")
@require_GET
def approval_queue(request, workspace_id):
    """Workspace-level approval queue showing pending posts."""
    workspace = _get_workspace(request, workspace_id)

    status_filter = request.GET.get("status", "all")
    base_filter = {"platform_posts__status__in": ["pending_review", "pending_client"]}
    posts = (
        Post.objects.for_workspace(workspace.id)
        .filter(**base_filter)
        .distinct()
        .select_related("author")
        .prefetch_related("platform_posts__social_account", "media_attachments__media_asset")
        .order_by("scheduled_at", "-created_at")
    )

    if status_filter == "pending_review":
        posts = posts.filter(platform_posts__status="pending_review").distinct()
    elif status_filter == "pending_client":
        posts = posts.filter(platform_posts__status="pending_client").distinct()

    from apps.composer.models import PlatformPost

    pp_qs = PlatformPost.objects.filter(post__workspace=workspace)
    pending_review_count = pp_qs.filter(status="pending_review").values("post_id").distinct().count()
    pending_client_count = pp_qs.filter(status="pending_client").values("post_id").distinct().count()
    counts = {
        "pending_review_count": pending_review_count,
        "pending_client_count": pending_client_count,
    }

    context = {
        "workspace": workspace,
        "posts": posts,
        "status_filter": status_filter,
        "pending_review_count": counts["pending_review_count"],
        "pending_client_count": counts["pending_client_count"],
    }

    if request.htmx:
        return render(request, "approvals/partials/post_list.html", context)

    return render(request, "approvals/queue.html", context)


@login_required
@require_GET
def org_approval_queue(request):
    """Cross-workspace org-level approval queue (read-only)."""
    org = request.org
    if not org:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("No organization found.")

    # Only org admins/owners
    if not request.org_membership or request.org_membership.org_role not in ("owner", "admin"):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("Insufficient role.")

    # Get all workspaces the user's org owns
    workspaces = Workspace.objects.filter(organization=org, is_archived=False)

    workspace_posts = []
    for ws in workspaces:
        pending = (
            Post.objects.for_workspace(ws.id)
            .filter(platform_posts__status__in=["pending_review", "pending_client"])
            .distinct()
            .select_related("author")
            .prefetch_related("platform_posts__social_account")
            .order_by("scheduled_at", "-created_at")
        )
        if pending.exists():
            workspace_posts.append({"workspace": ws, "posts": pending})

    return render(
        request,
        "approvals/org_queue.html",
        {
            "workspace_posts": workspace_posts,
        },
    )


# ---------------------------------------------------------------------------
# Approval Actions
# ---------------------------------------------------------------------------


@login_required
@require_permission("approve_posts")
@require_POST
def approve(request, workspace_id, post_id):
    """Approve a post."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    comment_text = request.POST.get("comment", "")

    try:
        services.approve_post(post, request.user, workspace, comment_text)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.htmx:
        # Return updated post row partial
        return render(
            request,
            "approvals/partials/post_row.html",
            {
                "post": post,
                "workspace": workspace,
            },
        )

    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps({"approvalAction": {"postId": str(post.id), "action": "approved"}}),
        },
    )


@login_required
@require_permission("approve_posts")
@require_POST
def request_changes_view(request, workspace_id, post_id):
    """Request changes on a post."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    comment_text = request.POST.get("comment", "")

    try:
        services.request_changes(post, request.user, workspace, comment_text)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.htmx:
        return render(
            request,
            "approvals/partials/post_row.html",
            {
                "post": post,
                "workspace": workspace,
            },
        )

    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps({"approvalAction": {"postId": str(post.id), "action": "changes_requested"}}),
        },
    )


@login_required
@require_permission("approve_posts")
@require_POST
def reject(request, workspace_id, post_id):
    """Reject a post."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    comment_text = request.POST.get("comment", "")

    try:
        services.reject_post(post, request.user, workspace, comment_text)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.htmx:
        return render(
            request,
            "approvals/partials/post_row.html",
            {
                "post": post,
                "workspace": workspace,
            },
        )

    return HttpResponse(
        status=204,
        headers={
            "HX-Trigger": json.dumps({"approvalAction": {"postId": str(post.id), "action": "rejected"}}),
        },
    )


@login_required
@require_permission("approve_posts")
@require_POST
def bulk_action(request, workspace_id):
    """Bulk approve or reject posts."""
    workspace = _get_workspace(request, workspace_id)
    action = request.POST.get("action")
    post_ids = request.POST.getlist("post_ids")

    if not post_ids:
        return HttpResponse("No posts selected.", status=400)

    if action == "approve":
        results = services.bulk_approve(post_ids, request.user, workspace)
    elif action == "reject":
        comment_text = request.POST.get("comment", "")
        try:
            results = services.bulk_reject(post_ids, request.user, workspace, comment_text)
        except ValueError as e:
            return HttpResponse(str(e), status=400)
    else:
        return HttpResponse("Invalid action.", status=400)

    success_count = sum(1 for _, success, _ in results if success)

    if request.htmx:
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps(
                    {
                        "bulkActionComplete": {"action": action, "count": success_count},
                    }
                )
            },
        )

    return JsonResponse({"results": [{"id": r[0], "success": r[1], "error": r[2]} for r in results]})


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


@login_required
@require_workspace_role("viewer")
@require_POST
def add_comment(request, workspace_id, post_id):
    """Add a comment to a post."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)

    body = request.POST.get("body", "").strip()
    if not body:
        return HttpResponse("Comment body is required.", status=400)

    visibility = request.POST.get("visibility", PostComment.Visibility.EXTERNAL)
    parent_id = request.POST.get("parent_id") or None
    attachment = request.FILES.get("attachment")

    try:
        comment_service.create_comment(
            post=post,
            author=request.user,
            body=body,
            visibility=visibility,
            parent_id=parent_id,
            attachment=attachment,
        )
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    # Return updated comment list
    comments = comment_service.get_comments_for_post(post, request.user)
    return render(
        request,
        "approvals/partials/comment_list.html",
        {
            "comments": comments,
            "post": post,
            "workspace": workspace,
        },
    )


@login_required
@require_workspace_role("viewer")
@require_POST
def edit_comment(request, workspace_id, post_id, comment_id):
    """Edit a comment."""
    workspace = _get_workspace(request, workspace_id)
    body = request.POST.get("body", "").strip()

    if not body:
        return HttpResponse("Comment body is required.", status=400)

    # Scope the post + comment lookup to the request workspace so a viewer
    # cannot edit / surface comments belonging to a different workspace.
    post = get_object_or_404(Post, id=post_id, workspace=workspace)

    try:
        comment_service.update_comment(comment_id, request.user, body, workspace=workspace)
    except (ValueError, PermissionError) as e:
        return HttpResponse(str(e), status=400 if isinstance(e, ValueError) else 403)

    comments = comment_service.get_comments_for_post(post, request.user)
    return render(
        request,
        "approvals/partials/comment_list.html",
        {
            "comments": comments,
            "post": post,
            "workspace": workspace,
        },
    )


@login_required
@require_workspace_role("viewer")
@require_POST
def delete_comment(request, workspace_id, post_id, comment_id):
    """Soft-delete a comment."""
    workspace = _get_workspace(request, workspace_id)

    try:
        comment_service.delete_comment(comment_id, request.user, workspace)
    except (ValueError, PermissionError) as e:
        return HttpResponse(str(e), status=400 if isinstance(e, ValueError) else 403)

    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    comments = comment_service.get_comments_for_post(post, request.user)
    return render(
        request,
        "approvals/partials/comment_list.html",
        {
            "comments": comments,
            "post": post,
            "workspace": workspace,
        },
    )


# ---------------------------------------------------------------------------
# Version Diff
# ---------------------------------------------------------------------------


@login_required
@require_workspace_role("viewer")
@require_GET
def version_diff(request, workspace_id, post_id):
    """Show diff between two post versions."""
    workspace = _get_workspace(request, workspace_id)
    post = get_object_or_404(Post, id=post_id, workspace=workspace)

    versions = PostVersion.objects.filter(post=post).order_by("-version_number")

    v1_num = request.GET.get("v1")
    v2_num = request.GET.get("v2")

    if v1_num and v2_num:
        version_old = versions.filter(version_number=int(v1_num)).first()
        version_new = versions.filter(version_number=int(v2_num)).first()
    elif versions.count() >= 2:
        version_new = versions[0]
        version_old = versions[1]
    else:
        version_old = None
        version_new = versions.first()

    # Build diff data
    diff_data = _build_diff(
        version_old.snapshot if version_old else {},
        version_new.snapshot if version_new else {},
    )

    context = {
        "post": post,
        "workspace": workspace,
        "versions": versions,
        "version_old": version_old,
        "version_new": version_new,
        "diff_data": diff_data,
    }

    if request.htmx:
        return render(request, "approvals/partials/version_diff.html", context)

    return render(request, "approvals/version_diff.html", context)


def _build_diff(old_snapshot, new_snapshot):
    """Build a structured diff between two version snapshots."""
    diff = {
        "caption_changed": old_snapshot.get("caption", "") != new_snapshot.get("caption", ""),
        "caption_old": old_snapshot.get("caption", ""),
        "caption_new": new_snapshot.get("caption", ""),
        "media_changed": old_snapshot.get("media", []) != new_snapshot.get("media", []),
        "media_old": old_snapshot.get("media", []),
        "media_new": new_snapshot.get("media", []),
        "platforms_changed": old_snapshot.get("platform_posts", []) != new_snapshot.get("platform_posts", []),
        "platforms_old": old_snapshot.get("platform_posts", []),
        "platforms_new": new_snapshot.get("platform_posts", []),
    }
    return diff
