"""The Resend bounce webhook: how the app learns an address is dead.

Resend accepts over SMTP and bounces later, so without this nothing in the
product can tell that an address is gone — which is how the Resend log ended up
showing repeated sends to addresses Resend had already suppressed.
"""

import base64
import hashlib
import hmac
import json
import time

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.common.models import EmailSuppression

SECRET = "whsec_" + base64.b64encode(b"super-secret-key").decode()


def signed_headers(body: bytes, secret: str = SECRET, timestamp: int | None = None, msg_id: str = "msg_1"):
    timestamp = timestamp if timestamp is not None else int(time.time())
    key = base64.b64decode(secret.split("_", 1)[1])
    signed = f"{msg_id}.{timestamp}.".encode() + body
    digest = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return {
        "HTTP_SVIX_ID": msg_id,
        "HTTP_SVIX_TIMESTAMP": str(timestamp),
        "HTTP_SVIX_SIGNATURE": f"v1,{digest}",
    }


def bounce(address="dead@example.com", event="email.bounced"):
    return json.dumps({"type": event, "data": {"to": [address], "reason": "mailbox not found"}}).encode()


@pytest.fixture
def url():
    return reverse("resend_webhook")


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_a_signed_bounce_suppresses_the_address(client, url):
    body = bounce()
    res = client.post(url, data=body, content_type="application/json", **signed_headers(body))

    assert res.status_code == 200
    assert EmailSuppression.objects.get(address="dead@example.com").reason == EmailSuppression.Reason.BOUNCED


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_a_complaint_suppresses_the_address(client, url):
    body = bounce("angry@example.com", event="email.complained")
    client.post(url, data=body, content_type="application/json", **signed_headers(body))

    assert EmailSuppression.objects.get(address="angry@example.com").reason == EmailSuppression.Reason.COMPLAINED


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_an_unsigned_request_suppresses_nothing(client, url):
    """Otherwise anyone who found the URL could silence any address they liked."""
    res = client.post(url, data=bounce(), content_type="application/json")

    assert res.status_code == 403
    assert not EmailSuppression.objects.exists()


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_a_tampered_body_is_rejected(client, url):
    headers = signed_headers(bounce("dead@example.com"))
    res = client.post(url, data=bounce("someone-else@example.com"), content_type="application/json", **headers)

    assert res.status_code == 403
    assert not EmailSuppression.objects.exists()


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_a_replayed_request_is_rejected(client, url):
    body = bounce()
    stale = int(time.time()) - 3600
    res = client.post(url, data=body, content_type="application/json", **signed_headers(body, timestamp=stale))

    assert res.status_code == 403
    assert not EmailSuppression.objects.exists()


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET="")
def test_an_unconfigured_secret_refuses_rather_than_trusts(client, url):
    body = bounce()
    res = client.post(url, data=body, content_type="application/json", **signed_headers(body))

    assert res.status_code == 403
    assert not EmailSuppression.objects.exists()


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_an_event_we_do_not_act_on_is_acknowledged(client, url):
    """A non-200 would just make Resend retry something with nothing to retry."""
    body = json.dumps({"type": "email.delivered", "data": {"to": ["fine@example.com"]}}).encode()
    res = client.post(url, data=body, content_type="application/json", **signed_headers(body))

    assert res.status_code == 200
    assert not EmailSuppression.objects.exists()


@pytest.mark.django_db
@override_settings(RESEND_WEBHOOK_SECRET=SECRET)
def test_a_repeated_bounce_does_not_error(client, url):
    body = bounce()
    for _ in range(2):
        res = client.post(url, data=body, content_type="application/json", **signed_headers(body))
        assert res.status_code == 200
    assert EmailSuppression.objects.filter(address="dead@example.com").count() == 1
