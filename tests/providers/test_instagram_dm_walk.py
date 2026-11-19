"""The Instagram DM walk survives a slow Graph API and sees new chats first."""

import httpx
import pytest

from providers.meta_messaging import DM_REQUEST_TIMEOUT_SECONDS, fetch_instagram_page_messages

BASE = "https://graph.facebook.com/v25.0"
T0 = "2026-11-10T10:00:00+0000"
T1 = "2026-11-18T20:59:00+0000"


class FakeGraph:
    """Lists the given conversations, answers each with one DM, can time out."""

    def __init__(self, conversations=(("c1", T0), ("c2", T0), ("c3", T0)), timeout_on=()):
        self.conversations = list(conversations)
        self.calls = []
        self.timeout_on = set(timeout_on)

    def __call__(self, method, url, **kwargs):
        self.calls.append((url, kwargs["timeout"]))
        if len(self.calls) in self.timeout_on:
            raise httpx.ReadTimeout("slow")
        if url.endswith("/conversations"):
            payload = {"data": [{"id": cid, "updated_time": stamp} for cid, stamp in self.conversations]}
        else:
            convo = url.rsplit("/", 2)[-2]
            payload = {
                "data": [
                    {
                        "id": f"m-{convo}",
                        "message": "hi",
                        "from": {"id": "customer"},
                        "created_time": "2026-11-18T10:00:00+0000",
                    }
                ]
            }
        return httpx.Response(200, json=payload, request=httpx.Request(method, url))

    def fetched_conversations(self):
        return [url.rsplit("/", 2)[-2] for url, _ in self.calls if url.endswith("/messages")]


def _walk(request, poll_state=None):
    return fetch_instagram_page_messages(
        request,
        base_url=BASE,
        page_id="page",
        owner_id="owner",
        access_token="token",
        poll_state=poll_state,
    )


def test_every_request_gets_the_full_timeout():
    """A call started late in the walk must not get a 1 s timeout against a 3 s API."""
    graph = FakeGraph()
    _walk(graph)

    assert {timeout for _, timeout in graph.calls} == {DM_REQUEST_TIMEOUT_SECONDS}


def test_a_timeout_after_progress_keeps_messages_and_cursor():
    graph = FakeGraph(timeout_on={3})  # list, c1 messages, then c2 times out
    batch = _walk(graph)

    assert [m.platform_message_id for m in batch] == ["m-c1"]
    assert batch.poll_state["conversations"] == ["c2", "c3"]


def test_the_next_poll_resumes_where_the_timeout_stopped():
    first = _walk(FakeGraph(timeout_on={3}))
    second = _walk(FakeGraph(), poll_state=first.poll_state)

    assert [m.platform_message_id for m in second] == ["m-c2", "m-c3"]


def test_a_timeout_before_any_progress_still_raises():
    """A dead API must stay visible as a failed sync, not look like an empty inbox."""
    with pytest.raises(httpx.ReadTimeout):
        _walk(FakeGraph(timeout_on={1}))


def test_a_recently_updated_chat_is_read_before_the_old_backlog():
    """A new DM must not wait for the whole history walk to finish."""
    state = {
        "page_id": "page",
        "owner_id": "owner",
        "conversations": ["old1", "old2"],
        "conversation_after": "next-page",
        "message_after": None,
        "recent_watermark": T0,
    }
    graph = FakeGraph(conversations=[("new", T1), ("c1", T0)])
    batch = _walk(graph, poll_state=state)

    assert graph.fetched_conversations()[:3] == ["new", "old1", "old2"]
    assert batch.poll_state["recent_watermark"] == "2026-11-18T20:59:00+00:00"


def test_a_half_read_chat_is_not_interrupted_by_a_new_one():
    state = {
        "page_id": "page",
        "owner_id": "owner",
        "conversations": ["old1", "old2"],
        "conversation_after": None,
        "message_after": "cursor-in-old1",
        "recent_watermark": T0,
    }
    graph = FakeGraph(conversations=[("new", T1)], timeout_on={2})  # list ok, old1 times out
    batch = _walk(graph, poll_state=state)

    assert batch.poll_state["conversations"] == ["old1", "new", "old2"]
    assert batch.poll_state["message_after"] == "cursor-in-old1"


def test_a_finished_walk_only_checks_recent_chats_next_time():
    """Re-walking the whole history every poll is what made the walk so slow."""
    first = _walk(FakeGraph())
    assert first.poll_state["conversations"] == []
    assert first.poll_state["recent_watermark"]

    graph = FakeGraph()  # nothing newer than the watermark
    second = _walk(graph, poll_state=first.poll_state)

    assert len(graph.calls) == 1  # the recent-chats list, no history walk
    assert list(second) == []
