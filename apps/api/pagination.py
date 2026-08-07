"""Opaque offset cursors shared by the REST list endpoints and the MCP list tools.

We encode an integer offset rather than a composite ``(value, id)`` tuple
because cursor stability across a reorder isn't a stated requirement, and
offset paginates correctly as long as the caller's ``order_by`` carries a
stable ``id`` tiebreak.

``decode_offset_cursor`` raises ``ValueError`` on a malformed cursor so each
surface can map it onto its own error shape — ``HttpError(422)`` for REST,
``JsonRpcError(INVALID_PARAMS)`` for MCP — without this module importing
either framework.
"""

from __future__ import annotations

import base64
import json


def encode_offset_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).rstrip(b"=").decode()


def decode_offset_cursor(cursor: str | None) -> int:
    """Return the offset encoded in ``cursor``; 0 when there is no cursor.

    Raises ``ValueError`` if the cursor isn't a base64 JSON object with a
    non-negative integer ``o``.
    """
    if not cursor:
        return 0
    if not isinstance(cursor, str):
        raise ValueError("Invalid cursor.")
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode() + b"==").decode())
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid cursor.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid cursor.")
    offset = payload.get("o", 0)
    # ``bool`` is an ``int`` subclass — reject it so ``{"o": true}`` isn't offset 1.
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("Invalid cursor.")
    return offset
