import io
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.brands.models import BrandProfile
from apps.composer.models import Post, PostMedia
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

from ..forms import AIProviderConfigurationForm
from ..image_providers import generate_image
from ..models import AIProviderConfiguration, VisualBrief
from ..providers import ProviderError
from ..visuals import process_visual_brief, queue_visual_brief


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


class VisualBriefTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="visual@example.com", password="pass12345", tos_accepted_at=timezone.now()
        )
        OrgMembership.objects.filter(user=self.user).delete()
        self.organization = Organization.objects.create(name="Visual Agency")
        self.workspace = Workspace.objects.create(organization=self.organization, name="Visual Client")
        OrgMembership.objects.create(user=self.user, organization=self.organization, org_role="owner")
        WorkspaceMembership.objects.create(
            user=self.user, workspace=self.workspace, workspace_role="owner"
        )
        self.brand = BrandProfile.objects.create(workspace=self.workspace, name="NEXUS", brand_voice="Calm")
        AIProviderConfiguration.objects.create(
            organization=self.organization,
            provider="agnes",
            api_key="secret",
            default_model="agnes-image-2.1-flash",
            is_enabled=True,
        )

    @patch("apps.content_intelligence.tasks.run_visual_generation")
    def test_visual_brief_is_queued(self, run_visual_generation):
        brief = VisualBrief.objects.create(
            workspace=self.workspace,
            brand=self.brand,
            provider="agnes",
            objective="Launch visual",
            requested_by=self.user,
        )
        queue_visual_brief(brief=brief)
        run_visual_generation.assert_called_once_with(str(brief.id))

    @patch("apps.content_intelligence.visuals.generate_image", return_value=png_bytes())
    def test_generated_image_is_registered_and_attached_to_post(self, _generate_image):
        post = Post.objects.create(workspace=self.workspace, author=self.user, caption="Launch")
        brief = VisualBrief.objects.create(
            workspace=self.workspace,
            brand=self.brand,
            post=post,
            provider="agnes",
            objective="Launch visual",
            requested_by=self.user,
        )
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            asset = process_visual_brief(brief.id)
            brief.refresh_from_db()
            self.assertEqual(brief.status, VisualBrief.Status.COMPLETED)
            self.assertEqual(brief.media_asset, asset)
            self.assertTrue(PostMedia.objects.filter(post=post, media_asset=asset).exists())
            self.assertEqual(asset.source, "ai_agnes")

    def test_provider_url_allowlist_rejects_untrusted_host(self):
        configuration = AIProviderConfiguration(organization=self.organization, provider="agnes")
        form = AIProviderConfigurationForm(
            data={"base_url": "https://evil.example", "daily_request_limit": 10, "timeout_seconds": 30,
                  "max_retries": 1, "is_enabled": False},
            instance=configuration,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("allowlist", form.errors["base_url"][0])

    @patch("apps.content_intelligence.image_providers._post", return_value={"data": [{"url": "https://evil.example/a.png"}]})
    def test_provider_response_rejects_untrusted_download_url(self, _post):
        with self.assertRaisesRegex(ProviderError, "untrusted"):
            generate_image(provider="agnes", model="", prompt="test", size="1024x1024", api_key="secret")
