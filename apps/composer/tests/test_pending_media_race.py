"""Uploads that finish after autosave created the post must still attach.

The composer starts an upload against the post-less endpoint; if autosave
creates the post while it is in flight, the asset lands in the session's
pending list. The next save — to the post's own URL — must drain that list,
or the post publishes without its media (a YouTube post then fails with
"only supports VIDEO and SHORT post types").
"""

import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PendingMediaRaceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        self.org = Organization.objects.create(name="Test Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Test Workspace")
        OrgMembership.objects.create(
            user=self.user,
            organization=self.org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
        )
        self.client.force_login(self.user)
        # Autosave already created the post before the upload finished.
        self.post = Post.objects.create(workspace=self.workspace, author=self.user, caption="hi")

    def _upload_without_post(self):
        response = self.client.post(
            reverse("composer:upload_media", kwargs={"workspace_id": self.workspace.id}),
            {"file": SimpleUploadedFile("clip.mp4", b"\x00" * 64, content_type="video/mp4")},
        )
        self.assertEqual(response.status_code, 200)
        return self.client.session[f"pending_media_{self.workspace.id}"][0]

    def _attached_ids(self):
        return [str(pm.media_asset_id) for pm in self.post.media_attachments.all()]

    def test_save_on_existing_post_attaches_pending_upload(self):
        asset_id = self._upload_without_post()

        self.client.post(
            reverse("composer:save_post_edit", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id}),
            {"action": "save_draft", "caption": "hi"},
        )

        self.assertEqual(self._attached_ids(), [asset_id])
        self.assertNotIn(f"pending_media_{self.workspace.id}", self.client.session)

    def test_autosave_on_existing_post_attaches_pending_upload(self):
        asset_id = self._upload_without_post()

        self.client.post(
            reverse("composer:autosave_edit", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id}),
            {"caption": "hi"},
        )

        self.assertEqual(self._attached_ids(), [asset_id])
