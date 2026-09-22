"""Explicit history seeding must not inherit the routine poll's bounds.

``backfill_inbox`` exists to pull a deliberate window of history on request.
The comment poll's early exit and 5-page cap protect a daily budget across
hundreds of automatic polls; applying them to a one-off the operator asked for
would silently seed a fraction of the requested days and say nothing.
"""

from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.social_accounts.models import SocialAccount
from providers.youtube import YouTubeMessageBatch


@pytest.fixture
def backfill_workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Backfill WS", organization=organization)


def _account(workspace, platform, platform_id):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=platform_id,
        account_name=f"{platform} acct",
        oauth_access_token="tok",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        token_expires_at=timezone.now() + timedelta(days=30),
    )


@pytest.mark.django_db
class TestBackfillInbox:
    def test_youtube_asks_for_the_deep_walk(self, backfill_workspace):
        _account(backfill_workspace, "youtube", "yt-backfill")
        provider = MagicMock()
        provider.get_messages.return_value = []

        with patch("apps.inbox.management.commands.backfill_inbox.get_provider", return_value=provider):
            call_command("backfill_inbox", "--days", "90", stdout=StringIO())

        assert provider.get_messages.call_args.kwargs["deep"] is True

    def test_youtube_continues_after_a_deep_page_cap(self, backfill_workspace):
        _account(backfill_workspace, "youtube", "yt-backfill")
        provider = MagicMock()
        provider.get_messages.side_effect = [YouTubeMessageBatch([], "next-page"), YouTubeMessageBatch([])]

        with patch("apps.inbox.management.commands.backfill_inbox.get_provider", return_value=provider):
            call_command("backfill_inbox", "--days", "90", stdout=StringIO())

        assert provider.get_messages.call_count == 2
        assert provider.get_messages.call_args_list[1].kwargs["page_token"] == "next-page"

    def test_other_platforms_are_not_passed_a_flag_they_do_not_take(self, backfill_workspace):
        """Only YouTube's provider has the parameter; passing it elsewhere is a TypeError."""
        _account(backfill_workspace, "facebook", "fb-backfill")
        provider = MagicMock()
        provider.get_messages.return_value = []

        with patch("apps.inbox.management.commands.backfill_inbox.get_provider", return_value=provider):
            call_command("backfill_inbox", "--days", "90", stdout=StringIO())

        assert "deep" not in provider.get_messages.call_args.kwargs
