from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.brands.models import BrandProfile
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

from ..generation import create_composer_draft, request_generation
from ..models import GeneratedContent, GenerationRequest
from ..providers import ProviderError


class GenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ai@example.com", password="pass12345", tos_accepted_at=timezone.now()
        )
        OrgMembership.objects.filter(user=self.user).delete()
        org = Organization.objects.create(name="Agency")
        self.workspace = Workspace.objects.create(organization=org, name="Client")
        OrgMembership.objects.create(user=self.user, organization=org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, workspace_role="owner")
        self.brand = BrandProfile.objects.create(
            workspace=self.workspace,
            name="NEXUS",
            brand_voice="Evidence-based",
            content_pillars=["AI"],
            prohibited_terms=["miracle"],
        )

    @patch("apps.content_intelligence.generation.generate_text")
    def test_generation_persists_draft_and_context(self, generate_text):
        generate_text.return_value = "Reviewed draft with hook and CTA."
        request, output = request_generation(
            brand=self.brand,
            provider="openai",
            platform="linkedin",
            content_type="authority",
            user=self.user,
            audience="Recruiters",
            previous_content=["old"],
            analytics={"engagement_rate": 0.4},
        )
        self.assertEqual(request.status, GenerationRequest.Status.COMPLETED)
        self.assertEqual(output.status, GeneratedContent.Status.DRAFT)
        self.assertEqual(request.context["previous_content"], ["old"])
        self.assertEqual(output.metadata["strategy_version"], 1)

    @patch("apps.content_intelligence.generation.generate_text", side_effect=ProviderError("provider down"))
    def test_provider_failure_is_audited(self, _generate_text):
        with self.assertRaises(ProviderError):
            request_generation(
                brand=self.brand, provider="ollama", platform="instagram", content_type="post", user=self.user
            )
        request = GenerationRequest.objects.get(brand=self.brand)
        self.assertEqual(request.status, GenerationRequest.Status.FAILED)
        self.assertFalse(GeneratedContent.objects.exists())

    @patch("apps.content_intelligence.generation.generate_text", return_value="Draft caption")
    def test_generated_content_creates_one_composer_draft(self, _generate_text):
        _, output = request_generation(
            brand=self.brand, provider="openai", platform="linkedin", content_type="post", user=self.user
        )
        post, created = create_composer_draft(output=output, user=self.user)
        same_post, created_again = create_composer_draft(output=output, user=self.user)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(same_post, post)
        self.assertEqual(post.caption, "Draft caption")
        self.assertEqual(post.workspace, self.workspace)
