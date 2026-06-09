"""Tests for the CSV upload size cap (DoS guard)."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.views import MAX_CSV_UPLOAD_BYTES
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


class CSVUploadSizeCapTests(TestCase):
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
        self.url = reverse("composer:csv_upload", kwargs={"workspace_id": self.workspace.id})

    def test_oversized_csv_rejected_without_reading(self):
        # 1 byte over the cap. Use ASCII bytes so the size matches `len`.
        oversized = b"a" * (MAX_CSV_UPLOAD_BYTES + 1)
        upload = SimpleUploadedFile("big.csv", oversized, content_type="text/csv")
        response = self.client.post(self.url, data={"csv_file": upload})
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("too large", body)

    def test_under_cap_csv_proceeds_to_mapping(self):
        small_csv = b"date,platform,caption\n2026-05-01,instagram,Hello\n"
        upload = SimpleUploadedFile("small.csv", small_csv, content_type="text/csv")
        response = self.client.post(self.url, data={"csv_file": upload})
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertNotIn("too large", body)
