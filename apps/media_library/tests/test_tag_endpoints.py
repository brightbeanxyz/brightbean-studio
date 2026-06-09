"""HTTP-level tests for the media library tag-update endpoint.

Covers the asset_tags POST contract: validation, overflow rejection, dedup,
cross-workspace isolation, and end-to-end XSS round-trip.
"""

import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.common.validators import MAX_TAG_LENGTH, MAX_TAGS
from apps.media_library.models import MediaAsset
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


class AssetTagEndpointTests(TestCase):
    """POST /workspace/<id>/media/<asset_id>/tags/"""

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
        self.asset = MediaAsset.objects.create(
            organization=self.org,
            workspace=self.workspace,
            uploaded_by=self.user,
            file="media_library/tests/asset.png",
            filename="asset.png",
            media_type=MediaAsset.MediaType.IMAGE,
            mime_type="image/png",
            file_size=128,
            source="upload",
        )
        self.client.force_login(self.user)
        self.url = reverse(
            "media_library:asset_tags",
            kwargs={"workspace_id": self.workspace.id, "asset_id": self.asset.id},
        )

    def _post_json(self, body):
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_happy_path_persists_tags(self):
        response = self._post_json(["alpha", "beta", "gamma"])
        self.assertEqual(response.status_code, 200)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.tags, ["alpha", "beta", "gamma"])

    def test_dedupes_tags(self):
        response = self._post_json(["alpha", "alpha", "beta", "alpha"])
        self.assertEqual(response.status_code, 200)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.tags, ["alpha", "beta"])

    def test_strips_whitespace(self):
        self._post_json(["  alpha  ", "beta"])
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.tags, ["alpha", "beta"])

    def test_rejects_over_max_tags(self):
        response = self._post_json([f"t{i}" for i in range(MAX_TAGS + 1)])
        self.assertEqual(response.status_code, 400)
        self.assertIn("too many tags", response.json()["error"])

    def test_rejects_oversized_tag(self):
        response = self._post_json(["x" * (MAX_TAG_LENGTH + 1)])
        self.assertEqual(response.status_code, 400)
        self.assertIn("too long", response.json()["error"])

    def test_rejects_non_list_body(self):
        response = self._post_json({"tags": ["alpha"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a list", response.json()["error"])

    def test_rejects_non_string_element(self):
        response = self._post_json(["alpha", 123, "beta"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a string", response.json()["error"])

    def test_unauthenticated_request_redirects(self):
        self.client.logout()
        response = self._post_json(["alpha"])
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_cross_workspace_user_gets_403(self):
        """User not a member of this workspace must not reach the view at all.

        The RBAC middleware rejects with PermissionDenied (403) before the
        view body executes, so the asset's existence is not leaked.
        """
        other_user = User.objects.create_user(
            email="outsider@example.com",
            password="testpass123",
            tos_accepted_at=timezone.now(),
        )
        other_org = Organization.objects.create(name="Other Org")
        OrgMembership.objects.create(
            user=other_user,
            organization=other_org,
            org_role=OrgMembership.OrgRole.OWNER,
        )
        self.client.force_login(other_user)
        response = self._post_json(["alpha"])
        self.assertEqual(response.status_code, 403)
        # Existing tags must not have changed
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.tags, [])

    def test_xss_payload_persists_verbatim_and_renders_escaped(self):
        """A tag containing HTML must round-trip through save → render escaped."""
        payload = "<script>alert(1)</script>"
        response = self._post_json([payload])
        self.assertEqual(response.status_code, 200)
        self.asset.refresh_from_db()
        # Server-side: the string is stored verbatim — escape happens at render.
        self.assertEqual(self.asset.tags, [payload])

        # Now render the tag list partial via the HTMX response path and assert
        # the rendered HTML contains escaped output, not raw <script>.
        response = self.client.post(
            self.url,
            data=json.dumps([payload]),
            content_type="application/json",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        rendered = response.content.decode("utf-8")
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)
