"""Invitations cannot be sent in a loop.

The Resend log behind this had ``cmo@aethercomics.art`` invited four times in
thirteen seconds and ``realgarmentkonveksi@gmail.com`` twelve times in five
minutes. Nothing in the resend path stopped either.
"""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.members.models import Invitation, OrgMembership
from apps.members.services import create_invitation, resend_invitation, revoke_invitation
from apps.organizations.models import Organization


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Test Org")


@pytest.fixture
def owner(db, org):
    user = User.objects.create_user(
        email="owner@example.com", password="x", name="Owner", tos_accepted_at=timezone.now()
    )
    OrgMembership.objects.create(user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER)
    return user


def invite(org, owner, email="invitee@example.com"):
    return create_invitation(
        org=org,
        email=email,
        org_role=OrgMembership.OrgRole.MEMBER,
        workspace_assignments=[],
        invited_by=owner,
        inviter=owner,
    )


@pytest.mark.django_db
def test_a_first_invitation_sends_and_is_counted(org, owner):
    invitation = invite(org, owner)
    assert len(mail.outbox) == 1
    invitation.refresh_from_db()
    assert invitation.send_count == 1
    assert invitation.last_sent_at is not None


@pytest.mark.django_db
def test_resending_inside_the_cooldown_is_refused(org, owner):
    invitation = invite(org, owner)

    with pytest.raises(ValueError, match="just sent"):
        resend_invitation(invitation)

    assert len(mail.outbox) == 1, "the refused resend must not have sent anything"


@pytest.mark.django_db
def test_resending_is_allowed_once_the_cooldown_passes(org, owner):
    invitation = invite(org, owner)
    invitation.last_sent_at = timezone.now() - datetime.timedelta(minutes=10)
    invitation.save(update_fields=["last_sent_at"])

    resend_invitation(invitation)
    assert len(mail.outbox) == 2


@pytest.mark.django_db
@override_settings(INVITE_MAX_SENDS=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_an_invitation_runs_out_of_sends(org, owner):
    invitation = invite(org, owner)
    resend_invitation(invitation)
    resend_invitation(invitation)
    assert len(mail.outbox) == 3

    with pytest.raises(ValueError, match="already been sent"):
        resend_invitation(invitation)
    assert len(mail.outbox) == 3


@pytest.mark.django_db
@override_settings(INVITE_MAX_SENDS=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_revoking_and_reinviting_stops_at_the_send_budget(org, owner):
    """revoke_invitation() expires the row, which clears the 'already pending'
    guard — so this was the loop that let one address be mailed twelve times.

    The assertion that matters is the outbox, not the counter: carrying
    send_count forward is only half a fix if create_invitation goes on to send
    anyway.
    """
    invitation = invite(org, owner)
    resend_invitation(invitation)
    resend_invitation(invitation)
    assert len(mail.outbox) == 3

    revoke_invitation(invitation)
    with pytest.raises(ValueError, match="already been emailed"):
        invite(org, owner)

    assert len(mail.outbox) == 3, "the re-invite must not have sent a fourth email"


@pytest.mark.django_db
@override_settings(INVITE_MAX_SENDS=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_the_revoke_loop_cannot_be_ground_out(org, owner):
    """The shape of the original abuse: revoke, re-invite, repeat."""
    for _ in range(10):
        try:
            inv = invite(org, owner)
        except ValueError:
            break
        revoke_invitation(inv)

    assert len(mail.outbox) == 3


@pytest.mark.django_db
@override_settings(INVITE_MAX_SENDS=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_an_invitation_older_than_its_lifetime_does_not_bar_the_address(org, owner):
    """The budget is a rolling window, not a permanent ban — an invitation that
    quietly expired months ago must not lock someone out of being invited."""
    from apps.members.services import INVITE_EXPIRY_DAYS

    invitation = invite(org, owner)
    resend_invitation(invitation)
    resend_invitation(invitation)
    assert len(mail.outbox) == 3

    long_ago = timezone.now() - datetime.timedelta(days=INVITE_EXPIRY_DAYS + 1)
    Invitation.objects.filter(pk=invitation.pk).update(created_at=long_ago, expires_at=long_ago)

    invite(org, owner)
    assert len(mail.outbox) == 4


@pytest.mark.django_db
def test_an_accepted_invitation_is_never_resent(org, owner):
    invitation = invite(org, owner)
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])

    with pytest.raises(ValueError, match="already been accepted"):
        resend_invitation(invitation)


@pytest.mark.django_db
@override_settings(INVITE_MAX_PER_ORG_PER_DAY=3)
def test_an_organization_runs_out_of_invitations_for_the_day(org, owner):
    for i in range(3):
        invite(org, owner, email=f"person{i}@example.com")
    assert len(mail.outbox) == 3

    with pytest.raises(ValueError, match="invitation emails for today"):
        invite(org, owner, email="one-too-many@example.com")

    assert len(mail.outbox) == 3
    assert not Invitation.objects.filter(email="one-too-many@example.com").exists()


@pytest.mark.django_db
def test_a_duplicate_pending_invitation_is_still_refused(org, owner):
    invite(org, owner)
    with pytest.raises(ValueError, match="already pending"):
        invite(org, owner)


@pytest.mark.django_db
def test_a_send_that_fails_does_not_burn_the_allowance(org, owner, monkeypatch):
    """A misconfigured mail server must not cost the recipient their invites."""
    from apps.members import services

    def boom(*args, **kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(services.EmailMultiAlternatives, "send", boom)
    invitation = invite(org, owner)

    invitation.refresh_from_db()
    assert invitation.send_count == 0
    assert invitation.last_sent_at is None


@pytest.mark.django_db
@override_settings(INVITE_MAX_PER_ORG_PER_DAY=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_resending_spends_the_organizations_daily_allowance(org, owner):
    """Charging only create() would make the cap a third of what it claims:
    25 invitations each resent twice is 75 emails from an org told it had spent
    its 25."""
    invitation = invite(org, owner)
    resend_invitation(invitation)
    resend_invitation(invitation)
    assert len(mail.outbox) == 3

    with pytest.raises(ValueError, match="invitation emails for today"):
        invite(org, owner, email="someone-else@example.com")

    assert len(mail.outbox) == 3


@pytest.mark.django_db
@override_settings(INVITE_MAX_SENDS=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_two_overlapping_resends_cannot_both_take_the_last_slot(org, owner):
    """The cap is enforced by a conditional UPDATE, not by an if-statement over
    a value read a moment earlier — otherwise two requests arriving together
    both read send_count=2, both decide they are fine, and both send."""
    invitation = invite(org, owner)
    resend_invitation(invitation)
    assert invitation.send_count == 2

    # Two callers holding their own object, each still believing count is 2 —
    # exactly what two concurrent requests would have.
    first = Invitation.objects.get(pk=invitation.pk)
    second = Invitation.objects.get(pk=invitation.pk)
    assert first.send_count == second.send_count == 2

    resend_invitation(first)
    with pytest.raises(ValueError):
        resend_invitation(second)

    invitation.refresh_from_db()
    assert invitation.send_count == 3, "the cap must not be overshot"
    assert len(mail.outbox) == 3


@pytest.mark.django_db
@override_settings(INVITE_MAX_SENDS=3, INVITE_RESEND_COOLDOWN_SECONDS=0)
def test_a_dropped_send_gives_the_slot_back(org, owner):
    """The outbound budget declines by returning 0, not by raising. Counting
    that as a send would spend the recipient's allowance on an email that never
    left."""
    invitation = invite(org, owner)
    assert invitation.send_count == 1

    with (
        patch("apps.members.services.EmailMultiAlternatives.send", return_value=0),
        pytest.raises(ValueError, match="could not send"),
    ):
        resend_invitation(invitation)

    invitation.refresh_from_db()
    assert invitation.send_count == 1, "a dropped send must not be charged"
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_creation_whose_email_is_dropped_does_not_claim_it_was_sent(org, owner):
    with patch("apps.members.services.EmailMultiAlternatives.send", return_value=0):
        invitation = invite(org, owner)

    invitation.refresh_from_db()
    assert invitation.send_count == 0
    assert invitation.last_sent_at is None, "last_sent_at is the signal that it went out"
    # The invitation itself is real and resendable — that part is deliberate.
    assert Invitation.objects.filter(pk=invitation.pk).exists()
