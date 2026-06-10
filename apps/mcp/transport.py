"""Streamable HTTP MCP transport, mounted at ``/api/v1/mcp/`` by
``apps/api/api.py``.

Auth piggy-backs on the same ``ApiKeyAuth`` the REST surface uses, so
every MCP request carries a ``Authorization: Bearer bb_studio_...``
header — one credential surface, one audit trail, one revocation path.

For v1 we only implement the POST direction (client → server requests
and notifications). The spec's GET-with-SSE direction (server →
client) is unused because none of our tools need to stream progress
or send unsolicited messages.
"""

from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import Router

from apps.api.limits import enforce_http_rate_limits
from apps.api.middleware import log_audit_entry
from apps.mcp.protocol import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    MCP_PROTOCOL_VERSION,
    PARSE_ERROR,
    SERVER_NAME,
    SERVER_VERSION,
    JsonRpcError,
    dispatch,
    make_error,
)
from apps.mcp.tools import all_tools, get_tool

router = Router(tags=["mcp"])


# ---------------------------------------------------------------------------
# Built-in methods (initialize, ping, tools/list, tools/call)
# ---------------------------------------------------------------------------


def _initialize(params: dict, context: dict[str, Any]) -> dict:
    """MCP handshake.

    The client sends its ``protocolVersion`` and ``capabilities``; we
    reply with ours plus ``serverInfo``. We don't return a
    ``Mcp-Session-Id`` because our bearer token already identifies the
    session — every authenticated request stands on its own.
    """
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            # Static tool catalog; we don't send listChanged notifications.
            "tools": {"listChanged": False},
        },
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def _initialized(params: dict, context: dict[str, Any]) -> None:
    """Notification — no reply, just acknowledge boot completion."""
    return None


def _ping(params: dict, context: dict[str, Any]) -> dict:
    """Keepalive / liveness probe per the MCP spec."""
    return {}


def _tools_list(params: dict, context: dict[str, Any]) -> dict:
    return {"tools": [t.to_mcp_dict() for t in all_tools()]}


def _tools_call(params: dict, context: dict[str, Any]) -> dict:
    name = params.get("name")
    if not isinstance(name, str):
        raise JsonRpcError(INVALID_PARAMS, "tools/call: 'name' is required")
    tool = get_tool(name)
    if tool is None:
        raise JsonRpcError(INVALID_PARAMS, f"tools/call: unknown tool '{name}'")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, dict):
        raise JsonRpcError(INVALID_PARAMS, "tools/call: 'arguments' must be an object")
    # Validate against the tool's published ``inputSchema``. The schema
    # we advertise via ``tools/list`` is the contract clients see —
    # without this check it was a polite suggestion only, and clients
    # could pass e.g. ``caption: {"x": 1}`` (a dict where a string was
    # required) and reach the handler with a type mismatch. ``jsonschema``
    # is already a transitive dependency, so no new package is needed.
    try:
        _validate_tool_arguments(tool.input_schema, arguments)
    except _ToolValidationError as exc:
        raise JsonRpcError(INVALID_PARAMS, f"tools/call '{name}': {exc}") from exc
    return tool.handler(arguments, context)


class _ToolValidationError(ValueError):
    """Raised when a tool's arguments don't conform to its inputSchema."""


def _validate_tool_arguments(schema: dict, arguments: dict) -> None:
    """Enforce the tool's published ``inputSchema`` against ``arguments``.

    Uses ``jsonschema`` (already pulled in transitively). We raise our
    own ``_ToolValidationError`` rather than letting the library's
    ``ValidationError`` escape so the JSON-RPC dispatcher receives a
    plain ValueError, and the error message we hand to the client is
    short and human-readable rather than a multi-line stack trace.
    """
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError as _JsonSchemaValidationError

    try:
        Draft202012Validator(schema).validate(arguments)
    except _JsonSchemaValidationError as exc:
        # ``exc.path`` is a deque of the failing JSON pointer; render
        # it as "field.nested" for a friendly message.
        location = ".".join(str(p) for p in exc.path) or "(root)"
        raise _ToolValidationError(f"{location}: {exc.message}") from exc


METHODS = {
    "initialize": _initialize,
    "notifications/initialized": _initialized,
    "ping": _ping,
    "tools/list": _tools_list,
    "tools/call": _tools_call,
}


# ---------------------------------------------------------------------------
# Transport — single POST endpoint
# ---------------------------------------------------------------------------


# The no-slash alias matters: the RFC 9728 metadata and the README both
# advertise ``/api/v1/mcp``, and a bare ``@router.post("/")`` would leave that
# URL to CommonMiddleware's APPEND_SLASH 301 — which HTTP clients follow as a
# GET, killing the MCP handshake before the 401 challenge is ever issued.
@router.post("", include_in_schema=False)
@router.post(
    "/",
    summary="MCP Streamable HTTP endpoint (JSON-RPC over POST)",
)
def mcp_endpoint(request: HttpRequest):
    """One endpoint handles single requests, notifications, and batches.

    Per the JSON-RPC 2.0 spec:
      * Body is either an object (single message) or an array (batch).
      * Notifications get no response — we return 202 Accepted with an
        empty body when every message in the input was a notification.
      * Otherwise we return 200 with the response JSON (object or array
        matching the request shape).

    Rate limiting is charged per JSON-RPC message, not per HTTP request,
    so a batch of N messages costs N tokens. We defer the
    ``enforce_http_rate_limits`` call until we know whether the body is
    a single message (charge once) or a batch (charge per element).
    Charging both up-front AND per-message would over-bill batches by
    one token, as Codex review flagged.
    """
    context: dict[str, Any] = {
        "api_key": request.api_key,  # type: ignore[attr-defined]  # set by ApiKeyAuth
        "workspace": request.workspace,  # type: ignore[attr-defined]
        "membership": request.workspace_membership,  # type: ignore[attr-defined]
        "request": request,
    }

    try:
        body = json.loads(request.body or b"null")
    except json.JSONDecodeError:
        # Charge the bad-request as one HTTP-tier hit so a flood of
        # malformed bodies still trips the throttle.
        enforce_http_rate_limits(request, is_write=True)
        return JsonResponse(make_error(None, PARSE_ERROR, "Invalid JSON"), status=400)

    # Batch.
    if isinstance(body, list):
        if not body:
            enforce_http_rate_limits(request, is_write=True)
            return JsonResponse(make_error(None, INVALID_REQUEST, "Empty batch"), status=400)
        responses = []
        for msg in body:
            # One rate-limit charge per JSON-RPC message — agents that
            # batch 100 calls into one HTTP request still consume 100
            # tokens, exactly as if they had sent 100 separate POSTs.
            enforce_http_rate_limits(request, is_write=True)
            r = dispatch(msg, context, METHODS)
            # Codex fix: always audit, even notifications (r is None),
            # and derive the status code from the dispatch envelope so
            # JSON-RPC errors don't masquerade as successes in the log.
            audit_status = _status_for_response(r)
            _log_mcp_audit(request, msg, status_code=audit_status)
            if r is not None:
                responses.append(r)
        if not responses:
            return HttpResponse(status=202)
        return JsonResponse(responses, safe=False, status=200)

    # Single message.
    if isinstance(body, dict):
        enforce_http_rate_limits(request, is_write=True)
        response = dispatch(body, context, METHODS)
        audit_status = _status_for_response(response)
        _log_mcp_audit(request, body, status_code=audit_status)
        if response is None:
            # Notification — fire-and-forget per JSON-RPC.
            return HttpResponse(status=202)
        return JsonResponse(response, status=200)

    enforce_http_rate_limits(request, is_write=True)
    return JsonResponse(
        make_error(None, INVALID_REQUEST, "Body must be a JSON object or array"),
        status=400,
    )


def _status_for_response(response: dict | None) -> int:
    """Pick the audit-log status code that reflects what actually happened.

    Codex review found that the previous code hardcoded ``200`` for every
    dispatched message — JSON-RPC errors travel inside HTTP 200, so the
    audit log silently lost the distinction between success and failure.
    We instead derive a synthetic status from the envelope:

    * ``None`` → notification → ``202 Accepted`` (no reply, but the
      message was received and processed).
    * envelope contains ``error`` → use a 4xx that roughly matches the
      JSON-RPC error code so a forensic query like
      ``WHERE status_code != 200`` actually finds failures.
    * otherwise → ``200`` (real success).
    """
    if response is None:
        return 202
    if not isinstance(response, dict):
        return 200
    err = response.get("error")
    if not isinstance(err, dict):
        return 200
    code = err.get("code")
    # JSON-RPC codes are mostly negative; map the conventional ones
    # to an approximate HTTP code so they're searchable. ``code`` arrives
    # via JSON parsing so it may be any type; coerce to int (or use the
    # 400 default) before the dict lookup.
    if not isinstance(code, int):
        return 400
    return {
        -32700: 400,  # parse error
        -32600: 400,  # invalid request
        -32601: 404,  # method not found
        -32602: 422,  # invalid params
        -32603: 500,  # internal error
    }.get(code, 400)


def _log_mcp_audit(request: HttpRequest, msg: dict, *, status_code: int) -> None:
    """Translate an MCP method into a coarse audit-log action label.

    For ``tools/call`` we drill in to ``params.name`` so a forensic
    review can tell ``list_accounts`` from ``schedule_post`` without
    digging into request bodies (which we deliberately don't store).
    """
    method = msg.get("method", "unknown") if isinstance(msg, dict) else "unknown"
    action = f"mcp.{method}"
    if method == "tools/call":
        tool_name = ((msg.get("params") or {}) if isinstance(msg, dict) else {}).get("name")
        if isinstance(tool_name, str):
            action = f"mcp.tools/call:{tool_name}"
    log_audit_entry(request, action=action, target_id=None, status_code=status_code)
