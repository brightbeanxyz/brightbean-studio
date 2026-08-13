"""Switching a platform on in ``AnalyticsPlatformConfig`` re-checks its accounts.

The queueing lives in a signal rather than in ``AnalyticsPlatformConfigAdmin``
so it covers every write path — a shell ``save()`` and ``update_or_create`` as
well as the admin checkbox. (``queryset.update()`` fires no signals at all and
is deliberately out of reach; the page copy promises nothing that depends on
this running.)
"""

from unittest.mock import patch

import pytest

from apps.analytics.signals import BACKFILL_QUEUED_ATTR
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount


@pytest.fixture
def workspace(db):
    from apps.organizations.models import Organization
    from apps.workspaces.models import Workspace

    org = Organization.objects.create(name="Analytics Signals Org")
    return Workspace.objects.create(organization=org, name="Analytics Signals WS")


def _account(workspace, *, platform="instagram_login", status=SocialAccount.ConnectionStatus.CONNECTED):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=f"{platform}-{status}",
        account_name="Pink Lion",
        account_handle="pinklion.xyz",
        oauth_access_token="token",
        connection_status=status,
    )


def _set_enabled(platform, *, is_enabled):
    """Write the row as it stands before the edit under test.

    The handler still fires here, but its enqueue is deferred to commit and
    nothing outside ``captureOnCommitCallbacks`` ever executes those callbacks
    in a test — so arranging state can't leak a queued task into the assertion.
    """
    AnalyticsPlatformConfig.objects.update_or_create(platform=platform, defaults={"is_enabled": is_enabled})
    return AnalyticsPlatformConfig.objects.get(platform=platform)


def _toggle(platform, *, is_enabled):
    """Flip the row through ``save()`` and return the patched backfill task.

    ``captureOnCommitCallbacks`` runs the ``transaction.on_commit`` hook the
    handler defers its enqueue to — without it the callback is discarded with
    the test's rollback and nothing is ever queued.
    """
    from django.test import TestCase

    config = AnalyticsPlatformConfig.objects.get(platform=platform)
    config.is_enabled = is_enabled
    with (
        patch("apps.analytics.tasks.backfill_account_analytics") as backfill,
        TestCase.captureOnCommitCallbacks(execute=True),
    ):
        config.save()
    return backfill, config


@pytest.mark.django_db(transaction=False)
class TestPlatformEnableQueuesBackfill:
    def test_switching_on_queues_each_connected_account_deduped(self, workspace):
        account = _account(workspace)
        _set_enabled("instagram_login", is_enabled=False)

        backfill, config = _toggle("instagram_login", is_enabled=True)

        backfill.assert_called_once_with(str(account.id), remove_existing_tasks=True)
        assert getattr(config, BACKFILL_QUEUED_ATTR) == 1

    def test_a_shell_update_or_create_queues_too(self, workspace):
        """The reason this isn't in ``ModelAdmin.save_model``: non-admin writes."""
        from django.test import TestCase

        account = _account(workspace)
        _set_enabled("instagram_login", is_enabled=False)

        with (
            patch("apps.analytics.tasks.backfill_account_analytics") as backfill,
            TestCase.captureOnCommitCallbacks(execute=True),
        ):
            AnalyticsPlatformConfig.objects.update_or_create(
                platform="instagram_login",
                defaults={"is_enabled": True},
            )

        backfill.assert_called_once_with(str(account.id), remove_existing_tasks=True)

    def test_a_platform_with_no_analytics_api_queues_nothing(self, workspace):
        """``bluesky`` is listed in the admin but has no analytics API at all.

        Queueing would insert a task per account that returns immediately from
        ``backfill_account_analytics``'s own availability check.
        """
        _account(workspace, platform="bluesky")
        _set_enabled("bluesky", is_enabled=False)

        backfill, config = _toggle("bluesky", is_enabled=True)

        backfill.assert_not_called()
        assert not hasattr(config, BACKFILL_QUEUED_ATTR)

    def test_a_disconnected_account_is_left_alone(self, workspace):
        _account(workspace, status=SocialAccount.ConnectionStatus.DISCONNECTED)
        _set_enabled("instagram_login", is_enabled=False)

        backfill, config = _toggle("instagram_login", is_enabled=True)

        backfill.assert_not_called()
        assert getattr(config, BACKFILL_QUEUED_ATTR) == 0

    def test_accounts_on_other_platforms_are_left_alone(self, workspace):
        _account(workspace, platform="facebook")
        _set_enabled("instagram_login", is_enabled=False)

        backfill, _ = _toggle("instagram_login", is_enabled=True)

        backfill.assert_not_called()

    def test_resaving_an_already_enabled_row_queues_nothing(self, workspace):
        _account(workspace)
        _set_enabled("instagram_login", is_enabled=True)

        backfill, config = _toggle("instagram_login", is_enabled=True)

        backfill.assert_not_called()
        assert not hasattr(config, BACKFILL_QUEUED_ATTR)

    def test_switching_a_platform_off_queues_nothing(self, workspace):
        _account(workspace)
        _set_enabled("instagram_login", is_enabled=True)

        backfill, _ = _toggle("instagram_login", is_enabled=False)

        backfill.assert_not_called()
        assert AnalyticsPlatformConfig.objects.get(platform="instagram_login").is_enabled is False

    def test_creating_a_row_is_not_a_transition(self, workspace):
        """A platform with no row already reads as enabled, so writing the first
        row with ``is_enabled=True`` states the status quo rather than changing it.

        The connected account is on the same platform as the row being created,
        so this fails if ``created`` stops being skipped — a distractor account
        on some other platform would pass either way.
        """
        from django.test import TestCase

        _account(workspace, platform="threads")
        AnalyticsPlatformConfig.objects.filter(platform="threads").delete()

        with (
            patch("apps.analytics.tasks.backfill_account_analytics") as backfill,
            TestCase.captureOnCommitCallbacks(execute=True),
        ):
            AnalyticsPlatformConfig.objects.create(platform="threads", is_enabled=True)

        backfill.assert_not_called()

    def test_nothing_is_queued_when_the_save_rolls_back(self, workspace):
        """The enqueue is deferred to commit, so an aborted save queues nothing.

        ``captureOnCommitCallbacks`` wraps the rollback rather than sitting
        inside it: it executes whatever survived, so the assertion fails if the
        callback outlives the transaction instead of passing vacuously.
        """
        from django.db import transaction
        from django.test import TestCase

        _account(workspace)
        _set_enabled("instagram_login", is_enabled=False)

        config = AnalyticsPlatformConfig.objects.get(platform="instagram_login")
        config.is_enabled = True
        with (
            patch("apps.analytics.tasks.backfill_account_analytics") as backfill,
            TestCase.captureOnCommitCallbacks(execute=True),
            pytest.raises(RuntimeError),
            transaction.atomic(),
        ):
            config.save()
            raise RuntimeError("boom")

        backfill.assert_not_called()
