"""RBAC middleware that resolves org role + workspace role on every request."""

from django.core.exceptions import PermissionDenied

from .models import OrgMembership, WorkspaceMembership

# Prefixes served straight off disk by a URLconf route rather than by a view.
# Nothing downstream of them reads request.org / request.workspace, so
# resolving that context would only cost a session read, a user query and two
# membership queries — once per file, and a media-heavy page requests dozens.
CONTEXT_FREE_PATH_PREFIXES = ("/static/", "/media/")


class RBACMiddleware:
    """Attach org and workspace context to the request.

    Sets:
        request.org - the user's Organization (or None)
        request.org_membership - the user's OrgMembership (or None)
        request.workspace - the current Workspace (or None, set by views)
        request.workspace_membership - the WorkspaceMembership (or None)

    Note: v1 supports one org per user. The query uses .first() which is
    correct since unique_together=("user", "organization") and v1 only
    creates one org membership per user. If multi-org is added later,
    this must resolve org from URL or session context.

    Resolution happens in process_view (not __call__) because
    request.resolver_match is only available after URL resolution,
    which occurs inside get_response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Initialize attributes; actual resolution happens in process_view
        request.org = None
        request.org_membership = None
        request.workspace = None
        request.workspace_membership = None

        if request.path.startswith(CONTEXT_FREE_PATH_PREFIXES):
            return self.get_response(request)

        # Resolve org and workspace context early.
        # Workspace-from-URL resolution happens in process_view() (after URL
        # resolution). Here we only resolve org directly and fall back to
        # last_workspace_id for global pages that have no workspace_id in the URL.
        if hasattr(request, "user") and request.user.is_authenticated:
            # Resolve org membership.
            # In v1, each user belongs to exactly one organization.
            org_membership = OrgMembership.objects.filter(user=request.user).select_related("organization").first()
            if org_membership:
                request.org = org_membership.organization
                request.org_membership = org_membership

            # Fall back to last_workspace_id so global pages
            # (e.g. /notifications/) can still show workspace nav.
            # For workspace-specific URLs, process_view() will override this.
            if getattr(request.user, "last_workspace_id", None):
                ws_membership = (
                    WorkspaceMembership.objects.filter(
                        user=request.user,
                        workspace_id=request.user.last_workspace_id,
                        workspace__is_archived=False,
                    )
                    .select_related("workspace__organization", "custom_role")
                    .first()
                )
                if ws_membership:
                    request.workspace = ws_membership.workspace
                    request.workspace_membership = ws_membership

        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Resolve workspace context from URL kwargs.

        This runs after URL resolution, so resolver_match and view_kwargs
        are available.
        """
        # workspace_id first: it is a dict lookup, while ``request.user`` is
        # lazy and forces a session read plus a user query on every URL that
        # has no workspace in it at all.
        workspace_id = view_kwargs.get("workspace_id")
        if not workspace_id:
            return None

        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        # Clear stale context from __call__ before resolving
        request.workspace = None
        request.workspace_membership = None

        ws_membership = (
            WorkspaceMembership.objects.filter(
                user=request.user,
                workspace_id=workspace_id,
            )
            .select_related("workspace__organization", "custom_role")
            .first()
        )
        if not ws_membership:
            raise PermissionDenied("You do not have access to this workspace.")

        request.workspace = ws_membership.workspace
        request.workspace_membership = ws_membership

        # Keep last_workspace_id in sync so global pages show the right workspace
        if request.user.last_workspace_id != ws_membership.workspace_id:
            request.user.last_workspace_id = ws_membership.workspace_id
            request.user.save(update_fields=["last_workspace_id"])

        # Also resolve org from workspace for consistency
        org = ws_membership.workspace.organization
        org_membership = (
            OrgMembership.objects.filter(
                user=request.user,
                organization=org,
            )
            .select_related("organization")
            .first()
        )
        if org_membership:
            request.org = org_membership.organization
            request.org_membership = org_membership

        return None
