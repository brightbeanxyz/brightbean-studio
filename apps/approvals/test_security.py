"""Security regression tests for approvals comments (V9)."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import PostComment
from apps.composer.models import Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


def _make_user(email):
    user = User.objects.create_user(
        email=email,
        password="testpass123",
        tos_accepted_at=timezone.now(),
    )
    # The accounts post_save signal auto-provisions a default Organization +
    # Workspace + OrgMembership for every new User. Tests that want to attach
    # the user to a specific org must start from a clean slate, otherwise the
    # RBAC middleware (which does OrgMembership.objects.filter(...).first())
    # may pick the auto-org instead of the test org.
    from apps.members.models import OrgMembership, WorkspaceMembership
    from apps.organizations.models import Organization

    auto_org_ids = list(OrgMembership.objects.filter(user=user).values_list("organization_id", flat=True))
    WorkspaceMembership.objects.filter(user=user).delete()
    OrgMembership.objects.filter(user=user).delete()
    Organization.objects.filter(id__in=auto_org_ids).delete()
    return user


class EditCommentWorkspaceScopeTests(TestCase):
    """V9: edit_comment must reject cross-workspace post_id."""

    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.ws_a = Workspace.objects.create(organization=self.org, name="WS-A")
        self.ws_b = Workspace.objects.create(organization=self.org, name="WS-B")
        self.user = _make_user("user@example.com")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.ws_a, workspace_role="editor")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.ws_b, workspace_role="editor")

        self.post_b = Post.objects.create(workspace=self.ws_b, author=self.user, caption="b")
        self.comment = PostComment.objects.create(
            post=self.post_b,
            author=self.user,
            body="hi",
            visibility=PostComment.Visibility.INTERNAL,
        )

    def test_cross_workspace_edit_returns_404(self):
        self.client.force_login(self.user)
        # Edit a comment that lives in WS-B, but POST through WS-A's URL.
        url = reverse(
            "approvals:edit_comment",
            kwargs={
                "workspace_id": self.ws_a.id,
                "post_id": self.post_b.id,
                "comment_id": self.comment.id,
            },
        )
        response = self.client.post(url, data={"body": "rewritten"})
        self.assertEqual(response.status_code, 404)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.body, "hi")

    def test_same_workspace_edit_succeeds(self):
        self.client.force_login(self.user)
        url = reverse(
            "approvals:edit_comment",
            kwargs={
                "workspace_id": self.ws_b.id,
                "post_id": self.post_b.id,
                "comment_id": self.comment.id,
            },
        )
        response = self.client.post(url, data={"body": "rewritten"})
        self.assertLess(response.status_code, 400)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.body, "rewritten")
