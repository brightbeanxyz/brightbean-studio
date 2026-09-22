"""Comment attachments are served by a view, not by a public MEDIA_URL route.

``PostComment.visibility`` can be ``internal``, and
``apps/client_portal/views.py`` filters those out of what a portal client is
shown. When local storage started serving MEDIA_ROOT in production, a public
``/media/comment_attachments/...`` URL would have handed back exactly what that
filter withholds, so ``config.urls.PUBLIC_MEDIA_PREFIXES`` leaves the prefix out
and readers come through here instead.
"""

import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import PostComment
from apps.composer.models import Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="bb-test-comment-attach-")


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def _make_user(email):
    user = User.objects.create_user(email=email, password="testpass123", tos_accepted_at=timezone.now())
    # The accounts post_save signal auto-provisions an Organization + Workspace
    # for every new User; clear it so the RBAC middleware resolves the test org.
    auto_org_ids = list(OrgMembership.objects.filter(user=user).values_list("organization_id", flat=True))
    WorkspaceMembership.objects.filter(user=user).delete()
    OrgMembership.objects.filter(user=user).delete()
    Organization.objects.filter(id__in=auto_org_ids).delete()
    return user


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CommentAttachmentAccessTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")

        self.member = _make_user("member@example.com")
        OrgMembership.objects.create(user=self.member, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.member, workspace=self.workspace, workspace_role="editor")

        self.outsider = _make_user("outsider@example.com")

        self.post = Post.objects.create(workspace=self.workspace, author=self.member, caption="p")
        self.comment = PostComment.objects.create(
            post=self.post,
            author=self.member,
            body="internal note",
            visibility=PostComment.Visibility.INTERNAL,
            attachment=ContentFile(b"png-bytes", name="note.png"),
        )

    def _url(self):
        return reverse(
            "approvals:comment_attachment",
            kwargs={
                "workspace_id": self.workspace.id,
                "post_id": self.post.id,
                "comment_id": self.comment.id,
            },
        )

    def test_workspace_member_gets_the_bytes(self):
        self.client.force_login(self.member)

        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"png-bytes")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self._url())

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_non_member_is_refused(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self._url())

        self.assertIn(response.status_code, (403, 404))

    def test_comment_from_another_workspace_is_404(self):
        other_ws = Workspace.objects.create(organization=self.org, name="Other")
        WorkspaceMembership.objects.create(user=self.member, workspace=other_ws, workspace_role="editor")
        self.client.force_login(self.member)

        url = reverse(
            "approvals:comment_attachment",
            kwargs={
                "workspace_id": other_ws.id,
                "post_id": self.post.id,
                "comment_id": self.comment.id,
            },
        )

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_comment_without_an_attachment_is_404(self):
        bare = PostComment.objects.create(post=self.post, author=self.member, body="no file")
        self.client.force_login(self.member)

        url = reverse(
            "approvals:comment_attachment",
            kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id, "comment_id": bare.id},
        )

        self.assertEqual(self.client.get(url).status_code, 404)
