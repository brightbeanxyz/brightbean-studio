"""list_social_accounts."""

from __future__ import annotations

from typing import Any

from apps.social_accounts.models import SocialAccount


def _serialize(account: SocialAccount) -> dict[str, Any]:
    return {
        "id": str(account.id),
        "platform": account.platform,
        "account_name": account.account_name,
        "account_handle": account.account_handle,
        "follower_count": account.follower_count,
        "connection_status": account.connection_status,
        "needs_reconnect": account.needs_reconnect,
        "is_token_expiring_soon": account.is_token_expiring_soon,
        "last_health_check_at": (account.last_health_check_at.isoformat() if account.last_health_check_at else None),
        "last_error": account.last_error,
        "char_limit": account.char_limit,
    }


def register(mcp, ctx):
    @mcp.tool()
    def list_social_accounts(platform: str | None = None) -> list[dict[str, Any]]:
        """List social accounts connected to the current workspace. Optionally filter by platform."""
        ws = ctx.require_workspace()
        qs = SocialAccount.objects.for_workspace(ws.id).order_by("platform", "account_name")
        if platform:
            qs = qs.filter(platform=platform)
        return [_serialize(a) for a in qs]
