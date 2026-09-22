"""One-click unsubscribe.

Before this the only way to stop a notification was a footer link to a page
that requires signing in. Someone buried by mail they did not ask for does not
sign in to stop it — they press the spam button, and the sending domain pays.
"""

import pytest
from django.core import mail, signing
from django.urls import reverse

from apps.notifications.engine import notify
from apps.notifications.models import Channel, EventType, NotificationPreference
from apps.notifications.unsubscribe import SALT, make_token


def url_for(user, event_type=EventType.SOCIAL_ACCOUNT_DISCONNECTED):
    return reverse("notifications:unsubscribe", kwargs={"token": make_token(user.pk, event_type)})


@pytest.mark.django_db
def test_one_click_post_turns_the_email_off(client, user):
    res = client.post(url_for(user))

    assert res.status_code == 200
    pref = NotificationPreference.objects.get(
        user=user, event_type=EventType.SOCIAL_ACCOUNT_DISCONNECTED, channel=Channel.EMAIL
    )
    assert pref.is_enabled is False


@pytest.mark.django_db
def test_a_get_shows_the_page_without_changing_anything(client, user):
    """Mail scanners and link prefetchers — Outlook Safe Links, corporate
    gateways, antivirus proxies — fetch every URL they find in a message,
    including the List-Unsubscribe header. If a GET unsubscribed, they would
    silently switch off people's publish-failure alerts."""
    res = client.get(url_for(user))

    assert res.status_code == 200
    assert b"Unsubscribe" in res.content
    assert not NotificationPreference.objects.exists(), "a fetch is not a decision"


@pytest.mark.django_db
def test_the_page_a_get_returns_can_complete_the_unsubscribe(client, user):
    """The confirm page has to actually work without a session or a CSRF token."""
    url = url_for(user)
    client.get(url)
    res = client.post(url)

    assert res.status_code == 200
    assert not NotificationPreference.objects.get(
        user=user, event_type=EventType.SOCIAL_ACCOUNT_DISCONNECTED, channel=Channel.EMAIL
    ).is_enabled


@pytest.mark.django_db
def test_unsubscribing_actually_stops_the_email(client, user):
    notify(user, EventType.SOCIAL_ACCOUNT_DISCONNECTED, "TikTok disconnected")
    assert len(mail.outbox) == 1

    client.post(url_for(user))
    notify(user, EventType.SOCIAL_ACCOUNT_DISCONNECTED, "YouTube disconnected")

    assert len(mail.outbox) == 1, "no further email for that event type"


@pytest.mark.django_db
def test_it_only_silences_the_one_event_type(client, user):
    client.post(url_for(user, EventType.SOCIAL_ACCOUNT_DISCONNECTED))

    notify(user, EventType.POST_SUBMITTED, "Post submitted")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_a_forged_token_changes_nothing(client, user):
    res = client.post(reverse("notifications:unsubscribe", kwargs={"token": "not-a-real-token"}))

    assert res.status_code == 400
    assert not NotificationPreference.objects.exists()


@pytest.mark.django_db
def test_a_token_naming_an_unknown_event_is_rejected(client, user):
    token = signing.dumps({"u": str(user.pk), "e": "made_up_event"}, salt=SALT)
    res = client.post(reverse("notifications:unsubscribe", kwargs={"token": token}))

    assert res.status_code == 400
    assert not NotificationPreference.objects.exists()


@pytest.mark.django_db
def test_notification_email_carries_the_one_click_headers(user):
    notify(user, EventType.SOCIAL_ACCOUNT_DISCONNECTED, "TikTok disconnected")

    headers = mail.outbox[0].extra_headers
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert headers["List-Unsubscribe"].startswith("<")
    assert "/notifications/unsubscribe/" in headers["List-Unsubscribe"]


@pytest.mark.django_db(transaction=True)
def test_a_token_for_a_deleted_account_is_refused_not_a_500(client, user):
    """The endpoint is public and unauthenticated, so an odd token has to come
    back as a 400 rather than an exception.

    transaction=True because the foreign key has to be checked when the insert
    happens, as it is in production. Inside the usual test transaction Django
    defers constraint checks to teardown, so the request would appear to
    succeed and the violation would surface as a teardown error instead.
    """
    url = url_for(user)
    user.delete()

    res = client.post(url)

    assert res.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"e": EventType.POST_FAILED},  # no user
        {"u": "", "e": EventType.POST_FAILED},  # blank user
        {"u": "abc"},  # no event type
        ["not", "a", "dict"],
    ],
)
def test_a_malformed_payload_is_refused_not_a_500(client, user, payload):
    token = signing.dumps(payload, salt=SALT)
    res = client.post(reverse("notifications:unsubscribe", kwargs={"token": token}))

    assert res.status_code == 400
