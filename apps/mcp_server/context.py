"""AuthContext + RBAC bridge for MCP tools.

The MCP server runs in-process with Django, so tools can use the ORM and service
layer directly. Every tool receives an AuthContext (built once per stdio session
or per HTTP request) and uses it to:

  * resolve the calling user from the API token
  * resolve the current workspace (token-scoped, or chosen via select_workspace)
  * check RBAC via WorkspaceMembership.effective_permissions
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.accounts.models import ApiToken, User
from apps.members.models import WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


class MCPAuthError(Exception):
    """Raised when the caller is not authenticated or lacks permission."""


class MCPWorkspaceError(Exception):
    """Raised when no workspace is selected or the workspace is invalid."""


@dataclass
class AuthContext:
    user: User
    api_token: ApiToken
    organization: Organization | None = None
    current_workspace: Workspace | None = None
    _membership_cache: dict = field(default_factory=dict)

    @classmethod
    def from_token(cls, raw_token: str) -> AuthContext:
        """Build an AuthContext from a raw API token string. Raises MCPAuthError on failure."""
        from apps.accounts.api_auth import authenticate_token

        result = authenticate_token(raw_token)
        if result is None:
            raise MCPAuthError("Invalid, revoked, or expired API token.")
        user, token = result

        org = None
        from apps.members.models import OrgMembership

        org_membership = OrgMembership.objects.filter(user=user).select_related("organization").first()
        if org_membership:
            org = org_membership.organization

        # Resolve starting workspace
        current = None
        if token.scoped_workspace_id:
            current = token.scoped_workspace
        elif (
            user.last_workspace_id
            and WorkspaceMembership.objects.filter(
                user=user,
                workspace_id=user.last_workspace_id,
                workspace__is_archived=False,
            ).exists()
        ):
            current = Workspace.objects.filter(pk=user.last_workspace_id).first()

        return cls(user=user, api_token=token, organization=org, current_workspace=current)

    @property
    def is_workspace_scoped(self) -> bool:
        return self.api_token.scoped_workspace_id is not None

    def select_workspace(self, workspace_id) -> Workspace:
        """Set the current workspace. Errors if scoped token tries to switch."""
        if self.is_workspace_scoped and str(workspace_id) != str(self.api_token.scoped_workspace_id):
            raise MCPAuthError("This token is scoped to a single workspace and cannot switch.")
        membership = (
            WorkspaceMembership.objects.filter(
                user=self.user,
                workspace_id=workspace_id,
                workspace__is_archived=False,
            )
            .select_related("workspace")
            .first()
        )
        if membership is None:
            raise MCPAuthError("You are not a member of that workspace.")
        self.current_workspace = membership.workspace
        self._membership_cache[str(membership.workspace.id)] = membership
        return membership.workspace

    def require_workspace(self) -> Workspace:
        if self.current_workspace is None:
            raise MCPWorkspaceError("No workspace selected. Call list_workspaces then select_workspace.")
        return self.current_workspace

    def membership(self) -> WorkspaceMembership:
        ws = self.require_workspace()
        key = str(ws.id)
        if key not in self._membership_cache:
            m = WorkspaceMembership.objects.filter(user=self.user, workspace=ws).select_related("custom_role").first()
            if m is None:
                raise MCPAuthError("You are no longer a member of the current workspace.")
            self._membership_cache[key] = m
        return self._membership_cache[key]

    def require_permission(self, key: str) -> None:
        perms = self.membership().effective_permissions or {}
        if not perms.get(key, False):
            raise MCPAuthError(f"Your role in this workspace does not allow '{key}'.")
