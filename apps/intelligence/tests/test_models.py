"""Tests for the four Studio-side Intelligence models.

Focus is on the partial-unique constraint that the financial-correctness
backstop relies on, the OneToOne with Organization, and the encrypted
api_key roundtrip.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.intelligence.models import (
    IntelligenceSubscription,
    IntelligenceUsageEvent,
    PendingActivation,
    StudioCheckoutAttempt,
)
from apps.organizations.models import Organization


class IntelligenceSubscriptionTests(TestCase):
    def test_one_per_organization(self):
        org = Organization.objects.create(name="Acme")
        IntelligenceSubscription.objects.create(organization=org)
        with self.assertRaises(IntegrityError), transaction.atomic():
            IntelligenceSubscription.objects.create(organization=org)

    def test_encrypted_api_key_roundtrip(self):
        org = Organization.objects.create(name="Acme")
        sub = IntelligenceSubscription.objects.create(
            organization=org,
            intelligence_api_key="bb_secret_plaintext",
            intelligence_api_key_prefix="bb_secre",
        )
        sub.refresh_from_db()
        # Reads back as plaintext via from_db_value.
        self.assertEqual(sub.intelligence_api_key, "bb_secret_plaintext")
        self.assertEqual(sub.intelligence_api_key_prefix, "bb_secre")

    def test_default_status_is_provisioning(self):
        org = Organization.objects.create(name="Acme")
        sub = IntelligenceSubscription.objects.create(organization=org)
        self.assertEqual(sub.status, IntelligenceSubscription.Status.PROVISIONING)


class StudioCheckoutAttemptPartialUniqueTests(TestCase):
    def test_one_in_progress_per_org(self):
        """The financial-correctness backstop: two concurrent
        Subscribe clicks cannot both reach Intelligence."""
        org = Organization.objects.create(name="Acme")
        StudioCheckoutAttempt.objects.create(
            organization=org,
            plan_slug="hobby",
            status=StudioCheckoutAttempt.Status.CREATING,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            StudioCheckoutAttempt.objects.create(
                organization=org,
                plan_slug="hobby",
                status=StudioCheckoutAttempt.Status.OPEN,
            )

    def test_partial_unique_covers_creating_open_pending(self):
        org = Organization.objects.create(name="Acme")
        for s in (StudioCheckoutAttempt.Status.OPEN, StudioCheckoutAttempt.Status.PENDING):
            StudioCheckoutAttempt.objects.create(
                organization=org,
                plan_slug="hobby",
                status=s,
            ).delete()
        # Now lay down a CREATING; OPEN/PENDING must conflict.
        StudioCheckoutAttempt.objects.create(
            organization=org,
            plan_slug="hobby",
            status=StudioCheckoutAttempt.Status.CREATING,
        )
        for s in (StudioCheckoutAttempt.Status.OPEN, StudioCheckoutAttempt.Status.PENDING):
            with self.assertRaises(IntegrityError), transaction.atomic():
                StudioCheckoutAttempt.objects.create(
                    organization=org,
                    plan_slug="hobby",
                    status=s,
                )

    def test_terminal_states_do_not_block_new_attempt(self):
        org = Organization.objects.create(name="Acme")
        for s in (
            StudioCheckoutAttempt.Status.ACTIVATED,
            StudioCheckoutAttempt.Status.EXPIRED,
            StudioCheckoutAttempt.Status.CANCELED,
        ):
            StudioCheckoutAttempt.objects.create(
                organization=org,
                plan_slug="hobby",
                status=s,
            )
        # A fresh creating attempt is allowed.
        StudioCheckoutAttempt.objects.create(
            organization=org,
            plan_slug="hobby",
            status=StudioCheckoutAttempt.Status.CREATING,
        )
        self.assertEqual(
            StudioCheckoutAttempt.objects.filter(organization=org).count(),
            4,
        )

    def test_different_orgs_dont_collide(self):
        org_a = Organization.objects.create(name="A")
        org_b = Organization.objects.create(name="B")
        StudioCheckoutAttempt.objects.create(
            organization=org_a,
            plan_slug="hobby",
            status=StudioCheckoutAttempt.Status.CREATING,
        )
        StudioCheckoutAttempt.objects.create(
            organization=org_b,
            plan_slug="hobby",
            status=StudioCheckoutAttempt.Status.CREATING,
        )


class PendingActivationTests(TestCase):
    def test_session_id_unique(self):
        from django.utils import timezone

        from apps.accounts.models import User

        user = User.objects.create_user(
            email="alice@example.com",
            password="pw",
            tos_accepted_at=timezone.now(),
        )
        PendingActivation.objects.create(user=user, session_id="cs_test")
        with self.assertRaises(IntegrityError), transaction.atomic():
            PendingActivation.objects.create(user=user, session_id="cs_test")

    def test_resolved_organization_nullable(self):
        from django.utils import timezone

        from apps.accounts.models import User

        user = User.objects.create_user(
            email="alice@example.com",
            password="pw",
            tos_accepted_at=timezone.now(),
        )
        p = PendingActivation.objects.create(user=user, session_id="cs_x")
        self.assertIsNone(p.resolved_organization)


class IntelligenceUsageEventTests(TestCase):
    def test_create_event(self):
        from django.utils import timezone

        from apps.accounts.models import User

        user = User.objects.create_user(
            email="alice@example.com",
            password="pw",
            tos_accepted_at=timezone.now(),
        )
        org = Organization.objects.create(name="Acme")
        event = IntelligenceUsageEvent.objects.create(
            organization=org,
            user=user,
            endpoint="/v1/score/packaging",
            credits_charged=1,
            status_code=200,
            latency_ms=243,
        )
        self.assertEqual(event.organization, org)
        self.assertEqual(event.endpoint, "/v1/score/packaging")
