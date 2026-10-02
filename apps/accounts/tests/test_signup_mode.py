"""Tests for SIGNUP_MODE — the gate on creating new accounts.

The point of the setting is that an installation reachable from the
internet does not have to accept arbitrary sign-ups. Two things have to
hold for it to be worth anything:

* Both doors are covered. Closing the email form alone achieves nothing,
  because SOCIALACCOUNT_AUTO_SIGNUP creates the account during the
  provider callback without ever rendering the signup page.
* Existing users keep getting in. A gate that locks out the people it was
  meant to protect is worse than no gate.
"""

import uuid
from datetime import timedelta

import pytest
from allauth.socialaccount.models import SocialAccount as AllAuthSocialAccount
from allauth.socialaccount.models import SocialLogin
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.accounts.adapters import AccountAdapter, SocialAccountAdapter
from apps.accounts.models import User
from apps.members.models import Invitation
from apps.organizations.models import Organization


def _request(session_data=None):
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    for key, value in (session_data or {}).items():
        request.session[key] = value
    return request


@pytest.fixture
def account_adapter():
    return AccountAdapter()


@pytest.fixture
def social_adapter():
    return SocialAccountAdapter()


@pytest.fixture
def sociallogin():
    account = AllAuthSocialAccount(provider="google", uid=f"uid-{uuid.uuid4()}")
    return SocialLogin(user=User(email="new@example.com"), account=account)


@pytest.fixture
def invitation(db):
    org = Organization.objects.create(name="Acme")
    return Invitation.objects.create(
        organization=org,
        email="invited@example.com",
        expires_at=timezone.now() + timedelta(days=7),
    )


class TestOpenMode:
    def test_email_signup_allowed(self, settings, account_adapter):
        settings.SIGNUP_MODE = "open"
        assert account_adapter.is_open_for_signup(_request()) is True

    def test_social_signup_allowed(self, settings, social_adapter, sociallogin):
        settings.SIGNUP_MODE = "open"
        assert social_adapter.is_open_for_signup(_request(), sociallogin) is True


class TestClosedMode:
    def test_email_signup_blocked(self, settings, account_adapter):
        settings.SIGNUP_MODE = "closed"
        assert account_adapter.is_open_for_signup(_request()) is False

    def test_social_signup_blocked(self, settings, social_adapter, sociallogin):
        """The door that closing the form alone would leave wide open."""
        settings.SIGNUP_MODE = "closed"
        assert social_adapter.is_open_for_signup(_request(), sociallogin) is False

    @pytest.mark.django_db
    def test_an_invite_does_not_reopen_it(self, settings, account_adapter, invitation):
        settings.SIGNUP_MODE = "closed"
        request = _request({"pending_invite_token": invitation.token})
        assert account_adapter.is_open_for_signup(request) is False


@pytest.mark.django_db
class TestInviteMode:
    def test_blocked_without_invite(self, settings, account_adapter):
        settings.SIGNUP_MODE = "invite"
        assert account_adapter.is_open_for_signup(_request()) is False

    def test_allowed_with_valid_invite(self, settings, account_adapter, invitation):
        settings.SIGNUP_MODE = "invite"
        request = _request({"pending_invite_token": invitation.token})
        assert account_adapter.is_open_for_signup(request) is True

    def test_social_allowed_with_valid_invite(self, settings, social_adapter, sociallogin, invitation):
        settings.SIGNUP_MODE = "invite"
        request = _request({"pending_invite_token": invitation.token})
        assert social_adapter.is_open_for_signup(request, sociallogin) is True

    def test_expired_invite_rejected(self, settings, account_adapter, invitation):
        settings.SIGNUP_MODE = "invite"
        invitation.expires_at = timezone.now() - timedelta(minutes=1)
        invitation.save(update_fields=["expires_at"])
        request = _request({"pending_invite_token": invitation.token})
        assert account_adapter.is_open_for_signup(request) is False

    def test_already_accepted_invite_rejected(self, settings, account_adapter, invitation):
        """Otherwise one invitation link would mint accounts indefinitely."""
        settings.SIGNUP_MODE = "invite"
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at"])
        request = _request({"pending_invite_token": invitation.token})
        assert account_adapter.is_open_for_signup(request) is False

    def test_unknown_token_rejected(self, settings, account_adapter):
        settings.SIGNUP_MODE = "invite"
        request = _request({"pending_invite_token": "not-a-real-token"})
        assert account_adapter.is_open_for_signup(request) is False


@pytest.mark.django_db
class TestExistingUsersAreUnaffected:
    def test_login_page_still_reachable_when_closed(self, settings, client):
        settings.SIGNUP_MODE = "closed"
        assert client.get(reverse("account_login")).status_code == 200

    def test_existing_user_can_log_in_when_closed(self, settings, client):
        settings.SIGNUP_MODE = "closed"
        User.objects.create_user(email="existing@example.com", password="pw-for-test-only")

        response = client.post(
            reverse("account_login"),
            {"login": "existing@example.com", "password": "pw-for-test-only"},
        )

        assert response.status_code == 302
        assert response.wsgi_request.user.is_authenticated

    def test_signup_page_shows_the_closed_notice(self, settings, client):
        settings.SIGNUP_MODE = "closed"
        response = client.get(reverse("account_signup"))
        assert b"Sign-up is closed" in response.content


@pytest.mark.django_db
class TestLoginPageSignupLink:
    def test_link_shown_when_open(self, settings, client):
        settings.SIGNUP_MODE = "open"
        assert b"Sign up" in client.get(reverse("account_login")).content

    def test_link_hidden_when_closed(self, settings, client):
        settings.SIGNUP_MODE = "closed"
        assert b"Sign up" not in client.get(reverse("account_login")).content

    def test_link_hidden_in_invite_mode_without_invite(self, settings, client):
        settings.SIGNUP_MODE = "invite"
        assert b"Sign up" not in client.get(reverse("account_login")).content

    def test_link_shown_in_invite_mode_with_invite(self, settings, client, invitation):
        settings.SIGNUP_MODE = "invite"
        session = client.session
        session["pending_invite_token"] = invitation.token
        session.save()
        assert b"Sign up" in client.get(reverse("account_login")).content
