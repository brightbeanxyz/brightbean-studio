from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from providers.exceptions import (
    APIError,
    MessagingError,
    OAuthError,
    RateLimitError,
    TokenExpiredError,
    WebhookChannelError,
)
from providers.facebook import FacebookProvider
from providers.instagram import InstagramProvider
from providers.meta_messaging import normalize_attachments


def response(data):
    return SimpleNamespace(json=lambda: data)


def provider():
    return InstagramProvider(
        {"client_id": "app-1", "client_secret": "secret", "ig_user_id": "ig-1", "page_id": "page-1"}
    )


@pytest.mark.parametrize("flag", [None, False, True, "false", "true"])
def test_oauth_requests_message_permission_by_default_with_explicit_opt_out(flag):
    instance = provider()
    if flag is not None:
        instance.credentials["dm_oauth_scopes_enabled"] = flag
    scopes = parse_qs(urlparse(instance.get_auth_url("https://example.com/cb", "s")).query)["scope"][0].split(",")
    assert "instagram_manage_messages" in instance.required_scopes
    omitted = {"instagram_manage_messages"} if flag in (False, "false") else set()
    assert set(scopes) == set(instance.required_scopes) - omitted
    assert "pages_manage_metadata" in scopes


@pytest.mark.parametrize("flag", [False, True])
def test_business_login_preserves_its_configuration_in_both_flag_states(flag):
    instance = provider()
    instance.credentials["dm_oauth_scopes_enabled"] = flag
    instance.credentials["config_id"] = "config-1"
    query = parse_qs(urlparse(instance.get_auth_url("https://example.com/cb", "s")).query)
    assert query["config_id"] == ["config-1"]
    assert "scope" not in query
    assert query["response_type"] == ["code"]
    assert query["override_default_response_type"] == ["true"]


@pytest.mark.parametrize("flag", [False, True])
def test_existing_grant_can_send_in_both_flag_states(flag):
    instance = provider()
    instance.credentials["dm_oauth_scopes_enabled"] = flag
    instance._request = MagicMock(return_value=response({"message_id": "sent-1"}))
    result = instance.reply_to_message("page-token", "incoming", "Thanks", {"sender_id": "customer"})
    assert result.platform_message_id == "sent-1"
    assert instance._request.call_args.args[1].endswith("/page-1/messages")


@pytest.mark.parametrize("flag", [False, True])
def test_missing_message_scope_only_prompts_reconnect_when_requested(flag):
    instance = provider()
    instance.credentials.update(dm_oauth_scopes_enabled=flag, missing_scopes=["instagram_manage_messages"])
    instance._request = MagicMock(return_value=response({"success": True}))
    if flag:
        with pytest.raises(WebhookChannelError, match="Reconnect") as error:
            instance.subscribe_webhooks("page-token", "ig-1")
        assert error.value.needs_reconnect
    else:
        assert instance.subscribe_webhooks("page-token", "ig-1")
    assert instance._request.call_count == 1
    assert instance._request.call_args.args[1].endswith("/ig-1/subscribed_apps")


def test_metadata_scope_still_requires_reconnect_with_message_requests_off():
    instance = provider()
    instance.credentials["dm_oauth_scopes_enabled"] = False
    instance.credentials["missing_scopes"] = ["instagram_manage_messages", "pages_manage_metadata"]
    instance._request = MagicMock(return_value=response({"success": True}))
    with pytest.raises(WebhookChannelError, match="Page metadata permissions.*Reconnect") as error:
        instance.subscribe_webhooks("page-token", "ig-1")
    assert error.value.needs_reconnect
    assert instance._request.call_count == 1


def test_poll_walks_both_cursors_and_ignores_own_messages():
    instance = provider()
    stamp = "2026-10-12T10:00:00+0000"
    instance._request = MagicMock(
        side_effect=[
            response(
                {"data": [{"id": "convo-1"}], "paging": {"next": "https://untrusted/token", "cursors": {"after": "c2"}}}
            ),
            response(
                {
                    "data": [
                        {"id": "own", "from": {"id": "ig-1"}, "created_time": stamp},
                        {
                            "id": "m1",
                            "from": {"id": "customer"},
                            "created_time": stamp,
                            "attachments": {"data": [{"image_data": {"url": "https://cdn.example/image.jpg"}}]},
                        },
                    ],
                    "paging": {"next": "https://untrusted/token", "cursors": {"after": "m2"}},
                }
            ),
            response({"data": [{"id": "m2", "from": {"id": "customer"}, "created_time": stamp, "message": "Hi"}]}),
            response({"data": [{"id": "convo-2"}]}),
            response({"data": [{"id": "m3", "from": {"id": "other"}, "created_time": stamp, "message": "Hello"}]}),
        ]
    )
    messages = instance._fetch_direct_messages("page-token")
    assert [m.platform_message_id for m in messages] == ["m1", "m2", "m3"]
    assert messages[0].extra["attachments"] == [{"type": "image", "url": "https://cdn.example/image.jpg"}]
    assert messages[0].extra["sender_id"] == "customer"
    assert messages[0].timestamp == datetime(2026, 10, 12, 10, tzinfo=UTC)
    calls = instance._request.call_args_list
    assert calls[0].args[1].endswith("/page-1/conversations")
    assert calls[0].kwargs["params"]["platform"] == "instagram"
    assert calls[2].kwargs["params"]["after"] == "m2"
    assert calls[3].kwargs["params"]["after"] == "c2"
    assert all("untrusted" not in c.args[1] for c in calls)


@pytest.mark.parametrize("failed_half", ["dm", "comments"])
def test_partial_poll_failure_keeps_the_other_half(failed_half):
    instance = provider()
    instance._fetch_direct_messages = MagicMock(return_value=["dm"])
    instance._fetch_media_comments = MagicMock(return_value=["comments"])
    fetch = instance._fetch_direct_messages if failed_half == "dm" else instance._fetch_media_comments
    fetch.side_effect = APIError("private payload")
    assert instance.get_messages("token") == ["comments" if failed_half == "dm" else "dm"]


@pytest.mark.parametrize("text", ["", " " * 2, "a" * 1001, "🙂" * 251])
def test_send_validates_utf8_limit_before_network(text):
    instance = provider()
    instance._request = MagicMock()
    with pytest.raises(MessagingError, match="1,000"):
        instance.reply_to_message("token", "m", text, {"sender_id": "igsid"})
    instance._request.assert_not_called()


def test_send_requires_confirmation_id():
    instance = provider()
    instance._request = MagicMock(return_value=response({"success": True}))
    with pytest.raises(MessagingError, match="confirmed"):
        instance.reply_to_message("token", "m", "Hi", {"sender_id": "igsid"})


def test_subscriptions_preserve_page_fields_and_read_back():
    instance = provider()
    instance._request = MagicMock(
        side_effect=[
            response({"success": True}),
            response(
                {
                    "data": [
                        {"id": "app-1", "subscribed_fields": ["feed", "mention"]},
                        {"id": "other-app", "subscribed_fields": ["leadgen"]},
                    ]
                }
            ),
            response({"success": True}),
            response({"data": [{"id": "app-1", "subscribed_fields": ["feed", "mention", "messages"]}]}),
        ]
    )
    assert instance.subscribe_webhooks("page-token", "ig-1")
    calls = instance._request.call_args_list
    assert calls[0].args[1].endswith("/ig-1/subscribed_apps")
    assert calls[2].args[1].endswith("/page-1/subscribed_apps")
    assert set(calls[2].kwargs["params"]["subscribed_fields"].split(",")) == {"feed", "mention", "messages"}


def test_missing_permission_does_not_remove_comment_subscription():
    instance = provider()
    instance.credentials["dm_oauth_scopes_enabled"] = True
    instance.credentials["missing_scopes"] = ["instagram_manage_messages"]
    instance._request = MagicMock(return_value=response({"success": True}))
    with pytest.raises(WebhookChannelError, match="DM notifications") as failure:
        instance.subscribe_webhooks("token", "ig-1")
    assert failure.value.needs_reconnect
    assert instance._request.call_count == 1


def test_failed_page_readback_reports_dm_channel():
    instance = provider()
    instance._request = MagicMock(
        side_effect=[
            response({"success": True}),
            response({"data": []}),
            response({"success": True}),
            response({"data": []}),
        ]
    )
    with pytest.raises(WebhookChannelError, match="DM notifications"):
        instance.subscribe_webhooks("token", "ig-1")


def test_attachments_exclude_unsafe_urls_and_preserve_unavailable_media():
    assert normalize_attachments(
        [{"type": "image", "payload": {"url": "javascript:alert(1)"}}, {"type": "ephemeral"}]
    ) == [{"type": "image", "url": ""}, {"type": "ephemeral", "url": ""}]


def test_comment_high_water_mark_cannot_hide_an_older_dm():
    instance = provider()
    instance._request = MagicMock(
        side_effect=[
            response({"data": [{"id": "c"}]}),
            response(
                {
                    "data": [
                        {
                            "id": "m",
                            "from": {"id": "customer"},
                            "created_time": "2026-10-11T10:00:00Z",
                            "message": "Question",
                        }
                    ]
                }
            ),
        ]
    )
    messages = instance._fetch_direct_messages("token", since=datetime(2026, 10, 12, tzinfo=UTC))
    assert [m.platform_message_id for m in messages] == ["m"]


def test_facebook_reconnect_preserves_other_existing_page_fields():
    instance = FacebookProvider({"client_id": "app-1", "client_secret": "secret"})
    instance._request = MagicMock(
        side_effect=[
            response({"data": [{"id": "app-1", "subscribed_fields": ["messaging_postbacks", "messages"]}]}),
            response({"success": True}),
            response(
                {"data": [{"id": "app-1", "subscribed_fields": ["feed", "mention", "messages", "messaging_postbacks"]}]}
            ),
        ]
    )
    assert instance.subscribe_webhooks("token", "page-1")
    fields = instance._request.call_args_list[1].kwargs["params"]["subscribed_fields"].split(",")
    assert set(fields) == {"feed", "mention", "messages", "messaging_postbacks"}


def test_paginated_poll_has_a_shared_request_budget(caplog):
    instance = provider()
    calls = 0

    def endless_page(method, url, **kwargs):
        nonlocal calls
        calls += 1
        data = (
            [{"id": "conversation"}]
            if url.endswith("/conversations")
            else [{"id": f"message-{calls}", "from": {"id": "customer"}, "created_time": "2026-10-12T10:00:00Z"}]
        )
        return response(
            {"data": data, "paging": {"next": "https://untrusted.example/next", "cursors": {"after": str(calls)}}}
        )

    instance._request = MagicMock(side_effect=endless_page)
    messages = instance._fetch_direct_messages("page-token")
    assert len(messages) == 99
    assert instance._request.call_count == 100
    assert caplog.text.count("bounded request/time budget") == 1


def test_capped_poll_resumes_history_and_reaches_later_conversations():
    calls = []

    def paginated_request(method, url, **kwargs):
        after = kwargs["params"].get("after")
        calls.append((url.rsplit("/", 2)[-2], after))
        if url.endswith("/conversations"):
            if after == "next-conversations":
                return response({"data": [{"id": "last-conversation"}]})
            return response(
                {
                    "data": [{"id": "busy-conversation"}, {"id": "later-conversation"}],
                    "paging": {"next": "https://untrusted/token", "cursors": {"after": "next-conversations"}},
                }
            )
        page = int(after or "0")
        data = {"data": [{"id": f"{url}-{page}", "from": {"id": "customer"}, "created_time": "2026-10-12T10:00:00Z"}]}
        if "busy-conversation" in url and page < 100:
            data["paging"] = {"next": "https://untrusted/token", "cursors": {"after": str(page + 1)}}
        return response(data)

    first = provider()
    first._request = MagicMock(side_effect=paginated_request)
    batch = first._fetch_direct_messages("page-token")
    assert first._request.call_count == 100
    # Simulate a fresh worker/provider using the previous poll's durable state.
    second = provider()
    second.credentials["instagram_dm_poll_state"] = batch.poll_state
    second._request = MagicMock(side_effect=paginated_request)
    resumed = second._fetch_direct_messages("page-token")
    # Each poll first lists the newest chats, then resumes the half-read one.
    assert calls[100] == ("page-1", None)
    assert calls[101] == ("busy-conversation", "99")
    assert {message.extra["conversation_id"] for message in resumed} == {
        "busy-conversation",
        "later-conversation",
        "last-conversation",
    }
    assert resumed.poll_state == {}


def test_time_capped_poll_keeps_the_unvisited_conversation():
    clock = [0]

    def request(method, url, **kwargs):
        if url.endswith("/conversations"):
            return response({"data": [{"id": "first"}, {"id": "later"}]})
        clock[0] = 21
        return response({"data": []})

    first = provider()
    first._request = MagicMock(side_effect=request)
    with patch("providers.meta_messaging.time.monotonic", side_effect=lambda: clock[0]):
        batch = first._fetch_direct_messages("token")
    assert first._request.call_count == 2
    assert batch.poll_state["conversations"] == ["later"]

    second = provider()
    second.credentials["instagram_dm_poll_state"] = batch.poll_state
    second._request = MagicMock(return_value=response({"data": []}))
    assert second._fetch_direct_messages("token").poll_state == {}
    assert second._request.call_args.args[1].endswith("/later/messages")


def test_continuation_is_discarded_when_linked_page_changes():
    instance = provider()
    instance.credentials["instagram_dm_poll_state"] = {
        "page_id": "old-page",
        "owner_id": "ig-1",
        "conversations": ["old-conversation"],
    }
    instance._request = MagicMock(return_value=response({"data": []}))
    assert instance._fetch_direct_messages("token").poll_state == {}
    assert instance._request.call_args.args[1].endswith("/page-1/conversations")


@pytest.mark.parametrize(
    "comment_error,dm_error,needs_reconnect",
    [
        (APIError("permission", status_code=403), None, True),
        (TokenExpiredError("expired"), None, True),
        (OAuthError("revoked"), None, True),
        (APIError("permission", status_code=400, raw_response={"error": {"code": 200}}), None, True),
        (APIError("expired", status_code=400, raw_response={"error": {"code": 190}}), None, True),
        (APIError("permission", status_code=403), APIError("temporary", status_code=503), True),
        (APIError("temporary", status_code=503), APIError("permission", status_code=401), True),
        (RateLimitError("throttled"), None, False),
        (APIError("invalid parameter", status_code=400, raw_response={"error": {"code": 100}}), None, False),
        (None, APIError("invalid parameter", status_code=400), False),
    ],
)
def test_subscription_combines_both_channels_reconnect_requirements(comment_error, dm_error, needs_reconnect):
    instance = provider()

    def request(method, url, **kwargs):
        if url.endswith("/ig-1/subscribed_apps"):
            if comment_error:
                raise comment_error
            return response({"success": True})
        if dm_error:
            raise dm_error
        if method == "POST":
            return response({"success": True})
        return response({"data": [{"id": "app-1", "subscribed_fields": ["messages"]}]})

    instance._request = MagicMock(side_effect=request)
    with pytest.raises(WebhookChannelError) as failure:
        instance.subscribe_webhooks("page-token", "ig-1")
    assert failure.value.needs_reconnect is needs_reconnect
    assert instance._request.call_count >= 2
