from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.brands.models import BrandProfile
from apps.composer.models import Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

from ..forms import CampaignForm
from ..models import Campaign, GeneratedContent, GenerationRequest


class ContentLibraryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="library@example.com", password="pass12345", tos_accepted_at=timezone.now()
        )
        OrgMembership.objects.filter(user=self.user).delete()
        self.organization = Organization.objects.create(name="Library Agency")
        self.workspace = Workspace.objects.create(organization=self.organization, name="Client A")
        self.other_workspace = Workspace.objects.create(organization=self.organization, name="Client B")
        OrgMembership.objects.create(user=self.user, organization=self.organization, org_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, workspace_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.other_workspace, workspace_role="owner")
        self.brand = BrandProfile.objects.create(workspace=self.workspace, name="NEXUS")
        self.other_brand = BrandProfile.objects.create(workspace=self.other_workspace, name="SECRET")
        self.client.force_login(self.user)

    def test_library_search_and_workspace_isolation(self):
        Post.objects.create(workspace=self.workspace, author=self.user, title="Visible launch", caption="Public")
        Post.objects.create(workspace=self.other_workspace, author=self.user, title="Secret launch", caption="Hidden")
        url = reverse("content_intelligence:content_library", kwargs={"workspace_id": self.workspace.id})
        response = self.client.get(url, {"q": "launch"})
        self.assertContains(response, "Visible launch")
        self.assertNotContains(response, "Secret launch")

    def test_library_search_includes_tags(self):
        Post.objects.create(
            workspace=self.workspace, author=self.user, title="Generic title", tags=["product-launch"]
        )
        url = reverse("content_intelligence:content_library", kwargs={"workspace_id": self.workspace.id})
        response = self.client.get(url, {"q": "product-launch"})
        self.assertContains(response, "Generic title")

    def test_library_paginates_unified_results(self):
        Post.objects.bulk_create([
            Post(workspace=self.workspace, author=self.user, title=f"Post {number}") for number in range(25)
        ])
        url = reverse("content_intelligence:content_library", kwargs={"workspace_id": self.workspace.id})
        response = self.client.get(url, {"page": 2})
        self.assertEqual(response.context["page"].paginator.count, 25)
        self.assertEqual(len(response.context["page"].object_list), 1)

    def test_bulk_archive_cannot_touch_another_workspace(self):
        local = Post.objects.create(workspace=self.workspace, author=self.user, title="Local")
        foreign = Post.objects.create(workspace=self.other_workspace, author=self.user, title="Foreign")
        url = reverse("content_intelligence:content_library_bulk", kwargs={"workspace_id": self.workspace.id})
        self.client.post(url, {"selected": [f"post:{local.id}", f"post:{foreign.id}"]})
        local.refresh_from_db()
        foreign.refresh_from_db()
        self.assertIsNotNone(local.archived_at)
        self.assertIsNone(foreign.archived_at)

    def test_campaign_form_only_accepts_workspace_brand(self):
        form = CampaignForm(
            data={"name": "Launch", "brand": self.other_brand.id, "status": Campaign.Status.ACTIVE},
            workspace=self.workspace,
        )
        self.assertFalse(form.is_valid())

    def test_generated_content_filter_and_archive(self):
        request = GenerationRequest.objects.create(
            workspace=self.workspace, brand=self.brand, provider="openai", platform="linkedin", content_type="post"
        )
        output = GeneratedContent.objects.create(
            request=request, workspace=self.workspace, brand=self.brand, platform="linkedin",
            content_type="post", body="AI launch copy"
        )
        url = reverse("content_intelligence:content_library_action", kwargs={"workspace_id": self.workspace.id})
        self.client.post(url, {"kind": "generated", "id": output.id, "action": "archive"})
        output.refresh_from_db()
        self.assertEqual(output.status, GeneratedContent.Status.ARCHIVED)
        self.assertIsNotNone(output.archived_at)

    def test_bulk_campaign_assignment_is_scoped(self):
        campaign = Campaign.objects.create(workspace=self.workspace, brand=self.brand, name="Launch")
        foreign_campaign = Campaign.objects.create(workspace=self.other_workspace, name="Foreign")
        post = Post.objects.create(workspace=self.workspace, author=self.user, title="Campaign post")
        url = reverse("content_intelligence:content_library_bulk", kwargs={"workspace_id": self.workspace.id})
        response = self.client.post(
            url, {"selected": [f"post:{post.id}"], "action": "assign_campaign", "campaign": campaign.id}
        )
        self.assertEqual(response.status_code, 302)
        post.refresh_from_db()
        self.assertEqual(post.campaign, campaign)
        forbidden = self.client.post(
            url, {"selected": [f"post:{post.id}"], "action": "assign_campaign", "campaign": foreign_campaign.id}
        )
        self.assertEqual(forbidden.status_code, 404)
