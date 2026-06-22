"""Tests for clone_post (Clone / Repost) — service + endpoint."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PlatformPost, Post
from apps.composer.services import clone_post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


class ClonePostServiceTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Clone Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Clone WS")
        self.author = User.objects.create_user(
            email="author@example.com", password="pw", tos_accepted_at=timezone.now()
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-clone",
            account_name="TT",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(
            workspace=self.workspace,
            author=self.author,
            title="Launch",
            caption="hello world",
            tags=["a", "b"],
        )
        self.pp = PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            published_at=timezone.now(),
            scheduled_at=timezone.now(),
            platform_specific_caption="tiktok caption",
            platform_extra={"privacy_level": "SELF_ONLY", "disable_duet": True},
        )

    def test_clone_creates_independent_draft_copy(self):
        clone = clone_post(self.post, author=self.author)

        self.assertNotEqual(clone.id, self.post.id)
        self.assertEqual(clone.caption, "hello world")
        self.assertEqual(clone.title, "Copy of Launch")
        self.assertEqual(clone.tags, ["a", "b"])
        self.assertIsNone(clone.scheduled_at)

        child = clone.platform_posts.get()
        self.assertEqual(child.status, PlatformPost.Status.DRAFT)
        self.assertIsNone(child.scheduled_at)
        self.assertIsNone(child.published_at)
        self.assertEqual(child.social_account, self.account)
        self.assertEqual(child.platform_specific_caption, "tiktok caption")
        self.assertEqual(child.platform_extra, {"privacy_level": "SELF_ONLY", "disable_duet": True})

        # Mutating the clone's extras must not bleed into the source (deepcopy).
        child.platform_extra["privacy_level"] = "PUBLIC"
        child.save(update_fields=["platform_extra"])
        self.pp.refresh_from_db()
        self.assertEqual(self.pp.platform_extra["privacy_level"], "SELF_ONLY")


class ClonePostEndpointTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Clone EP Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="Clone EP WS")
        self.owner = User.objects.create_user(email="owner@example.com", password="pw", tos_accepted_at=timezone.now())
        OrgMembership.objects.create(user=self.owner, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.owner, workspace=self.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-clone",
            account_name="LI",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.post = Post.objects.create(workspace=self.workspace, author=self.owner, caption="published thing")
        PlatformPost.objects.create(
            post=self.post,
            social_account=self.account,
            status=PlatformPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )

    def test_clone_endpoint_creates_draft_and_redirects(self):
        self.client.force_login(self.owner)
        url = reverse("composer:clone_post", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id})
        resp = self.client.post(url, HTTP_HX_REQUEST="true")

        self.assertEqual(resp.status_code, 204)
        redirect_url = resp.headers.get("HX-Redirect", "")
        self.assertIn("/compose/", redirect_url)

        clone = Post.objects.exclude(id=self.post.id).get(workspace=self.workspace)
        self.assertEqual(clone.caption, "published thing")
        self.assertEqual(clone.platform_posts.get().status, PlatformPost.Status.DRAFT)
        self.assertIn(str(clone.id), redirect_url)

    def test_clone_endpoint_denies_member_without_create_posts(self):
        viewer = User.objects.create_user(email="viewer@example.com", password="pw", tos_accepted_at=timezone.now())
        WorkspaceMembership.objects.create(
            user=viewer, workspace=self.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.VIEWER
        )
        self.client.force_login(viewer)
        url = reverse("composer:clone_post", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id})
        resp = self.client.post(url, HTTP_HX_REQUEST="true")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Post.objects.filter(workspace=self.workspace).count(), 1)
