from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.brands.forms import BrandProfileForm
from apps.brands.models import BrandProfile
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace


class BrandProfileTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="brand-owner@example.com", password="testpass123", tos_accepted_at=timezone.now()
        )
        # User provisioning creates defaults; isolate this fixture explicitly.
        OrgMembership.objects.filter(user=self.owner).delete()
        self.org = Organization.objects.create(name="Agency")
        self.workspace = Workspace.objects.create(organization=self.org, name="Client A")
        self.other_workspace = Workspace.objects.create(organization=self.org, name="Client B")
        OrgMembership.objects.create(user=self.owner, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.owner, workspace=self.workspace, workspace_role="owner")
        self.client.force_login(self.owner)

    def _payload(self, **overrides):
        payload = {
            "name": "NEXUS Wellness",
            "description": "Human-centered digital wellness.",
            "industry": "Digital Health",
            "target_audience": "HealthTech leaders",
            "brand_voice": "Evidence-based and accessible",
            "tone": "Professional",
            "vocabulary": "human-centered AI\nexercise science",
            "prohibited_terms": "miracle cure",
            "preferred_terminology": "behavior change",
            "primary_language": "English",
            "secondary_language": "Portuguese",
            "brand_colors": "#1D4ED8\n#10B981",
            "positioning": "AI + Digital Health + Exercise Science",
            "value_proposition": "Translate research into useful products.",
            "content_pillars": "Artificial Intelligence\nDigital Health",
            "cta_strategy": "Invite professional collaboration.",
            "posting_frequency": "3 posts per week",
            "target_geographies": "United States\nBrazil",
            "target_personas": "Recruiters\nProduct leaders",
            "recruiting_objective": "Create international opportunities.",
            "business_objective": "Generate collaborations.",
            "is_active": "on",
        }
        payload.update(overrides)
        return payload

    def test_model_supports_multiple_brands_per_workspace(self):
        first = BrandProfile.objects.create(workspace=self.workspace, name="Brand One")
        second = BrandProfile.objects.create(workspace=self.workspace, name="Brand Two")
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(BrandProfile.objects.for_workspace(self.workspace.id).count(), 2)

    def test_model_rejects_invalid_color_and_duplicate_list_items(self):
        brand = BrandProfile(
            workspace=self.workspace,
            name="Invalid",
            brand_colors=["blue"],
            content_pillars=["AI", "ai"],
        )
        with self.assertRaises(ValidationError) as raised:
            brand.full_clean()
        self.assertIn("brand_colors", raised.exception.message_dict)
        self.assertIn("content_pillars", raised.exception.message_dict)

    def test_form_normalizes_multiline_fields(self):
        form = BrandProfileForm(self._payload(), workspace=self.workspace)
        self.assertTrue(form.is_valid(), form.errors)
        brand = form.save()
        self.assertEqual(brand.content_pillars, ["Artificial Intelligence", "Digital Health"])
        self.assertEqual(brand.brand_colors, ["#1D4ED8", "#10B981"])
        self.assertEqual(brand.organization, self.org)

    def test_owner_can_create_brand(self):
        response = self.client.post(
            reverse("brands:create", kwargs={"workspace_id": self.workspace.id}), data=self._payload()
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BrandProfile.objects.filter(workspace=self.workspace, name="NEXUS Wellness").exists())

    def test_editor_cannot_create_or_edit_brand(self):
        editor = User.objects.create_user(
            email="editor@example.com", password="testpass123", tos_accepted_at=timezone.now()
        )
        OrgMembership.objects.filter(user=editor).delete()
        OrgMembership.objects.create(user=editor, organization=self.org, org_role="member")
        WorkspaceMembership.objects.create(user=editor, workspace=self.workspace, workspace_role="editor")
        brand = BrandProfile.objects.create(workspace=self.workspace, name="Protected")
        self.client.force_login(editor)

        create_response = self.client.get(reverse("brands:create", kwargs={"workspace_id": self.workspace.id}))
        edit_response = self.client.get(
            reverse("brands:edit", kwargs={"workspace_id": self.workspace.id, "brand_id": brand.id})
        )
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(edit_response.status_code, 403)

    def test_cross_workspace_brand_is_not_disclosed(self):
        BrandProfile.objects.create(workspace=self.other_workspace, name="Other Client")
        visible = BrandProfile.objects.create(workspace=self.workspace, name="Visible")
        response = self.client.get(reverse("brands:list", kwargs={"workspace_id": self.workspace.id}))
        self.assertContains(response, visible.name)
        self.assertNotContains(response, "Other Client")

    def test_cross_workspace_edit_returns_permission_denied_before_lookup(self):
        other_brand = BrandProfile.objects.create(workspace=self.other_workspace, name="Other Client")
        response = self.client.get(
            reverse("brands:edit", kwargs={"workspace_id": self.workspace.id, "brand_id": other_brand.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_duplicate_name_is_rejected_case_insensitively(self):
        BrandProfile.objects.create(workspace=self.workspace, name="NEXUS Wellness")
        form = BrandProfileForm(self._payload(name="nexus wellness"), workspace=self.workspace)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
