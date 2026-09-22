"""Shared inbox fixtures.

The inbox test modules each grew their own workspace/account/message setup;
new modules should take these instead. Existing modules still define their
own — a module-level fixture shadows the one here, so they are unaffected.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.inbox.models import InboxMessage
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def inbox_workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Inbox WS", organization=organization)


@pytest.fixture
def inbox_account(db, inbox_workspace):
    return SocialAccount.objects.create(
        workspace=inbox_workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="Page",
        oauth_access_token="tok",
    )


@pytest.fixture
def inbox_message(db, inbox_workspace, inbox_account):
    return InboxMessage.objects.create(
        workspace=inbox_workspace,
        social_account=inbox_account,
        platform_message_id="pm-1",
        message_type=InboxMessage.MessageType.COMMENT,
        sender_name="Ada",
        body="hi?",
        received_at=timezone.now() - timedelta(hours=2),
    )
