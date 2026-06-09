"""Regression tests for the ``0002_backfill_view_analytics`` migration.

Locks in the rule that the backfill ONLY touches full-scope keys (those
that already held every other workspace permission at issuance), not
partial-scope keys.

We test against the live models rather than ``django-migrate`` because
running migrations from inside pytest fights with the standard test
database setup; the migration's actual logic is plain Python, so we can
import the predicate and exercise it directly.
"""

from __future__ import annotations

import importlib

import pytest

# Migration module names start with a digit, so a plain ``from … import``
# doesn't work. ``importlib`` is the standard escape hatch.
migration_module = importlib.import_module("apps.api_keys.migrations.0002_backfill_view_analytics")

from apps.api_keys.models import ApiKey  # noqa: E402
from apps.members.models import PERMISSION_KEYS  # noqa: E402
from apps.organizations.models import Organization  # noqa: E402


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Backfill Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Backfill WS", organization=organization)


_KEY_COUNTER = {"n": 0}


def _make_key(workspace, *, name: str, permissions: list[str]) -> ApiKey:
    # The migration only cares about ``permissions``; auth fields just
    # need unique placeholder values so the model can be saved.
    _KEY_COUNTER["n"] += 1
    return ApiKey.objects.create(
        workspace=workspace,
        name=name,
        lookup_prefix=f"test_{_KEY_COUNTER['n']:04d}",
        token_hash="x" * 64,
        permissions=permissions,
    )


@pytest.mark.django_db
class TestBackfillViewAnalyticsMigration:
    def test_full_scope_key_gets_view_analytics_added(self, workspace):
        full_scope_without_analytics = [p for p in PERMISSION_KEYS if p != "view_analytics"]
        key = _make_key(workspace, name="full-scope", permissions=full_scope_without_analytics)

        migration_module.add_view_analytics_to_full_scope_keys(_StubApps(), None)

        key.refresh_from_db()
        assert "view_analytics" in key.permissions

    def test_partial_scope_key_is_left_untouched(self, workspace):
        key = _make_key(workspace, name="partial", permissions=["create_posts", "upload_media"])
        before = list(key.permissions)

        migration_module.add_view_analytics_to_full_scope_keys(_StubApps(), None)

        key.refresh_from_db()
        assert key.permissions == before
        assert "view_analytics" not in key.permissions

    def test_key_with_view_analytics_already_is_idempotent(self, workspace):
        key = _make_key(
            workspace,
            name="already-has-analytics",
            permissions=sorted(set(PERMISSION_KEYS)),
        )
        before = list(key.permissions)

        migration_module.add_view_analytics_to_full_scope_keys(_StubApps(), None)

        key.refresh_from_db()
        assert key.permissions == before

    def test_reverse_drops_view_analytics_from_backfilled_keys(self, workspace):
        # A key that's exactly "full-scope catalog + view_analytics" matches
        # the reverse predicate.
        key = _make_key(
            workspace,
            name="backfilled",
            permissions=sorted(set(PERMISSION_KEYS)),
        )

        migration_module.remove_view_analytics_from_backfilled_keys(_StubApps(), None)

        key.refresh_from_db()
        assert "view_analytics" not in key.permissions

    def test_reverse_leaves_partial_keys_alone(self, workspace):
        key = _make_key(workspace, name="partial-with-analytics", permissions=["view_analytics"])
        before = list(key.permissions)

        migration_module.remove_view_analytics_from_backfilled_keys(_StubApps(), None)

        key.refresh_from_db()
        assert key.permissions == before


class _StubApps:
    """Stand-in for the ``apps`` arg Django migrations get.

    The migration only calls ``apps.get_model("api_keys", "ApiKey")``, so
    we return the live model — close enough for a Python-level test of
    the predicate.
    """

    def get_model(self, app_label: str, model_name: str):
        assert (app_label, model_name) == ("api_keys", "ApiKey")
        return ApiKey
