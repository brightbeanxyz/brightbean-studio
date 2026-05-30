"""``GET /api/v1/me`` — echo the caller's scope so they can self-introspect."""

from __future__ import annotations

from ninja import Router

from apps.api.limits import enforce_http_rate_limits
from apps.api.middleware import log_audit_entry
from apps.api.schemas import AccountSummary, MeResponse

router = Router(tags=["me"])


@router.get("/", response=MeResponse, summary="Inspect the caller's scope")
def me(request):
    enforce_http_rate_limits(request, is_write=False)
    api_key = request.api_key
    workspace = request.workspace
    accounts = [
        AccountSummary(
            id=sa.id,
            platform=sa.platform,
            account_name=sa.account_name,
            account_handle=getattr(sa, "account_handle", "") or "",
            connection_status=sa.connection_status,
        )
        for sa in api_key.social_accounts.all()
    ]
    body = MeResponse(
        api_key_id=api_key.id,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        organization_id=workspace.organization_id,
        permissions=[k for k, v in request.workspace_membership.effective_permissions.items() if v],
        allowlisted_accounts=accounts,
    )
    log_audit_entry(request, action="me.read", target_id=None, status_code=200)
    return body
