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
