from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.brands.forms import EditorialStrategyForm
from apps.brands.models import BrandProfile, EditorialStrategy
from apps.brands.services import save_editorial_strategy
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

from ..models import ContentPlan
from ..services import create_content_plan


class EditorialPlanTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="strategy-owner@example.com", password="testpass123", tos_accepted_at=timezone.now()
        )
        OrgMembership.objects.filter(user=self.owner).delete()
        self.org = Organization.objects.create(name="Agency")
        self.workspace = Workspace.objects.create(organization=self.org, name="Client A")
        self.other_workspace = Workspace.objects.create(organization=self.org, name="Client B")
        OrgMembership.objects.create(user=self.owner, organization=self.org, org_role="owner")
        WorkspaceMembership.objects.create(user=self.owner, workspace=self.workspace, workspace_role="owner")
        self.brand = BrandProfile.objects.create(
            workspace=self.workspace,
            name="NEXUS",
            industry="Digital Health",
            content_pillars=["AI", "Wearables", "Behavior Change"],
            posting_frequency="3 posts per week",
            cta_strategy="Invite collaboration.",
        )
        self.client.force_login(self.owner)

    def test_strategy_requires_exactly_one_hundred_percent(self):
        form = EditorialStrategyForm({"reach_percentage": 40, "authority_percentage": 40, "conversion_percentage": 10})
        self.assertFalse(form.is_valid())
        strategy = EditorialStrategy(
            brand=self.brand, reach_percentage=101, authority_percentage=0, conversion_percentage=0
        )
        with self.assertRaises(ValidationError):
            strategy.full_clean()

    def test_saving_strategy_creates_immutable_versions(self):
        first, v1 = save_editorial_strategy(
            brand=self.brand,
            data={"reach_percentage": 35, "authority_percentage": 50, "conversion_percentage": 15},
            user=self.owner,
        )
        _, v2 = save_editorial_strategy(
            brand=self.brand,
            data={"reach_percentage": 30, "authority_percentage": 60, "conversion_percentage": 10},
            user=self.owner,
        )
        self.assertEqual((v1.version, v2.version), (1, 2))
        self.assertEqual(v1.authority_percentage, 50)
        first.refresh_from_db()
        self.assertEqual(first.authority_percentage, 60)

    def test_weekly_plan_contains_weighted_complete_briefs(self):
        save_editorial_strategy(
            brand=self.brand,
            data={"reach_percentage": 35, "authority_percentage": 50, "conversion_percentage": 15},
            user=self.owner,
        )
        plan = create_content_plan(brand=self.brand, cadence="weekly", start_date=date(2026, 9, 7), user=self.owner)
        items = list(plan.items.all())
        self.assertEqual(len(items), 3)
        self.assertEqual(plan.end_date, date(2026, 9, 13))
        objectives = [item.objective for item in items]
        self.assertEqual(objectives.count("authority"), 2)
        self.assertEqual(objectives.count("reach"), 1)
        for item in items:
            self.assertTrue(item.topic and item.hook and item.cta and item.keywords and item.hashtags)
            self.assertIn(item.recommended_platform, {"linkedin", "instagram"})

    def test_monthly_plan_uses_frequency_and_strategy_snapshot(self):
        plan = create_content_plan(brand=self.brand, cadence="monthly", start_date=date(2026, 9, 1), user=self.owner)
        self.assertEqual(plan.items.count(), 12)
        self.assertEqual(plan.end_date, date(2026, 9, 30))
        self.assertEqual(plan.strategy_version.reach_percentage, 35)

    def test_plan_creation_never_creates_composer_posts(self):
        from apps.composer.models import Post

        create_content_plan(brand=self.brand, cadence="weekly", start_date=date(2026, 9, 7), user=self.owner)
        self.assertEqual(Post.objects.count(), 0)

    def test_owner_can_save_strategy_and_generate_plan(self):
        strategy_url = reverse(
            "content_intelligence:strategy", kwargs={"workspace_id": self.workspace.id, "brand_id": self.brand.id}
        )
        response = self.client.post(
            strategy_url, {"reach_percentage": 35, "authority_percentage": 50, "conversion_percentage": 15}
        )
        self.assertEqual(response.status_code, 302)
        create_url = reverse(
            "content_intelligence:plan_create", kwargs={"workspace_id": self.workspace.id, "brand_id": self.brand.id}
        )
        response = self.client.post(create_url, {"cadence": "weekly", "start_date": "2026-09-07"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContentPlan.objects.for_workspace(self.workspace.id).count(), 1)

    def test_editor_has_read_only_access(self):
        editor = User.objects.create_user(
            email="strategy-editor@example.com", password="testpass123", tos_accepted_at=timezone.now()
        )
        OrgMembership.objects.filter(user=editor).delete()
        OrgMembership.objects.create(user=editor, organization=self.org, org_role="member")
        WorkspaceMembership.objects.create(user=editor, workspace=self.workspace, workspace_role="editor")
        self.client.force_login(editor)
        strategy_url = reverse(
            "content_intelligence:strategy", kwargs={"workspace_id": self.workspace.id, "brand_id": self.brand.id}
        )
        self.assertEqual(self.client.get(strategy_url).status_code, 200)
        self.assertEqual(
            self.client.post(
                strategy_url, {"reach_percentage": 35, "authority_percentage": 50, "conversion_percentage": 15}
            ).status_code,
            403,
        )
        create_url = reverse(
            "content_intelligence:plan_create", kwargs={"workspace_id": self.workspace.id, "brand_id": self.brand.id}
        )
        self.assertEqual(self.client.get(create_url).status_code, 403)

    def test_cross_workspace_resources_are_not_disclosed(self):
        other_brand = BrandProfile.objects.create(workspace=self.other_workspace, name="Other")
        strategy_url = reverse(
            "content_intelligence:strategy", kwargs={"workspace_id": self.workspace.id, "brand_id": other_brand.id}
        )
        self.assertEqual(self.client.get(strategy_url).status_code, 404)
        plan = create_content_plan(brand=self.brand, cadence="weekly", start_date=date(2026, 9, 7), user=self.owner)
        detail_url = reverse(
            "content_intelligence:plan_detail",
            kwargs={"workspace_id": self.other_workspace.id, "brand_id": self.brand.id, "plan_id": plan.id},
        )
        self.assertEqual(self.client.get(detail_url).status_code, 403)
