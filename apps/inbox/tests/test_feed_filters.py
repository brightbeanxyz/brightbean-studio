"""Filter params on the inbox feed."""

import pytest

from apps.members.models import WorkspaceMembership


@pytest.mark.django_db
def test_blank_filter_values_mean_no_filter(client, inbox_workspace, inbox_message, org_owner, user):
    """Switching a select back to "All ..." submits an empty value; it must not empty the list."""
    WorkspaceMembership.objects.create(
        user=user, workspace=inbox_workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    client.force_login(user)

    resp = client.get(
        f"/workspace/{inbox_workspace.id}/inbox/",
        {"platform": "", "account": "", "type": "", "status": "", "sentiment": "", "q": ""},
        headers={"HX-Request": "true"},
    )

    assert resp.status_code == 200
    assert f'id="msg-{inbox_message.id}"'.encode() in resp.content


@pytest.mark.django_db
def test_platform_filter_still_narrows(client, inbox_workspace, inbox_message, org_owner, user):
    WorkspaceMembership.objects.create(
        user=user, workspace=inbox_workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    client.force_login(user)

    resp = client.get(
        f"/workspace/{inbox_workspace.id}/inbox/",
        {"platform": "instagram"},
        headers={"HX-Request": "true"},
    )

    assert resp.status_code == 200
    assert f'id="msg-{inbox_message.id}"'.encode() not in resp.content
