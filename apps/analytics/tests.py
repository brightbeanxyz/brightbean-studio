from unittest.mock import MagicMock, patch

import pytest

from apps.analytics.tasks import _resolve_provider
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Test Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test Workspace", organization=organization)


@pytest.mark.django_db
@patch("providers.get_provider")
@patch("apps.credentials.models.resolve_platform_credentials", return_value={})
def test_facebook_analytics_provider_uses_connected_page_id(_mock_creds, mock_get_provider, workspace):
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-123",
        account_name="Test Page",
        oauth_access_token="page-token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    mock_provider = MagicMock()
    mock_get_provider.return_value = mock_provider

    provider = _resolve_provider(account)

    assert provider is mock_provider
    platform, credentials = mock_get_provider.call_args.args
    assert platform == "facebook"
    assert credentials["page_id"] == "page-123"
