"""Sidebar Trustpilot card — who sees it, and how long a dismissal lasts.

The card asks for a review only once the user has something worth reviewing (a
connected channel in any of their workspaces), and closing it — or clicking
through to Trustpilot — hides it for the rest of that login only: the dismissal
is a timestamp on the user, and the next login's ``last_login`` overtakes it.
"""

import tempfile
from io import BytesIO

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.accounts.views import _handle_password_update, _handle_photo_update
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

# The card's class also appears in base.html's pre-paint CSS, so match its copy.
BANNER = "Enjoying BrightBean?"
TRUSTPILOT_URL = "https://www.trustpilot.com/review/brightbean.xyz"


class ReviewBannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org = Organization.objects.create(name="Org")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        self.ws = self._make_workspace("WS")
        self.client.force_login(self.user)

    def _make_workspace(self, name):
        ws = Workspace.objects.create(organization=self.org, name=name, timezone="Europe/Berlin")
        WorkspaceMembership.objects.create(
            user=self.user, workspace=ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        return ws

    def _connect(self, workspace, status=SocialAccount.ConnectionStatus.CONNECTED):
        return SocialAccount.objects.create(
            workspace=workspace,
            platform="linkedin_personal",
            account_platform_id=f"li-{workspace.id}",
            account_name="Channel",
            connection_status=status,
        )

    def _workspace_page(self, workspace=None):
        workspace = workspace or self.ws
        return self.client.get(reverse("social_accounts:list", kwargs={"workspace_id": workspace.id}))

    def test_hidden_without_a_connected_channel(self):
        resp = self._workspace_page()
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, BANNER)

    def test_unhealthy_channels_do_not_count(self):
        self._connect(self.ws, status=SocialAccount.ConnectionStatus.DISCONNECTED)
        self.assertNotContains(self._workspace_page(), BANNER)

    def test_shown_with_a_connected_channel(self):
        self._connect(self.ws)
        resp = self._workspace_page()
        self.assertContains(resp, BANNER)
        self.assertContains(resp, f'href="{TRUSTPILOT_URL}" target="_blank"')
        self.assertContains(resp, reverse("accounts:dismiss_review_banner"))

    def test_channel_in_another_workspace_counts(self):
        other = self._make_workspace("Other")
        self._connect(other)
        self.assertContains(self._workspace_page(self.ws), BANNER)

    def test_shown_on_pages_without_a_workspace(self):
        self._connect(self.ws)
        resp = self.client.get(reverse("accounts:settings"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, BANNER)

    def test_dismiss_hides_it_for_the_rest_of_the_login(self):
        self._connect(self.ws)
        resp = self.client.post(reverse("accounts:dismiss_review_banner"))
        self.assertEqual(resp.status_code, 204)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.review_banner_dismissed_at)
        self.assertNotContains(self._workspace_page(), BANNER)
        self.assertNotContains(self.client.get(reverse("accounts:settings")), BANNER)

    def test_next_login_brings_it_back(self):
        self._connect(self.ws)
        self.client.post(reverse("accounts:dismiss_review_banner"))
        self.client.get(reverse("accounts:logout"))
        self.client.force_login(self.user)
        self.assertContains(self._workspace_page(), BANNER)

    def test_dismiss_requires_post(self):
        resp = self.client.get(reverse("accounts:dismiss_review_banner"))
        self.assertEqual(resp.status_code, 405)

    def test_dismiss_requires_login(self):
        self.client.logout()
        resp = self.client.post(reverse("accounts:dismiss_review_banner"))
        self.assertEqual(resp.status_code, 302)


class SettingsSavesKeepDismissalTests(TestCase):
    """A settings save already in flight must not undo a dismissal.

    Each handler gets a User read *before* the dismissal landed, which is what
    an avatar upload or password change holds when the user closes the card
    mid-request. A full ``save()`` would write that instance's stale
    ``review_banner_dismissed_at`` (None) back over the new timestamp.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.stale = User.objects.get(pk=self.user.pk)
        User.objects.filter(pk=self.user.pk).update(review_banner_dismissed_at=timezone.now())

    def _request(self, data):
        request = RequestFactory().post(reverse("accounts:settings"), data)
        request.user = self.stale
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        return request

    def _assert_dismissal_kept(self):
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.review_banner_dismissed_at)

    def test_password_change_keeps_dismissal(self):
        data = {"current_password": "testpass123", "password": "newpass123", "password_confirm": "newpass123"}
        _handle_password_update(self._request(data), self.stale)
        self._assert_dismissal_kept()
        self.assertTrue(self.user.check_password("newpass123"))

    def test_photo_removal_keeps_dismissal(self):
        _handle_photo_update(self._request({"delete_photo": "1"}), self.stale)
        self._assert_dismissal_kept()

    def test_photo_upload_keeps_dismissal(self):
        buf = BytesIO()
        Image.new("RGB", (200, 200)).save(buf, "PNG")
        avatar = SimpleUploadedFile("avatar.png", buf.getvalue(), content_type="image/png")
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            _handle_photo_update(self._request({"avatar": avatar}), self.stale)
            self._assert_dismissal_kept()
            self.assertTrue(self.user.avatar)
