"""Tests for YouTubeProvider.get_post_analytics and get_account_metrics."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from providers.exceptions import APIError
from providers.youtube import _ANALYTICS_VIDEO_FILTER_CHUNK, YouTubeProvider


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


def _channels_response(subscriber_count: int) -> MagicMock:
    return _make_response(
        {"items": [{"statistics": {"subscriberCount": str(subscriber_count), "viewCount": "0", "videoCount": "0"}}]}
    )


def _reports_response(rows: list) -> MagicMock:
    return _make_response(
        {
            "columnHeaders": [
                {"name": "estimatedMinutesWatched"},
                {"name": "averageViewPercentage"},
                {"name": "subscribersGained"},
                {"name": "shares"},
            ],
            "rows": rows,
        }
    )


class TestGetAccountMetrics:
    """A channel's subscriber total comes from ``channels.list``, not the lagged
    Analytics ``/reports`` endpoint — see Fix 1's context: Analytics can return
    zero rows for today (1-2 day lag) while the channel's real total is known
    right away, and an Analytics failure must not lose it either.
    """

    @patch.object(YouTubeProvider, "_request")
    def test_followers_set_from_channel_statistics(self, mock_request):
        def fake_request(method, url, **kwargs):
            if url.endswith("/channels"):
                return _channels_response(4321)
            return _reports_response([[1500.0, 47.5, 3.0, 12.0]])

        mock_request.side_effect = fake_request

        provider = YouTubeProvider()
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 4321
        # The Analytics extra is untouched by the followers fetch.
        assert metrics.extra == {"watch_time": 1500.0, "avg_view_pct": 47.5, "subscribers": 3.0, "shares": 12.0}

    @patch.object(YouTubeProvider, "_request")
    def test_empty_analytics_day_still_returns_followers(self, mock_request):
        # A channel with zero activity today: /reports comes back with no rows
        # (Analytics lags 1-2 days), but the subscriber total is still real.
        def fake_request(method, url, **kwargs):
            if url.endswith("/channels"):
                return _channels_response(4321)
            return _reports_response([])

        mock_request.side_effect = fake_request

        provider = YouTubeProvider()
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 4321
        assert metrics.extra == {}

    @patch.object(YouTubeProvider, "_request")
    def test_analytics_failure_still_returns_followers(self, mock_request):
        def fake_request(method, url, **kwargs):
            if url.endswith("/channels"):
                return _channels_response(4321)
            raise APIError("YouTube API error 500: internal error", status_code=500, platform="YouTube")

        mock_request.side_effect = fake_request

        provider = YouTubeProvider()
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 4321
        # The failed /reports call is recorded rather than silently dropped.
        assert "reports" in metrics.extra.get("insight_errors", {})

    @patch.object(YouTubeProvider, "_request")
    def test_channel_statistics_failure_does_not_lose_analytics(self, mock_request):
        # The inverse: channels.list failing must not also blank the Analytics
        # data — followers just comes back unknown (None), not a fabricated 0.
        def fake_request(method, url, **kwargs):
            if url.endswith("/channels"):
                raise APIError("YouTube API error 403: forbidden", status_code=403, platform="YouTube")
            return _reports_response([[1500.0, 47.5, 3.0, 12.0]])

        mock_request.side_effect = fake_request

        provider = YouTubeProvider()
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers is None
        assert metrics.extra == {"watch_time": 1500.0, "avg_view_pct": 47.5, "subscribers": 3.0, "shares": 12.0}

    @patch.object(YouTubeProvider, "_request")
    def test_analytics_scope_error_still_raises(self, mock_request):
        # Unlike a generic failure, an auth/scope error from /reports must
        # still propagate: it's the only thing that surfaces to the sync
        # layer's _is_insufficient_scope check and sets
        # analytics_needs_reconnect. Swallowing it here would silently break
        # that reconnect path for every YouTube account.
        def fake_request(method, url, **kwargs):
            if url.endswith("/channels"):
                return _channels_response(4321)
            raise APIError(
                "YouTube API error 403: Request had insufficient authentication scopes.",
                status_code=403,
                platform="YouTube",
            )

        mock_request.side_effect = fake_request

        provider = YouTubeProvider()
        try:
            provider.get_account_metrics("token", _date_range())
        except APIError as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("expected APIError to propagate")

    @patch.object(YouTubeProvider, "_request")
    def test_channels_list_request_shape(self, mock_request):
        def fake_request(method, url, **kwargs):
            if url.endswith("/channels"):
                return _channels_response(1)
            return _reports_response([])

        mock_request.side_effect = fake_request

        provider = YouTubeProvider()
        provider.get_account_metrics("token-xyz", _date_range())

        channels_calls = [c for c in mock_request.call_args_list if c.args[1].endswith("/channels")]
        assert len(channels_calls) == 1
        args, kwargs = channels_calls[0]
        assert args[0] == "GET"
        assert kwargs["access_token"] == "token-xyz"
        assert kwargs["params"] == {"part": "statistics", "mine": "true"}
