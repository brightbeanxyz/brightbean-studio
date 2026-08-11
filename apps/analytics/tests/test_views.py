"""HTTP-level tests for the analytics page's account list.

Regression cover for accounts disappearing from the account switcher. A
platform switched off in ``AnalyticsPlatformConfig`` used to be filtered out of
the queryset feeding the switcher, so a connected Instagram (Direct) account
simply wasn't there and nothing anywhere said why.
"""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount
from apps.workspaces.models import Workspace


@pytest.fixture
def workspace(db):
    org = Organization.objects.create(name="Analytics Views Org")
    return Workspace.objects.create(organization=org, name="Analytics Views WS")


@pytest.fixture
def owner_client(client, workspace):
    user = User.objects.create_user(
        email="analytics-views@example.com",
        password="testpass123",
        tos_accepted_at=timezone.now(),
    )
    OrgMembership.objects.create(
        user=user,
        organization=workspace.organization,
        org_role=OrgMembership.OrgRole.OWNER,
    )
    WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )
    client.force_login(user)
    return client


def _account(workspace, platform, name):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=f"{platform}-1",
        account_name=name,
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


def _disable_analytics(platform):
    AnalyticsPlatformConfig.objects.update_or_create(platform=platform, defaults={"is_enabled": False})


def _account_url(workspace, account):
    return reverse("analytics:account", kwargs={"workspace_id": workspace.id, "account_id": account.id})


@pytest.mark.django_db
def test_instagram_direct_account_is_listed_and_available(owner_client, workspace):
    account = _account(workspace, "instagram_login", "Direct IG")

    response = owner_client.get(_account_url(workspace, account))

    assert response.status_code == 200
    assert [a.id for a in response.context["accounts"]] == [account.id]
    assert response.context["analytics_unavailable"] is False


@pytest.mark.django_db
def test_disabled_platform_account_stays_listed_with_a_reason(owner_client, workspace):
    """The reported bug: the account vanished from the switcher entirely.

    It must still be listed, and selecting it must explain both that analytics
    is off for the platform and that reconnecting is needed once it's back on —
    the insights scope is requested at connect time, so flipping the admin
    toggle alone leaves the stored token unable to read insights.
    """
    account = _account(workspace, "instagram_login", "Direct IG")
    _disable_analytics("instagram_login")

    response = owner_client.get(_account_url(workspace, account))

    assert response.status_code == 200
    assert [a.id for a in response.context["accounts"]] == [account.id]
    assert response.context["analytics_unavailable"] is True
    assert response.context["analytics_disabled_by_admin"] is True
    assert response.context["accounts"][0].analytics_unavailable_reason
    body = response.content.decode()
    assert "Reconnect this account" in body
    # The switcher marks it rather than listing it indistinguishably.
    assert "No data" in body


@pytest.mark.django_db
def test_index_lands_on_the_only_account_even_when_disabled(owner_client, workspace):
    """Better to land on the explanation than on "connect an account"."""
    account = _account(workspace, "instagram_login", "Direct IG")
    _disable_analytics("instagram_login")

    response = owner_client.get(reverse("analytics:index", kwargs={"workspace_id": workspace.id}), follow=True)

    assert response.status_code == 200
    assert response.context["active_account"].id == account.id
    assert response.context["analytics_unavailable"] is True


@pytest.mark.django_db
def test_index_prefers_an_account_with_analytics_available(owner_client, workspace):
    disabled = _account(workspace, "facebook", "AAA Disabled")
    available = _account(workspace, "instagram_login", "ZZZ Available")
    _disable_analytics("facebook")

    response = owner_client.get(reverse("analytics:index", kwargs={"workspace_id": workspace.id}), follow=True)

    # "facebook" sorts first and would have been the redirect target on
    # ordering alone; availability wins.
    assert disabled.platform < available.platform
    assert response.context["active_account"].id == available.id


@pytest.mark.django_db
def test_inherently_unavailable_platform_gets_no_reconnect_hint(owner_client, workspace):
    """Bluesky has no analytics API — reconnecting would achieve nothing."""
    account = _account(workspace, "bluesky", "Bluesky")

    response = owner_client.get(_account_url(workspace, account))

    assert response.context["analytics_unavailable"] is True
    assert response.context["analytics_disabled_by_admin"] is False
    assert "Reconnect this account" not in response.content.decode()


@pytest.mark.django_db
def test_disconnected_account_is_not_listed(owner_client, workspace):
    """The connection-status filter is the one that still drops accounts."""
    listed = _account(workspace, "instagram_login", "Direct IG")
    dropped = _account(workspace, "threads", "Threads")
    dropped.connection_status = SocialAccount.ConnectionStatus.ERROR
    dropped.save(update_fields=["connection_status"])

    response = owner_client.get(_account_url(workspace, listed))

    assert [a.id for a in response.context["accounts"]] == [listed.id]


@pytest.mark.django_db
def test_devto_account_renders_the_unavailable_state(owner_client, workspace):
    """DEV.to has no metrics methods and no entry in the PLATFORM_* maps.

    It reaches the page now that a missing config row counts as enabled, so the
    platform-keyed lookups all have to tolerate it rather than KeyError.
    """
    account = _account(workspace, "devto", "Dev Blog")

    response = owner_client.get(_account_url(workspace, account))

    assert response.status_code == 200
    assert response.context["analytics_unavailable"] is True
    assert response.context["analytics_disabled_by_admin"] is False


@pytest.mark.django_db
def test_unavailable_account_suppresses_the_scope_reconnect_banner(owner_client, workspace):
    """Two reconnect CTAs on one screen give contradictory instructions.

    The unavailable state carries its own, so the insufficient-scope banner
    stands down while it's showing.
    """
    account = _account(workspace, "instagram_login", "Direct IG")
    account.analytics_needs_reconnect = True
    account.save(update_fields=["analytics_needs_reconnect"])
    _disable_analytics("instagram_login")

    response = owner_client.get(_account_url(workspace, account))

    assert response.context["analytics_needs_reconnect"] is False
    assert "insufficient-scope" not in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize("platform", ["instagram_login", "bluesky"])
def test_pages_never_leak_raw_template_tags(owner_client, workspace, platform):
    """Django's ``{# #}`` is single-line only: a multi-line one is emitted as
    visible page text instead of being stripped. Cheap to assert, and it caught
    two real leaks in the account switcher and the unavailable state.
    """
    account = _account(workspace, platform, "Acct")
    _disable_analytics(platform)

    body = owner_client.get(_account_url(workspace, account)).content.decode()

    assert "{#" not in body
    assert "{%" not in body
