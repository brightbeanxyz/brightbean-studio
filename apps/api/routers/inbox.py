"""``/api/v1/inbox/*`` — read inbox messages and draft / send replies.

The inbox equivalent of :mod:`apps.api.routers.posts`: every route is a
thin adapter over :mod:`apps.inbox.services`, the single source of truth
shared with the HTMX views and the MCP inbox tools. Message and reply
lookups are scoped to the key's workspace **and** its account allowlist,
returning 404 (never 403) for anything outside it so a partial-scope key
can't probe foreign IDs.

Permissions mirror the web inbox: ``use_inbox`` to read and to manage
drafts, ``reply_from_inbox`` to actually deliver a reply to the platform.
"""

from __future__ import annotations

import uuid

from django.db.models import QuerySet
from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError

from apps.api.limits import enforce_http_rate_limits
from apps.api.middleware import (
    claim_idempotency_slot,
    finalize_idempotent_response,
    fingerprint_request,
    log_audit_entry,
    release_idempotent_claim,
)
from apps.api.pagination import decode_offset_cursor, encode_offset_cursor
from apps.api.schemas import (
    CreateReplyRequest,
    InboxMessageResponse,
    InboxMessagesListResponse,
    InboxReplyResponse,
    UpdateReplyRequest,
)
from apps.inbox.models import InboxMessage, InboxReply
from apps.inbox.services import (
    ReplyStateError,
    create_reply_draft,
    discard_reply_draft,
    send_reply_now,
    update_reply_draft,
)

router = Router(tags=["inbox"])

_LIMIT_DEFAULT = 50
_LIMIT_MAX = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_perm(request: HttpRequest, key: str) -> None:
    membership = getattr(request, "workspace_membership", None)
    if membership is None or not membership.effective_permissions.get(key, False):
        raise HttpError(403, f"Permission denied: {key}")


def _allowlisted_account_ids(request: HttpRequest) -> set[uuid.UUID]:
    return {sa.id for sa in request.api_key.social_accounts.all()}  # type: ignore[attr-defined]


def _visible_messages_qs(request: HttpRequest) -> QuerySet[InboxMessage]:
    """Messages in the key's workspace whose account is in the allowlist."""
    return InboxMessage.objects.filter(
        workspace_id=request.api_key.workspace_id,  # type: ignore[attr-defined]
        social_account_id__in=_allowlisted_account_ids(request),
    ).select_related("social_account")


def _get_message(request: HttpRequest, message_id: uuid.UUID) -> InboxMessage:
    return get_object_or_404(_visible_messages_qs(request), id=message_id)


def _get_reply(request: HttpRequest, reply_id: uuid.UUID) -> InboxReply:
    reply = get_object_or_404(
        InboxReply.objects.select_related("inbox_message", "inbox_message__social_account", "author"),
        id=reply_id,
        inbox_message__workspace_id=request.api_key.workspace_id,  # type: ignore[attr-defined]
    )
    if reply.inbox_message.social_account_id not in _allowlisted_account_ids(request):
        raise Http404()
    return reply


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response=InboxMessagesListResponse, summary="List inbox messages")
def list_messages(
    request,
    status: str | None = Query(None),
    message_type: str | None = Query(None),
    social_account_id: uuid.UUID | None = Query(None),
    limit: int = Query(_LIMIT_DEFAULT, ge=1, le=_LIMIT_MAX),
    cursor: str | None = Query(None),
):
    enforce_http_rate_limits(request, is_write=False)
    _require_perm(request, "use_inbox")

    if status is not None and status not in InboxMessage.Status.values:
        raise HttpError(422, f"status must be one of {', '.join(InboxMessage.Status.values)}")
    if message_type is not None and message_type not in InboxMessage.MessageType.values:
        raise HttpError(422, f"message_type must be one of {', '.join(InboxMessage.MessageType.values)}")

    try:
        offset = decode_offset_cursor(cursor)
    except ValueError as exc:
        raise HttpError(422, "cursor is not a valid pagination cursor") from exc

    qs = _visible_messages_qs(request).prefetch_related("replies__author")
    if status:
        qs = qs.filter(status=status)
    if message_type:
        qs = qs.filter(message_type=message_type)
    if social_account_id is not None:
        if social_account_id not in _allowlisted_account_ids(request):
            raise HttpError(403, "social_account_id is not in this key's allowlist.")
        qs = qs.filter(social_account_id=social_account_id)
    qs = qs.order_by("-received_at", "id")

    rows = list(qs[offset : offset + limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    log_audit_entry(request, action="inbox.list", target_id=None, status_code=200)
    return InboxMessagesListResponse(
        messages=[InboxMessageResponse.from_message(m, include_replies=True) for m in rows],
        limit=limit,
        next_cursor=encode_offset_cursor(offset + limit) if has_more else None,
    )


@router.get("/{message_id}", response=InboxMessageResponse, summary="Read one inbox message")
def retrieve_message(request, message_id: uuid.UUID):
    enforce_http_rate_limits(request, is_write=False)
    _require_perm(request, "use_inbox")
    message = _get_message(request, message_id)
    log_audit_entry(request, action="inbox.read", target_id=message.id, status_code=200)
    return InboxMessageResponse.from_message(message, include_replies=True)


@router.post(
    "/{message_id}/replies",
    response={201: InboxReplyResponse},
    summary="Create a draft reply (optionally send it)",
)
def create_reply(request, message_id: uuid.UUID, payload: CreateReplyRequest):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "use_inbox")
    if payload.send:
        _require_perm(request, "reply_from_inbox")

    message = _get_message(request, message_id)
    idempotency_key = payload.idempotency_key or request.headers.get("Idempotency-Key") or None
    fingerprint = fingerprint_request(request.method or "POST", request.path, payload.model_dump(mode="json"))
    try:
        disposition, replay_status, replay_body = claim_idempotency_slot(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
    if disposition == "replay":
        assert replay_status is not None and replay_body is not None
        if replay_status >= 400:
            raise HttpError(replay_status, replay_body["detail"])
        return replay_status, replay_body
    if disposition == "in_flight":
        raise HttpError(409, "An identical request with this idempotency_key is still in flight; retry shortly.")

    try:
        reply = create_reply_draft(
            message=message,
            body=payload.body,
            author=request.user if not request.user.is_anonymous else None,
        )
    except ValueError as exc:
        release_idempotent_claim(api_key=request.api_key, idempotency_key=idempotency_key)
        raise HttpError(422, str(exc)) from exc
    except Exception:
        release_idempotent_claim(api_key=request.api_key, idempotency_key=idempotency_key)
        raise

    # Once a draft exists, retain the claim even on failure: replaying a
    # create-and-send request must never create another reply or send twice.
    try:
        if payload.send:
            try:
                send_reply_now(reply, actor=request.user if not request.user.is_anonymous else None)
            except ReplyStateError as exc:
                raise HttpError(409, str(exc)) from exc
            except Exception as exc:  # platform refused it — reply is left in "failed"
                raise HttpError(502, f"Reply not sent: {reply.send_error or 'Please try again later.'}") from exc

        body = InboxReplyResponse.from_reply(reply)
        log_audit_entry(request, action="inbox.reply.create", target_id=reply.id, status_code=201)
        finalize_idempotent_response(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            status_code=201,
            body=body.model_dump(mode="json"),
        )
        return 201, body
    except HttpError as exc:
        finalize_idempotent_response(
            api_key=request.api_key,
            idempotency_key=idempotency_key,
            status_code=exc.status_code,
            body={"detail": exc.message},
        )
        raise


@router.patch("/replies/{reply_id}", response=InboxReplyResponse, summary="Edit a draft reply")
def update_reply(request, reply_id: uuid.UUID, payload: UpdateReplyRequest):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "use_inbox")
    reply = _get_reply(request, reply_id)
    try:
        update_reply_draft(reply, body=payload.body)
    except ReplyStateError as exc:
        raise HttpError(409, str(exc)) from exc
    except ValueError as exc:
        raise HttpError(422, str(exc)) from exc
    log_audit_entry(request, action="inbox.reply.update", target_id=reply.id, status_code=200)
    return InboxReplyResponse.from_reply(reply)


@router.post("/replies/{reply_id}/send", response=InboxReplyResponse, summary="Send a draft reply")
def send_reply(request, reply_id: uuid.UUID):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "reply_from_inbox")
    reply = _get_reply(request, reply_id)
    try:
        send_reply_now(reply, actor=request.user if not request.user.is_anonymous else None)
    except ReplyStateError as exc:
        raise HttpError(409, str(exc)) from exc
    except Exception as exc:
        raise HttpError(502, f"Reply not sent: {reply.send_error or 'Please try again later.'}") from exc
    log_audit_entry(request, action="inbox.reply.send", target_id=reply.id, status_code=200)
    return InboxReplyResponse.from_reply(reply)


@router.delete("/replies/{reply_id}", response={204: None}, summary="Discard a draft reply")
def delete_reply(request, reply_id: uuid.UUID):
    enforce_http_rate_limits(request, is_write=True)
    _require_perm(request, "use_inbox")
    reply = _get_reply(request, reply_id)
    try:
        discard_reply_draft(reply)
    except ReplyStateError as exc:
        raise HttpError(409, str(exc)) from exc
    log_audit_entry(request, action="inbox.reply.discard", target_id=reply_id, status_code=204)
    return 204, None
