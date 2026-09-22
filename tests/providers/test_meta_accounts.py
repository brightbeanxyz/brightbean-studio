"""The shared /me/accounts walk both Facebook-hosted Meta providers use."""

from unittest.mock import MagicMock

import httpx
import pytest

from providers.exceptions import APIError
from providers.facebook import FacebookProvider
from providers.meta_accounts import META_ACCOUNTS_MAX_PAGES, fetch_me_accounts, page_can_publish


def _resp(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", "https://graph.facebook.com/"))


def _page(cursor: str | None = None, entries: list[dict] | None = None) -> httpx.Response:
    body: dict = {"data": entries if entries is not None else [{"id": "p"}]}
    if cursor:
        body["paging"] = {"cursors": {"after": cursor}, "next": "https://graph.facebook.com/next"}
    return _resp(body)


def _fetch(provider, **kwargs):
    return fetch_me_accounts(
        provider,
        access_token="user-token",
        base_url="https://graph.facebook.com/v25.0",
        fields="id,name",
        error_message="Failed to fetch pages",
        **kwargs,
    )


def test_a_repeated_cursor_stops_the_walk():
    """A Graph that keeps handing back the same cursor must not spin forever."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(side_effect=[_page("same"), _page("same"), _page("same")])

    assert len(_fetch(provider)) == 2
    assert provider._request.call_count == 2


def test_the_time_budget_stops_the_walk(caplog):
    """This runs inside the OAuth callback; an unbounded walk times the request out."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(side_effect=lambda *a, **k: _page(f"c{provider._request.call_count}"))

    with caplog.at_level("WARNING"):
        pages = _fetch(provider, max_seconds=-1)

    assert len(pages) == 1
    assert provider._request.call_count == 1
    assert "time budget" in caplog.text
    assert "truncated" in caplog.text


def test_each_request_is_bounded_by_the_remaining_budget():
    """A page answering at 19 of 20 seconds must not start a 30-second call.

    The budget exists to keep the whole walk under the router timeout, so it
    has to bound the requests themselves, not just the gaps between them.
    """
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(side_effect=[_page("c1"), _page(None)])

    _fetch(provider, max_seconds=5)

    timeouts = [c.kwargs["timeout"] for c in provider._request.call_args_list]
    assert all(t <= 5 for t in timeouts), timeouts
    # Strictly shrinking: the second call can only have what the first left.
    assert timeouts[1] <= timeouts[0]


def test_a_spent_budget_still_allows_the_first_request():
    """Never hand httpx a zero or negative timeout."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(return_value=_page(None))

    _fetch(provider, max_seconds=-1)

    assert provider._request.call_args.kwargs["timeout"] > 0


def test_exhausting_the_page_cap_is_logged_not_silent(caplog):
    """Silently hiding the remainder is the bug following cursors set out to fix."""
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(side_effect=lambda *a, **k: _page(f"c{provider._request.call_count}"))

    with caplog.at_level("WARNING"):
        pages = _fetch(provider)

    assert provider._request.call_count == META_ACCOUNTS_MAX_PAGES
    assert len(pages) == META_ACCOUNTS_MAX_PAGES
    assert "page cap" in caplog.text


def test_a_complete_walk_logs_no_truncation_warning(caplog):
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(side_effect=[_page("c1"), _page(None)])

    with caplog.at_level("WARNING"):
        assert len(_fetch(provider)) == 2

    assert "truncated" not in caplog.text


def test_a_graph_error_body_raises():
    provider = FacebookProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(return_value=_resp({"error": {"message": "Bad token"}}))

    with pytest.raises(APIError, match="Failed to fetch pages: Bad token"):
        _fetch(provider)


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        ({"tasks": ["CREATE_CONTENT", "ANALYZE"]}, True),
        ({"tasks": ["ANALYZE"]}, False),
        # Explicitly empty is Meta saying "no tasks", not "field unavailable".
        ({"tasks": []}, False),
        # Omitted predates the field: unknown, so keep the historical behaviour.
        ({}, True),
    ],
)
def test_page_can_publish_reads_the_task_list(page, expected):
    assert page_can_publish(page) is expected
