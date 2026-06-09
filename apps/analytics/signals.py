"""Signal handlers: enqueue analytics backfill when a SocialAccount is
created or reconnected (oauth_access_token changes).
"""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.social_accounts.models import SocialAccount


@receiver(post_save, sender=SocialAccount)
def enqueue_analytics_backfill(sender, instance: SocialAccount, created: bool, update_fields=None, **kwargs):
    """Schedule a backfill when:
    - a new account is created (initial connection), or
    - an existing account is updated and ``oauth_access_token`` is in the
      update_fields (a reconnect with fresh credentials).
    """
    # Only act on real OAuth-token changes or first connect — anything else
    # (avatar refresh, follower count update) would re-trigger the backfill
    # noisily.
    if not created:
        if update_fields is None:
            return
        if "oauth_access_token" not in update_fields:
            return
    if instance.connection_status != SocialAccount.ConnectionStatus.CONNECTED:
        return
    # Import inside the handler so AppConfig.ready() doesn't pull in
    # background_task before the apps registry is fully loaded.
    from .tasks import backfill_account_analytics

    backfill_account_analytics(str(instance.id))
