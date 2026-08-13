"""Tests for the social_accounts admin.

``AnalyticsPlatformConfigAdmin`` no longer decides anything about the analytics
backfill — that lives in ``apps.analytics.signals`` so non-admin writes are
covered too (see ``apps/analytics/tests/test_signals.py``). What is left here is
operator feedback: ticking the box must say what it set in motion, rather than
looking like it only flipped a flag.
"""

from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from apps.social_accounts.admin import AnalyticsPlatformConfigAdmin
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount


@pytest.fixture
def workspace(db):
    from apps.organizations.models import Organization
    from apps.workspaces.models import Workspace

    org = Organization.objects.create(name="Admin Test Org")
    return Workspace.objects.create(organization=org, name="Admin Test WS")


@pytest.fixture
def model_admin():
    return AnalyticsPlatformConfigAdmin(AnalyticsPlatformConfig, AdminSite())


@pytest.fixture
def request_with_messages():
    """A real request carrying the messages framework, not a stub.

    The message is the whole point of ``save_model``, so it has to be readable
    back — patching ``messages`` out would leave every assertion below vacuous.
    """
    request = RequestFactory().post("/admin/social_accounts/analyticsplatformconfig/")
    SessionMiddleware(lambda r: None).process_request(request)
    MessageMiddleware(lambda r: None).process_request(request)
    return request


def _account(workspace, *, platform="instagram_login"):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=f"{platform}-1",
        account_name="Pink Lion",
        account_handle="pinklion.xyz",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


def _save(model_admin, request, platform, *, is_enabled):
    """Drive ``save_model`` the way the changelist's ``list_editable`` does."""
    config = AnalyticsPlatformConfig.objects.get(platform=platform)
    config.is_enabled = is_enabled
    with patch("apps.analytics.tasks.backfill_account_analytics"):
        model_admin.save_model(request, config, form=None, change=True)
    return [str(m) for m in get_messages(request)]


@pytest.mark.django_db
class TestAnalyticsPlatformConfigAdminSaveModel:
    def test_switching_on_reports_what_was_queued(self, workspace, model_admin, request_with_messages):
        _account(workspace)
        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram_login", defaults={"is_enabled": False})

        sent = _save(model_admin, request_with_messages, "instagram_login", is_enabled=True)

        assert len(sent) == 1
        assert "1 connected Instagram (Direct) account(s)" in sent[0]
        assert "may need reconnecting" in sent[0]
        assert AnalyticsPlatformConfig.objects.get(platform="instagram_login").is_enabled is True

    def test_no_connected_accounts_says_nothing(self, workspace, model_admin, request_with_messages):
        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram_login", defaults={"is_enabled": False})

        sent = _save(model_admin, request_with_messages, "instagram_login", is_enabled=True)

        assert sent == []

    def test_resaving_an_already_enabled_row_says_nothing(self, workspace, model_admin, request_with_messages):
        _account(workspace)
        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram_login", defaults={"is_enabled": True})

        sent = _save(model_admin, request_with_messages, "instagram_login", is_enabled=True)

        assert sent == []

    def test_switching_off_says_nothing(self, workspace, model_admin, request_with_messages):
        _account(workspace)
        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram_login", defaults={"is_enabled": True})

        sent = _save(model_admin, request_with_messages, "instagram_login", is_enabled=False)

        assert sent == []
        assert AnalyticsPlatformConfig.objects.get(platform="instagram_login").is_enabled is False

    def test_a_platform_with_no_analytics_api_says_nothing(self, workspace, model_admin, request_with_messages):
        """Nothing is queued for Bluesky, so there is nothing to claim."""
        _account(workspace, platform="bluesky")
        AnalyticsPlatformConfig.objects.update_or_create(platform="bluesky", defaults={"is_enabled": False})

        sent = _save(model_admin, request_with_messages, "bluesky", is_enabled=True)

        assert sent == []
