"""Helpers shared by Meta-backed providers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .exceptions import APIError

logger = logging.getLogger(__name__)


def parse_insights_response(data: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for entry in data.get("data", []):
        name = entry.get("name", "")
        if not name:
            continue
        if "total_value" in entry:
            values[name] = entry.get("total_value", {}).get("value", 0)
            continue
        values[name] = entry.get("values", [{}])[0].get("value", 0)
    return values


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
