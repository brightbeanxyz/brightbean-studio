"""Analytics service — orchestrates metric fetching and storage."""

import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from apps.analytics.models import PostSnapshot, RefreshLog
from apps.credentials.models import PlatformCredential
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers import get_provider
from providers.exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)


def refresh_metrics(workspace: Workspace) -> list[dict]:
    """Refresh engagement metrics for all connected accounts in a workspace.

    Returns a list of result dicts, one per account:
        {"account": SocialAccount, "status": str, "posts_fetched": int, "error": str | None}
    """
    accounts = SocialAccount.objects.filter(
        workspace=workspace,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )

    results = []
    for account in accounts:
        # Load app-level credentials for this platform
        try:
            cred = PlatformCredential.objects.for_org(
                workspace.organization_id
            ).get(platform=account.platform, is_configured=True)
            credentials = cred.credentials
        except PlatformCredential.DoesNotExist:
            env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
            credentials = env_creds.get(account.platform, {})

        try:
            provider = get_provider(account.platform, credentials=credentials)
        except ValueError:
            logger.warning("No provider for platform %s", account.platform)
            continue

        started_at = timezone.now()

        try:
            metrics_list = provider.get_recent_post_metrics(
                access_token=account.oauth_access_token,
                account_platform_id=account.account_platform_id,
            )
        except NotImplementedError:
            # Platform doesn't support analytics — skip silently
            results.append({
                "account": account,
                "status": "unsupported",
                "posts_fetched": 0,
                "error": None,
            })
            continue
        except RateLimitError as e:
            completed_at = timezone.now()
            RefreshLog.objects.create(
                workspace=workspace,
                social_account=account,
                status=RefreshLog.Status.RATE_LIMITED,
                posts_fetched=0,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
            )
            results.append({
                "account": account,
                "status": "rate_limited",
                "posts_fetched": 0,
                "error": str(e),
            })
            continue
        except (APIError, Exception) as e:
            completed_at = timezone.now()
            RefreshLog.objects.create(
                workspace=workspace,
                social_account=account,
                status=RefreshLog.Status.ERROR,
                posts_fetched=0,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
            )
            results.append({
                "account": account,
                "status": "error",
                "posts_fetched": 0,
                "error": str(e),
            })
            continue

        # Upsert snapshots
        for metrics in metrics_list:
            extra = metrics.extra
            posted_at_str = extra.get("posted_at", "")
            try:
                posted_at = datetime.fromisoformat(
                    posted_at_str.replace("+0000", "+00:00")
                )
            except (ValueError, AttributeError):
                posted_at = timezone.now()

            PostSnapshot.objects.update_or_create(
                social_account=account,
                platform_post_id=extra.get("platform_post_id", ""),
                defaults={
                    "workspace": workspace,
                    "post_url": extra.get("post_url", ""),
                    "post_text": extra.get("post_text", ""),
                    "post_type": extra.get("post_type", ""),
                    "posted_at": posted_at,
                    "likes": metrics.likes,
                    "comments": metrics.comments,
                    "shares": metrics.shares,
                    "saves": metrics.saves,
                    "engagements": metrics.engagements,
                    "impressions": metrics.impressions,
                    "extra": {
                        k: v
                        for k, v in metrics.extra.items()
                        if k
                        not in (
                            "platform_post_id",
                            "post_url",
                            "post_text",
                            "posted_at",
                            "post_type",
                        )
                    },
                    "fetched_at": timezone.now(),
                },
            )

        completed_at = timezone.now()
        RefreshLog.objects.create(
            workspace=workspace,
            social_account=account,
            status=RefreshLog.Status.SUCCESS,
            posts_fetched=len(metrics_list),
            started_at=started_at,
            completed_at=completed_at,
        )
        results.append({
            "account": account,
            "status": "success",
            "posts_fetched": len(metrics_list),
            "error": None,
        })

    return results
