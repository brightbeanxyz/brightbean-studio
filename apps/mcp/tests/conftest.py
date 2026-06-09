"""Per-test cache isolation for the MCP transport surface.

See the docstring of ``apps/api/tests/conftest.py`` — the MCP transport
uses the same ``ApiKeyAuth`` and therefore the same failed-auth bucket,
so the same isolation applies.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_failed_auth_throttle():
    from django.core.cache import cache

    cache.delete("agent_api:auth_fail:127.0.0.1")
    yield
    cache.delete("agent_api:auth_fail:127.0.0.1")
