"""Views for the Client Portal (F-1.4)."""

import json

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.approvals import comments as comment_service
from apps.approvals import services as approval_services
from apps.approvals.models import ApprovalAction
from apps.composer.models import Post

from .decorators import portal_auth_required
from .services import consume_magic_link, create_portal_session, peek_magic_link

# ---------------------------------------------------------------------------
# Magic Link Entry
# ---------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def magic_link_entry(request, token):
    """Confirm and consume a magic link.

    GET renders a confirmation page without consuming the token, so email link
    scanners that prefetch the URL cannot burn the one-time token. POST consumes
    the token, creates the portal session, and redirects to the dashboard.
    """
    if request.method == "POST":
        user, workspace, is_valid = consume_magic_link(token)
        if not is_valid:
            return redirect("client_portal:magic_link_expired")
        create_portal_session(request, user, workspace)
        return redirect("client_portal:dashboard")

    magic_token = peek_magic_link(token)
    if magic_token is None:
        return redirect("client_portal:magic_link_expired")
    return render(
        request,
        "client_portal/magic_link_confirm.html",
        {
            "token": token,
            "workspace": magic_token.workspace,
        },
    )


def magic_link_expired(request):
    """Show page for expired or invalid magic links."""
    return render(request, "client_portal/magic_link_expired.html")


# ---------------------------------------------------------------------------
# Portal Dashboard
# ---------------------------------------------------------------------------


@portal_auth_required
@require_GET
def portal_dashboard(request):
    """Portal landing page with summary counts and quick links."""
    workspace = request.portal_workspace

    pending_count = (
        Post.objects.for_workspace(workspace.id).filter(platform_posts__status="pending_client").distinct().count()
    )

    recent_published = (
        Post.objects.for_workspace(workspace.id)
        .filter(platform_posts__status="published")
        .distinct()
        .order_by("-published_at")[:5]
    )

    my_actions = ApprovalAction.objects.filter(
        user=request.user,
        post__workspace=workspace,
    ).order_by("-created_at")[:5]

    return render(
        request,
        "client_portal/dashboard.html",
        {
            "workspace": workspace,
            "pending_count": pending_count,
            "recent_published": recent_published,
            "my_actions": my_actions,
        },
    )


# ---------------------------------------------------------------------------
# Portal Approval Queue
# ---------------------------------------------------------------------------


@portal_auth_required
@require_GET
def portal_approval_queue(request):
    """Posts pending client approval."""
    workspace = request.portal_workspace

    posts = (
        Post.objects.for_workspace(workspace.id)
        .filter(platform_posts__status="pending_client")
        .distinct()
        .select_related("author")
        .prefetch_related(
            "platform_posts__social_account",
            "media_attachments__media_asset",
        )
        .order_by("scheduled_at", "-created_at")
    )

    # Annotate each post with visible comments (external only for clients)
    posts = list(posts)
    for post in posts:
        post.visible_comments = list(comment_service.get_comments_for_post(post, request.user))

    return render(
        request,
        "client_portal/approval_queue.html",
        {
            "workspace": workspace,
            "posts": posts,
        },
    )


@portal_auth_required
@require_POST
def portal_approve(request, post_id):
    """Approve a post from the client portal."""
    workspace = request.portal_workspace
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    if not post.platform_posts.filter(status="pending_client").exists():
        raise Http404
    comment_text = request.POST.get("comment", "")

    try:
        approval_services.approve_post(post, request.user, workspace, comment_text)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.htmx:
        return HttpResponse(
            status=204,
            headers={"HX-Trigger": json.dumps({"portalAction": {"postId": str(post.id), "action": "approved"}})},
        )
    return redirect("client_portal:approval_queue")


@portal_auth_required
@require_POST
def portal_request_changes(request, post_id):
    """Request changes on a post from the client portal."""
    workspace = request.portal_workspace
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    if not post.platform_posts.filter(status="pending_client").exists():
        raise Http404
    comment_text = request.POST.get("comment", "")

    try:
        approval_services.request_changes(post, request.user, workspace, comment_text)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.htmx:
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps({"portalAction": {"postId": str(post.id), "action": "changes_requested"}})
            },
        )
    return redirect("client_portal:approval_queue")


@portal_auth_required
@require_POST
def portal_reject(request, post_id):
    """Reject a post from the client portal."""
    workspace = request.portal_workspace
    post = get_object_or_404(Post, id=post_id, workspace=workspace)
    if not post.platform_posts.filter(status="pending_client").exists():
        raise Http404
    comment_text = request.POST.get("comment", "")

    try:
        approval_services.reject_post(post, request.user, workspace, comment_text)
    except ValueError as e:
        return HttpResponse(str(e), status=400)

    if request.htmx:
        return HttpResponse(
            status=204,
            headers={"HX-Trigger": json.dumps({"portalAction": {"postId": str(post.id), "action": "rejected"}})},
        )
    return redirect("client_portal:approval_queue")


# ---------------------------------------------------------------------------
# Published Content
# ---------------------------------------------------------------------------


@portal_auth_required
@require_GET
def portal_published(request):
    """Chronological list of published posts."""
    workspace = request.portal_workspace

    posts = (
        Post.objects.for_workspace(workspace.id)
        .filter(platform_posts__status="published")
        .distinct()
        .select_related("author")
        .prefetch_related("platform_posts__social_account", "media_attachments__media_asset")
        .order_by("-published_at")
    )

    return render(
        request,
        "client_portal/published.html",
        {
            "workspace": workspace,
            "posts": posts,
        },
    )


# ---------------------------------------------------------------------------
# Activity Log
# ---------------------------------------------------------------------------


@portal_auth_required
@require_GET
def portal_activity(request):
    """Client's own approval actions."""
    workspace = request.portal_workspace

    actions = (
        ApprovalAction.objects.filter(
            user=request.user,
            post__workspace=workspace,
        )
        .select_related("post")
        .order_by("-created_at")
    )

    return render(
        request,
        "client_portal/activity.html",
        {
            "workspace": workspace,
            "actions": actions,
        },
    )


# ---------------------------------------------------------------------------
# Reports (Placeholder)
# ---------------------------------------------------------------------------


@portal_auth_required
@require_GET
def portal_reports(request):
    """Placeholder reports page."""
    workspace = request.portal_workspace

    return render(
        request,
        "client_portal/reports.html",
        {
            "workspace": workspace,
        },
    )
