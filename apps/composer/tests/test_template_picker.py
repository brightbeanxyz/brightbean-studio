"""HTTP-level tests for the composer template picker view.

Guards the workspace scoping of saved post templates surfaced through the
"Use Template" picker on the composer page (issue #46).
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.composer.models import PostTemplate
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


class TemplatePickerTests(TestCase):
    """GET /workspace/<id>/composer/templates/picker/"""

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
        self.picker_url = reverse("composer:template_picker", kwargs={"workspace_id": self.workspace.id})

    def test_picker_returns_templates_for_workspace(self):
        PostTemplate.objects.create(
            workspace=self.workspace,
            name="Launch announcement",
            description="Reusable launch copy",
            template_data={"caption": "We just launched!"},
            created_by=self.user,
        )
        PostTemplate.objects.create(
            workspace=self.workspace,
            name="Weekly digest",
            description="",
            template_data={"caption": "This week at Acme..."},
            created_by=self.user,
        )

        response = self.client.get(self.picker_url)

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("Launch announcement", body)
        self.assertIn("Weekly digest", body)
        self.assertNotIn("No templates yet.", body)

    def test_picker_excludes_other_workspace_templates(self):
        other_workspace = Workspace.objects.create(organization=self.org, name="Other Workspace")
        PostTemplate.objects.create(
            workspace=other_workspace,
            name="Secret template",
            template_data={"caption": "Hidden"},
            created_by=self.user,
        )
        PostTemplate.objects.create(
            workspace=self.workspace,
            name="Mine",
            template_data={"caption": "Visible"},
            created_by=self.user,
        )

        response = self.client.get(self.picker_url)

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("Mine", body)
        self.assertNotIn("Secret template", body)

    def test_picker_empty_state(self):
        response = self.client.get(self.picker_url)

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("No templates yet.", body)
