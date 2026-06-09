"""JSON-RPC 2.0 / MCP protocol primitives.

We implement just enough of the spec to serve the Brightbean Studio
tool surface over the Streamable HTTP transport. The bits we *don't*
implement (and don't need for v1):

* SSE streaming responses — every tool call is a single synchronous
  JSON reply. We can upgrade individual handlers to streaming later
  without changing the transport contract.
* Server-initiated requests (GET endpoint) — no need until we add
  sampling or progress notifications.
* Sessions — our bearer token IS the session; clients carry it in the
  ``Authorization`` header, so ``Mcp-Session-Id`` adds no value.
* Resources, prompts, sampling — tools-only catalog for v1.

The reason for rolling our own rather than depending on the official
``mcp`` SDK: the SDK's HTTP transport assumes Starlette/ASGI, and the
Brightbean app is WSGI on Django + Ninja. Re-implementing the small
JSON-RPC core keeps dependencies and abstractions to a minimum.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

#: Wire protocol revision we implement. The official MCP versions are
#: date-stamped; the 2025-03-26 revision is what most current clients
#: target. Server-side we accept any client revision and always reply
#: with this one — newer clients gracefully degrade.
MCP_PROTOCOL_VERSION = "2025-03-26"

SERVER_NAME = "brightbean-studio"
SERVER_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

#: Standard JSON-RPC 2.0 error codes. Application-specific errors live
#: above -32000 per the spec, but we keep all four std codes for clarity.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class JsonRpcError(Exception):
    """Raised inside a handler to translate into a JSON-RPC error envelope.

    Handlers raise this for any user-facing failure (bad params,
    permission denied, resource not found). The dispatcher catches it
    and emits a properly-shaped ``{"error": {...}}`` response with the
    request's ``id`` preserved.
    """

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------


def make_response(id_: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def make_error(id_: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def is_notification(msg: dict) -> bool:
    """JSON-RPC: requests without ``id`` are notifications (no response).

    Note the spec quirk: ``id`` may legitimately be ``null``, so we
    check for *presence* of the key, not truthiness.
    """
    return "id" not in msg


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def dispatch(
    msg: Any,
    context: Any,
    # Using ``Mapping`` (covariant in the value type) rather than ``dict``
    # so callers can pass narrower handler signatures than ``(dict, Any) -> Any``
    # without mypy invariance errors. Every concrete handler returns either
    # ``dict`` or ``None`` and only reads from ``context``.
    methods: Mapping[str, Callable[[dict, Any], Any]],
) -> dict | None:
    """Route one JSON-RPC message to its handler.

    Returns:
      * a response envelope (success or error) for requests
      * ``None`` for notifications — per JSON-RPC, notifications never
        get a reply, even on failure

    The handler signature is ``(params: dict, context: Any) -> result``.
    Handlers may raise ``JsonRpcError`` for user-facing failures; any
    other exception becomes a generic ``INTERNAL_ERROR`` so we don't
    leak Python tracebacks to clients.
    """
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return make_error(None, INVALID_REQUEST, "Not a valid JSON-RPC 2.0 message")
    method = msg.get("method")
    if not isinstance(method, str):
        return make_error(msg.get("id"), INVALID_REQUEST, "Missing 'method'")
    params = msg.get("params") or {}
    if not isinstance(params, dict):
        return make_error(msg.get("id"), INVALID_PARAMS, "'params' must be an object")

    import contextlib

    handler = methods.get(method)
    if is_notification(msg):
        # No reply allowed regardless of outcome — fire-and-forget. No
        # channel exists to surface a notification-handler failure on,
        # so any exception is intentionally suppressed.
        if handler is not None:
            with contextlib.suppress(Exception):
                handler(params, context)
        return None

    if handler is None:
        return make_error(msg["id"], METHOD_NOT_FOUND, f"Method '{method}' not found")
    try:
        result = handler(params, context)
        return make_response(msg["id"], result)
    except JsonRpcError as exc:
        return make_error(msg["id"], exc.code, exc.message, exc.data)
    except Exception as exc:  # noqa: BLE001 — last-ditch
        # Don't leak internals to clients; log for ops.
        import logging

        logging.getLogger(__name__).exception("MCP handler '%s' raised", method)
        return make_error(msg["id"], INTERNAL_ERROR, str(exc))
