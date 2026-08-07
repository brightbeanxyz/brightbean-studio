"""Regression tests for the ``0015_backfill_threads_refresh_token`` migration.

Threads accounts connected before the provider returned the long-lived token as
its own refresh credential sit with an empty ``oauth_refresh_token``, which every
refresh path treats as "not refreshable". The backfill seeds it so those accounts
rejoin the refresh cycle instead of lapsing at 60 days.

Unlike ``apps/api_keys/tests/test_migration_0002.py``, which runs its migration
against the live model, these drive the *historical* model the migration actually
receives — the encrypted-token write is the part most likely to behave
differently there, and the real migration never exercises it (the table is empty
when the test database is built).
"""

from __future__ import annotations

import importlib

import pytest
from django.db.migrations.loader import MigrationLoader

# Migration module names start with a digit, so a plain ``from … import``
# doesn't work. ``importlib`` is the standard escape hatch.
migration_module = importlib.import_module("apps.social_accounts.migrations.0015_backfill_threads_refresh_token")

from apps.social_accounts.models import SocialAccount  # noqa: E402


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Backfill Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Backfill WS", organization=organization)


def _account(workspace, *, platform, platform_id, access_token, refresh_token=""):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=platform_id,
        account_name="Test",
        oauth_access_token=access_token,
        oauth_refresh_token=refresh_token,
    )


def _historical_apps():
    """The model registry Django hands this migration at run time.

    Built from the state after the migration's dependency, so ``get_model``
    returns the historical ``SocialAccount`` — a plain manager and the field
    classes frozen into the migration graph, rather than the live model's
    manager and any behavior added since.
    """
    loader = MigrationLoader(None, ignore_no_migrations=True)
    dependency = migration_module.Migration.dependencies[0]
    return loader.project_state(dependency).apps


@pytest.mark.django_db
class TestBackfillThreadsRefreshToken:
    def test_threads_account_adopts_its_access_token(self, workspace):
        account = _account(workspace, platform="threads", platform_id="th-1", access_token="long_lived")

        migration_module.backfill_threads_refresh_token(_historical_apps(), None)

        account.refresh_from_db()
        assert account.oauth_refresh_token == "long_lived"

    def test_existing_refresh_token_is_not_overwritten(self, workspace):
        account = _account(
            workspace,
            platform="threads",
            platform_id="th-2",
            access_token="long_lived",
            refresh_token="already_set",
        )

        migration_module.backfill_threads_refresh_token(_historical_apps(), None)

        account.refresh_from_db()
        assert account.oauth_refresh_token == "already_set"

    def test_account_without_access_token_is_skipped(self, workspace):
        account = _account(workspace, platform="threads", platform_id="th-3", access_token="")

        migration_module.backfill_threads_refresh_token(_historical_apps(), None)

        account.refresh_from_db()
        assert account.oauth_refresh_token == ""

    def test_other_platforms_are_untouched(self, workspace):
        """Only Threads replays its access token; copying it elsewhere would
        hand the refresh flow a credential the platform rejects."""
        account = _account(workspace, platform="facebook", platform_id="fb-1", access_token="fb_token")

        migration_module.backfill_threads_refresh_token(_historical_apps(), None)

        account.refresh_from_db()
        assert account.oauth_refresh_token == ""
