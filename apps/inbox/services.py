"""Inbox service helpers.

Extracted from views so MCP tools (and any future REST or background path)
can perform the same operations as the web UI without redundantly
re-implementing provider calls, auto-status, and notification logic.
"""

from __future__ import annotations

import logging

from apps.notifications.engine import notify
from apps.notifications.models import EventType
from providers import get_provider

from .models import InboxMessage, InboxReply, InboxSLAConfig, InternalNote

logger = logging.getLogger(__name__)


def send_reply(*, message: InboxMessage, body: str, author) -> InboxReply:
    """Post a reply via the platform provider and persist InboxReply.

    Performs the same auto-status transitions as the web UI: respects
    InboxSLAConfig.auto_resolve_on_reply, else promotes unread → open.
    """
    account = message.social_account
    platform_reply_id = ""

    try:
        provider = get_provider(account.platform)
        result = provider.reply_to_message(
            access_token=account.oauth_access_token,
            message_id=message.platform_message_id,
            text=body,
            extra=message.extra,
        )
        platform_reply_id = result.platform_message_id
    except NotImplementedError:
        logger.info("Provider %s does not support reply_to_message.", account.platform)
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.exception("Network error sending reply for message %s: %s", message.id, exc)
    except Exception:
        logger.exception("Failed to send reply for message %s", message.id)

    reply = InboxReply.objects.create(
        inbox_message=message,
        author=author,
        body=body,
        platform_reply_id=platform_reply_id,
    )

    sla_config = InboxSLAConfig.objects.filter(workspace=message.workspace_id, is_active=True).first()
    if sla_config and sla_config.auto_resolve_on_reply:
        message.status = InboxMessage.Status.RESOLVED
        message.save(update_fields=["status"])
    elif message.status == InboxMessage.Status.UNREAD:
        message.status = InboxMessage.Status.OPEN
        message.save(update_fields=["status"])

    return reply


def add_internal_note(*, message: InboxMessage, body: str, author) -> InternalNote:
    return InternalNote.objects.create(inbox_message=message, author=author, body=body)


def assign_message(*, message: InboxMessage, assignee, actor) -> InboxMessage:
    """Assign or unassign a message. `assignee` may be None to clear.

    Notifies the assignee unless they are the actor.
    """
    message.assigned_to = assignee
    message.save(update_fields=["assigned_to"])

    if assignee and assignee != actor:
        notify(
            user=assignee,
            event_type=EventType.NEW_INBOX_MESSAGE,
            title=f"You were assigned a {message.get_message_type_display()}",
            body=f"From {message.sender_name}: {message.body[:100]}",
            data={
                "message_id": str(message.id),
                "workspace_id": str(message.workspace_id),
            },
        )
    return message


def change_status(*, message: InboxMessage, status: str) -> InboxMessage:
    message.status = status
    message.save(update_fields=["status"])
    return message
