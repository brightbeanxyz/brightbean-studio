"""Add-to-Queue must be atomic across queues: a full queue rolls back partials."""

from datetime import time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import PostingSlot, Queue, QueueEntry
from apps.composer.models import PlatformPost, Post
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


class AddToQueueRollbackTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="rb@example.com", password="pw", tos_accepted_at=timezone.now())
        self.org = Organization.objects.create(name="RB Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="RB WS")
        OrgMembership.objects.create(user=self.user, organization=self.org, org_role=OrgMembership.OrgRole.OWNER)
        WorkspaceMembership.objects.create(
            user=self.user, workspace=self.workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
        )
        self.client.force_login(self.user)

        # Account A has posting slots; account B has none, so its queue is always full.
        self.acct_a = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-a",
            account_name="A",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.acct_b = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="bluesky",
            account_platform_id="bs-b",
            account_name="B",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        for day in range(7):
            PostingSlot.objects.create(social_account=self.acct_a, day_of_week=day, time=time(9, 0))
        Queue.objects.create(workspace=self.workspace, name="QA", social_account=self.acct_a)
        Queue.objects.create(workspace=self.workspace, name="QB", social_account=self.acct_b)

        self.post = Post.objects.create(workspace=self.workspace, author=self.user, caption="multi")
        self.pp_a = PlatformPost.objects.create(
            post=self.post, social_account=self.acct_a, status=PlatformPost.Status.DRAFT
        )
        self.pp_b = PlatformPost.objects.create(
            post=self.post, social_account=self.acct_b, status=PlatformPost.Status.DRAFT
        )

    def test_full_queue_rolls_back_the_other_queue_writes(self):
        url = reverse("composer:save_post_edit", kwargs={"workspace_id": self.workspace.id, "post_id": self.post.id})
        resp = self.client.post(
            url,
            data={
                "action": "add_to_queue",
                "title": "",
                "caption": "multi",
                "tags": "",
                "selected_accounts": f"{self.acct_a.id},{self.acct_b.id}",
            },
        )

        self.assertEqual(resp.status_code, 400)
        # No partial state: no queue entries, both children still draft + unscheduled.
        self.assertEqual(QueueEntry.objects.filter(post=self.post).count(), 0)
        self.pp_a.refresh_from_db()
        self.pp_b.refresh_from_db()
        self.assertIsNone(self.pp_a.scheduled_at)
        self.assertIsNone(self.pp_b.scheduled_at)
        self.assertEqual(self.pp_a.status, PlatformPost.Status.DRAFT)
        self.assertEqual(self.pp_b.status, PlatformPost.Status.DRAFT)
