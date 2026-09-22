"""The quota_status command tells a spent budget apart from a broken account.

Support's question when an account stops syncing is always the same, and the
two answers call for opposite actions: reconnect the grant, or wait for the
window. Getting it wrong the second way is actively harmful — a reconnect mints
a fresh token and the sync resumes spending a budget that is already empty.
"""

import re
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.common.quota import credential_key, trip_quota_block


def _run(*args) -> str:
    out = StringIO()
    call_command("quota_status", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
class TestQuotaStatusCommand:
    def test_no_blocks_says_so_plainly(self):
        assert "No quota blocks in effect" in _run()

    def test_a_live_block_names_the_platform_scope_and_reset(self):
        trip_quota_block(
            "youtube",
            credential_key({"client_id": "c"}),
            "data",
            until=timezone.now() + timedelta(hours=9, minutes=30),
            reason="YouTube daily quota exhausted (data API)",
        )

        output = _run()

        assert "youtube" in output
        assert "[data]" in output
        # Not an exact minute: the few hundred microseconds between writing the
        # block and reading it back round the remainder down.
        assert re.search(r"blocked for another 9h(29|30)m", output), output
        assert "daily quota exhausted" in output

    def test_the_output_says_the_accounts_are_not_broken(self):
        """The whole point of the command, in the one line support will read."""
        trip_quota_block(
            "youtube",
            credential_key({"client_id": "c"}),
            "data",
            until=timezone.now() + timedelta(hours=3),
            reason="spent",
        )

        assert "not broken" in _run()

    def test_an_expired_block_is_hidden_by_default(self):
        trip_quota_block(
            "youtube",
            credential_key({"client_id": "c"}),
            "data",
            until=timezone.now() - timedelta(hours=1),
            reason="yesterday's exhaustion",
        )

        assert "No quota blocks in effect" in _run()

    def test_all_shows_the_history(self):
        trip_quota_block(
            "youtube",
            credential_key({"client_id": "c"}),
            "data",
            until=timezone.now() - timedelta(hours=2),
            reason="yesterday's exhaustion",
        )

        output = _run("--all")

        assert "expired" in output
        assert re.search(r"expired 1h59m ago|expired 2h00m ago", output), output

    def test_a_platform_with_one_budget_does_not_print_an_empty_scope(self):
        trip_quota_block(
            "tiktok",
            credential_key({"client_id": "c"}),
            "",
            until=timezone.now() + timedelta(hours=2),
            reason="spent",
        )

        assert "[(single budget)]" in _run()

    def test_the_client_id_is_never_printed(self):
        """It reaches a terminal and often a support ticket after that."""
        trip_quota_block(
            "youtube",
            credential_key({"client_id": "super-secret-client"}),
            "data",
            until=timezone.now() + timedelta(hours=2),
            reason="spent",
        )

        assert "super-secret-client" not in _run()
