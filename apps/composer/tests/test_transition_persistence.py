"""Every scheduling path must persist everything ``transition_to`` writes.

``transition_to("scheduled")`` resets the previous attempt's state: the retry
budget, the error text, and the platform publish handle. Callers that pass
``update_fields`` (or ``bulk_update``) silently drop whichever of those they
forget to list — and four of the six scheduling paths did exactly that, leaving
a retried post carrying the *previous* upload's handle into the confirmation
sweep, which then settled it against an unrelated outcome.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


def _failed_row(workspace, account, **extra):
    post = Post.objects.create(workspace=workspace, caption="hi", **extra)
    return PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.FAILED,
        platform_post_id="v_pub_file~previous",
        retry_count=3,
        next_retry_at=timezone.now() + timedelta(minutes=30),
        publish_error="Publishing kept failing.",
    )


class TransitionFieldsCoversEveryWriteTest(TestCase):
    """Structural guard: the constant must not drift from the method.

    This is the test that makes the six call sites safe. If someone adds a
    field to ``transition_to`` and forgets ``TRANSITION_FIELDS``, every
    ``update_fields`` caller starts dropping it silently — no error, just a
    reset that doesn't stick.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

    def _fields_written_by(self, pp, target):
        concrete = [f.name for f in PlatformPost._meta.concrete_fields]
        before = {name: getattr(pp, name) for name in concrete}
        pp.transition_to(target)
        after = {name: getattr(pp, name) for name in concrete}
        return {name for name in concrete if before[name] != after[name]}

    def test_scheduled_writes_nothing_outside_the_constant(self):
        pp = _failed_row(self.workspace, self.account)

        written = self._fields_written_by(pp, "scheduled")

        assert written, "transition_to should have changed something"
        assert written <= set(PlatformPost.TRANSITION_FIELDS), (
            f"transition_to writes {sorted(written - set(PlatformPost.TRANSITION_FIELDS))}, "
            "which no update_fields caller lists — add it to TRANSITION_FIELDS"
        )

    def test_published_writes_nothing_outside_the_constant(self):
        pp = _failed_row(self.workspace, self.account)
        pp.status = PlatformPost.Status.PUBLISHING

        written = self._fields_written_by(pp, "published")

        assert written <= set(PlatformPost.TRANSITION_FIELDS)

    def test_scheduled_clears_the_previous_attempts_state(self):
        pp = _failed_row(self.workspace, self.account)

        pp.transition_to("scheduled")

        assert pp.platform_post_id == ""
        assert pp.retry_count == 0
        assert pp.next_retry_at is None
        assert pp.publish_error == ""

    def test_other_targets_leave_it_alone(self):
        pp = _failed_row(self.workspace, self.account)

        pp.transition_to("draft")

        assert pp.platform_post_id == "v_pub_file~previous"
        assert pp.retry_count == 3


class SchedulingPathsPersistTheResetTest(TestCase):
    """Each path that puts a row back to ``scheduled`` must write it to the DB."""

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="tiktok",
            account_platform_id="tt-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

    def _assert_reset_persisted(self, pp):
        pp.refresh_from_db()
        assert pp.platform_post_id == "", "the previous attempt's handle survived the reschedule"
        assert pp.retry_count == 0
        assert pp.next_retry_at is None
        assert pp.publish_error == ""

    def test_rest_and_mcp_scheduling_service(self):
        from apps.composer.services import transition_platform_post

        pp = _failed_row(self.workspace, self.account)

        transition_platform_post(pp, "scheduled", scheduled_at=timezone.now() + timedelta(hours=1))

        self._assert_reset_persisted(pp)

    def test_calendar_bulk_save(self):
        from apps.calendar.views import _bulk_save_platform_posts

        pp = _failed_row(self.workspace, self.account)
        pp.transition_to("scheduled")

        _bulk_save_platform_posts([pp])

        self._assert_reset_persisted(pp)

    def test_approvals_transition(self):
        from apps.approvals.services import _transition_or_skip

        pp = _failed_row(self.workspace, self.account)
        pp.status = PlatformPost.Status.APPROVED
        pp.save(update_fields=["status"])

        assert _transition_or_skip(pp, "scheduled") is True

        self._assert_reset_persisted(pp)
