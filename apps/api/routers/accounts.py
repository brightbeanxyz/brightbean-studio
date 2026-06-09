"""``GET /api/v1/accounts`` — list the connected accounts this key may target."""

from __future__ import annotations

from ninja import Router

from apps.api.limits import enforce_http_rate_limits
from apps.api.middleware import log_audit_entry
from apps.api.schemas import AccountsListResponse, AccountSummary

router = Router(tags=["accounts"])


@router.get(
    "/",
    response=AccountsListResponse,
    summary="List the SocialAccounts this API key is allowed to act on",
)
def list_accounts(request):
    enforce_http_rate_limits(request, is_write=False)
    api_key = request.api_key
    accounts = [AccountSummary.from_social_account(sa) for sa in api_key.social_accounts.all()]
    log_audit_entry(request, action="accounts.list", target_id=None, status_code=200)
    return AccountsListResponse(accounts=accounts)
