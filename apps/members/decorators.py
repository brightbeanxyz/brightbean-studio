"""Permission decorators for RBAC enforcement."""

import functools

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def require_org_role(min_role):
    """Decorator that requires a minimum org role.

    Role hierarchy: owner > admin > member
    """
    role_hierarchy = {"owner": 3, "admin": 2, "member": 1}

    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.org_membership:
                raise PermissionDenied("You are not a member of any organization.")
            user_level = role_hierarchy.get(request.org_membership.org_role, 0)
            required_level = role_hierarchy.get(min_role, 0)
            if user_level < required_level:
                raise PermissionDenied("Insufficient organization role.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def require_workspace_role(min_role):
    """Decorator that requires a minimum workspace role.

    For users with custom roles, this checks the custom role's permissions
    against the built-in role's permissions to determine equivalence.
    Users with custom roles are treated as having the permissions defined
    in their custom role, so this decorator falls back to require_permission
    for the key permissions of the minimum role.

    Role hierarchy (built-in): owner > manager > editor > contributor > client > viewer
    """
    role_hierarchy = {
        "owner": 6,
        "manager": 5,
        "editor": 4,
        "contributor": 3,
        "client": 2,
        "viewer": 1,
    }

    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.workspace_membership:
                raise PermissionDenied("You are not a member of this workspace.")
            membership = request.workspace_membership
            user_level = role_hierarchy.get(membership.workspace_role, 0)
            required_level = role_hierarchy.get(min_role, 0)
            if user_level < required_level:
                raise PermissionDenied("Insufficient workspace role.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def require_permission(permission_key):
    """Decorator that checks a specific permission key against effective permissions.

    This works with both built-in roles and custom roles via the
    effective_permissions property on WorkspaceMembership.
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.workspace_membership:
                raise PermissionDenied("You are not a member of this workspace.")
            perms = request.workspace_membership.effective_permissions
            if not perms.get(permission_key, False):
                raise PermissionDenied(f"Permission denied: {permission_key}")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def require_org_permission(permission_key):
    """Decorator that gates a view on an org-level permission key.

    Unlike ``require_workspace_role`` / ``require_permission`` (workspace-
    scoped via the RBAC middleware), this decorator resolves the
    ``OrgMembership`` for ``(request.user, URL <org_id>)`` directly — no
    middleware fallback to ``last_workspace_id``. The view must accept
    ``org_id`` as a URL kwarg (typed ``<uuid:org_id>``).

    Composes ``@login_required`` internally so the view file doesn't
    need to remember to stack it. Anonymous → login redirect; non-member
    of the URL org → 403; member but lacking the permission → 403.

    On success, attaches ``request.org_membership`` and ``request.org``
    so the wrapped view can use them without re-querying.
    """
    from apps.members.models import OrgMembership, has_org_permission

    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            org_id = kwargs.get("org_id")
            if org_id is None:
                raise PermissionDenied("URL is missing required org_id.")
            try:
                membership = OrgMembership.objects.select_related("organization").get(
                    user=request.user, organization_id=org_id
                )
            except OrgMembership.DoesNotExist as exc:
                raise PermissionDenied("Not a member of this organization.") from exc

            if not has_org_permission(membership, permission_key):
                raise PermissionDenied(f"Missing org permission: {permission_key}")

            # Make resolved context available to the view body.
            request.org_membership = membership
            request.org = membership.organization
            return view_func(request, *args, **kwargs)

        return login_required(_wrapped)

    return decorator
