"""Tests for the Intelligence-related fields/properties on Organization."""

from __future__ import annotations

from django.test import TestCase, override_settings

from apps.organizations.models import Organization


class BillingEmailDefaultTests(TestCase):
    def test_billing_email_blank_by_default(self):
        org = Organization.objects.create(name="Acme")
        self.assertEqual(org.billing_email, "")

    def test_billing_email_can_be_set(self):
        org = Organization.objects.create(
            name="Acme",
            billing_email="finance@acme.com",
        )
        self.assertEqual(org.billing_email, "finance@acme.com")


class HasIntelligenceTests(TestCase):
    @override_settings(INTELLIGENCE_ENABLED=False)
    def test_returns_false_when_feature_flag_off(self):
        org = Organization.objects.create(name="Acme")
        self.assertFalse(org.has_intelligence)

    @override_settings(INTELLIGENCE_ENABLED=True)
    def test_returns_false_when_no_subscription_row(self):
        org = Organization.objects.create(name="Acme")
        self.assertFalse(org.has_intelligence)
