"""``GET /api/v1/me`` — echo the caller's scope so they can self-introspect."""

from __future__ import annotations

from ninja import Router

from apps.api.limits import enforce_http_rate_limits
from apps.api.middleware import log_audit_entry
from apps.api.schemas import AccountSummary, MeResponse, StorageSummary
from apps.media_library.quotas import resolve_storage_quota, used_storage_bytes

router = Router(tags=["me"])


@router.get("/", response=MeResponse, summary="Inspect the caller's scope")
def me(request):
    enforce_http_rate_limits(request, is_write=False)
    api_key = request.api_key
    workspace = request.workspace
    accounts = [AccountSummary.from_social_account(sa) for sa in api_key.social_accounts.all()]

    organization = workspace.organization
    quota = resolve_storage_quota(organization)
    used = used_storage_bytes(organization)
    storage = StorageSummary(
        used_bytes=used,
        limit_bytes=quota.limit_bytes,
        remaining_bytes=max(quota.limit_bytes - used, 0),
        plan_slug=quota.plan_slug,
    )

    body = MeResponse(
        api_key_id=api_key.id,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        organization_id=workspace.organization_id,
        permissions=[k for k, v in request.workspace_membership.effective_permissions.items() if v],
        storage=storage,
        allowlisted_accounts=accounts,
    )
    log_audit_entry(request, action="me.read", target_id=None, status_code=200)
    return body
