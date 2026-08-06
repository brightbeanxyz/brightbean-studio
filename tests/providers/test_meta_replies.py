"""Reply and webhook-subscription behaviour for the three Meta providers.

These cover the edges Meta actually accepts: comments answered on a comment
edge, DMs sent through the Send API addressed to a person's scoped ID, and the
HUMAN_AGENT tag once the incoming message is more than 24 hours old.
"""

from unittest.mock import MagicMock

import pytest

from providers.exceptions import APIError
from providers.facebook import FacebookProvider
from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider


def _resp(data):
    return MagicMock(json=MagicMock(return_value=data))


CREDS = {"client_id": "id", "client_secret": "secret"}


# ----------------------------------------------------------------- comments


def test_facebook_comment_reply_posts_to_the_comment_edge():
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock(return_value=_resp({"id": "reply-1"}))

    result = provider.reply_to_comment("page-token", "comment-9", "Thanks!")

    assert result.platform_message_id == "reply-1"
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/comment-9/comments",
        access_token="page-token",
        json={"message": "Thanks!"},
    )


def test_instagram_comment_reply_posts_to_the_replies_edge():
    provider = InstagramProvider({**CREDS, "ig_user_id": "ig-1"})
    provider._request = MagicMock(return_value=_resp({"id": "reply-2"}))

    result = provider.reply_to_comment("token", "comment-9", "Thanks!")

    assert result.platform_message_id == "reply-2"
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/comment-9/replies",
        access_token="token",
        json={"message": "Thanks!"},
    )


def test_instagram_login_comment_reply_uses_the_instagram_graph_host():
    provider = InstagramLoginProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"id": "reply-3"}))

    provider.reply_to_comment("token", "comment-9", "Thanks!")

    provider._request.assert_called_once_with(
        "POST",
        "https://graph.instagram.com/v25.0/comment-9/replies",
        access_token="token",
        json={"message": "Thanks!"},
    )


# ---------------------------------------------------------------------- DMs


def test_facebook_dm_reply_uses_send_api_with_psid_recipient():
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock(return_value=_resp({"message_id": "mid.1", "recipient_id": "psid-7"}))

    result = provider.reply_to_message(
        "page-token",
        "mid.incoming",
        "Hi there",
        extra={"sender_id": "psid-7"},
    )

    assert result.platform_message_id == "mid.1"
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/page-1/messages",
        access_token="page-token",
        json={
            "recipient": {"id": "psid-7"},
            "message": {"text": "Hi there"},
            "messaging_type": "RESPONSE",
        },
    )


def test_facebook_dm_reply_tags_human_agent_when_overdue():
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock(return_value=_resp({"message_id": "mid.2"}))

    provider.reply_to_message(
        "page-token",
        "mid.incoming",
        "Sorry for the delay",
        extra={"sender_id": "psid-7"},
        human_agent=True,
    )

    payload = provider._request.call_args.kwargs["json"]
    assert payload["messaging_type"] == "MESSAGE_TAG"
    assert payload["tag"] == "HUMAN_AGENT"


@pytest.mark.parametrize(
    "extra,expected",
    [
        ({"recipient_id": "explicit"}, "explicit"),
        ({"sender": {"id": "from-webhook"}}, "from-webhook"),
        ({"from": {"id": "from-polling"}}, "from-polling"),
        ({"sender_id": "stored"}, "stored"),
        # recipient_id wins when several are present
        ({"recipient_id": "explicit", "sender_id": "stored"}, "explicit"),
    ],
)
def test_facebook_resolves_recipient_from_either_payload_shape(extra, expected):
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock(return_value=_resp({"message_id": "mid"}))

    provider.reply_to_message("t", "mid.in", "hi", extra=extra)

    assert provider._request.call_args.kwargs["json"]["recipient"] == {"id": expected}


def test_facebook_dm_reply_refuses_without_a_recipient():
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock()

    with pytest.raises(APIError, match="page-scoped ID"):
        provider.reply_to_message("t", "mid.in", "hi", extra={})

    provider._request.assert_not_called()


def test_instagram_via_facebook_offers_no_dm_surface():
    """That OAuth flow never requests instagram_manage_messages.

    Leaving the methods in place would produce runtime API rejections instead
    of a clear "this connection cannot do DMs".
    """
    provider = InstagramProvider({**CREDS, "ig_user_id": "ig-1"})

    with pytest.raises(NotImplementedError):
        provider.get_messages("token")
    with pytest.raises(NotImplementedError):
        provider.reply_to_message("token", "mid.in", "Hi", extra={"sender_id": "igsid-2"})


def test_instagram_via_facebook_does_not_subscribe_to_messages():
    provider = InstagramProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"success": True}))

    provider.subscribe_webhooks("page-token", "page-77")

    fields = provider._request.call_args.kwargs["params"]["subscribed_fields"]
    assert "messages" not in fields


def test_instagram_login_dm_reply_addresses_me_on_the_instagram_host():
    provider = InstagramLoginProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"message_id": "mid.4"}))

    provider.reply_to_message("token", "mid.in", "Hi", extra={"sender_id": "igsid-2"}, human_agent=True)

    args = provider._request.call_args
    assert args.args == ("POST", "https://graph.instagram.com/v25.0/me/messages")
    assert args.kwargs["json"]["tag"] == "HUMAN_AGENT"


def test_instagram_login_dm_reply_refuses_without_a_recipient():
    provider = InstagramLoginProvider(CREDS)
    provider._request = MagicMock()

    with pytest.raises(APIError, match="Instagram-scoped ID"):
        provider.reply_to_message("t", "mid.in", "hi", extra=None)

    provider._request.assert_not_called()


# ------------------------------------------------------------------ webhooks


def test_facebook_subscribes_page_to_feed_mention_and_messages():
    provider = FacebookProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"success": True}))

    assert provider.subscribe_webhooks("page-token", "page-1") is True
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/page-1/subscribed_apps",
        access_token="page-token",
        params={"subscribed_fields": "feed,mention,messages"},
    )


def test_facebook_unsubscribe_deletes_the_subscription():
    provider = FacebookProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"success": True}))

    assert provider.unsubscribe_webhooks("page-token", "page-1") is True
    provider._request.assert_called_once_with(
        "DELETE",
        "https://graph.facebook.com/v25.0/page-1/subscribed_apps",
        access_token="page-token",
    )


def test_facebook_subscribe_reports_failure_without_raising():
    provider = FacebookProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"success": False}))

    assert provider.subscribe_webhooks("page-token", "page-1") is False


def test_instagram_subscribes_through_the_linked_page():
    provider = InstagramProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"success": True}))

    assert provider.subscribe_webhooks("page-token", "page-77") is True
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.facebook.com/v25.0/page-77/subscribed_apps",
        access_token="page-token",
        params={"subscribed_fields": "comments,mentions"},
    )


def test_instagram_login_subscribes_the_account_itself():
    provider = InstagramLoginProvider(CREDS)
    provider._request = MagicMock(return_value=_resp({"success": True}))

    assert provider.subscribe_webhooks("token", "ignored-17") is True
    provider._request.assert_called_once_with(
        "POST",
        "https://graph.instagram.com/v25.0/me/subscribed_apps",
        access_token="token",
        params={"subscribed_fields": "comments,messages"},
    )


def test_providers_without_webhook_support_report_false():
    from providers.bluesky import BlueskyProvider

    provider = BlueskyProvider(CREDS)
    assert provider.subscribe_webhooks("t", "a") is False
    assert provider.unsubscribe_webhooks("t", "a") is False


# ------------------------------------------------- sender id survives polling


def test_facebook_polled_messages_carry_the_sender_psid():
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"id": "convo-1"}]}),
            _resp(
                {
                    "data": [
                        {
                            "id": "mid.9",
                            "message": "Hello",
                            "from": {"id": "psid-7", "name": "Marta"},
                            "created_time": "2026-08-01T10:00:00+0000",
                        }
                    ]
                }
            ),
        ]
    )

    messages = provider.get_messages("page-token")

    assert messages[0].extra["sender_id"] == "psid-7"
    assert messages[0].extra["conversation_id"] == "convo-1"


# ------------------------------------------------- shared recipient resolver


def test_the_recipient_resolver_is_shared_by_the_messaging_providers():
    """One resolver, so a new payload shape is taught in one place.

    Instagram-via-Facebook is absent on purpose: that flow has no DM surface,
    because it never requests instagram_manage_messages.
    """
    from providers import facebook, instagram_login
    from providers.meta_messaging import resolve_recipient_id

    assert facebook.resolve_recipient_id is resolve_recipient_id
    assert instagram_login.resolve_recipient_id is resolve_recipient_id


def test_resolver_ignores_a_nested_key_with_no_id():
    from providers.meta_messaging import resolve_recipient_id

    assert resolve_recipient_id({"sender": {}, "sender_id": "fallback"}) == "fallback"
    assert resolve_recipient_id({}) == ""
    assert resolve_recipient_id(None) == ""


def test_send_payload_only_carries_a_tag_when_asked():
    from providers.meta_messaging import build_send_payload

    plain = build_send_payload("psid", "hi")
    assert plain["messaging_type"] == "RESPONSE"
    assert "tag" not in plain

    tagged = build_send_payload("psid", "hi", human_agent=True)
    assert tagged["messaging_type"] == "MESSAGE_TAG"
    assert tagged["tag"] == "HUMAN_AGENT"


# ------------------------------------------- comment vs media reply edge (IG)


@pytest.mark.parametrize(
    "provider_cls,host",
    [
        (InstagramProvider, "https://graph.facebook.com/v25.0"),
        (InstagramLoginProvider, "https://graph.instagram.com/v25.0"),
    ],
)
def test_caption_mention_is_answered_on_the_media_comments_edge(provider_cls, host):
    """A media ID has no replies edge; commenting on the media is the answer."""
    provider = provider_cls({**CREDS, "ig_user_id": "ig-1"})
    provider._request = MagicMock(return_value=_resp({"id": "r-1"}))

    provider.reply_to_comment("token", "media-9", "Thanks!", {"reply_edge": "media"})

    assert provider._request.call_args.args == ("POST", f"{host}/media-9/comments")


@pytest.mark.parametrize(
    "provider_cls,host",
    [
        (InstagramProvider, "https://graph.facebook.com/v25.0"),
        (InstagramLoginProvider, "https://graph.instagram.com/v25.0"),
    ],
)
def test_comment_mention_still_uses_the_replies_edge(provider_cls, host):
    provider = provider_cls({**CREDS, "ig_user_id": "ig-1"})
    provider._request = MagicMock(return_value=_resp({"id": "r-1"}))

    provider.reply_to_comment("token", "comment-9", "Thanks!", {"reply_edge": "comment"})

    assert provider._request.call_args.args == ("POST", f"{host}/comment-9/replies")


# ------------------------------------------- the account's own messages


def test_facebook_polling_skips_the_pages_own_replies():
    """A conversation holds both sides; our sent replies must not come back.

    Once the Send API call works, the next poll returns the Page's own message
    and would create it as a fresh inbound DM, re-notifying the team.
    """
    provider = FacebookProvider({**CREDS, "page_id": "page-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"id": "convo-1"}]}),
            _resp(
                {
                    "data": [
                        {
                            "id": "mid.customer",
                            "message": "Do you ship?",
                            "from": {"id": "psid-7", "name": "Marta"},
                            "created_time": "2026-08-01T10:00:00+0000",
                        },
                        {
                            "id": "mid.ours",
                            "message": "Yes we do!",
                            "from": {"id": "page-1", "name": "Northlight"},
                            "created_time": "2026-08-01T10:05:00+0000",
                        },
                    ]
                }
            ),
        ]
    )

    messages = provider.get_messages("page-token")

    assert [m.platform_message_id for m in messages] == ["mid.customer"]


def test_instagram_login_polling_skips_the_accounts_own_replies():
    provider = InstagramLoginProvider({**CREDS, "ig_user_id": "ig-self"})
    provider._request = MagicMock(
        return_value=_resp(
            {
                "data": [
                    {
                        "id": "convo-1",
                        "messages": {
                            "data": [
                                {
                                    "id": "mid.customer",
                                    "message": "Hi",
                                    "from": {"id": "igsid-2", "username": "curious"},
                                    "created_time": "2026-08-01T10:00:00+0000",
                                },
                                {
                                    "id": "mid.ours",
                                    "message": "Hello!",
                                    "from": {"id": "ig-self", "username": "northlight"},
                                    "created_time": "2026-08-01T10:05:00+0000",
                                },
                            ]
                        },
                    }
                ]
            }
        )
    )

    messages = provider.get_messages("token")

    assert [m.platform_message_id for m in messages] == ["mid.customer"]


def test_instagram_login_without_its_own_id_keeps_every_message():
    """Filtering must not silently drop inbound mail when the ID is unknown."""
    provider = InstagramLoginProvider(CREDS)
    provider._request = MagicMock(
        return_value=_resp(
            {
                "data": [
                    {
                        "id": "convo-1",
                        "messages": {
                            "data": [
                                {
                                    "id": "mid.customer",
                                    "message": "Hi",
                                    "from": {"id": "igsid-2", "username": "curious"},
                                    "created_time": "2026-08-01T10:00:00+0000",
                                }
                            ]
                        },
                    }
                ]
            }
        )
    )

    assert len(provider.get_messages("token")) == 1
