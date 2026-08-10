"""Subscribing and unsubscribing accounts to their platform's activity push.

Webhooks are the fast path for comments and mentions, not the only one:
``run_inbox_sync_cycle`` polls every connected account every few minutes. A
failed subscription therefore degrades the inbox to polling latency rather than
breaking it — which is what the account card says, and why a failure is
recorded on the account instead of on ``last_error`` (owned by the periodic
health check, which would wipe it on the next successful token check).

Lives outside ``views`` because four callers need it: the OAuth flow, the
card's retry button, the periodic health check, and the ``subscribe_webhooks``
backfill command.
"""

import logging

from background_task import background

from .error_messages import WEBHOOK_REJECTED_MESSAGE, WEBHOOK_UNAVAILABLE_MESSAGE, classify_webhook_failure
from .models import SocialAccount
from .provider_factory import _get_provider_for_platform

logger = logging.getLogger(__name__)

# How many times the periodic health check will re-attempt a failed
# subscription before it stops. Without a cap a permanent rejection — a Page
# type that simply cannot subscribe, say — would be retried against the
# platform every cycle forever. The user's own "Try again" button clears the
# counter, so an operator is never locked out of retrying.
MAX_AUTOMATIC_RETRIES = 5


def webhook_target(account):
    """The object whose webhooks we subscribe for this account: the account itself.

    This used to hand Instagram's linked Page (``webhook_target_id``) to
    ``subscribe_webhooks`` on the theory that the Page delivers Instagram
    events. Meta disagrees: ``comments``/``mentions`` are fields of the
    *Instagram* object, and a Page answers them with "(#100) Param
    subscribed_fields[0] must be one of {feed, mention, ...}" — so every
    Instagram account ended up with ``webhooks_active=False`` and an inbox that
    never saw a comment.

    ``webhook_target_id`` is still stored: ``_is_own_activity`` uses it to
    recognise the account's own Page-side activity.
    """
    return account.account_platform_id


def supports_webhooks(provider) -> bool:
    """Whether this provider actually implements a subscription.

    The base class returns False for every platform that has no webhooks, so
    without this check a genuine API rejection is indistinguishable from a
    platform that was never going to subscribe.
    """
    from providers.base import SocialProvider

    return type(provider).subscribe_webhooks is not SocialProvider.subscribe_webhooks


def subscribe_account_webhooks(account) -> bool:
    """Ask the platform to push this account's activity to us in real time.

    Best-effort on purpose — a platform that refuses the subscription should not
    block the user from connecting — but every outcome is recorded, including
    the ones where the call is never attempted. A silent return would leave the
    card's retry button re-rendering an identical warning with no hint that
    nothing happened.
    """
    try:
        provider = _get_provider_for_platform(account.platform, account.workspace.organization_id)
    except Exception:
        logger.exception("Could not build provider to subscribe webhooks for %s", account.id)
        # Almost always missing or misconfigured app credentials. Recorded
        # rather than swallowed so the retry reports something changed.
        record_subscription_result(account, False, WEBHOOK_UNAVAILABLE_MESSAGE, detail="provider unavailable")
        return False

    if not supports_webhooks(provider):
        # "Not applicable", not a failure — and if this account is carrying a
        # stale False from when the platform did support webhooks, clear it so
        # the card stops warning about something nobody can fix.
        clear_subscription_state(account)
        return False

    try:
        subscribed = provider.subscribe_webhooks(account.oauth_access_token, webhook_target(account))
    except Exception as exc:
        logger.exception("Webhook subscription failed for %s (%s)", account.id, account.platform)
        failure = classify_webhook_failure(exc)
        record_subscription_result(
            account,
            False,
            failure.message,
            needs_reconnect=failure.needs_reconnect,
            detail=str(exc),
        )
        return False

    if not subscribed:
        logger.warning(
            "%s declined the webhook subscription for account %s; its comments will only arrive by polling.",
            account.platform,
            account.id,
        )
    record_subscription_result(
        account,
        subscribed,
        "" if subscribed else WEBHOOK_REJECTED_MESSAGE,
        detail="" if subscribed else "the platform returned a falsy subscription result",
    )
    return subscribed


def record_subscription_result(
    account,
    active: bool,
    message: str,
    *,
    needs_reconnect: bool = False,
    detail: str = "",
):
    """Record whether the platform is pushing this account's activity to us.

    ``message`` is user-facing — it is rendered straight into the account card,
    so callers pass it through ``classify_webhook_failure`` rather than handing
    over a provider exception. ``detail`` is the raw text for operators
    (``diagnose_facebook`` prints it); it never reaches a template.
    """
    updates = {
        "webhooks_active": active,
        "webhook_error": "" if active else message[:500],
        "webhook_needs_reconnect": False if active else needs_reconnect,
        "webhook_error_detail": "" if active else detail,
    }
    if active:
        updates["webhook_retry_count"] = 0
    else:
        # Counted here rather than at the retry site so every path that records
        # a failure — connect, backfill command, health check — advances the
        # same budget.
        updates["webhook_retry_count"] = (account.webhook_retry_count or 0) + 1

    SocialAccount.objects.filter(pk=account.pk).update(**updates)


def clear_subscription_state(account):
    """Reset an account to "no verdict": the platform has no webhooks to subscribe."""
    if account.webhooks_active is None and not account.webhook_error:
        return
    SocialAccount.objects.filter(pk=account.pk).update(
        webhooks_active=None,
        webhook_error="",
        webhook_needs_reconnect=False,
        webhook_error_detail="",
        webhook_retry_count=0,
    )


def retry_failed_subscription(account) -> bool:
    """Re-attempt a subscription that previously failed, if it is worth it.

    Subscribing otherwise happens only when an account is connected, so a
    failure — including one caused by a bug we have since fixed — sticks to the
    account until somebody notices the warning and acts on it. Retrying from the
    health check means a fix ships and affected accounts heal themselves.

    Bounded on three axes so a hopeless account is not retried forever: the
    connection has to be healthy, the grant has to be capable of satisfying the
    call at all, and the automatic budget has to be unspent.
    """
    if account.needs_reconnect:
        return False
    if account.webhooks_active is not False:
        return False
    if account.webhook_needs_reconnect:
        return False
    if (account.webhook_retry_count or 0) >= MAX_AUTOMATIC_RETRIES:
        logger.info(
            "Not retrying webhooks for %s: %d automatic attempts already spent.",
            account.id,
            account.webhook_retry_count,
        )
        return False

    try:
        return subscribe_account_webhooks(account)
    except Exception:
        logger.exception("Webhook re-subscription failed for %s", account.id)
        return False


@background(schedule=0)
def subscribe_account_webhooks_task(account_id):
    """Subscribe webhooks off the OAuth request path.

    Connecting several Pages at once would otherwise fire one blocking round
    trip to Meta per Page inside the redirect the user is waiting on.
    """
    try:
        account = SocialAccount.objects.select_related("workspace").get(pk=account_id)
    except SocialAccount.DoesNotExist:
        logger.info("Account %s gone before webhooks could be subscribed.", account_id)
        return
    subscribe_account_webhooks(account)


def _webhook_target_is_shared(account) -> bool:
    """Whether another live connection depends on this same subscription.

    A subscription belongs to the platform object, not to our row: the same
    Page can be connected in two workspaces. Unsubscribing on one disconnect
    would silence the others' inboxes too, so we leave it in place and let the
    revoked token end our access.
    """
    return (
        SocialAccount.objects.filter(
            platform=account.platform,
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
            account_platform_id=webhook_target(account),
        )
        .exclude(pk=account.pk)
        .exists()
    )


def unsubscribe_account_webhooks(account) -> bool:
    """Stop the platform pushing this account's activity to us."""
    if _webhook_target_is_shared(account):
        logger.info(
            "Leaving the webhook subscription for %s in place; another connected account shares it.",
            webhook_target(account),
        )
        return False

    try:
        provider = _get_provider_for_platform(account.platform, account.workspace.organization_id)
        return provider.unsubscribe_webhooks(account.oauth_access_token, webhook_target(account))
    except Exception:
        logger.warning(
            "Failed to unsubscribe webhooks for %s (%s); continuing with disconnect.",
            account.id,
            account.platform,
        )
        return False
