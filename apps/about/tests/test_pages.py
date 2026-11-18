"""The Source code link reaches every studio and portal user, and the pages it leads to."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone

from apps.about.apps import sync_site_record
from apps.about.version import running_commit
from apps.accounts.models import User
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

SHA = "14b92fc0123456789abcdef0123456789abcdef0"
REPO = "https://github.com/studio/brown-creative-studio"
SOURCE_LINK = "data-source-code-link"


@pytest.fixture(autouse=True)
def _pinned_source(settings):
    settings.SOURCE_CODE_URL = REPO
    settings.SOURCE_COMMIT = SHA
    running_commit.cache_clear()
    yield
    running_commit.cache_clear()


@pytest.fixture
def studio_user(db):
    org = Organization.objects.create(name="Brown Creative Studio")
    user = User.objects.create_user(email="owner@example.com", password="pw-123456789", tos_accepted_at=timezone.now())
    OrgMembership.objects.create(user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER)
    return user


@pytest.fixture
def portal_client(db, client):
    org = Organization.objects.create(name="Studio")
    workspace = Workspace.objects.create(organization=org, name="Client Restaurant")
    user = User.objects.create_user(email="client@example.com", password="pw-123456789", tos_accepted_at=timezone.now())
    WorkspaceMembership.objects.create(
        user=user, workspace=workspace, workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT
    )
    client.force_login(user)
    session = client.session
    session["is_portal_session"] = True
    session["portal_workspace_id"] = str(workspace.id)
    session.save()
    return client


# ── The link is visible everywhere ───────────────────────────────────────────


@pytest.mark.django_db
def test_sign_in_page_shows_source_link(client):
    response = client.get(reverse("account_login"))
    assert response.status_code == 200
    assert SOURCE_LINK in response.content.decode()


@pytest.mark.django_db
def test_studio_sidebar_shows_source_link_with_running_version(client, studio_user):
    client.force_login(studio_user)
    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    html = response.content.decode()
    assert SOURCE_LINK in html
    assert SHA[:7] in html


@pytest.mark.django_db
def test_portal_shows_source_link(portal_client):
    response = portal_client.get(reverse("client_portal:dashboard"))
    assert response.status_code == 200
    assert SOURCE_LINK in response.content.decode()


@pytest.mark.django_db
def test_portal_link_expired_page_shows_source_link(client):
    response = client.get(reverse("client_portal:magic_link_expired"))
    assert SOURCE_LINK in response.content.decode()


# Pages that render their own <html> shell instead of extending base.html or
# portal_base.html. Each must carry the footer partial; emails are exempt
# (AGPL section 13 is about users interacting over the network).
_TEMPLATE_DIRS = [Path(settings.BASE_DIR) / "templates", Path(settings.BASE_DIR) / "apps"]


def _standalone_page_templates():
    for root in _TEMPLATE_DIRS:
        for path in root.rglob("*.html"):
            if "/email/" in str(path) or "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"<!DOCTYPE", text, re.IGNORECASE) and "{% extends" not in text:
                yield path, text


def test_every_standalone_page_shell_includes_the_source_link():
    missing = []
    for path, text in _standalone_page_templates():
        if path.name == "base.html" and path.parent.name == "templates":
            ok = "about/_sidebar_source_link.html" in text and "about/_public_footer.html" in text
        else:
            ok = "about/_public_footer.html" in text
        if not ok:
            missing.append(str(path.relative_to(settings.BASE_DIR)))
    assert not missing, f"Page shells without the Source code link: {missing}"


# ── The source page ──────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_source_page_is_public_and_pinned_to_running_commit(client):
    response = client.get(reverse("about:source"))
    assert response.status_code == 200
    html = response.content.decode()
    assert f"{REPO}/tree/{SHA}" in html
    assert f"{REPO}/archive/{SHA}.zip" in html
    assert f'data-running-commit="{SHA}"' in html


@pytest.mark.django_db
def test_source_page_credits_brightbean(client):
    html = client.get(reverse("about:source")).content.decode()
    assert "Based on" in html
    assert "BrightBean Studio" in html
    assert "https://github.com/brightbeanxyz/brightbean-studio" in html
    assert "AGPL-3.0" in html


@pytest.mark.django_db
def test_source_page_without_known_commit_says_so(client, settings, tmp_path):
    settings.SOURCE_COMMIT = ""
    settings.BASE_DIR = tmp_path  # no .git here
    running_commit.cache_clear()
    html = client.get(reverse("about:source")).content.decode()
    assert "could not be determined" in html
    assert "/tree/" not in html


@pytest.mark.django_db
def test_source_page_without_repository(client, settings):
    settings.SOURCE_CODE_URL = ""
    settings.SUPPORT_EMAIL = "hello@studio.example"
    html = client.get(reverse("about:source")).content.decode()
    assert "has not been configured" in html
    assert "hello@studio.example" in html


@pytest.mark.django_db
def test_user_who_has_not_accepted_terms_can_read_source_and_policies(client):
    user = User.objects.create_user(email="new@example.com", password="pw-123456789")
    assert user.tos_accepted_at is None
    client.force_login(user)
    for name in ("about:source", "about:terms", "about:privacy"):
        assert client.get(reverse(name)).status_code == 200, name


# ── Legal pages ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_unpublished_policies_never_show_brightbeans(client, settings):
    settings.TERMS_URL = ""
    settings.PRIVACY_URL = ""
    for name in ("about:terms", "about:privacy"):
        html = client.get(reverse(name)).content.decode()
        assert "has not published this document" in html
        assert "brightbean.xyz" not in html


@pytest.mark.django_db
def test_published_policies_redirect(client, settings):
    settings.TERMS_URL = "https://studio.example/terms"
    settings.PRIVACY_URL = "https://studio.example/privacy"
    assert client.get(reverse("about:terms"))["Location"] == "https://studio.example/terms"
    assert client.get(reverse("about:privacy"))["Location"] == "https://studio.example/privacy"


@pytest.mark.django_db
def test_signup_page_links_to_studio_policies(client, settings):
    settings.SIGNUP_MODE = "open"
    settings.TERMS_URL = "https://studio.example/terms"
    html = client.get(reverse("account_signup")).content.decode()
    assert "https://studio.example/terms" in html
    assert "brightbean.xyz/terms" not in html


# ── Site record ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_site_record_follows_settings(settings):
    settings.SITE_NAME = "Brown Creative Studio"
    settings.APP_URL = "https://studio.example"
    sync_site_record(sender=None)
    site = Site.objects.get(pk=settings.SITE_ID)
    assert site.name == "Brown Creative Studio"
    assert site.domain == "studio.example"
