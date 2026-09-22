"""Service layer for the Unified Social Inbox (F-3.1).

Both the HTMX views and the programmatic surfaces (the ``/api/v1/inbox``
REST router and the MCP inbox tools) go through these functions so the
three can't drift — the same rule the composer follows with
``apps.composer.services``.

A reply now has a lifecycle: it is created as a ``draft``, then a separate
send step delivers it to the platform and moves it to ``sent`` (or
``failed`` if the platform refused it). The platform-dispatch logic used
to live in ``apps/inbox/views.py``; it moved here verbatim.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from providers import get_provider

from .models import InboxMessage, InboxReply, InboxSLAConfig

logger = logging.getLogger(__name__)

# Message types answered on a comment edge rather than a messaging endpoint.
_COMMENT_LIKE_TYPES = {
    InboxMessage.MessageType.COMMENT,
    InboxMessage.MessageType.MENTION,
    InboxMessage.MessageType.REVIEW,
}

# Past this age Meta only accepts a reply tagged as written by a person.
HUMAN_AGENT_AFTER = timedelta(hours=24)

# States a reply can be sent (or re-sent) from.
_SENDABLE_STATUSES = {InboxReply.Status.DRAFT, InboxReply.Status.FAILED}


class ReplyStateError(ValueError):
    """Raised when an operation is not valid for a reply's current status."""


# ---------------------------------------------------------------------------
# Platform dispatch (moved from views.py, behaviour unchanged)
# ---------------------------------------------------------------------------


def reply_failure_reason(exc: Exception) -> str:
    """A short, actionable reason for the user.

    The platform's own error text carries internal diagnostics (trace IDs,
    raw API JSON) that mean nothing to a workspace member, so it stays in
    the log and the UI/API gets a stable sentence instead.
    """
    from providers.exceptions import OAuthError, RateLimitError, TokenExpiredError

    if isinstance(exc, RateLimitError):
        return "the account has hit its rate limit. Wait a few minutes and try again."
    if isinstance(exc, TokenExpiredError | OAuthError):
        return "the connection has expired. Reconnect the account in Workspace Settings."
    return "the platform rejected it. Try again, or reconnect the account if this keeps happening."


def _dispatch_to_platform(message: InboxMessage, body: str) -> str:
    """Post ``body`` back to the platform and return the platform's reply ID.

    Raises if the platform refuses it, so the caller can avoid recording a
    reply as delivered when it never was.
    """
    from apps.publisher.engine import _resolve_publish_credentials

    account = message.social_account
    provider = get_provider(account.platform, _resolve_publish_credentials(account))

    # The messaging endpoints address a person, not a message, so carry the
    # sender's platform-scoped ID alongside the original payload.
    extra = dict(message.extra or {})
    if message.sender_handle:
        extra.setdefault("recipient_id", message.sender_handle)

    if message.message_type in _COMMENT_LIKE_TYPES:
        result = provider.reply_to_comment(
            access_token=account.oauth_access_token,
            comment_id=message.platform_message_id,
            text=body,
            extra=extra,
        )
    else:
        overdue = timezone.now() - message.received_at > HUMAN_AGENT_AFTER
        result = provider.reply_to_message(
            access_token=account.oauth_access_token,
            message_id=message.platform_message_id,
            text=body,
            extra=extra,
            human_agent=overdue,
        )

    return result.platform_message_id


def _apply_post_send_side_effects(message: InboxMessage) -> None:
    """Resolve or open the message after a reply goes out, per SLA config."""
    sla_config = InboxSLAConfig.objects.filter(workspace=message.workspace, is_active=True).first()
    if sla_config and sla_config.auto_resolve_on_reply:
        if message.status != InboxMessage.Status.RESOLVED:
            message.status = InboxMessage.Status.RESOLVED
            message.save(update_fields=["status"])
    elif message.status == InboxMessage.Status.UNREAD:
        message.status = InboxMessage.Status.OPEN
        message.save(update_fields=["status"])


# ---------------------------------------------------------------------------
# Draft lifecycle
# ---------------------------------------------------------------------------


def create_reply_draft(*, message: InboxMessage, body: str, author=None) -> InboxReply:
    """Create a ``draft`` reply against ``message``. Not sent anywhere."""
    body = (body or "").strip()
    if not body:
        raise ValueError("Reply body cannot be empty.")
    return InboxReply.objects.create(
        inbox_message=message,
        author=author,
        body=body,
        status=InboxReply.Status.DRAFT,
    )


def _lock_reply(reply: InboxReply) -> None:
    """Refresh the caller's instance while locking the row for this transaction."""
    try:
        reply.refresh_from_db(from_queryset=InboxReply.objects.select_for_update())
    except InboxReply.DoesNotExist as exc:
        raise ReplyStateError("This reply has been discarded.") from exc


@transaction.atomic
def update_reply_draft(reply: InboxReply, *, body: str) -> InboxReply:
    """Edit a draft (or failed) reply's body."""
    _lock_reply(reply)
    if reply.status not in _SENDABLE_STATUSES:
        raise ReplyStateError(f"A {reply.get_status_display().lower()} reply cannot be edited.")
    body = (body or "").strip()
    if not body:
        raise ValueError("Reply body cannot be empty.")
    reply.body = body
    reply.save(update_fields=["body", "updated_at"])
    return reply


@transaction.atomic
def discard_reply_draft(reply: InboxReply) -> None:
    """Delete a draft (or failed) reply. Sent replies are permanent."""
    _lock_reply(reply)
    if reply.status not in _SENDABLE_STATUSES:
        raise ReplyStateError(f"A {reply.get_status_display().lower()} reply cannot be discarded.")
    reply.delete()


def send_reply_now(reply: InboxReply, *, actor=None) -> InboxReply:
    """Deliver an existing draft/failed reply to the platform.

    On a platform refusal the row is kept and moved to ``failed`` with a
    human-readable ``send_error`` so the team can retry; the underlying
    exception is re-raised for the caller to shape into its own error.
    ``NotImplementedError`` (provider has no reply API) is not a failure —
    the reply is recorded locally with an empty ``platform_reply_id``,
    matching the pre-existing behaviour.
    """
    failure = None
    with transaction.atomic():
        # Keep the lock through delivery and persistence. Every competing send,
        # edit or discard must check the latest state after acquiring this lock.
        _lock_reply(reply)
        if reply.status not in _SENDABLE_STATUSES:
            raise ReplyStateError(f"A {reply.get_status_display().lower()} reply cannot be sent again.")

        message = reply.inbox_message
        if actor is not None and reply.author_id is None:
            reply.author = actor

        try:
            platform_reply_id = _dispatch_to_platform(message, reply.body)
        except NotImplementedError:
            logger.info(
                "Provider %s cannot send replies; recording reply %s locally.",
                message.social_account.platform,
                reply.id,
            )
            platform_reply_id = ""
        except Exception as exc:
            logger.exception("Failed to send inbox reply %s (%s)", reply.id, message.social_account.platform)
            reply.status = InboxReply.Status.FAILED
            reply.send_error = reply_failure_reason(exc)
            reply.save(update_fields=["status", "send_error", "author", "updated_at"])
            failure = exc

        if failure is None:
            reply.status = InboxReply.Status.SENT
            reply.platform_reply_id = platform_reply_id
            reply.send_error = ""
            reply.sent_at = timezone.now()
            reply.save(update_fields=["status", "platform_reply_id", "send_error", "sent_at", "author", "updated_at"])

    # Raising inside atomic would roll back the failed status and its reason.
    if failure is not None:
        raise failure
    # SLA bookkeeping must not roll back a reply already delivered externally.
    try:
        _apply_post_send_side_effects(message)
    except Exception:
        logger.exception("Inbox reply %s was sent, but updating the message status failed", reply.id)
    return reply


def send_reply(*, message: InboxMessage, body: str, author=None) -> InboxReply:
    """Create a reply and send it in one step (the classic composer flow).

    If the platform refuses it, the ``failed`` row is removed and the
    exception propagates — the thread must never show a reply the customer
    never received. ``NotImplementedError`` keeps the local record.
    """
    with transaction.atomic():
        reply = create_reply_draft(message=message, body=body, author=author)
    try:
        return send_reply_now(reply, actor=author)
    except Exception:
        InboxReply.objects.filter(pk=reply.pk, status=InboxReply.Status.FAILED).delete()
        raise
