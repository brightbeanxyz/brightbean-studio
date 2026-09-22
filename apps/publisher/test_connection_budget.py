"""Tests for the publish engine's Postgres connection budget.

On 2026-09-15 production went down with ``FATAL: too many connections for role``
— every dyno, web included, unable to reach the database. The publish engine
nested its thread pools, so the platform fan-out multiplied: one pool per post
group meant the real ceiling was groups × platforms, and Django connections are
thread-local, so each of those threads held its own.

The fix is one platform pool shared across groups, sized to the budget. These
tests pin that: the ceiling holds no matter how many groups are running, the
knobs that set it are readable at call time, and the arithmetic still fits the
smallest plan the project claims to support.
"""

import re
import threading
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher import engine
from apps.publisher.engine import PublishEngine
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

REPO_ROOT = Path(__file__).resolve().parents[2]


class PlatformPublishCeilingTest(TransactionTestCase):
    """The ceiling is global across post groups, not per group."""

    PLATFORM_BUDGET = 2
    GROUPS = 6
    LINGER_SECONDS = 0.25

    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.workspace = Workspace.objects.create(organization=self.org, name="WS")
        self.account = SocialAccount.objects.create(
            workspace=self.workspace,
            platform="linkedin_personal",
            account_platform_id="li-1",
            account_name="acct",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        past = timezone.now() - timedelta(minutes=5)
        # One platform post per post, so every group contributes exactly one
        # publish and the observed peak is purely a function of the pool.
        for _ in range(self.GROUPS):
            post = Post.objects.create(workspace=self.workspace, caption="hi", scheduled_at=past)
            PlatformPost.objects.create(
                post=post,
                social_account=self.account,
                status=PlatformPost.Status.SCHEDULED,
                scheduled_at=past,
            )

    def test_concurrent_platform_publishes_never_exceed_the_budget(self):
        live = 0
        peak = 0
        lock = threading.Lock()
        # Two halves, because a ceiling can be wrong in both directions.
        #
        # The barrier proves the pool is no NARROWER than the budget: a publish
        # that never finds a full party times out and breaks it.
        #
        # The linger proves it is no WIDER. Without it the barrier releases each
        # party the instant it forms, so arrivals stagger and the observed peak
        # is the party size no matter how many threads the pool really has —
        # which is how the first version of this test passed against the very
        # per-group fan-out it was written to catch. Holding the slot open keeps
        # over-admitted publishes concurrently visible.
        barrier = threading.Barrier(self.PLATFORM_BUDGET, timeout=10)
        broken = []

        def dispatch(platform_post, media_cache=None):
            nonlocal live, peak
            with lock:
                live += 1
                peak = max(peak, live)
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                broken.append(platform_post.id)
            time.sleep(self.LINGER_SECONDS)
            with lock:
                live -= 1
            return {"success": True, "platform_post_id": "x", "url": None, "response": {}}

        with (
            override_settings(
                PUBLISHER_MAX_CONCURRENT_PLATFORM_PUBLISHES=self.PLATFORM_BUDGET,
                PUBLISHER_MAX_CONCURRENT_POSTS=self.GROUPS,
            ),
            patch.object(PublishEngine, "_dispatch_to_provider", side_effect=dispatch, autospec=False),
        ):
            PublishEngine().poll_and_publish()

        self.assertEqual(broken, [], "a publish never found a partner — the pool is narrower than the budget")
        self.assertEqual(
            peak,
            self.PLATFORM_BUDGET,
            f"peak concurrent platform publishes was {peak}, budget is {self.PLATFORM_BUDGET}",
        )

    def test_counts_only_groups_that_published(self):
        # Every row is held, so no group dispatches anything. The count feeds
        # the one INFO line an operator reads to tell whether publishing
        # recovered, so a group that published nothing must not register.
        PlatformPost.objects.update(status=PlatformPost.Status.ON_HOLD)

        self.assertEqual(PublishEngine().poll_and_publish(), 0)


class BudgetSettingTests(TransactionTestCase):
    """The ceilings are readable at call time and floored at 1."""

    @override_settings(PUBLISHER_MAX_CONCURRENT_PLATFORM_PUBLISHES=3)
    def test_override_settings_actually_takes_effect(self):
        # Regression: binding these at import time made every override_settings
        # in this file a silent no-op that tested the default.
        self.assertEqual(engine._max_concurrent_platform_publishes(), 3)

    @override_settings(
        PUBLISHER_MAX_CONCURRENT_PLATFORM_PUBLISHES=0,
        PUBLISHER_MAX_CONCURRENT_POSTS=0,
        PUBLISHER_MAX_CONCURRENT_PUBLISHES=0,
    )
    def test_zero_is_floored_rather_than_wedging_the_worker(self):
        # An operator throttling during an incident reaches for 0. Unfloored
        # that is a ValueError from ThreadPoolExecutor, or — worse, with the
        # semaphore this replaced — a cycle that blocks forever with no log.
        self.assertEqual(engine._max_concurrent_platform_publishes(), 1)
        self.assertEqual(engine._max_concurrent_posts(), 1)
        self.assertEqual(engine._max_concurrent_publishes(), 1)

    @override_settings(PUBLISHER_MAX_CONCURRENT_PLATFORM_PUBLISHES=-4)
    def test_negative_is_floored(self):
        self.assertEqual(engine._max_concurrent_platform_publishes(), 1)

    def test_an_empty_cycle_does_no_work(self):
        # min(len(groups), ...) is 0 with nothing due, which ThreadPoolExecutor
        # rejects outright — the cycle has to return before building a pool.
        self.assertEqual(PublishEngine().poll_and_publish(), 0)


class BudgetArithmeticTest(TransactionTestCase):
    def test_defaults_fit_the_smallest_supported_plan(self):
        """Peak demand across every process has to fit essential-0's 20.

        The web figure is read from the Procfile rather than copied, so raising
        ``--threads`` fails here instead of in production.
        """
        web = next(line for line in (REPO_ROOT / "Procfile").read_text().splitlines() if line.startswith("web:"))
        workers = int(re.search(r"--workers\s+(\d+)", web).group(1))
        threads = int(re.search(r"--threads\s+(\d+)", web).group(1))

        peak = (
            workers * threads  # gunicorn, one connection per thread
            + 1  # the worker's own process_tasks connection
            + engine._max_concurrent_posts()
            + engine._max_concurrent_platform_publishes()
        )

        self.assertLess(peak, 20, f"peak connection demand {peak} leaves no headroom under essential-0's 20")
