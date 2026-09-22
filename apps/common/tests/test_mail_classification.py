"""Which mail is exempt from the per-recipient cap, exercised end to end.

This is the most dangerous thing the budget can get wrong. The cap is six
notification emails per recipient per hour; if a password reset is not marked
transactional, a user who has just had six posts fail cannot recover their own
account for the rest of the hour. The exemption rests on
``AccountAdapter.render_mail`` overriding an allauth-internal signature, so it
is worth a test that would notice the day that signature changes.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.common.mail import EMAIL_CLASS_HEADER
from apps.members.models import OrgMembership
from apps.organizations.models import Organization


def budgeted(**limits):
    """Put the wrapper back in the path — Django's test setup pins EMAIL_BACKEND
    to locmem — with every cap off unless the test names it."""
    settings = {
        "EMAIL_BACKEND": "apps.common.mail.BudgetedEmailBackend",
        "EMAIL_INNER_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        "EMAIL_SENDING_ENABLED": True,
        "EMAIL_DAILY_SEND_LIMIT": -1,
        "EMAIL_RECIPIENT_HOURLY_LIMIT": -1,
        "EMAIL_RECIPIENT_DAILY_LIMIT": -1,
    }
    settings.update(limits)
    return override_settings(**settings)


def burn_the_hourly_allowance(address, n):
    from django.core.mail import EmailMultiAlternatives

    for i in range(n):
        EmailMultiAlternatives(subject=f"noise {i}", body="b", from_email="noreply@example.com", to=[address]).send(
            fail_silently=False
        )


@pytest.fixture
def account(db):
    user = get_user_model().objects.create_user(
        email="person@example.com", password="pw-that-is-long", name="Person", tos_accepted_at=timezone.now()
    )
    return user


@pytest.mark.django_db
@budgeted(EMAIL_RECIPIENT_HOURLY_LIMIT=3)
def test_a_password_reset_reaches_a_recipient_whose_allowance_is_spent(client, account):
    burn_the_hourly_allowance(account.email, 5)
    assert len(mail.outbox) == 3, "the cap should have stopped the rest"
    mail.outbox.clear()

    res = client.post(reverse("account_reset_password"), {"email": account.email})

    assert res.status_code in (200, 302)
    assert len(mail.outbox) == 1, "a password reset must not be eaten by the notification cap"
    assert "reset" in mail.outbox[0].subject.lower()


@pytest.mark.django_db
@budgeted(EMAIL_RECIPIENT_HOURLY_LIMIT=3)
def test_allauth_mail_is_marked_transactional_before_the_header_is_stripped(account):
    """Guards the adapter override itself: if allauth's render_mail signature
    changes, this is what notices."""
    from allauth.account.adapter import get_adapter

    msg = get_adapter().render_mail("account/email/password_reset_key", account.email, {})

    assert msg.extra_headers.get(EMAIL_CLASS_HEADER) == "transactional"


@pytest.mark.django_db
@budgeted(EMAIL_RECIPIENT_HOURLY_LIMIT=2)
def test_an_invitation_reaches_a_recipient_whose_allowance_is_spent(account):
    from apps.members.services import create_invitation

    org = Organization.objects.create(name="Org")
    owner = get_user_model().objects.create_user(
        email="owner@example.com", password="pw-that-is-long", name="Owner", tos_accepted_at=timezone.now()
    )
    OrgMembership.objects.create(user=owner, organization=org, org_role=OrgMembership.OrgRole.OWNER)

    burn_the_hourly_allowance("invitee@example.com", 4)
    assert len(mail.outbox) == 2
    mail.outbox.clear()

    create_invitation(
        org=org,
        email="invitee@example.com",
        org_role=OrgMembership.OrgRole.MEMBER,
        workspace_assignments=[],
        invited_by=owner,
        inviter=owner,
    )

    assert len(mail.outbox) == 1


@pytest.mark.django_db
@budgeted(EMAIL_RECIPIENT_HOURLY_LIMIT=2, EMAIL_DAILY_SEND_LIMIT=2)
def test_the_global_cap_still_stops_transactional_mail(client, account):
    """transactional buys an exemption from the per-recipient cap only. Nothing
    is allowed through a spent global budget, or the quota is not a quota."""
    burn_the_hourly_allowance("other@example.com", 2)
    assert len(mail.outbox) == 2
    mail.outbox.clear()

    client.post(reverse("account_reset_password"), {"email": account.email})

    assert mail.outbox == []
