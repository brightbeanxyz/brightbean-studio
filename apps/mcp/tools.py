"""MCP tool registry.

Each ``Tool`` bundles the protocol metadata a client needs to discover
and invoke the tool (name, description, JSON-schema'd input) with the
server-side handler that actually does the work. Handlers receive a
context dict containing the authenticated ``api_key``, the resolved
``workspace``, and the membership shim so they can re-check
permissions exactly the way REST routes do.

Tools are registered at import time from ``apps.mcp.handlers``; the
app's ``ready()`` hook forces that import so the catalog is always
complete by the time the transport starts serving.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict, Any], dict]

    def to_mcp_dict(self) -> dict:
        """Wire shape returned by ``tools/list`` per the MCP spec."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


_REGISTRY: dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    if tool.name in _REGISTRY:
        raise ValueError(f"Duplicate MCP tool registered: {tool.name}")
    _REGISTRY[tool.name] = tool


def all_tools() -> list[Tool]:
    """Sorted catalog — sort is stable so ``tools/list`` is deterministic."""
    return sorted(_REGISTRY.values(), key=lambda t: t.name)


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def _reset_registry_for_tests() -> None:  # pragma: no cover
    """Test-only helper for re-importing handlers without collisions."""
    _REGISTRY.clear()
