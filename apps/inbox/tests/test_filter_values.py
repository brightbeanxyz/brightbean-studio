"""Inbox filters ignore the blank values the unused dropdowns submit."""

import pytest
from django.utils import timezone

from apps.inbox.models import InboxMessage
from apps.members.models import WorkspaceMembership
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Filter WS", organization=organization)


@pytest.fixture
def logged_in(client, workspace, org_owner, user):
    WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role="owner")
    client.force_login(user)
    return client


def _message(workspace, platform, platform_message_id):
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=f"id-{platform}",
        account_name=platform.title(),
        oauth_access_token="tok",
    )
    return InboxMessage.objects.create(
        workspace=workspace,
        social_account=account,
        platform_message_id=platform_message_id,
        message_type=InboxMessage.MessageType.COMMENT,
        sender_name="Ada",
        body=f"hello {platform_message_id}",
        received_at=timezone.now(),
    )


@pytest.mark.django_db
def test_blank_values_from_the_other_dropdowns_are_ignored(logged_in, workspace):
    """The browser sends every dropdown, the unused ones as empty strings."""
    _message(workspace, "facebook", "fb-1")
    _message(workspace, "instagram", "ig-1")

    url = f"/workspace/{workspace.id}/inbox/?platform=facebook&type=&status=&sentiment=&q="
    html = logged_in.get(url).content.decode()

    assert "hello fb-1" in html
    assert "hello ig-1" not in html


@pytest.mark.django_db
def test_all_blank_filters_show_every_message(logged_in, workspace):
    _message(workspace, "facebook", "fb-1")
    _message(workspace, "instagram", "ig-1")

    url = f"/workspace/{workspace.id}/inbox/?platform=&type=&status=&sentiment=&q="
    html = logged_in.get(url).content.decode()

    assert "hello fb-1" in html
    assert "hello ig-1" in html
