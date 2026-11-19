"""The inbox filter lists each connected account by platform and profile name."""

import pytest

from apps.inbox.models import InboxMessage
from apps.members.models import WorkspaceMembership
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Filter WS", organization=organization)


def _account(workspace, platform, name, platform_id):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=platform_id,
        account_name=name,
        oauth_access_token="tok",
    )


def _message(account, platform_message_id):
    from django.utils import timezone

    return InboxMessage.objects.create(
        workspace=account.workspace,
        social_account=account,
        platform_message_id=platform_message_id,
        message_type=InboxMessage.MessageType.DM,
        sender_name="Ada",
        body=f"hello {platform_message_id}",
        received_at=timezone.now(),
    )


@pytest.fixture
def logged_in(client, workspace, org_owner, user):
    WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role="owner")
    client.force_login(user)
    return client


def _feed(workspace, **params):
    return f"/workspace/{workspace.id}/inbox/?" + "&".join(f"{k}={v}" for k, v in params.items())


@pytest.mark.django_db
def test_filter_names_the_profile_next_to_the_platform(logged_in, workspace):
    _account(workspace, "facebook", "Anovatra", "p1")
    _account(workspace, "facebook", "Den's Hub", "p2")

    html = logged_in.get(_feed(workspace)).content.decode()

    assert "Facebook - Anovatra" in html
    assert "Facebook - Den&#x27;s Hub" in html or "Facebook - Den's Hub" in html


@pytest.mark.django_db
def test_choosing_an_account_shows_only_its_messages(logged_in, workspace):
    first = _account(workspace, "facebook", "Anovatra", "p1")
    second = _account(workspace, "facebook", "Hub", "p2")
    _message(first, "m-first")
    _message(second, "m-second")

    html = logged_in.get(_feed(workspace, account=first.id)).content.decode()

    assert "hello m-first" in html
    assert "hello m-second" not in html
