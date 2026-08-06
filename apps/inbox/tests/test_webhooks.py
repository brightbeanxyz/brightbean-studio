"""Tests for inbound webhook receivers (Facebook + Instagram-Login)."""

import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.inbox.models import InboxMessage
from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Test WS", organization=organization)


@pytest.fixture
def ig_login_account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram_login",
        account_platform_id="ig-login-123",
        account_name="Test IG Login",
    )


@pytest.fixture
def ig_account(db, workspace):
    """Instagram account on the *Facebook Login* path (different platform key)."""
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-fb-login-456",
        account_name="Test IG (FB Login)",
    )


def _sign_body(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.django_db
class TestInstagramLoginWebhookVerify:
    """GET handshake: hub.mode=subscribe, hub.verify_token, hub.challenge."""

    @override_settings(INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN="secret-token")
    def test_correct_token_echoes_challenge(self, client):
        url = reverse("inbox_webhooks:webhook_instagram_login")
        response = client.get(
            url,
            {"hub.mode": "subscribe", "hub.verify_token": "secret-token", "hub.challenge": "hello"},
        )
        assert response.status_code == 200
        assert response.content == b"hello"

    @override_settings(INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN="secret-token")
    def test_wrong_token_returns_403(self, client):
        url = reverse("inbox_webhooks:webhook_instagram_login")
        response = client.get(
            url,
            {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "hello"},
        )
        assert response.status_code == 403

    @override_settings(INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN="")
    def test_unconfigured_token_returns_403(self, client):
        url = reverse("inbox_webhooks:webhook_instagram_login")
        response = client.get(
            url,
            {"hub.mode": "subscribe", "hub.verify_token": "anything", "hub.challenge": "hello"},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestInstagramLoginWebhookReceive:
    """POST event delivery: HMAC signature + dispatch to instagram_login accounts only."""

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_invalid_signature_returns_403(self, client):
        url = reverse("inbox_webhooks:webhook_instagram_login")
        body = json.dumps({"entry": []}).encode()
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=deadbeef",
        )
        assert response.status_code == 403

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_valid_signature_processes_dm(self, client, ig_login_account):
        url = reverse("inbox_webhooks:webhook_instagram_login")
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "messaging": [
                        {
                            "sender": {"id": "user-1", "name": "Alice"},
                            "message": {"mid": "msg-1", "text": "Hi there!"},
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        signature = _sign_body(body, "ig-secret")
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        assert response.status_code == 200
        msg = InboxMessage.objects.get(platform_message_id="msg-1")
        assert msg.social_account_id == ig_login_account.id
        assert msg.body == "Hi there!"
        assert msg.message_type == InboxMessage.MessageType.DM

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_does_not_dispatch_to_facebook_login_instagram_account(self, client, ig_account):
        """Events arriving at /webhooks/instagram_login/ must only match `instagram_login` accounts.

        An `instagram` account (Facebook-Login path) sharing the same platform-side ID
        must NOT receive events from this endpoint.
        """
        # Override the FB-login account ID to match the inbound event's entry.id
        ig_account.account_platform_id = "ig-login-123"
        ig_account.save()

        url = reverse("inbox_webhooks:webhook_instagram_login")
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "messaging": [
                        {
                            "sender": {"id": "user-1", "name": "Alice"},
                            "message": {"mid": "msg-fb-login", "text": "ignored"},
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        signature = _sign_body(body, "ig-secret")
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        assert response.status_code == 200
        assert not InboxMessage.objects.filter(platform_message_id="msg-fb-login").exists()

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": ""}},
    )
    def test_unconfigured_app_secret_returns_403(self, client):
        url = reverse("inbox_webhooks:webhook_instagram_login")
        body = json.dumps({"entry": []}).encode()
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "anything"),
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestFacebookWebhookStillWorks:
    """Sanity check: the existing facebook_webhook keeps passing after the refactor."""

    @override_settings(FACEBOOK_WEBHOOK_VERIFY_TOKEN="fb-token")
    def test_correct_token_echoes_challenge(self, client):
        url = reverse("inbox_webhooks:webhook_facebook")
        response = client.get(
            url,
            {"hub.mode": "subscribe", "hub.verify_token": "fb-token", "hub.challenge": "ok"},
        )
        assert response.status_code == 200
        assert response.content == b"ok"

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_secret": "fb-secret"}},
    )
    def test_processes_facebook_dm_with_valid_signature(self, client, db, workspace):
        fb_account = SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="fb-page-1",
            account_name="Test FB Page",
        )
        url = reverse("inbox_webhooks:webhook_facebook")
        payload = {
            "entry": [
                {
                    "id": "fb-page-1",
                    "messaging": [
                        {
                            "sender": {"id": "user-2", "name": "Bob"},
                            "message": {"mid": "fb-msg-1", "text": "Hello FB!"},
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        signature = _sign_body(body, "fb-secret")
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        assert response.status_code == 200
        msg = InboxMessage.objects.get(platform_message_id="fb-msg-1")
        assert msg.social_account_id == fb_account.id


@pytest.mark.django_db
class TestMetaWebhookCrossTenantIsolation:
    """A delivery signed with one org's app secret must not write into a different
    org's accounts, even though that secret is a valid configured secret."""

    def _setup_org(self, name, page_id, secret):
        from apps.credentials.models import PlatformCredential
        from apps.organizations.models import Organization
        from apps.workspaces.models import Workspace

        org = Organization.objects.create(name=name)
        ws = Workspace.objects.create(name=f"{name} WS", organization=org)
        PlatformCredential.objects.create(
            organization=org,
            platform="facebook",
            credentials={"client_id": f"{name}-id", "client_secret": secret},
        )
        account = SocialAccount.objects.create(
            workspace=ws,
            platform="facebook",
            account_platform_id=page_id,
            account_name=f"{name} Page",
        )
        return account

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def test_other_orgs_secret_cannot_forge_into_victim_account(self, client):
        self._setup_org("OrgA", "page-A", "SECRET_A")  # victim
        self._setup_org("OrgB", "page-B", "SECRET_B")  # attacker (knows SECRET_B)

        # Attacker forges an event for the victim's page, signed with their own secret.
        payload = {
            "entry": [
                {
                    "id": "page-A",
                    "messaging": [
                        {"sender": {"id": "x", "name": "Mallory"}, "message": {"mid": "forged-1", "text": "forged"}}
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        url = reverse("inbox_webhooks:webhook_facebook")
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "SECRET_B"),
        )
        # SECRET_B is a valid configured secret, so the signature check passes (not 403),
        # but the event must NOT be written into Org A's account.
        assert response.status_code == 200
        assert not InboxMessage.objects.filter(platform_message_id="forged-1").exists()

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def test_owning_orgs_secret_processes_event(self, client):
        account = self._setup_org("OrgC", "page-C", "SECRET_C")

        payload = {
            "entry": [
                {
                    "id": "page-C",
                    "messaging": [{"sender": {"id": "u", "name": "Bob"}, "message": {"mid": "legit-1", "text": "hi"}}],
                }
            ]
        }
        body = json.dumps(payload).encode()
        url = reverse("inbox_webhooks:webhook_facebook")
        response = client.post(
            url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "SECRET_C"),
        )
        assert response.status_code == 200
        msg = InboxMessage.objects.get(platform_message_id="legit-1")
        assert msg.social_account_id == account.id


@pytest.mark.django_db
class TestInstagramCommentEvents:
    """Instagram names and shapes its comment events differently to a Page.

    A Page sends ``feed``/``mention`` with the body under ``message``;
    Instagram sends ``comments``/``mentions`` with the body under ``text``.
    Handling only the Page shape silently drops every Instagram comment.
    """

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_instagram_comment_lands_in_the_inbox_with_its_text(self, client, ig_login_account):
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "ig-comment-1",
                                "text": "That jasmine note is unreal",
                                "from": {"id": "igsid-9", "username": "lenasorensen"},
                                "media": {"id": "media-1", "media_product_type": "FEED"},
                            },
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        response = client.post(
            reverse("inbox_webhooks:webhook_instagram_login"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "ig-secret"),
        )

        assert response.status_code == 200
        msg = InboxMessage.objects.get(platform_message_id="ig-comment-1")
        assert msg.message_type == InboxMessage.MessageType.COMMENT
        assert msg.body == "That jasmine note is unreal"
        assert msg.sender_name == "lenasorensen"
        assert msg.sender_handle == "igsid-9"

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_instagram_mention_lands_as_a_mention(self, client, ig_login_account):
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "mentions",
                            "value": {"media_id": "media-2", "comment_id": "ig-comment-2"},
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        response = client.post(
            reverse("inbox_webhooks:webhook_instagram_login"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "ig-secret"),
        )

        assert response.status_code == 200
        msg = InboxMessage.objects.get(platform_message_id="ig-comment-2")
        assert msg.message_type == InboxMessage.MessageType.MENTION

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_comment_without_an_id_is_ignored(self, client, ig_login_account):
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [{"field": "comments", "value": {"text": "orphan"}}],
                }
            ]
        }
        body = json.dumps(payload).encode()
        response = client.post(
            reverse("inbox_webhooks:webhook_instagram_login"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "ig-secret"),
        )

        assert response.status_code == 200
        assert InboxMessage.objects.count() == 0


@pytest.mark.django_db
class TestOwnActivityIsNotEchoed:
    """Replying from the inbox posts a real comment, which comes straight back.

    Without a guard the team's own answers reappear as fresh customer comments,
    re-notify everyone and start an SLA clock on themselves.
    """

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_instagram_comment_from_the_account_itself_is_ignored(self, client, ig_login_account):
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "own-reply-1",
                                "text": "Thanks for asking!",
                                "from": {"id": "ig-login-123", "username": "northlight"},
                            },
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        response = client.post(
            reverse("inbox_webhooks:webhook_instagram_login"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "ig-secret"),
        )

        assert response.status_code == 200
        assert InboxMessage.objects.count() == 0

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_secret": "fb-secret"}},
    )
    def test_facebook_comment_from_the_page_itself_is_ignored(self, client, db, workspace):
        account = SocialAccount.objects.create(
            workspace=workspace,
            platform="facebook",
            account_platform_id="page-echo",
            account_name="Echo Page",
        )
        payload = {
            "entry": [
                {
                    "id": "page-echo",
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "item": "comment",
                                "comment_id": "own-fb-reply",
                                "message": "Our own answer",
                                "from": {"id": "page-echo", "name": "Echo Page"},
                            },
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        response = client.post(
            reverse("inbox_webhooks:webhook_facebook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "fb-secret"),
        )

        assert response.status_code == 200
        assert not InboxMessage.objects.filter(social_account=account).exists()

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_a_comment_from_someone_else_still_arrives(self, client, ig_login_account):
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "customer-1",
                                "text": "Do you ship?",
                                "from": {"id": "igsid-outside", "username": "curious"},
                            },
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        client.post(
            reverse("inbox_webhooks:webhook_instagram_login"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "ig-secret"),
        )

        assert InboxMessage.objects.filter(platform_message_id="customer-1").exists()


@pytest.mark.django_db
class TestInstagramMentionReplyEdge:
    """A caption mention gives us a media ID, which has no ``replies`` edge."""

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def _post(self, client, value):
        payload = {"entry": [{"id": "ig-login-123", "changes": [{"field": "mentions", "value": value}]}]}
        body = json.dumps(payload).encode()
        return client.post(
            reverse("inbox_webhooks:webhook_instagram_login"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "ig-secret"),
        )

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_comment_mention_is_answered_on_the_replies_edge(self, client, ig_login_account):
        self._post(client, {"comment_id": "c-1", "media_id": "m-1"})

        msg = InboxMessage.objects.get(platform_message_id="c-1")
        assert msg.extra["reply_edge"] == "comment"

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_caption_mention_is_answered_on_the_media_edge(self, client, ig_login_account):
        self._post(client, {"media_id": "m-2"})

        msg = InboxMessage.objects.get(platform_message_id="m-2")
        assert msg.extra["reply_edge"] == "media"
        assert msg.body  # a pointer, not a blank row
