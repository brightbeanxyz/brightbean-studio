import pytest

from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


@pytest.fixture
def workspace(organization):
    return Workspace.objects.create(organization=organization, name="Nike")


@pytest.fixture
def social_account(workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig_12345",
        account_name="Nike",
        account_handle="nike",
    )


from apps.accounts.models import User
from apps.members.models import OrgMembership
from apps.organizations.models import Organization


@pytest.fixture
def user(db):
    from django.utils import timezone
    return User.objects.create_user(
        email="test@example.com", password="testpass123", name="Test User", tos_accepted_at=timezone.now()
    )


@pytest.fixture
def org_member(user, organization):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.MEMBER)
    return user


@pytest.fixture
def other_organization(db):
    return Organization.objects.create(name="Other Org")


@pytest.fixture
def other_workspace(other_organization):
    return Workspace.objects.create(organization=other_organization, name="Other Brand")
