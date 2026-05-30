"""NinjaAPI instance for the Agent API.

Lives at ``/api/v1/`` (mounted in ``config/urls.py``). All routes are
behind ``ApiKeyAuth`` — there is no anonymous surface here, not even
``/me``: a bearer is required to learn anything about the workspace.

OpenAPI docs render at ``/api/v1/docs`` (Ninja's default).
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import NinjaAPI
from ninja.errors import HttpError

from apps.api.auth import ApiKeyAuth
from apps.api.routers.accounts import router as accounts_router
from apps.api.routers.me import router as me_router
from apps.api.routers.posts import router as posts_router
from apps.mcp.transport import router as mcp_router

api = NinjaAPI(
    title="Brightbean Agent API",
    version="1.0.0",
    description=(
        "Programmatic access for external AI agents. Authentication is via "
        "scoped bearer tokens; create one from the Organization → API Keys "
        "page in the Brightbean Studio settings."
    ),
    auth=ApiKeyAuth(),
    # Trailing slashes are tolerated by the router but we use the
    # explicit-slash form everywhere internally for OpenAPI clarity.
    urls_namespace="agent_api_v1",
    # CSRF is off by default in Ninja for stateless APIs. Our bearer
    # auth means no session cookie is involved, so CSRF doesn't apply.
)

api.add_router("/me", me_router)
api.add_router("/accounts", accounts_router)
api.add_router("/posts", posts_router)
# MCP Streamable HTTP transport. Same auth, same audit, same rate
# limits — only the wire protocol differs.
api.add_router("/mcp", mcp_router)


# ---------------------------------------------------------------------------
# Error envelopes — convert Ninja's plain-text 4xx/5xx into the structured
# error shape so agents can parse ``tier``, ``retry_after``, etc. without
# string scraping.
# ---------------------------------------------------------------------------


@api.exception_handler(HttpError)
def _http_error_handler(request: HttpRequest, exc: HttpError) -> HttpResponse:
    body, headers = _parse_quota_message(exc.message) if exc.status_code == 429 else (
        {"error": _slug_for(exc.status_code), "detail": exc.message},
        {},
    )
    response = JsonResponse(body, status=exc.status_code)
    for k, v in headers.items():
        response[k] = v
    _audit_failed_request(request, status_code=exc.status_code)
    return response


# Catch ``Http404`` separately so allowlist-blocked / not-found probes
# also produce an audit row AND a uniform error envelope (the default
# Ninja handler emits ``{"detail": "Not Found"}``, which diverges from
# our ``{"error": "...", "detail": "..."}`` shape).
from django.http import Http404  # noqa: E402 — keep with the handler


@api.exception_handler(Http404)
def _not_found_handler(request: HttpRequest, exc: Http404) -> HttpResponse:
    _audit_failed_request(request, status_code=404)
    return JsonResponse({"error": "not_found", "detail": "Not found."}, status=404)


def _audit_failed_request(request: HttpRequest, *, status_code: int) -> None:
    """Write one audit row for an authenticated failure.

    Codex review flagged that the per-route ``log_audit_entry`` calls
    only fire on the success exit; every 403/404/422/429 raised before
    the success line wrote nothing, so an authenticated key probing
    foreign Post UUIDs left zero forensic trail. Centralising audit
    for failures here closes that gap without duplicating per-route
    code.

    The audit-log helper itself short-circuits when ``request.api_key``
    is missing (anonymous or pre-auth path), so pre-auth 4xx like the
    HTTPS guard or 401 do NOT produce audit rows — those are tracked
    by the IP-failed-auth throttle counter instead.
    """
    # Lazy-import here to keep ``apps.api.api`` light: this handler is
    # only reached on the slow (error) path.
    from apps.api.middleware import log_audit_entry

    # Action label: derive a coarse verb from the URL so the audit
    # query language stays consistent with the success-path rows
    # (``post.create``, ``post.read`` etc.). The path-based fallback
    # is good enough for forensic review.
    path = request.path or ""
    action = _action_for_path(request.method or "GET", path, status_code=status_code)
    log_audit_entry(request, action=action, target_id=None, status_code=status_code)


def _action_for_path(method: str, path: str, *, status_code: int) -> str:
    """Map (method, path) → a short audit-action label for failures.

    Mirrors the labels used on success paths so a forensic query like
    ``WHERE action LIKE 'post.%'`` catches both successes and 4xx.
    """
    # Order matters: longer prefixes first.
    if "/posts/" in path:
        if path.endswith("/schedule"):
            return f"post.schedule.{status_code}"
        if path.endswith("/cancel"):
            return f"post.cancel.{status_code}"
        if method == "POST":
            return f"post.create.{status_code}"
        if method == "GET":
            return f"post.read.{status_code}"
        if method == "PATCH":
            return f"post.update.{status_code}"
    if "/mcp" in path:
        return f"mcp.error.{status_code}"
    if "/accounts" in path:
        return f"accounts.list.{status_code}"
    if "/me" in path:
        return f"me.read.{status_code}"
    return f"unknown.{method.lower()}.{status_code}"


def _slug_for(status: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "unprocessable_entity",
        429: "rate_limited",
    }.get(status, "error")


def _parse_quota_message(msg: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Parse ``rate_limited tier=X limit=N remaining=N retry_after=N`` into JSON.

    The limits module emits this fixed format from ``_format_quota_message``;
    matching it here keeps the two ends decoupled (the limits module has no
    direct Ninja dependency).
    """
    parts: dict[str, Any] = {"error": "rate_limited"}
    for token in msg.split():
        if "=" in token:
            k, v = token.split("=", 1)
            parts[k] = int(v) if v.isdigit() else v
    headers: dict[str, str] = {}
    retry_after = parts.get("retry_after")
    if isinstance(retry_after, int):
        headers["Retry-After"] = str(retry_after)
    limit = parts.get("limit")
    if isinstance(limit, int):
        headers["X-RateLimit-Limit"] = str(limit)
    remaining = parts.get("remaining")
    if isinstance(remaining, int):
        headers["X-RateLimit-Remaining"] = str(remaining)
    return parts, headers
