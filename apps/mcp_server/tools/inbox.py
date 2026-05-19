"""list_inbox, get_inbox_message, send_reply, add_internal_note, change_status, assign_message."""

from __future__ import annotations

from typing import Any

from django.db.models import Q

from apps.inbox import services as inbox_services
from apps.inbox.models import InboxMessage
from apps.members.models import WorkspaceMembership


def _serialize_message(msg: InboxMessage) -> dict[str, Any]:
    return {
        "id": str(msg.id),
        "social_account_id": str(msg.social_account_id),
        "platform": msg.social_account.platform if msg.social_account_id else None,
        "message_type": msg.message_type,
        "status": msg.status,
        "sentiment": msg.sentiment,
        "sender_name": msg.sender_name,
        "sender_handle": msg.sender_handle,
        "body": msg.body,
        "assigned_to_id": str(msg.assigned_to_id) if msg.assigned_to_id else None,
        "parent_message_id": str(msg.parent_message_id) if msg.parent_message_id else None,
        "related_post_id": str(msg.related_post_id) if msg.related_post_id else None,
        "received_at": msg.received_at.isoformat() if msg.received_at else None,
        "created_at": msg.created_at.isoformat(),
    }


def _serialize_message_full(msg: InboxMessage) -> dict[str, Any]:
    data = _serialize_message(msg)
    data["thread"] = []
    for reply in msg.replies.select_related("author").order_by("sent_at"):
        data["thread"].append(
            {
                "kind": "reply",
                "id": str(reply.id),
                "body": reply.body,
                "author_email": reply.author.email if reply.author_id else None,
                "platform_reply_id": reply.platform_reply_id,
                "sent_at": reply.sent_at.isoformat() if reply.sent_at else None,
            }
        )
    for note in msg.internal_notes.select_related("author").order_by("created_at"):
        data["thread"].append(
            {
                "kind": "note",
                "id": str(note.id),
                "body": note.body,
                "author_email": note.author.email if note.author_id else None,
                "created_at": note.created_at.isoformat(),
            }
        )
    data["thread"].sort(key=lambda x: x.get("sent_at") or x.get("created_at") or "")
    return data


def _get_message(ctx, message_id: str) -> InboxMessage:
    ws = ctx.require_workspace()
    msg = (
        InboxMessage.objects.filter(pk=message_id, workspace_id=ws.id)
        .select_related("social_account", "assigned_to")
        .first()
    )
    if msg is None:
        raise ValueError(f"InboxMessage {message_id} not found in current workspace.")
    return msg


def register(mcp, ctx):
    @mcp.tool()
    def list_inbox(
        status: str | None = None,
        sentiment: str | None = None,
        message_type: str | None = None,
        social_account_id: str | None = None,
        assigned_to_me: bool = False,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List inbox messages in the current workspace.

        Filters: status (unread|open|resolved|archived), sentiment (positive|neutral|negative),
        message_type (comment|mention|dm|review), social_account_id, assigned_to_me.
        """
        ctx.require_permission("use_inbox")
        ws = ctx.require_workspace()
        qs = InboxMessage.objects.filter(workspace_id=ws.id).select_related("social_account", "assigned_to")
        if status:
            qs = qs.filter(status=status)
        if sentiment:
            qs = qs.filter(sentiment=sentiment)
        if message_type:
            qs = qs.filter(message_type=message_type)
        if social_account_id:
            qs = qs.filter(social_account_id=social_account_id)
        if assigned_to_me:
            qs = qs.filter(assigned_to=ctx.user)
        if search:
            qs = qs.filter(Q(body__icontains=search) | Q(sender_name__icontains=search))
        qs = qs.order_by("-received_at", "-created_at")
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        total = qs.count()
        items = [_serialize_message(m) for m in qs[offset : offset + limit]]
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    @mcp.tool()
    def get_inbox_message(message_id: str) -> dict[str, Any]:
        """Return one inbox message with its full reply + internal-note thread."""
        ctx.require_permission("use_inbox")
        msg = _get_message(ctx, message_id)
        return _serialize_message_full(msg)

    @mcp.tool()
    def send_reply(message_id: str, body: str) -> dict[str, Any]:
        """Send a reply to an inbox message via the underlying platform."""
        ctx.require_permission("reply_from_inbox")
        msg = _get_message(ctx, message_id)
        reply = inbox_services.send_reply(message=msg, body=body, author=ctx.user)
        return {
            "id": str(reply.id),
            "message_id": str(msg.id),
            "platform_reply_id": reply.platform_reply_id,
            "message_status": msg.status,
        }

    @mcp.tool()
    def add_internal_note(message_id: str, body: str) -> dict[str, Any]:
        """Attach an internal note (team-only) to an inbox message."""
        ctx.require_permission("reply_from_inbox")
        msg = _get_message(ctx, message_id)
        note = inbox_services.add_internal_note(message=msg, body=body, author=ctx.user)
        return {"id": str(note.id), "message_id": str(msg.id)}

    @mcp.tool()
    def change_status(message_id: str, status: str) -> dict[str, Any]:
        """Set inbox message status: unread | open | resolved | archived."""
        ctx.require_permission("reply_from_inbox")
        valid = {c[0] for c in InboxMessage.Status.choices}
        if status not in valid:
            raise ValueError(f"Invalid status '{status}'. Valid: {sorted(valid)}")
        msg = _get_message(ctx, message_id)
        inbox_services.change_status(message=msg, status=status)
        return _serialize_message(msg)

    @mcp.tool()
    def assign_message(message_id: str, user_id: str | None = None) -> dict[str, Any]:
        """Assign an inbox message to a workspace member (or unassign with user_id=None)."""
        ctx.require_permission("reply_from_inbox")
        msg = _get_message(ctx, message_id)
        ws = ctx.require_workspace()
        assignee = None
        if user_id:
            membership = (
                WorkspaceMembership.objects.filter(workspace=ws, user_id=user_id).select_related("user").first()
            )
            if membership is None:
                raise ValueError(f"User {user_id} is not a member of this workspace.")
            assignee = membership.user
        inbox_services.assign_message(message=msg, assignee=assignee, actor=ctx.user)
        return _serialize_message(msg)
