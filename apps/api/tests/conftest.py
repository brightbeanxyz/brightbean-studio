"""Per-test cache isolation for the Agent API surface.

The failed-auth IP throttle ([apps/api/limits.py](apps/api/limits.py))
intentionally persists state in Django's shared cache so a brute-force
script can't fork concurrent attempts and dodge the counter. That's
correct in production but bleeds across pytest's tests (which all
share ``127.0.0.1`` as the client IP), so an earlier test that
intentionally exercises a 401 path will exhaust the budget for later
tests that expect a clean slate.

Solution: clear just the auth-failure bucket before every test in this
package. Per-key rate-limit counters use a fresh ``api_key.id`` per
test fixture, so they don't need cleanup.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_failed_auth_throttle():
    """Clear the 127.0.0.1 failed-auth bucket around each test."""
    from django.core.cache import cache

    cache.delete("agent_api:auth_fail:127.0.0.1")
    yield
    cache.delete("agent_api:auth_fail:127.0.0.1")
