"""Inbox sync engine - polls connected accounts for new messages."""

import logging
from datetime import timedelta
from typing import Any

from background_task import background
from django.utils import timezone

from apps.members.models import WorkspaceMembership
from apps.notifications.engine import notify
from apps.notifications.models import EventType
from apps.social_accounts.models import SocialAccount
from providers import get_provider

from .models import InboxMessage, InboxSLAConfig
from .sentiment import analyze_sentiment

logger = logging.getLogger(__name__)

# On an account's first-ever sync we may pull a historical backlog; notifications
# are suppressed for it, EXCEPT messages newer than this window — so a long-quiet
# account's genuinely-new first message still alerts instead of being swallowed.
INBOX_BACKLOG_NOTIFY_WINDOW = timedelta(hours=1)


def _is_recent(ts):
    """True if a provider message timestamp falls within the backlog-notify window."""
    if ts is None:
        return False
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, timezone.get_default_timezone())
    return ts >= timezone.now() - INBOX_BACKLOG_NOTIFY_WINDOW


def _related_post_key(extra: dict | None) -> str:
    """The post id a message hangs off, as PlatformPost stores it.

    Providers report the platform's own id (Facebook's is ``PAGEID_POSTID``);
    ``stored_post_id`` is the stripped form that matches
    ``PlatformPost.platform_post_id``. Fall back to the raw id for providers
    that don't strip.
    """
    return str((extra or {}).get("stored_post_id") or (extra or {}).get("post_id") or "")


def resolve_related_posts(account, messages) -> dict[str, Any]:
    """Map post ids in a batch of messages to this account's PlatformPost pks.

    One query for the whole batch rather than one per message — an active Page
    polls dozens of comments spread over a handful of posts.
    """
    from apps.composer.models import PlatformPost

    post_ids = {_related_post_key(getattr(msg, "extra", None)) for msg in messages}
    post_ids.discard("")
    if not post_ids:
        return {}

    return {
        platform_post_id: pk
        for platform_post_id, pk in PlatformPost.objects.filter(
            social_account=account,
            platform_post_id__in=post_ids,
        ).values_list("platform_post_id", "id")
    }


class InboxSyncEngine:
    """Syncs inbox messages from all connected social accounts."""

    def run_cycle(self):
        """Run one full inbox cycle: poll every connected account, then check SLAs.

        Single shared entry point for the ``run_inbox_sync`` management command
        and the recurring ``run_inbox_sync_cycle`` background task, so the two
        never diverge.
        """
        self.sync_all()
        self.check_sla()

    def sync_all(self):
        """Poll each connected account for new messages."""
        accounts = SocialAccount.objects.filter(
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        ).select_related("workspace")

        for account in accounts:
            try:
                self._sync_account(account)
            except Exception:
                logger.exception("Inbox sync failed for account %s", account.id)

    def _sync_account(self, account):
        """Sync messages for a single social account."""
        from apps.publisher.engine import _resolve_publish_credentials

        try:
            provider = get_provider(account.platform, _resolve_publish_credentials(account))
        except ValueError:
            logger.warning("No provider for platform %s", account.platform)
            return

        last_msg = (
            InboxMessage.objects.filter(social_account=account)
            .order_by("-received_at")
            .values_list("received_at", flat=True)
            .first()
        )
        # First-sync suppression is per message *type*, not per account. An
        # account that has been polling DMs for months is not "first sync", but
        # the day comment polling starts working its whole comment backlog
        # arrives at once — and would notify every owner and manager for each
        # one. A type we have never seen before is a backlog by definition.
        seen_types = set(
            InboxMessage.objects.filter(social_account=account).values_list("message_type", flat=True).distinct()
        )

        try:
            messages = provider.get_messages(
                access_token=account.oauth_access_token,
                since=last_msg,
            )
        except NotImplementedError:
            return
        except Exception:
            logger.exception(
                "get_messages() failed for account %s (%s)",
                account.id,
                account.platform,
            )
            return

        related_posts = resolve_related_posts(account, messages)

        for msg in messages:
            # Suppress notifications for the historical backlog pulled the first
            # time we see a message type, but still alert for genuinely recent
            # messages: a long-quiet account's first real message also looks like
            # a backlog, so a blanket mute would silently swallow it.
            # backfill_inbox seeds explicit history silently (notify=False).
            is_backlog = msg.message_type not in seen_types
            notify_new = not is_backlog or _is_recent(msg.timestamp)
            self._upsert_message(
                account,
                msg,
                notify=notify_new,
                related_post_id=related_posts.get(_related_post_key(msg.extra)),
            )

    def _upsert_message(self, account, msg, notify=True, related_post_id=None):
        """Create or update an inbox message, deduplicating by platform_message_id."""
        defaults = {
            "workspace": account.workspace,
            "sender_name": msg.sender_name,
            "sender_handle": msg.extra.get("sender_handle", msg.sender_id),
            "sender_avatar_url": msg.extra.get("sender_avatar_url", ""),
            "body": msg.text,
            "message_type": msg.message_type,
            "received_at": msg.timestamp,
            "extra": msg.extra,
        }
        if related_post_id:
            defaults["related_post_id"] = related_post_id

        obj, created = InboxMessage.objects.update_or_create(
            social_account=account,
            platform_message_id=msg.platform_message_id,
            defaults=defaults,
        )
        if created:
            obj.sentiment = analyze_sentiment(obj.body)
            obj.save(update_fields=["sentiment"])
            if notify:
                self._notify_new_message(obj)

    def _notify_new_message(self, message):
        """Send notification for a new inbox message."""
        if message.assigned_to:
            users = [message.assigned_to]
        else:
            memberships = WorkspaceMembership.objects.filter(
                workspace=message.workspace,
                workspace_role__in=["owner", "manager"],
            ).select_related("user")
            users = [m.user for m in memberships]

        for user in users:
            notify(
                user=user,
                event_type=EventType.NEW_INBOX_MESSAGE,
                title=f"New {message.get_message_type_display()} from {message.sender_name}",
                body=message.body[:200],
                data={
                    "message_id": str(message.id),
                    "workspace_id": str(message.workspace_id),
                },
            )

    def check_sla(self):
        """Check for SLA-overdue messages and send notifications."""
        from datetime import timedelta

        configs = InboxSLAConfig.objects.filter(is_active=True).select_related("workspace")

        for config in configs:
            threshold = timezone.now() - timedelta(minutes=config.target_response_minutes)
            overdue_messages = InboxMessage.objects.filter(
                workspace=config.workspace,
                status__in=[InboxMessage.Status.UNREAD, InboxMessage.Status.OPEN],
                received_at__lte=threshold,
            ).exclude(extra__has_key="sla_notified")

            for message in overdue_messages:
                self._notify_sla_overdue(message, config)
                message.extra["sla_notified"] = True
                message.save(update_fields=["extra"])

    def _notify_sla_overdue(self, message, config):
        """Notify about an SLA-overdue message."""
        if message.assigned_to:
            users = [message.assigned_to]
        else:
            memberships = WorkspaceMembership.objects.filter(
                workspace=message.workspace,
                workspace_role__in=["owner", "manager"],
            ).select_related("user")
            users = [m.user for m in memberships]

        for user in users:
            notify(
                user=user,
                event_type=EventType.INBOX_SLA_OVERDUE,
                title=f"SLA overdue: {message.get_message_type_display()} from {message.sender_name}",
                body=f"Response target of {config.target_response_minutes} minutes exceeded.",
                data={
                    "message_id": str(message.id),
                    "workspace_id": str(message.workspace_id),
                },
            )


# How often the recurring inbox-sync cycle runs; registered on a repeating
# schedule by apps.inbox.apps.InboxConfig. Polling is the always-on baseline
# documented in architecture.md (webhooks, where configured, supplement it).
INBOX_SYNC_INTERVAL_SECONDS = 5 * 60  # every 5 minutes


@background(schedule=0)
def run_inbox_sync_cycle():
    """Run one inbox cycle on the shared ``process_tasks`` worker (every deploy target).

    Delegates to ``InboxSyncEngine.run_cycle`` — the same entry point the
    ``run_inbox_sync`` management command uses — so the two never diverge.
    """
    InboxSyncEngine().run_cycle()
