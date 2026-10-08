"""Tests for CUSTOM_SIGNUP_URL: where Studio's "Sign up" links point."""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.members.models import Invitation, OrgMembership
from apps.organizations.models import Organization

CUSTOM = "https://example.com/join"


@pytest.fixture
def custom_signup_url(settings):
    settings.CUSTOM_SIGNUP_URL = CUSTOM


def _open_invite(client, *, expires_in=timedelta(days=7)):
    """Visit an invite's accept page as an anonymous user, which stores its token in the session."""
    invitation = Invitation.objects.create(
        organization=Organization.objects.create(name="Inviting Org"),
        email="invitee@example.com",
        expires_at=timezone.now() + expires_in,
    )
    client.get(reverse("members:accept_invite", args=[invitation.token]))
    return invitation


def _signup_href(response):
    content = response.content.decode()
    marker = content.index(">Sign up</a>")
    start = content.rindex('href="', 0, marker) + len('href="')
    return content[start : content.index('"', start)]


@pytest.mark.django_db
class TestLoginSignupLink:
    def test_defaults_to_builtin_signup(self, client):
        response = client.get(reverse("account_login"))

        assert response.status_code == 200
        assert _signup_href(response) == "/accounts/signup/"

    def test_default_keeps_next_passthrough(self, client):
        response = client.get(reverse("account_login"), {"next": "/foo/"})

        assert _signup_href(response) == "/accounts/signup/?next=%2Ffoo%2F"

    def test_custom_signup_url_replaces_link(self, client, custom_signup_url):
        response = client.get(reverse("account_login"), {"next": "/foo/"})

        assert _signup_href(response) == CUSTOM

    def test_invitee_keeps_builtin_signup(self, client, custom_signup_url):
        # "Log In to Join" on the accept page lands here with next=<accept url>;
        # only the built-in signup can accept the invite.
        invitation = _open_invite(client)
        accept_url = f"/members/invite/{invitation.token}/accept/"

        response = client.get(reverse("account_login"), {"next": accept_url})

        assert _signup_href(response).startswith("/accounts/signup/?next=")

    def test_expired_invite_does_not_keep_builtin_signup(self, client, custom_signup_url):
        _open_invite(client, expires_in=timedelta(days=-1))

        response = client.get(reverse("account_login"))

        assert _signup_href(response) == CUSTOM


@pytest.mark.django_db
class TestUnknownAccountEmail:
    def test_links_builtin_signup_by_default(self, client):
        client.post(reverse("account_reset_password"), {"email": "nobody@example.com"})

        assert len(mail.outbox) == 1
        assert "http://testserver/accounts/signup/" in mail.outbox[0].body

    def test_links_custom_signup_url(self, client, custom_signup_url):
        client.post(reverse("account_reset_password"), {"email": "nobody@example.com"})

        assert len(mail.outbox) == 1
        assert CUSTOM in mail.outbox[0].body
        assert "/accounts/signup/" not in mail.outbox[0].body

    def test_relative_custom_signup_url_is_made_absolute(self, client, settings):
        settings.CUSTOM_SIGNUP_URL = "/waitlist/"

        client.post(reverse("account_reset_password"), {"email": "nobody@example.com"})

        assert "http://testserver/waitlist/" in mail.outbox[0].body


@pytest.mark.django_db
class TestOrgDeletionRedirect:
    @pytest.fixture
    def owner(self, client):
        user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        client.force_login(user)
        return user

    def _delete_org_now(self, client):
        return client.post(reverse("organizations:settings"), {"action": "delete_organization_now"})

    def test_redirects_to_builtin_signup_by_default(self, client, owner):
        assert OrgMembership.objects.filter(user=owner, org_role=OrgMembership.OrgRole.OWNER).exists()

        response = self._delete_org_now(client)

        assert response.status_code == 302
        assert response.url == reverse("account_signup")

    def test_redirects_to_custom_signup_url(self, client, owner, custom_signup_url):
        response = self._delete_org_now(client)

        assert response.status_code == 302
        assert response.url == CUSTOM
