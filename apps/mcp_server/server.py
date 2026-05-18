"""Builds the FastMCP server instance and registers tools.

Phase 0 registers only session/workspace tools (whoami, list_workspaces,
select_workspace, get_workspace). Subsequent phases will import additional
tool modules from apps/mcp_server/tools/.

The `mcp` package is imported lazily so Django can boot without it installed —
only the `mcp_serve` management command needs it at runtime.
"""

from __future__ import annotations

from typing import Any

from .context import AuthContext, MCPAuthError, MCPWorkspaceError


def _workspace_summary(ws) -> dict[str, Any]:
    return {
        "id": str(ws.id),
        "name": ws.name,
        "organization_id": str(ws.organization_id),
        "timezone": ws.effective_timezone,
        "approval_workflow_mode": ws.approval_workflow_mode,
        "is_archived": ws.is_archived,
    }


def build_server(ctx: AuthContext):
    """Construct a FastMCP instance with all Phase 0 tools registered.

    `ctx` is bound to the lifetime of the server (one stdio session = one user).
    """
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("brightbean")

    @mcp.tool()
    def whoami() -> dict[str, Any]:
        """Return the authenticated user, organization, and currently selected workspace."""
        return {
            "user": {
                "id": str(ctx.user.id),
                "email": ctx.user.email,
                "name": ctx.user.display_name,
            },
            "organization": (
                {"id": str(ctx.organization.id), "name": ctx.organization.name} if ctx.organization else None
            ),
            "current_workspace": (_workspace_summary(ctx.current_workspace) if ctx.current_workspace else None),
            "token": {
                "name": ctx.api_token.name,
                "prefix": ctx.api_token.token_prefix,
                "scoped_workspace_id": (
                    str(ctx.api_token.scoped_workspace_id) if ctx.api_token.scoped_workspace_id else None
                ),
            },
        }

    @mcp.tool()
    def list_workspaces() -> list[dict[str, Any]]:
        """List workspaces the authenticated user has access to."""
        from apps.members.models import WorkspaceMembership

        memberships = (
            WorkspaceMembership.objects.filter(user=ctx.user, workspace__is_archived=False)
            .select_related("workspace", "workspace__organization", "custom_role")
            .order_by("workspace__name")
        )
        out = []
        for m in memberships:
            role = m.custom_role.name if m.custom_role else m.workspace_role
            out.append({**_workspace_summary(m.workspace), "role": role})
        return out

    @mcp.tool()
    def select_workspace(workspace_id: str) -> dict[str, Any]:
        """Set the current workspace for the rest of this MCP session."""
        ws = ctx.select_workspace(workspace_id)
        return _workspace_summary(ws)

    @mcp.tool()
    def get_workspace(workspace_id: str | None = None) -> dict[str, Any]:
        """Return details for a workspace. Defaults to the current workspace."""
        if workspace_id is None:
            ws = ctx.require_workspace()
        else:
            from apps.members.models import WorkspaceMembership

            membership = (
                WorkspaceMembership.objects.filter(user=ctx.user, workspace_id=workspace_id)
                .select_related("workspace")
                .first()
            )
            if membership is None:
                raise MCPAuthError("You are not a member of that workspace.")
            ws = membership.workspace
        return _workspace_summary(ws)

    # Re-raise our domain errors as MCP-friendly exceptions; FastMCP turns
    # exceptions into structured tool errors visible to the AI client.
    _ = (MCPAuthError, MCPWorkspaceError)  # keep imported for downstream tool modules

    return mcp
