"""The Instagram DM walk survives a slow Graph API without losing progress."""

import httpx
import pytest

from providers.meta_messaging import DM_REQUEST_TIMEOUT_SECONDS, fetch_instagram_page_messages

BASE = "https://graph.facebook.com/v25.0"


class FakeGraph:
    """Answers each conversation with one DM; times out on chosen call numbers."""

    def __init__(self, timeout_on=()):
        self.calls = []
        self.timeout_on = set(timeout_on)

    def __call__(self, method, url, **kwargs):
        self.calls.append((url, kwargs["timeout"]))
        if len(self.calls) in self.timeout_on:
            raise httpx.ReadTimeout("slow")
        if url.endswith("/conversations"):
            payload = {"data": [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]}
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
