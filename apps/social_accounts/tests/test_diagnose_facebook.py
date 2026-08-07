"""The diagnose_facebook command tells a config problem from a code problem.

Both reported failures — a first comment that never posted, and Page comments
that never reached the inbox — have config causes that look identical from
inside the app. These assert the command names the cause.
"""

import contextlib
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Diag WS", organization=organization)


@pytest.fixture
def fb_account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="Diag Page",
        oauth_access_token="page-token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


def _provider(*, scopes, subscribed_fields, app_id="app-1"):
    provider = MagicMock()
    provider.credentials = {"client_id": app_id, "client_secret": "shh"}
    provider.required_scopes = ["pages_manage_engagement", "pages_read_user_content"]
    provider.debug_token.return_value = {"is_valid": True, "type": "PAGE", "scopes": scopes}
    provider.get_webhook_subscriptions.return_value = (
        [{"id": app_id, "subscribed_fields": subscribed_fields}] if subscribed_fields is not None else []
    )
    provider._request.return_value = MagicMock(json=MagicMock(return_value={"data": []}))
    return provider


def _run(account):
    out = StringIO()
    with patch("apps.social_accounts.views._get_provider_for_platform") as factory:
        factory.return_value = account["provider"]
        # Non-zero exit is the documented signal that a check failed; the
        # report is still what we assert on.
        with contextlib.suppress(CommandError):
            call_command("diagnose_facebook", "--account-id", account["id"], stdout=out, stderr=out)
    return out.getvalue()


@pytest.mark.django_db
def test_reports_a_missing_engagement_permission_by_consequence(fb_account):
    provider = _provider(scopes=["pages_read_user_content"], subscribed_fields=["feed", "mention", "messages"])

    output = _run({"id": str(fb_account.id), "provider": provider})

    assert "pages_manage_engagement" in output
    assert "first comments" in output


@pytest.mark.django_db
def test_reports_a_page_that_is_not_subscribed_at_all(fb_account):
    provider = _provider(
        scopes=["pages_manage_engagement", "pages_read_user_content"],
        subscribed_fields=None,
    )

    output = _run({"id": str(fb_account.id), "provider": provider})

    assert "not subscribed" in output
    assert "subscribe_webhooks" in output


@pytest.mark.django_db
def test_reports_a_subscription_missing_the_feed_field(fb_account):
    provider = _provider(
        scopes=["pages_manage_engagement", "pages_read_user_content"],
        subscribed_fields=["messages"],
    )

    output = _run({"id": str(fb_account.id), "provider": provider})

    assert "'feed' is what carries comments" in output


@pytest.mark.django_db
def test_a_healthy_account_reports_no_failures(fb_account, settings):
    settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN = "a-token"
    provider = _provider(
        scopes=["pages_manage_engagement", "pages_read_user_content"],
        subscribed_fields=["feed", "mention", "messages"],
    )

    output = _run({"id": str(fb_account.id), "provider": provider})

    assert "FAIL" not in output


@pytest.mark.django_db
def test_no_matching_account_is_an_error(db):
    with pytest.raises(CommandError, match="No connected Facebook accounts"):
        call_command("diagnose_facebook", "--account-id", "00000000-0000-0000-0000-000000000000")


@pytest.mark.django_db
def test_read_insights_is_not_reported_missing_when_analytics_is_off(fb_account, settings):
    """The OAuth flow omits read_insights when analytics is disabled for the
    platform, so demanding it here would fail a healthy, deliberately-limited
    token."""
    settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN = "a-token"

    # A real class, not a MagicMock: required_scopes has to be a property that
    # reacts to include_analytics_scopes, and setting that on MagicMock would
    # mutate the shared class for every other test in the process.
    class _StubProvider:
        credentials = {"client_id": "app-1", "client_secret": "shh"}
        include_analytics_scopes = True

        @property
        def required_scopes(self):
            base = ["pages_manage_engagement", "pages_read_user_content"]
            return [*base, "read_insights"] if self.include_analytics_scopes else base

        def debug_token(self, _token):
            return {
                "is_valid": True,
                "type": "PAGE",
                "scopes": ["pages_manage_engagement", "pages_read_user_content"],
            }

        def get_webhook_subscriptions(self, _token, _account_id):
            return [{"id": "app-1", "subscribed_fields": ["feed", "mention", "messages"]}]

        def _request(self, *_args, **_kwargs):
            return MagicMock(json=MagicMock(return_value={"data": []}))

    provider = _StubProvider()

    with patch("apps.social_accounts.models.AnalyticsPlatformConfig.enabled_platforms", return_value=set()):
        output = _run({"id": str(fb_account.id), "provider": provider})

    assert provider.include_analytics_scopes is False
    assert "read_insights" not in output
    assert "FAIL" not in output
