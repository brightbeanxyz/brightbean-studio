"""Tests for inbound webhook receivers (Facebook + Instagram-Login)."""

import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

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
    def test_an_instagram_comment_is_linked_to_the_media_it_belongs_to(self, client, ig_login_account):
        """Instagram nests the media id where a Page sends a flat ``post_id``.

        Without lifting it out, related_post is NULL for every Instagram comment
        even though PlatformPost holds that exact id — IG media ids carry no
        page prefix to strip, so the two match directly.
        """
        from apps.composer.models import PlatformPost, Post

        post = Post.objects.create(workspace=ig_login_account.workspace, caption="hi")
        platform_post = PlatformPost.objects.create(
            post=post,
            social_account=ig_login_account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="media-1",
            published_at=timezone.now(),
        )

        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "ig-comment-3",
                                "text": "Test from a different account",
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
        msg = InboxMessage.objects.get(platform_message_id="ig-comment-3")
        assert msg.related_post_id == platform_post.id
        assert msg.extra["post_id"] == "media-1"
        assert msg.extra["stored_post_id"] == "media-1"

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_an_instagram_reply_keeps_its_parent_comment_id(self, client, ig_login_account):
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "ig-reply-1",
                                "text": "Answering you",
                                "from": {"id": "igsid-9", "username": "lenasorensen"},
                                "parent_id": "ig-comment-1",
                                "media": {"id": "media-1"},
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

        msg = InboxMessage.objects.get(platform_message_id="ig-reply-1")
        assert msg.extra["parent_id"] == "ig-comment-1"

    @override_settings(
        PLATFORM_CREDENTIALS_FROM_ENV={"instagram_login": {"app_secret": "ig-secret"}},
    )
    def test_a_parent_id_naming_the_media_is_not_stored(self, client, ig_login_account):
        """Replying on the media publishes a new top-level comment instead of a
        threaded reply."""
        payload = {
            "entry": [
                {
                    "id": "ig-login-123",
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "id": "ig-comment-4",
                                "text": "Top level",
                                "from": {"id": "igsid-9", "username": "lenasorensen"},
                                "parent_id": "media-1",
                                "media": {"id": "media-1"},
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

        msg = InboxMessage.objects.get(platform_message_id="ig-comment-4")
        assert "parent_id" not in msg.extra

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


@pytest.fixture
def fb_account(db, workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-feed",
        account_name="Feed Page",
    )


def _post_feed_event(client, value, page_id="page-feed", secret="fb-secret"):
    payload = {"entry": [{"id": page_id, "changes": [{"field": "feed", "value": value}]}]}
    body = json.dumps(payload).encode()
    return client.post(
        reverse("inbox_webhooks:webhook_facebook"),
        data=body,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=_sign_body(body, secret),
    )


_FB_ENV = override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_secret": "fb-secret"}})


@pytest.mark.django_db
class TestFacebookFeedItemFiltering:
    """`feed` carries every Page timeline change, not just comments."""

    @_FB_ENV
    def test_a_reaction_on_a_comment_does_not_become_an_inbox_item(self, client, fb_account):
        # Reactions carry comment_id too, so without an `item` gate this lands
        # in the inbox as an empty-bodied "comment".
        response = _post_feed_event(
            client,
            {
                "item": "reaction",
                "reaction_type": "like",
                "comment_id": "comment-liked",
                "post_id": "page-feed_post-1",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        assert response.status_code == 200
        assert not InboxMessage.objects.filter(social_account=fb_account).exists()

    @_FB_ENV
    def test_the_pages_own_new_post_does_not_become_an_inbox_item(self, client, fb_account):
        response = _post_feed_event(
            client,
            {
                "item": "status",
                "post_id": "page-feed_post-2",
                "message": "Our new post",
                "from": {"id": "page-feed", "name": "Feed Page"},
            },
        )

        assert response.status_code == 200
        assert not InboxMessage.objects.filter(social_account=fb_account).exists()

    @_FB_ENV
    def test_a_removed_comment_is_archived_rather_than_recreated(self, client, fb_account):
        existing = InboxMessage.objects.create(
            workspace=fb_account.workspace,
            social_account=fb_account,
            platform_message_id="comment-gone",
            message_type=InboxMessage.MessageType.COMMENT,
            sender_name="Sam",
            body="Deleted soon",
            received_at=timezone.now(),
        )

        response = _post_feed_event(
            client,
            {
                "item": "comment",
                "verb": "remove",
                "comment_id": "comment-gone",
                "post_id": "page-feed_post-1",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        assert response.status_code == 200
        existing.refresh_from_db()
        assert existing.status == InboxMessage.Status.ARCHIVED
        assert InboxMessage.objects.filter(social_account=fb_account).count() == 1

    @_FB_ENV
    def test_an_added_comment_still_arrives(self, client, fb_account):
        response = _post_feed_event(
            client,
            {
                "item": "comment",
                "verb": "add",
                "comment_id": "comment-new",
                "post_id": "page-feed_post-1",
                "message": "Nice work",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        assert response.status_code == 200
        message = InboxMessage.objects.get(social_account=fb_account, platform_message_id="comment-new")
        assert message.body == "Nice work"
        assert message.extra["stored_post_id"] == "post-1"

    @_FB_ENV
    def test_an_edited_comment_we_have_not_seen_still_arrives(self, client, fb_account):
        response = _post_feed_event(
            client,
            {
                "item": "comment",
                "verb": "edited",
                "comment_id": "comment-edited",
                "post_id": "page-feed_post-1",
                "message": "Nice work, actually",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        assert response.status_code == 200
        assert InboxMessage.objects.filter(platform_message_id="comment-edited").exists()

    @_FB_ENV
    def test_a_comment_is_linked_to_the_post_it_belongs_to(self, client, fb_account):
        from apps.composer.models import PlatformPost, Post

        post = Post.objects.create(workspace=fb_account.workspace, caption="hi")
        platform_post = PlatformPost.objects.create(
            post=post,
            social_account=fb_account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="post-1",
        )

        _post_feed_event(
            client,
            {
                "item": "comment",
                "verb": "add",
                "comment_id": "comment-linked",
                "post_id": "page-feed_post-1",
                "message": "Nice",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        message = InboxMessage.objects.get(platform_message_id="comment-linked")
        assert message.related_post_id == platform_post.id

    @_FB_ENV
    def test_a_top_level_comments_parent_id_is_not_stored(self, client, fb_account):
        """Facebook reports parent_id == post_id for a top-level comment. Keeping
        it would make the inbox reply post a new top-level comment on the post
        instead of answering the person."""
        _post_feed_event(
            client,
            {
                "item": "comment",
                "verb": "add",
                "comment_id": "comment-top",
                "post_id": "page-feed_post-1",
                "parent_id": "page-feed_post-1",
                "message": "Hello",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        message = InboxMessage.objects.get(platform_message_id="comment-top")
        assert "parent_id" not in message.extra

    @_FB_ENV
    def test_a_real_reply_keeps_its_parent_comment_id(self, client, fb_account):
        _post_feed_event(
            client,
            {
                "item": "comment",
                "verb": "add",
                "comment_id": "comment-child",
                "post_id": "page-feed_post-1",
                "parent_id": "comment-parent",
                "message": "Replying",
                "from": {"id": "user-9", "name": "Sam"},
            },
        )

        message = InboxMessage.objects.get(platform_message_id="comment-child")
        assert message.extra["parent_id"] == "comment-parent"

    @_FB_ENV
    def test_an_edit_replaces_the_stored_body(self, client, fb_account):
        base = {
            "item": "comment",
            "comment_id": "comment-edit",
            "post_id": "page-feed_post-1",
            "from": {"id": "user-9", "name": "Sam"},
        }
        _post_feed_event(client, {**base, "verb": "add", "message": "this is broken"})
        _post_feed_event(client, {**base, "verb": "edited", "message": "never mind, fixed it"})

        message = InboxMessage.objects.get(platform_message_id="comment-edit")
        assert message.body == "never mind, fixed it"
        assert InboxMessage.objects.filter(social_account=fb_account).count() == 1

    @_FB_ENV
    def test_a_mention_carries_the_stripped_post_id(self, client, fb_account):
        from apps.composer.models import PlatformPost, Post

        post = Post.objects.create(workspace=fb_account.workspace, caption="hi")
        platform_post = PlatformPost.objects.create(
            post=post,
            social_account=fb_account,
            status=PlatformPost.Status.PUBLISHED,
            platform_post_id="post-9",
        )
        payload = {
            "entry": [
                {
                    "id": "page-feed",
                    "changes": [
                        {
                            "field": "mention",
                            "value": {
                                "post_id": "page-feed_post-9",
                                "message": "shout out",
                                "from": {"id": "user-9", "name": "Sam"},
                            },
                        }
                    ],
                }
            ]
        }
        body = json.dumps(payload).encode()
        client.post(
            reverse("inbox_webhooks:webhook_facebook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=_sign_body(body, "fb-secret"),
        )

        message = InboxMessage.objects.get(platform_message_id="page-feed_post-9")
        assert message.extra["stored_post_id"] == "post-9"
        assert message.related_post_id == platform_post.id

    @_FB_ENV
    def test_an_edit_does_not_overwrite_a_manual_sentiment(self, client, fb_account):
        """A human who set the sentiment by hand outranks the classifier."""
        base = {
            "item": "comment",
            "comment_id": "comment-manual",
            "post_id": "page-feed_post-1",
            "from": {"id": "user-9", "name": "Sam"},
        }
        _post_feed_event(client, {**base, "verb": "add", "message": "terrible"})

        message = InboxMessage.objects.get(platform_message_id="comment-manual")
        message.sentiment = InboxMessage.Sentiment.POSITIVE
        message.sentiment_source = InboxMessage.SentimentSource.MANUAL
        message.save(update_fields=["sentiment", "sentiment_source"])

        _post_feed_event(client, {**base, "verb": "edited", "message": "still terrible"})

        message.refresh_from_db()
        assert message.body == "still terrible"
        assert message.sentiment == InboxMessage.Sentiment.POSITIVE
        assert message.sentiment_source == InboxMessage.SentimentSource.MANUAL

    @_FB_ENV
    def test_an_edit_reclassifies_an_auto_scored_comment(self, client, fb_account):
        base = {
            "item": "comment",
            "comment_id": "comment-auto",
            "post_id": "page-feed_post-1",
            "from": {"id": "user-9", "name": "Sam"},
        }
        _post_feed_event(client, {**base, "verb": "add", "message": "this is terrible"})
        _post_feed_event(client, {**base, "verb": "edited", "message": "this is great, thanks!"})

        message = InboxMessage.objects.get(platform_message_id="comment-auto")
        assert message.sentiment_source == InboxMessage.SentimentSource.AUTO
        from apps.inbox.sentiment import analyze_sentiment

        assert message.sentiment == analyze_sentiment("this is great, thanks!")
