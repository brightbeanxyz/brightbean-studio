"""Tests for YouTubeProvider.get_post_analytics."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

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
