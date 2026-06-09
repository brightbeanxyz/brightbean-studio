"""HTTP-level tests for composer save_post and autosave tag normalization.

Verifies that excess tags are silently truncated and that XSS payloads survive
to storage and render escaped.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.common.validators import (
    MAX_TAG_LENGTH,
    MAX_TAGS,
    MAX_YT_TAGS_TOTAL_CHARS,
)
from apps.composer.models import PlatformPost, Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


class SavePostTagsTests(TestCase):
    """POST /workspace/<id>/composer/compose/save/"""

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
        self.save_url = reverse("composer:save_post", kwargs={"workspace_id": self.workspace.id})

    def _save_payload(self, tags_value, extra=None):
        payload = {
            "action": "save_draft",
            "title": "Test post",
            "caption": "body",
            "tags": tags_value,
        }
        if extra:
            payload.update(extra)
        return payload

    def test_30_tags_truncated_to_max(self):
        raw_tags = ",".join(f"tag{i}" for i in range(30))
        response = self.client.post(self.save_url, data=self._save_payload(raw_tags))
        self.assertIn(response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()
        self.assertIsNotNone(post)
        self.assertEqual(len(post.tags), MAX_TAGS)
        self.assertEqual(post.tags[0], "tag0")
        self.assertEqual(post.tags[-1], f"tag{MAX_TAGS - 1}")

    def test_oversized_tag_truncated(self):
        long_tag = "x" * (MAX_TAG_LENGTH + 50)
        response = self.client.post(self.save_url, data=self._save_payload(long_tag))
        self.assertIn(response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()
        self.assertEqual(post.tags, ["x" * MAX_TAG_LENGTH])

    def test_xss_payload_persists_verbatim(self):
        payload = "<script>alert(1)</script>"
        response = self.client.post(self.save_url, data=self._save_payload(payload))
        self.assertIn(response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()
        self.assertEqual(post.tags, [payload])

    def test_xss_payload_renders_escaped_in_compose_edit(self):
        """Post a tag with HTML, then GET the compose edit page; assert escaped."""
        payload = "<script>alert(1)</script>"
        save_response = self.client.post(self.save_url, data=self._save_payload(payload))
        self.assertIn(save_response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()

        edit_url = reverse(
            "composer:compose_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": post.id},
        )
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        # The page renders the tag list inside an x-data attribute via the
        # json_attr filter — must be HTML-escaped.
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn(f'"{payload}"', body)
        self.assertNotIn("<script>alert(1)</script>", body)

    def test_empty_tags_stores_empty_list(self):
        response = self.client.post(self.save_url, data=self._save_payload(""))
        self.assertIn(response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()
        self.assertEqual(post.tags, [])

    def test_compose_edit_renders_json_script_containers(self):
        """Follow-up 1: the four |json_script containers must be present in extra_js."""
        save_response = self.client.post(self.save_url, data=self._save_payload(""))
        self.assertIn(save_response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()

        edit_url = reverse(
            "composer:compose_edit",
            kwargs={"workspace_id": self.workspace.id, "post_id": post.id},
        )
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        # Each json_script container must render as a <script type="application/json" id="...">
        self.assertIn('<script id="composer-selected-accounts" type="application/json">', body)
        self.assertIn('<script id="composer-char-limits" type="application/json">', body)
        self.assertIn('<script id="composer-platform-extras" type="application/json">', body)
        self.assertIn('<script id="composer-media-items" type="application/json">', body)
        # The JS readers must reference the same IDs
        self.assertIn("document.getElementById('composer-selected-accounts')", body)
        self.assertIn("document.getElementById('composer-char-limits')", body)
        self.assertIn("document.getElementById('composer-platform-extras')", body)
        self.assertIn("document.getElementById('composer-media-items')", body)
        # No |safe leftovers
        self.assertNotIn("{{ selected_account_ids|safe }}", body)
        self.assertNotIn("{{ char_limits_json|safe }}", body)
        self.assertNotIn("{{ media_items_json|safe }}", body)


class YouTubePlatformTagsTests(TestCase):
    """POST /workspace/<id>/composer/compose/save/ with yt_tags_<acc_id>."""

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
        self.youtube_account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="youtube",
            account_platform_id="yt-1",
            account_name="Test YT Channel",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.client.force_login(self.user)
        self.save_url = reverse("composer:save_post", kwargs={"workspace_id": self.workspace.id})

    def test_yt_tags_truncated_to_total_chars_cap(self):
        # 25 tags × 30 chars + 24 delimiters = 774 > 500. Helper must truncate.
        tags_raw = ",".join("y" * 30 for _ in range(25))
        payload = {
            "action": "save_draft",
            "title": "YT post",
            "caption": "body",
            "tags": "",
            "selected_accounts": str(self.youtube_account.id),
            f"yt_tags_{self.youtube_account.id}": tags_raw,
        }
        response = self.client.post(self.save_url, data=payload)
        self.assertIn(response.status_code, (200, 204, 302))
        post = Post.objects.filter(workspace=self.workspace).order_by("-created_at").first()
        platform_post = PlatformPost.objects.get(post=post, social_account=self.youtube_account)
        stored_tags = platform_post.platform_extra.get("tags", [])
        total = sum(len(t) for t in stored_tags) + max(0, len(stored_tags) - 1)
        self.assertLessEqual(total, MAX_YT_TAGS_TOTAL_CHARS)
        self.assertGreater(len(stored_tags), 0)
