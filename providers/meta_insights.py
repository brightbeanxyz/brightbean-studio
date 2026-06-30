"""Helpers shared by Meta-backed providers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .exceptions import APIError

logger = logging.getLogger(__name__)

META_PERMISSION_ERROR_CODES = {10, 190, 200}
META_PERMISSION_ERROR_MARKERS = (
    "access token",
    "authorization",
    "authorized",
    "insufficient",
    "oauth",
    "permission",
    "permissions",
    "scope",
)


def parse_insights_response(data: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    periods: dict[str, str] = {}
    for entry in data.get("data", []):
        name = entry.get("name", "")
        if not name:
            continue
        period = entry.get("period", "")
        if periods.get(name) == "lifetime" and period != "lifetime":
            continue
        if "total_value" in entry:
            value = entry.get("total_value", {}).get("value", 0)
        else:
            value = entry.get("values", [{}])[0].get("value", 0)
        if name not in values or period == "lifetime":
            values[name] = value
            periods[name] = period
            continue
    return values


def is_meta_permission_error(exc: APIError) -> bool:
    """Return true for Meta auth/scope errors that should trigger reconnect handling."""
    error = exc.raw_response.get("error") if isinstance(exc.raw_response, dict) else None
    error = error if isinstance(error, dict) else {}
    code = error.get("code")
    message = " ".join(
        str(value)
        for value in (
            error.get("message"),
            error.get("type"),
            error.get("error_user_msg"),
            exc,
        )
        if value
    ).lower()

    if code in META_PERMISSION_ERROR_CODES:
        return True
    if exc.status_code == 403:
        return True
    return any(marker in message for marker in META_PERMISSION_ERROR_MARKERS)


def fetch_insights_safe(
    request: Callable[..., Any],
    *,
    platform: str,
    endpoint: str,
    access_token: str,
    metrics: list[str],
    base_params: dict[str, Any] | None = None,
    metric_params: dict[str, dict[str, Any]] | None = None,
    endpoint_type: str = "insights",
) -> tuple[dict[str, Any], dict[str, str]]:
    """Fetch Meta insights one metric at a time so one invalid metric cannot fail all metrics."""
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for metric in metrics:
        params = {**(base_params or {}), **(metric_params or {}).get(metric, {}), "metric": metric}
        try:
            resp = request("GET", endpoint, access_token=access_token, params=params)
        except APIError as exc:
            if is_meta_permission_error(exc):
                raise
            errors[metric] = str(exc)
            logger.warning(
                "Skipping unsupported %s %s metric %s at %s: %s",
                platform,
                endpoint_type,
                metric,
                endpoint,
                exc,
            )
            continue
        values.update(parse_insights_response(resp.json()))
    return values, errors
