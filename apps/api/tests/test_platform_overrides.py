"""Gap 2: per-platform overrides of title/caption/first_comment on POST /posts.

The cookie-authenticated UI accepts three form fields per account
(see [apps/composer/views.py:85-96]) and writes them into
``PlatformPost.platform_specific_*``. The Agent API now exposes the same
mechanism via ``platform_overrides`` on ``CreatePostRequest``.

Tests cover:

* Each override field independently applies (only the ones provided).
* Sending ``null`` (or omitting) leaves the post's default in place.
* The override social_account_id must match the post's target account.
"""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.composer.models import PlatformPost, Post
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="overrides@example.com",
        password="testpass123",
        name="Overrides",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Overrides Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Overrides WS", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
    return WorkspaceMembership.objects.create(
        user=user, workspace=workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-overrides",
        account_name="Overrides LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="overrides",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


def _post(client, body: dict):
    return client.post("/api/v1/posts/", data=json.dumps(body), content_type="application/json")


@pytest.mark.django_db
class TestPlatformOverrides:
    def test_all_three_fields_persist_to_platform_specific_columns(self, client_with_token, social_account):
        r = _post(
            client_with_token,
            {
                "social_account_id": str(social_account.id),
                "caption": "default caption",
                "title": "default title",
                "first_comment": "default first comment",
                "platform_overrides": [
                    {
                        "social_account_id": str(social_account.id),
                        "title": "LinkedIn-specific title",
                        "caption": "LinkedIn-specific caption",
                        "first_comment": "LinkedIn-specific first comment",
                    }
                ],
                "action": "draft",
            },
        )
        assert r.status_code == 201, r.content
        post = Post.objects.get()
        pp = PlatformPost.objects.get(post=post)
        assert pp.platform_specific_title == "LinkedIn-specific title"
        assert pp.platform_specific_caption == "LinkedIn-specific caption"
        assert pp.platform_specific_first_comment == "LinkedIn-specific first comment"
        # effective_* falls through correctly.
        assert pp.effective_title == "LinkedIn-specific title"
        assert pp.effective_caption == "LinkedIn-specific caption"
        assert pp.effective_first_comment == "LinkedIn-specific first comment"

    def test_only_provided_fields_override(self, client_with_token, social_account):
        """An override entry that sets ``caption`` only must leave
        title and first_comment falling back to the post's defaults.
        """
        r = _post(
            client_with_token,
            {
                "social_account_id": str(social_account.id),
                "caption": "default caption",
                "title": "default title",
                "first_comment": "default first comment",
                "platform_overrides": [
                    {
                        "social_account_id": str(social_account.id),
                        "caption": "ONLY caption is platform-specific",
                    }
                ],
                "action": "draft",
            },
        )
        assert r.status_code == 201, r.content
        pp = PlatformPost.objects.get()
        assert pp.platform_specific_caption == "ONLY caption is platform-specific"
        assert pp.platform_specific_title is None
        assert pp.platform_specific_first_comment is None
        # effective_title / effective_first_comment fall back to post.
        assert pp.effective_title == "default title"
        assert pp.effective_first_comment == "default first comment"
        assert pp.effective_caption == "ONLY caption is platform-specific"

    def test_empty_string_override_is_explicit_blank(self, client_with_token, social_account):
        """Empty string is treated as an explicit override (to blank the
        value out for this platform only). ``None`` would be "no override".
        """
        r = _post(
            client_with_token,
            {
                "social_account_id": str(social_account.id),
                "caption": "default caption",
                "first_comment": "default first comment",
                "platform_overrides": [
                    {
                        "social_account_id": str(social_account.id),
                        "first_comment": "",
                    }
                ],
                "action": "draft",
            },
        )
        assert r.status_code == 201, r.content
        pp = PlatformPost.objects.get()
        assert pp.platform_specific_first_comment == ""
        assert pp.effective_first_comment == ""  # explicit blank, NOT the post's default

    def test_no_platform_overrides_field_keeps_defaults(self, client_with_token, social_account):
        """The existing behavior — no overrides — must still work."""
        r = _post(
            client_with_token,
            {
                "social_account_id": str(social_account.id),
                "caption": "just defaults",
                "action": "draft",
            },
        )
        assert r.status_code == 201
        pp = PlatformPost.objects.get()
        assert pp.platform_specific_title is None
        assert pp.platform_specific_caption is None
        assert pp.platform_specific_first_comment is None

    def test_override_for_unrelated_account_is_422(self, db, client_with_token, social_account, workspace):
        """The plan calls this out: silently no-op'd overrides are a
        footgun. An override social_account_id that isn't this post's
        target must be rejected before persistence.
        """
        from apps.social_accounts.models import SocialAccount

        other = SocialAccount.objects.create(
            workspace=workspace,
            platform="linkedin_personal",
            account_platform_id="li-other",
            account_name="Other",
            connection_status="connected",
        )
        r = _post(
            client_with_token,
            {
                "social_account_id": str(social_account.id),
                "caption": "default",
                "platform_overrides": [
                    {
                        "social_account_id": str(other.id),
                        "caption": "would be applied to wrong account",
                    }
                ],
                "action": "draft",
            },
        )
        assert r.status_code == 422, r.content
        assert "social_account_id" in r.json()["detail"]
        assert Post.objects.count() == 0
