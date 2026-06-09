"""Background tasks for social account health checks."""

import logging
from datetime import timedelta

from background_task import background
from django.utils import timezone

logger = logging.getLogger(__name__)


@background(schedule=0)
def check_social_account_health(account_id: str):
    """Check health of a single social account.

    Validates the OAuth token by calling get_profile(). If the token
    is expiring soon, attempts to refresh it first.
    """
    from providers import get_provider

    from .error_messages import friendly_health_check_error
    from .models import SocialAccount

    try:
        account = SocialAccount.objects.get(id=account_id)
    except SocialAccount.DoesNotExist:
        logger.warning("Health check: account %s not found, skipping", account_id)
        return

    # Load app credentials (.env dominant, admin-entered org creds as fallback).
    from apps.credentials.models import PlatformCredential, resolve_platform_credentials

    credentials = resolve_platform_credentials(account.platform, account.workspace.organization_id)

    # For Mastodon, inject instance-specific client credentials
    if account.platform == PlatformCredential.Platform.MASTODON and account.instance_url:
        from .models import MastodonAppRegistration

        try:
            reg = MastodonAppRegistration.objects.get(instance_url=account.instance_url)
            credentials = {
                **credentials,
                "instance_url": account.instance_url,
                "client_id": reg.client_id,
                "client_secret": reg.client_secret,
            }
        except MastodonAppRegistration.DoesNotExist:
            pass

    try:
        provider = get_provider(account.platform, credentials)
    except ValueError:
        logger.error("Health check: no provider for platform %s", account.platform)
        return

    # Bluesky accounts connected before we recorded token_expires_at need a
    # one-shot refresh to populate it; without this, is_token_expiring_soon
    # stays False forever and the short-lived accessJwt is never rotated.
    needs_bluesky_bootstrap = account.platform == "bluesky" and account.token_expires_at is None
    if (account.is_token_expiring_soon or needs_bluesky_bootstrap) and account.oauth_refresh_token:
        try:
            new_tokens = provider.refresh_token(account.oauth_refresh_token)
            account.oauth_access_token = new_tokens.access_token
            if new_tokens.refresh_token:
                account.oauth_refresh_token = new_tokens.refresh_token
            if new_tokens.expires_in:
                account.token_expires_at = timezone.now() + timedelta(seconds=new_tokens.expires_in)
            account.connection_status = SocialAccount.ConnectionStatus.CONNECTED
            account.last_error = ""
            logger.info("Health check: refreshed token for %s", account)
        except Exception as e:
            logger.warning("Health check: token refresh failed for %s: %s", account, e)
            account.connection_status = SocialAccount.ConnectionStatus.TOKEN_EXPIRING
            account.last_error = friendly_health_check_error(e)

    # Validate token by fetching profile
    try:
        profile = provider.get_profile(account.oauth_access_token)
        account.follower_count = profile.follower_count
        # Provider CDNs (TikTok, Meta) return signed avatar URLs that
        # expire; display names and handles can also change on-platform.
        # Guard each write so a transient empty response doesn't wipe
        # previously-good values.
        if profile.avatar_url:
            account.avatar_url = profile.avatar_url
        if profile.name:
            account.account_name = profile.name
        if profile.handle:
            account.account_handle = profile.handle
        if account.connection_status != SocialAccount.ConnectionStatus.TOKEN_EXPIRING:
            account.connection_status = SocialAccount.ConnectionStatus.CONNECTED
        account.last_error = ""
    except Exception as e:
        logger.warning("Health check: profile fetch failed for %s: %s", account, e)
        account.connection_status = SocialAccount.ConnectionStatus.ERROR
        account.last_error = friendly_health_check_error(e)

    account.last_health_check_at = timezone.now()
    account.save(
        update_fields=[
            "oauth_access_token",
            "oauth_refresh_token",
            "token_expires_at",
            "follower_count",
            "avatar_url",
            "account_name",
            "account_handle",
            "connection_status",
            "last_error",
            "last_health_check_at",
            "updated_at",
        ]
    )


@background(schedule=0)
def schedule_all_health_checks():
    """Enqueue individual health checks for all active accounts."""
    from .models import SocialAccount

    accounts = SocialAccount.objects.filter(
        connection_status__in=[
            SocialAccount.ConnectionStatus.CONNECTED,
            SocialAccount.ConnectionStatus.TOKEN_EXPIRING,
        ]
    ).values_list("id", flat=True)

    count = 0
    for account_id in accounts:
        check_social_account_health(str(account_id))
        count += 1

    logger.info("Scheduled health checks for %d accounts", count)
