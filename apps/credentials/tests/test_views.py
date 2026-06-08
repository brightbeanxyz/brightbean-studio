from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.credentials.models import PlatformCredential
from apps.members.models import OrgMembership


@pytest.fixture
def admin_user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="credentials-admin@example.com",
        password="testpass123",
        name="Credentials Admin",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def member_user(db):
    from apps.accounts.models import User

    user = User.objects.create_user(
        email="credentials-member@example.com",
        password="testpass123",
        name="Credentials Member",
        tos_accepted_at=timezone.now(),
    )
    membership = user.org_memberships.first()
    membership.org_role = OrgMembership.OrgRole.MEMBER
    membership.save(update_fields=["org_role"])
    return user


@pytest.fixture
def organization(admin_user):
    return admin_user.org_memberships.first().organization


@pytest.fixture
def workspace(admin_user):
    return admin_user.workspace_memberships.first().workspace


@pytest.fixture
def authenticated_admin(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.mark.django_db
class TestPlatformCredentialsPage:
    def test_requires_login(self, client):
        response = client.get(reverse("credentials:list"))
        assert response.status_code == 302
        assert "/accounts/" in response.url

    def test_org_member_cannot_manage_credentials(self, client, member_user):
        client.force_login(member_user)
        response = client.get(reverse("credentials:list"))
        assert response.status_code == 403

    def test_page_renders_credential_groups_and_redirect_uris(self, authenticated_admin):
        response = authenticated_admin.get(reverse("credentials:list"))
        assert response.status_code == 200
        body = response.content.decode()
        assert "Platform Credentials" in body
        assert "Meta" in body
        assert "http://localhost:8000/social-accounts/callback/facebook/" in body
        assert "http://localhost:8000/social-accounts/callback/social1/" in body

    def test_saving_meta_credentials_configures_all_meta_platforms(
        self,
        authenticated_admin,
        organization,
        workspace,
    ):
        response = authenticated_admin.post(
            reverse("credentials:list"),
            {
                "group": "meta",
                "action": "save",
                "field_app_id": "meta-app-id",
                "field_app_secret": "meta-secret",
            },
        )
        assert response.status_code == 302

        rows = {
            row.platform: row
            for row in PlatformCredential.objects.filter(
                organization=organization,
                platform__in=["facebook", "instagram", "threads"],
            )
        }
        assert set(rows) == {"facebook", "instagram", "threads"}
        for row in rows.values():
            assert row.is_configured is True
            assert row.credentials == {"app_id": "meta-app-id", "app_secret": "meta-secret"}
            assert row.test_result == PlatformCredential.TestResult.UNTESTED

        connect_response = authenticated_admin.get(
            reverse("social_accounts:connect", kwargs={"workspace_id": workspace.id})
        )
        assert connect_response.status_code == 200
        assert b'name="platform" value="facebook"' in connect_response.content
        assert b'name="platform" value="instagram"' in connect_response.content
        assert b'name="platform" value="threads"' in connect_response.content

    def test_blank_secret_preserves_existing_configured_value(self, authenticated_admin, organization):
        PlatformCredential.objects.create(
            organization=organization,
            platform=PlatformCredential.Platform.LINKEDIN_PERSONAL,
            credentials={"client_id": "old-client", "client_secret": "old-secret"},
            is_configured=True,
        )

        response = authenticated_admin.post(
            reverse("credentials:list"),
            {
                "group": "linkedin_personal",
                "action": "save",
                "field_client_id": "new-client",
                "field_client_secret": "",
            },
        )
        assert response.status_code == 302

        row = PlatformCredential.objects.get(
            organization=organization,
            platform=PlatformCredential.Platform.LINKEDIN_PERSONAL,
        )
        assert row.is_configured is True
        assert row.credentials == {"client_id": "new-client", "client_secret": "old-secret"}

    def test_missing_new_secret_does_not_create_partial_credentials(self, authenticated_admin, organization):
        response = authenticated_admin.post(
            reverse("credentials:list"),
            {
                "group": "tiktok",
                "action": "save",
                "field_client_key": "tiktok-client",
                "field_client_secret": "",
            },
        )
        assert response.status_code == 302
        assert not PlatformCredential.objects.filter(
            organization=organization,
            platform=PlatformCredential.Platform.TIKTOK,
        ).exists()

    def test_clear_group_disables_saved_credentials(self, authenticated_admin, organization):
        for platform in (PlatformCredential.Platform.YOUTUBE, PlatformCredential.Platform.GOOGLE_BUSINESS):
            PlatformCredential.objects.create(
                organization=organization,
                platform=platform,
                credentials={"client_id": "google-client", "client_secret": "google-secret"},
                is_configured=True,
            )

        response = authenticated_admin.post(
            reverse("credentials:list"),
            {
                "group": "google",
                "action": "clear",
            },
        )
        assert response.status_code == 302

        for row in PlatformCredential.objects.filter(
            organization=organization, platform__in=["youtube", "google_business"]
        ):
            assert row.is_configured is False
            assert row.credentials == {}
