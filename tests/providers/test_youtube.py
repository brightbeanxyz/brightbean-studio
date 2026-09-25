"""Tests for YouTubeProvider analytics, batching and error classification."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from providers.exceptions import APIError, QuotaExceededError, RateLimitError, TokenExpiredError
from providers.google_errors import next_google_quota_reset
from providers.youtube import (
    _ANALYTICS_VIDEO_FILTER_CHUNK,
    _MAX_COMMENT_PAGES,
    _MAX_DEEP_COMMENT_PAGES,
    ANALYTICS_BASE,
    API_BASE,
    UPLOAD_BASE,
    YouTubeProvider,
)


def _make_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


def _date_range() -> tuple[datetime, datetime]:
    return (
        datetime(2005, 2, 14, 0, 0, 0, tzinfo=UTC),
        datetime(2026, 6, 3, 23, 59, 59, tzinfo=UTC),
    )


class TestGetPostAnalytics:
    @patch.object(YouTubeProvider, "_request")
    def test_request_shape(self, mock_request):
        mock_request.return_value = _make_response(
            {
                "columnHeaders": [
                    {"name": "video"},
                    {"name": "estimatedMinutesWatched"},
                    {"name": "averageViewPercentage"},
                    {"name": "shares"},
                ],
                "rows": [],
            }
        )

        provider = YouTubeProvider()
        provider.get_post_analytics("token-xyz", ["abc123", "def456"], _date_range())

        # One call, GET against the Analytics /reports endpoint.
        assert mock_request.call_count == 1
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == "https://youtubeanalytics.googleapis.com/v2/reports"
        assert kwargs["access_token"] == "token-xyz"
        params = kwargs["params"]
        assert params["ids"] == "channel==MINE"
        assert params["startDate"] == "2005-02-14"
        assert params["endDate"] == "2026-06-03"
        assert params["metrics"] == "estimatedMinutesWatched,averageViewPercentage,shares"
        assert params["dimensions"] == "video"
        # filter joins post_ids with commas after the `video==` operator.
        assert params["filters"] == "video==abc123,def456"

    @patch.object(YouTubeProvider, "_request")
    def test_parses_rows_into_post_metrics(self, mock_request):
        mock_request.return_value = _make_response(
            {
                "columnHeaders": [
                    {"name": "video"},
                    {"name": "estimatedMinutesWatched"},
                    {"name": "averageViewPercentage"},
                    {"name": "shares"},
                ],
                "rows": [
                    ["abc123", 1500.0, 47.5, 12.0],
                    ["def456", 0.0, 0.0, 0.0],
                ],
            }
        )

        provider = YouTubeProvider()
        result = provider.get_post_analytics("token", ["abc123", "def456"], _date_range())

        assert set(result.keys()) == {"abc123", "def456"}
        # watch_time and avg_view_pct flow through ``extra`` (the catalog
        # mapper reads them from _GENERIC_POST_EXTRA_KEYS).
        assert result["abc123"].extra == {"watch_time": 1500.0, "avg_view_pct": 47.5}
        # shares lives on the PostMetrics dataclass field — that's where
        # ``_post_metrics_to_dict`` looks for it.
        assert result["abc123"].shares == 12
        # Real zero is preserved on extras, not dropped — same semantics
        # as the closure in get_account_metrics.
        assert result["def456"].extra == {"watch_time": 0.0, "avg_view_pct": 0.0}
        assert result["def456"].shares == 0

    @patch.object(YouTubeProvider, "_request")
    def test_none_columns_are_skipped(self, mock_request):
        # Analytics returns ``None`` when a metric isn't reportable for a row
        # (e.g. shares disabled for a video). Skip the key entirely — not 0.
        mock_request.return_value = _make_response(
            {
                "columnHeaders": [
                    {"name": "video"},
                    {"name": "estimatedMinutesWatched"},
                    {"name": "averageViewPercentage"},
                    {"name": "shares"},
                ],
                "rows": [
                    ["abc123", 100.0, None, None],
                ],
            }
        )

        provider = YouTubeProvider()
        result = provider.get_post_analytics("token", ["abc123"], _date_range())

        assert result["abc123"].extra == {"watch_time": 100.0}
        # ``None`` shares falls back to the dataclass default of 0 (and
        # ``_post_metrics_to_dict`` skips writing zero-valued shares rows).
        assert result["abc123"].shares == 0

    @patch.object(YouTubeProvider, "_request")
    def test_empty_post_ids_skips_request(self, mock_request):
        provider = YouTubeProvider()
        result = provider.get_post_analytics("token", [], _date_range())

        assert result == {}
        mock_request.assert_not_called()

    @patch.object(YouTubeProvider, "_request")
    def test_chunks_over_filter_cap(self, mock_request):
        # YouTube caps `filters=video==<list>` at 500 IDs. Inputs above that
        # are split into multiple requests and their results merged.
        chunk = _ANALYTICS_VIDEO_FILTER_CHUNK
        post_ids = [f"v{i}" for i in range(chunk + 3)]

        def fake_request(*args, **kwargs):
            ids = kwargs["params"]["filters"].removeprefix("video==").split(",")
            return _make_response(
                {
                    "columnHeaders": [
                        {"name": "video"},
                        {"name": "estimatedMinutesWatched"},
                        {"name": "averageViewPercentage"},
                        {"name": "shares"},
                    ],
                    "rows": [[vid, 1.0, 1.0, 1.0] for vid in ids],
                }
            )

        mock_request.side_effect = fake_request
        provider = YouTubeProvider()
        result = provider.get_post_analytics("token", post_ids, _date_range())

        assert mock_request.call_count == 2
        assert len(result) == chunk + 3

        first_filter = mock_request.call_args_list[0].kwargs["params"]["filters"]
        second_filter = mock_request.call_args_list[1].kwargs["params"]["filters"]
        assert len(first_filter.removeprefix("video==").split(",")) == chunk
        assert len(second_filter.removeprefix("video==").split(",")) == 3

    @patch.object(YouTubeProvider, "_request")
    def test_deadline_stops_before_the_next_filter_chunk(self, mock_request):
        chunk = _ANALYTICS_VIDEO_FILTER_CHUNK
        post_ids = [f"v{i}" for i in range(chunk + 3)]
        mock_request.return_value = _make_response({"columnHeaders": [], "rows": []})
        before_deadline = datetime(2026, 1, 1, tzinfo=UTC)
        after_deadline = datetime(2026, 1, 1, 0, 0, 2, tzinfo=UTC)

        with patch("providers.youtube.datetime") as mocked_datetime:
            mocked_datetime.now.side_effect = [before_deadline, after_deadline]
            provider = YouTubeProvider()
            result = provider.get_post_analytics(
                "token",
                post_ids,
                _date_range(),
                deadline=datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
            )

        assert result == {}
        assert mock_request.call_count == 1

    @patch.object(YouTubeProvider, "_request")
    def test_empty_rows_returns_empty_dict(self, mock_request):
        # API returns no rows when no videos have analytics data in the window.
        mock_request.return_value = _make_response(
            {
                "columnHeaders": [
                    {"name": "video"},
                    {"name": "estimatedMinutesWatched"},
                ],
                "rows": [],
            }
        )

        provider = YouTubeProvider()
        result = provider.get_post_analytics("token", ["abc"], _date_range())

        assert result == {}

    @patch.object(YouTubeProvider, "_request")
    def test_row_with_no_extra_is_omitted(self, mock_request):
        # If every metric column came back as None, the video should be
        # absent from the result — callers treat absence as "no data".
        mock_request.return_value = _make_response(
            {
                "columnHeaders": [
                    {"name": "video"},
                    {"name": "estimatedMinutesWatched"},
                    {"name": "averageViewPercentage"},
                    {"name": "shares"},
                ],
                "rows": [
                    ["abc123", None, None, None],
                    ["def456", 50.0, None, None],
                ],
            }
        )

        provider = YouTubeProvider()
        result = provider.get_post_analytics("token", ["abc123", "def456"], _date_range())

        assert set(result.keys()) == {"def456"}
        assert result["def456"].extra == {"watch_time": 50.0}


class TestErrorClassification:
    """Google reports a spent quota as 403, not 429.

    The base class only ever looked at the status code, so every quota failure
    arrived as a generic ``APIError`` — indistinguishable from a permission
    refusal. That is what let an exhausted quota tell healthy accounts to
    reconnect, and what let the analytics sync keep hammering an API that had
    already said "not until tomorrow".
    """

    @staticmethod
    def _error(status: int, payload: dict, *, url: str = f"{API_BASE}/videos") -> MagicMock:
        resp = MagicMock()
        resp.status_code = status
        resp.url = url
        resp.headers = {}
        resp.text = json.dumps(payload)
        resp.json = MagicMock(return_value=payload)
        return resp

    _QUOTA_BODY = {
        "error": {
            "code": 403,
            "message": 'The request cannot be completed because you have exceeded your <a href="/youtube/v3/getting-started#quota">quota</a>.',
            "errors": [{"reason": "quotaExceeded", "domain": "youtube.quota"}],
        }
    }

    def test_quota_exceeded_403_raises_quota_exceeded_error(self):
        # A pinned clock, injected rather than patched: provider and assertion
        # then share one instant, where two live reads either side of Pacific
        # midnight would be a day apart.
        now = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)

        exc = YouTubeProvider()._error_for_response(self._error(403, self._QUOTA_BODY), now=now)

        assert isinstance(exc, QuotaExceededError)
        # Subclassing RateLimitError is what keeps every existing consumer right.
        assert isinstance(exc, RateLimitError)
        assert exc.quota_scope == "data"
        assert exc.status_code == 403
        # The real helper, not a stand-in: this is the assertion that ties a
        # daily-quota deadline to Pacific midnight at all. Which midnight that
        # is belongs to tests/providers/test_google_errors.py.
        assert exc.resets_at == next_google_quota_reset(now)
        assert exc.resets_at == datetime(2026, 9, 18, 7, 0, tzinfo=UTC)
        # Prose, not the response body: error_messages._is_user_safe rejects
        # anything containing '{"'.
        assert '{"' not in str(exc)
        assert exc.raw_response == self._QUOTA_BODY

    def test_analytics_endpoint_quota_uses_analytics_scope(self):
        exc = YouTubeProvider()._error_for_response(self._error(403, self._QUOTA_BODY, url=f"{ANALYTICS_BASE}/reports"))

        assert exc.quota_scope == "analytics"

    @pytest.mark.parametrize(
        "url",
        [
            # The resumable-session POST that publish_post opens with.
            f"{UPLOAD_BASE}/videos?uploadType=resumable&part=snippet,status",
            # The PUT to the session's Location, which keeps the path.
            f"{UPLOAD_BASE}/videos?uploadType=resumable&part=snippet,status&upload_id=xa298sd_f",
        ],
    )
    def test_videos_insert_quota_uses_its_own_upload_scope(self, url):
        """``videos.insert`` has had a bucket of its own since June 2026.

        The body is the same ``quotaExceeded`` / ``youtube.quota`` the regular
        pool sends, so only the request can say which ran dry. Filed under
        "data", 100 uploads would block the inbox, analytics and health checks
        for the rest of the day with 10,000 units still unspent.
        """
        now = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)

        exc = YouTubeProvider()._error_for_response(self._error(403, self._QUOTA_BODY, url=url), now=now)

        assert isinstance(exc, QuotaExceededError)
        assert exc.quota_scope == "upload"
        # The buckets roll over together at Pacific midnight.
        assert exc.resets_at == next_google_quota_reset(now)

    @pytest.mark.parametrize(
        "url",
        [
            # ``videos.list`` — the same resource name, not the upload host.
            f"{API_BASE}/videos?part=statistics&id=a,b",
            # On the upload host, but charged 50 units to the regular pool.
            f"{UPLOAD_BASE}/thumbnails/set?videoId=abc&uploadType=media",
            f"{API_BASE}/commentThreads?part=snippet",
        ],
    )
    def test_everything_else_stays_on_the_regular_data_pool(self, url):
        exc = YouTubeProvider()._error_for_response(self._error(403, self._QUOTA_BODY, url=url))

        assert exc.quota_scope == "data"

    def test_rate_limit_exceeded_gets_a_short_cooldown_not_a_day(self):
        """A per-second throttle must not cost the rest of the day's syncing."""
        body = {"error": {"code": 403, "errors": [{"reason": "rateLimitExceeded"}]}}
        # Deliberately inside the last five minutes of the Pacific day.
        now = datetime(2026, 9, 17, 6, 56, 29, tzinfo=UTC)

        exc = YouTubeProvider()._error_for_response(self._error(403, body), now=now)

        assert isinstance(exc, QuotaExceededError)
        # The literal five minutes, not ``_THROTTLE_COOLDOWN``: asserting
        # against the constant the code itself uses would hold for whatever
        # value someone later widened it to.
        assert exc.resets_at == now + timedelta(minutes=5)

    def test_a_throttle_cooldown_may_outlast_the_next_daily_reset(self):
        """The window that made the old assertion fail once a day.

        In the last five minutes of the Pacific day the next daily reset is
        *nearer* than a five-minute throttle cooldown. That is correct — a
        burst throttle and a daily budget are different clocks — so nothing
        may assert the cooldown is the earlier of the two.
        """
        body = {"error": {"code": 403, "errors": [{"reason": "rateLimitExceeded"}]}}
        now = datetime(2026, 9, 17, 6, 56, 29, tzinfo=UTC)

        exc = YouTubeProvider()._error_for_response(self._error(403, body), now=now)

        assert next_google_quota_reset(now) < exc.resets_at
        # Both are still ahead of the moment that produced them.
        assert now < next_google_quota_reset(now)
        assert now < exc.resets_at

    def test_401_invalid_credentials_raises_token_expired_carrying_status(self):
        """``status_code`` here is load-bearing, not decorative.

        ``engine._is_ambiguous_submission_failure`` reads it through a
        ``getattr`` default of None and treats a missing code as "outcome
        unknown, do not retry" — so dropping it would silently flip a 401 first
        comment from retryable to untouchable.
        """
        body = {
            "error": {
                "code": 401,
                "errors": [{"message": "Invalid Credentials", "reason": "authError"}],
                "status": "UNAUTHENTICATED",
            }
        }

        exc = YouTubeProvider()._error_for_response(self._error(401, body))

        assert isinstance(exc, TokenExpiredError)
        assert exc.status_code == 401

    def test_unauthenticated_status_without_401_still_classifies(self):
        """The Analytics API leans on ``error.status`` rather than a reason."""
        body = {"error": {"code": 403, "status": "UNAUTHENTICATED"}}

        exc = YouTubeProvider()._error_for_response(self._error(403, body, url=f"{ANALYTICS_BASE}/reports"))

        assert isinstance(exc, TokenExpiredError)

    def test_permission_403_still_raises_plain_api_error(self):
        """A scope refusal must keep reaching ``_is_insufficient_scope``."""
        from apps.analytics.tasks import _is_insufficient_scope

        body = {"error": {"code": 403, "message": "Forbidden", "errors": [{"reason": "forbidden"}]}}

        exc = YouTubeProvider()._error_for_response(self._error(403, body))

        assert isinstance(exc, APIError)
        assert not isinstance(exc, QuotaExceededError)
        assert exc.status_code == 403
        assert _is_insufficient_scope(exc)

    def test_429_still_raises_plain_rate_limit_error(self):
        """The base contract an override must preserve."""
        resp = self._error(429, {"error": {"code": 429}})
        resp.headers = {"Retry-After": "30"}

        exc = YouTubeProvider()._error_for_response(resp)

        assert type(exc) is RateLimitError
        assert exc.retry_after == 30

    def test_500_still_raises_plain_api_error(self):
        exc = YouTubeProvider()._error_for_response(self._error(500, {"error": {"code": 500}}))

        assert type(exc) is APIError
        assert exc.status_code == 500


class TestGetPostMetricsBatch:
    """``videos.list`` charges 1 quota unit for 50 ids exactly as for one.

    Asking one at a time spent 50x the quota it needed to, which is what put a
    10,000-unit daily budget within reach of a single misbehaving sync loop.
    """

    @staticmethod
    def _items(video_ids):
        return {"items": [{"id": vid, "statistics": {"viewCount": "10", "likeCount": "2"}} for vid in video_ids]}

    @patch.object(YouTubeProvider, "_request")
    def test_joins_ids_into_one_request(self, mock_request):
        mock_request.return_value = _make_response(self._items(["a", "b", "c"]))

        result = YouTubeProvider().get_post_metrics_batch("tok", ["a", "b", "c"])

        assert mock_request.call_count == 1
        assert mock_request.call_args.kwargs["params"]["id"] == "a,b,c"
        assert set(result) == {"a", "b", "c"}
        assert result["a"].video_views == 10
        assert result["a"].engagements == 2

    @patch.object(YouTubeProvider, "_request")
    def test_chunks_at_fifty(self, mock_request):
        ids = [f"v{i}" for i in range(120)]
        mock_request.side_effect = lambda *a, **kw: _make_response(self._items(kw["params"]["id"].split(",")))

        result = YouTubeProvider().get_post_metrics_batch("tok", ids)

        assert mock_request.call_count == 3  # 50 + 50 + 20
        assert len(result) == 120

    @patch.object(YouTubeProvider, "_request")
    def test_ids_the_api_omits_are_absent_not_zero(self, mock_request):
        """A deleted video must not overwrite its own history with a flat line."""
        mock_request.return_value = _make_response(self._items(["a"]))

        result = YouTubeProvider().get_post_metrics_batch("tok", ["a", "deleted"])

        assert "deleted" not in result

    @patch.object(YouTubeProvider, "_request")
    def test_empty_input_makes_no_request(self, mock_request):
        assert YouTubeProvider().get_post_metrics_batch("tok", []) == {}
        assert mock_request.call_count == 0

    @patch.object(YouTubeProvider, "_request")
    def test_singular_delegates_to_batch(self, mock_request):
        mock_request.return_value = _make_response(self._items(["a"]))

        metrics = YouTubeProvider().get_post_metrics("tok", "a")

        assert metrics.video_views == 10
        assert mock_request.call_args.kwargs["params"]["id"] == "a"

    @patch.object(YouTubeProvider, "_request")
    def test_singular_returns_empty_metrics_when_absent(self, mock_request):
        """The contract the single-post sync path has always relied on."""
        mock_request.return_value = _make_response({"items": []})

        metrics = YouTubeProvider().get_post_metrics("tok", "gone")

        assert metrics.video_views == 0
        assert metrics.likes == 0


def _thread(comment_id: str, published: datetime, *, replies: list[tuple[str, datetime]] | None = None) -> dict:
    """One ``commentThreads.list`` item, optionally carrying replies."""
    return {
        "snippet": {
            "topLevelComment": {
                "id": comment_id,
                "snippet": {
                    "publishedAt": published.isoformat().replace("+00:00", "Z"),
                    "videoId": "vid1",
                    "authorDisplayName": f"author-{comment_id}",
                    "textDisplay": f"text-{comment_id}",
                    "authorChannelId": {"value": f"chan-{comment_id}"},
                },
            }
        },
        "replies": {
            "comments": [
                {
                    "id": reply_id,
                    "snippet": {
                        "publishedAt": reply_published.isoformat().replace("+00:00", "Z"),
                        "videoId": "vid1",
                        "authorDisplayName": f"author-{reply_id}",
                        "textDisplay": f"text-{reply_id}",
                        "authorChannelId": {"value": f"chan-{reply_id}"},
                    },
                }
                for reply_id, reply_published in (replies or [])
            ]
        },
    }


def _page(threads: list[dict], *, next_token: str | None = None) -> dict:
    body: dict = {"items": threads}
    if next_token:
        body["nextPageToken"] = next_token
    return body


_CHANNEL_PAGE = {"items": [{"id": "UC_test"}]}


class TestGetMessages:
    """Pagination bounds on the comment poll.

    ``commentThreads.list`` costs a quota unit per page against a budget the
    whole deployment shares, so how far this pages is a quota decision, not a
    performance one. Each test below pins one of the three things that end the
    walk: the early exit, the page cap, and ``deep=True`` lifting both.
    """

    NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC)

    def _pages(self, *bodies: dict) -> list:
        """Channel lookup first, then one response per comment page."""
        return [_make_response(_CHANNEL_PAGE)] + [_make_response(b) for b in bodies]

    @patch.object(YouTubeProvider, "_request")
    def test_stops_once_a_page_reaches_past_the_lookback(self, mock_request):
        since = self.NOW - timedelta(minutes=30)
        # Page 2 ends well behind ``since - _COMMENT_LOOKBACK``, so page 3 —
        # which the token offers — must never be fetched.
        mock_request.side_effect = self._pages(
            _page([_thread("new", self.NOW - timedelta(minutes=5))], next_token="p2"),
            _page([_thread("old", self.NOW - timedelta(days=3))], next_token="p3"),
        )

        messages = YouTubeProvider().get_messages("tok", since=since)

        # 1 channel lookup + 2 comment pages, and no third page.
        assert mock_request.call_count == 3
        assert [m.platform_message_id for m in messages] == ["new"]

    @patch.object(YouTubeProvider, "_request")
    def test_keeps_paging_inside_the_lookback(self, mock_request):
        """A page older than ``since`` but inside the lookback is not the end."""
        since = self.NOW - timedelta(minutes=30)
        mock_request.side_effect = self._pages(
            _page([_thread("a", self.NOW - timedelta(minutes=5))], next_token="p2"),
            # Older than `since`, newer than `since - 2h`: still worth paging past,
            # because a thread this old can carry a brand-new reply.
            _page([_thread("b", self.NOW - timedelta(minutes=90))], next_token="p3"),
            _page([_thread("c", self.NOW - timedelta(days=3))]),
        )

        YouTubeProvider().get_messages("tok", since=since)

        assert mock_request.call_count == 4

    @patch.object(YouTubeProvider, "_request")
    def test_page_cap_bounds_a_channel_with_no_old_page(self, mock_request):
        """Every page is recent, so only the cap can end the walk."""
        recent = _page([_thread("x", self.NOW - timedelta(minutes=1))], next_token="more")
        mock_request.side_effect = self._pages(*[recent] * (_MAX_COMMENT_PAGES + 3))

        YouTubeProvider().get_messages("tok", since=self.NOW - timedelta(minutes=30))

        assert mock_request.call_count == _MAX_COMMENT_PAGES + 1

    @patch.object(YouTubeProvider, "_request")
    def test_page_cap_returns_a_cursor_that_resumes_the_walk(self, mock_request):
        recent = _page([_thread("x", self.NOW)], next_token="older-page")
        mock_request.side_effect = self._pages(*[recent] * _MAX_COMMENT_PAGES)

        batch = YouTubeProvider().get_messages("tok")

        assert batch.next_page_token == "older-page"

        mock_request.reset_mock()
        mock_request.side_effect = self._pages(_page([_thread("older", self.NOW - timedelta(days=30))]))
        resumed = YouTubeProvider().get_messages("tok", page_token=batch.next_page_token)
        assert [msg.platform_message_id for msg in resumed] == ["older"]
        assert resumed.next_page_token is None
        assert mock_request.call_args_list[1].kwargs["params"]["pageToken"] == "older-page"

    @patch.object(YouTubeProvider, "_request")
    def test_deep_lifts_both_bounds(self, mock_request):
        """The weekly sweep walks to the end of the history."""
        page_count = _MAX_COMMENT_PAGES + 3
        pages = [
            _page([_thread(f"t{i}", self.NOW - timedelta(days=i + 1))], next_token=f"p{i}") for i in range(page_count)
        ]
        pages.append(_page([_thread("last", self.NOW - timedelta(days=400))]))
        mock_request.side_effect = self._pages(*pages)

        YouTubeProvider().get_messages("tok", since=self.NOW - timedelta(minutes=30), deep=True)

        assert mock_request.call_count == page_count + 2

    @patch.object(YouTubeProvider, "_request")
    def test_a_new_reply_on_an_old_thread_is_returned(self, mock_request):
        """The thread predates ``since``; its reply does not.

        Filtering the thread out wholesale — which this used to do — dropped the
        reply with it, so a comment answered on an old video never reached the
        inbox at all.
        """
        since = self.NOW - timedelta(minutes=30)
        mock_request.side_effect = self._pages(
            _page(
                [
                    _thread(
                        "old-thread",
                        self.NOW - timedelta(days=1),
                        replies=[("fresh-reply", self.NOW - timedelta(minutes=2))],
                    )
                ]
            )
        )

        messages = YouTubeProvider().get_messages("tok", since=since)

        ids = [m.platform_message_id for m in messages]
        assert ids == ["fresh-reply"]
        assert messages[0].extra["parent_id"] == "old-thread"

    @patch.object(YouTubeProvider, "_request")
    def test_first_sync_has_no_cutoff_but_still_caps(self, mock_request):
        """No ``since`` means no early exit — the cap is the only bound."""
        old = _page([_thread("ancient", self.NOW - timedelta(days=900))], next_token="more")
        mock_request.side_effect = self._pages(*[old] * (_MAX_COMMENT_PAGES + 2))

        messages = YouTubeProvider().get_messages("tok")

        assert mock_request.call_count == _MAX_COMMENT_PAGES + 1
        assert len(messages) == _MAX_COMMENT_PAGES

    @patch.object(YouTubeProvider, "_request")
    def test_channel_without_items_makes_no_comment_call(self, mock_request):
        mock_request.return_value = _make_response({"items": []})

        assert YouTubeProvider().get_messages("tok") == []
        assert mock_request.call_count == 1


class TestDeepSweepBounds:
    """``deep=True`` raises the ceiling; it must not remove it.

    An unbounded walk of a 50,000-thread channel spends 500 units in one
    synchronous call inside a 5-minute cycle — the exact failure the routine
    poll's bounds exist to prevent.
    """

    NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC)

    @patch.object(YouTubeProvider, "_request")
    def test_deep_still_stops_at_its_own_cap(self, mock_request):
        endless = _page([_thread("x", self.NOW - timedelta(days=1))], next_token="more")
        mock_request.side_effect = [_make_response(_CHANNEL_PAGE)] + [
            _make_response(endless) for _ in range(_MAX_DEEP_COMMENT_PAGES + 5)
        ]

        YouTubeProvider().get_messages("tok", since=self.NOW - timedelta(days=30), deep=True)

        assert mock_request.call_count == _MAX_DEEP_COMMENT_PAGES + 1

    @patch.object(YouTubeProvider, "_request")
    def test_deep_reaches_further_than_a_routine_poll(self, mock_request):
        """The cap is raised, so the sweep is worth running at all."""
        endless = _page([_thread("x", self.NOW - timedelta(days=1))], next_token="more")
        mock_request.side_effect = [_make_response(_CHANNEL_PAGE)] + [
            _make_response(endless) for _ in range(_MAX_DEEP_COMMENT_PAGES + 5)
        ]

        YouTubeProvider().get_messages("tok", since=self.NOW - timedelta(days=30), deep=True)

        assert mock_request.call_count > _MAX_COMMENT_PAGES + 1

    @patch.object(YouTubeProvider, "_request")
    def test_deep_sweep_fetches_replies_omitted_from_thread_payload(self, mock_request):
        old = _thread("old", self.NOW - timedelta(days=40), replies=[("embedded", self.NOW - timedelta(days=20))])
        old["snippet"]["totalReplyCount"] = 3
        missing = {
            "id": "missing",
            "snippet": {
                "publishedAt": self.NOW.isoformat().replace("+00:00", "Z"),
                "authorDisplayName": "author",
                "textDisplay": "new reply",
            },
        }
        mock_request.side_effect = [
            _make_response(_CHANNEL_PAGE),
            _make_response(_page([old])),
            _make_response({"items": [], "nextPageToken": "reply-page-2"}),
            _make_response({"items": [missing]}),
        ]

        provider = YouTubeProvider()
        batch = provider.get_messages("tok", since=self.NOW - timedelta(days=7), deep=True)

        assert [msg.platform_message_id for msg in batch] == ["missing"]
        assert mock_request.call_args_list[2].kwargs["params"]["parentId"] == "old"
        assert mock_request.call_args_list[3].kwargs["params"]["pageToken"] == "reply-page-2"
        assert provider.last_call_quota_units == 4


class TestQuotaUnitAccounting:
    """The tally has to survive a call that failed, and a second call after it."""

    NOW = datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC)

    @patch.object(YouTubeProvider, "_request")
    def test_units_accumulate_across_calls_until_reset(self, mock_request):
        """The YouTube inbox retries once after an auth failure; both attempts cost."""
        page = _page([_thread("a", self.NOW)])
        mock_request.side_effect = [
            _make_response(_CHANNEL_PAGE),
            _make_response(page),
            _make_response(_CHANNEL_PAGE),
            _make_response(page),
        ]
        provider = YouTubeProvider()

        provider.get_messages("tok")
        assert provider.last_call_quota_units == 2

        provider.get_messages("tok")
        assert provider.last_call_quota_units == 4

        provider.reset_quota_counter()
        assert provider.last_call_quota_units == 0

    @patch.object(YouTubeProvider, "_request")
    def test_a_failed_channel_lookup_still_counts(self, mock_request):
        """Counted before the request, so a raise cannot erase the attempt."""
        mock_request.side_effect = APIError("boom", status_code=500)
        provider = YouTubeProvider()

        with pytest.raises(APIError):
            provider.get_messages("tok")

        assert provider.last_call_quota_units == 1
