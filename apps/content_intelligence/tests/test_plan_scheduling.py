from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.brands.models import BrandProfile, EditorialStrategy, EditorialStrategyVersion
from apps.composer.models import PlatformPost
from apps.content_intelligence.generation import (
    create_composer_draft_from_plan_item,
    schedule_plan_item_draft,
)
from apps.content_intelligence.models import ContentPlan, ContentPlanItem
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


class PlanSchedulingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="plan-scheduling@example.com",
            password="pass12345",
            tos_accepted_at=timezone.now(),
        )
        OrgMembership.objects.filter(user=self.user).delete()
        organization = Organization.objects.create(name="Scheduling agency")
        self.workspace = Workspace.objects.create(organization=organization, name="Client")
        OrgMembership.objects.create(user=self.user, organization=organization, org_role="owner")
        WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, workspace_role="owner")
        brand = BrandProfile.objects.create(workspace=self.workspace, name="Brand")
        strategy = EditorialStrategy.objects.create(brand=brand)
        version = EditorialStrategyVersion.objects.create(
            strategy=strategy,
            version=1,
            reach_percentage=35,
            authority_percentage=50,
            conversion_percentage=15,
            created_by=self.user,
        )
        day = timezone.localdate() + timedelta(days=7)
        plan = ContentPlan.objects.create(
            workspace=self.workspace,
            brand=brand,
            cadence="weekly",
            start_date=day,
            end_date=day,
            strategy_version=version,
            created_by=self.user,
        )
        self.item = ContentPlanItem.objects.create(
            plan=plan,
            position=1,
            planned_for=day,
            objective="reach",
            topic="Launch",
            recommended_format="text",
            recommended_platform="linkedin",
        )
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="plan-account",
            account_name="LinkedIn",
            connection_status="connected",
        )

    def test_service_blocks_direct_scheduling_when_approval_is_required(self):
        for mode in ("required_internal", "required_internal_and_client"):
            for existing_draft in (False, True):
                with self.subTest(mode=mode, existing_draft=existing_draft):
                    item = ContentPlanItem.objects.create(
                        plan=self.item.plan,
                        position=ContentPlanItem.objects.count() + 1,
                        planned_for=self.item.planned_for,
                        objective="reach",
                        topic="Review first",
                        recommended_format="text",
                        recommended_platform="linkedin",
                    )
                    self.workspace.approval_workflow_mode = mode
                    self.workspace.save(update_fields=["approval_workflow_mode"])
                    if existing_draft:
                        create_composer_draft_from_plan_item(item_id=item.id, workspace=self.workspace, user=self.user)
                    with self.assertRaisesMessage(ValueError, "Workspace requires approval before scheduling"):
                        schedule_plan_item_draft(item_id=item.id, workspace=self.workspace, user=self.user)
                    self.assertFalse(PlatformPost.objects.filter(post__workspace=self.workspace).exists())
                    item.refresh_from_db()
                    self.assertEqual(bool(item.composer_post_id), existing_draft)

    def schedule_url(self):
        return reverse(
            "content_intelligence:schedule_plan_item",
            kwargs={
                "workspace_id": self.workspace.id,
                "brand_id": self.item.plan.brand_id,
                "plan_id": self.item.plan_id,
                "item_id": self.item.id,
            },
        )

    def test_calendar_reports_required_approval_without_scheduling(self):
        self.client.force_login(self.user)
        for mode in ("required_internal", "required_internal_and_client"):
            with self.subTest(mode=mode):
                self.workspace.approval_workflow_mode = mode
                self.workspace.save(update_fields=["approval_workflow_mode"])
                response = self.client.post(self.schedule_url())
                self.assertRedirects(
                    response,
                    reverse(
                        "content_intelligence:plan_detail",
                        kwargs={
                            "workspace_id": self.workspace.id,
                            "brand_id": self.item.plan.brand_id,
                            "plan_id": self.item.plan_id,
                        },
                    ),
                    fetch_redirect_response=False,
                )
                self.assertTrue(
                    any(
                        "Workspace requires approval before scheduling" in str(message)
                        for message in get_messages(response.wsgi_request)
                    )
                )
                self.assertFalse(PlatformPost.objects.filter(post__workspace=self.workspace).exists())

    def test_calendar_allows_scheduling_without_mandatory_approval(self):
        self.client.force_login(self.user)
        for mode in ("none", "optional"):
            with self.subTest(mode=mode):
                self.workspace.approval_workflow_mode = mode
                self.workspace.save(update_fields=["approval_workflow_mode"])
                self.item = ContentPlanItem.objects.create(
                    plan=self.item.plan,
                    position=ContentPlanItem.objects.count() + 1,
                    planned_for=self.item.planned_for,
                    objective="reach",
                    topic="Ready",
                    recommended_format="text",
                    recommended_platform="linkedin",
                )
                response = self.client.post(self.schedule_url())
                self.item.refresh_from_db()
                self.assertIsNotNone(self.item.composer_post_id)
                self.assertRedirects(
                    response,
                    reverse(
                        "composer:compose_edit",
                        kwargs={
                            "workspace_id": self.workspace.id,
                            "post_id": self.item.composer_post_id,
                        },
                    ),
                    fetch_redirect_response=False,
                )
                target = self.item.composer_post.platform_posts.get()
                self.assertEqual(target.status, PlatformPost.Status.SCHEDULED)
                self.assertIsNotNone(target.scheduled_at)

    def test_calendar_requires_publish_permission(self):
        viewer = User.objects.create_user(
            email="plan-viewer@example.com",
            password="pass12345",
            tos_accepted_at=timezone.now(),
        )
        OrgMembership.objects.filter(user=viewer).delete()
        OrgMembership.objects.create(user=viewer, organization=self.workspace.organization, org_role="member")
        WorkspaceMembership.objects.create(user=viewer, workspace=self.workspace, workspace_role="viewer")
        self.client.force_login(viewer)
        self.assertEqual(self.client.post(self.schedule_url()).status_code, 403)
        self.assertFalse(PlatformPost.objects.filter(post__workspace=self.workspace).exists())
