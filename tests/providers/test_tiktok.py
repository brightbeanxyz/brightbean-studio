"""Tests for TikTokProvider analytics methods (video.list + user.info.stats)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from providers.tiktok import TikTokProvider


def _make_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


def _date_range() -> tuple[datetime, datetime]:
    return (
        datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
        datetime(2026, 6, 4, 23, 59, 59, tzinfo=UTC),
    )


class TestGetPostMetrics:
    @patch.object(TikTokProvider, "_request")
    def test_request_shape_with_video_id(self, mock_request):
        # A bare numeric ID is treated as a TikTok video_id — no publish-status
        # round trip, single POST to /v2/video/query/.
        mock_request.return_value = _make_response({"data": {"videos": []}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        provider.get_post_metrics("token-xyz", "7234567890")

        assert mock_request.call_count == 1
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"
        assert args[1] == "https://open.tiktokapis.com/v2/video/query/"
        assert kwargs["access_token"] == "token-xyz"
        assert kwargs["params"] == {"fields": "id,view_count,like_count,comment_count,share_count"}
        assert kwargs["json"] == {"filters": {"video_ids": ["7234567890"]}}

    @patch.object(TikTokProvider, "_request")
    def test_parses_counts_into_post_metrics(self, mock_request):
        mock_request.return_value = _make_response(
            {
                "data": {
                    "videos": [
                        {
                            "id": "7234567890",
                            "view_count": 1500,
                            "like_count": 80,
                            "comment_count": 12,
                            "share_count": 5,
                        }
                    ]
                }
            }
        )

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "7234567890")

        # video_views is the field the catalog mapper turns into "views".
        assert metrics.video_views == 1500
        assert metrics.likes == 80
        assert metrics.comments == 12
        assert metrics.shares == 5
        # ``engagements`` is intentionally NOT populated — the catalog's
        # ``engagement`` rate is derived from raw parts by
        # ``apps.analytics.derive.engagement_rate``; populating the
        # dataclass field would be dead computation (no snapshot mapping).
        assert metrics.engagements == 0

    @patch.object(TikTokProvider, "_request")
    def test_missing_video_returns_empty_metrics(self, mock_request):
        # TikTok returns an empty videos list if the ID is gone (deleted,
        # privacy-changed, or not yet visible to the API). The sync layer
        # treats empty PostMetrics as "no data" rather than "all zeros".
        mock_request.return_value = _make_response({"data": {"videos": []}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "doesnt-exist")

        assert metrics.video_views == 0
        assert metrics.likes == 0
        assert metrics.comments == 0
        assert metrics.shares == 0

    @patch.object(TikTokProvider, "_request")
    def test_missing_fields_default_to_zero(self, mock_request):
        # TikTok occasionally omits counters for sparse videos (e.g. brand-new
        # uploads where share_count hasn't been computed yet). Treat absent
        # keys as zero so the parser doesn't raise.
        mock_request.return_value = _make_response({"data": {"videos": [{"id": "7234567890", "view_count": 100}]}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "7234567890")

        assert metrics.video_views == 100
        assert metrics.likes == 0
        assert metrics.comments == 0
        assert metrics.shares == 0

    @patch.object(TikTokProvider, "_request")
    def test_publish_id_resolves_to_video_id_before_query(self, mock_request):
        # ``platform_post_id`` stored by ``publish_post`` is a publish_id
        # (``v_pub_…``), not a video_id. The provider must resolve via
        # /v2/post/publish/status/fetch/ before the analytics call —
        # ``/v2/video/query/`` only accepts video_ids.
        responses = [
            _make_response(
                {
                    "data": {
                        "status": "PUBLISH_COMPLETE",
                        "publicaly_available_post_id": ["7234567890"],
                    }
                }
            ),
            _make_response(
                {
                    "data": {
                        "videos": [
                            {
                                "id": "7234567890",
                                "view_count": 100,
                                "like_count": 10,
                                "comment_count": 2,
                                "share_count": 1,
                            }
                        ]
                    }
                }
            ),
        ]
        mock_request.side_effect = responses

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "v_pub_url~xxxx")

        # Two calls: status fetch then video query.
        assert mock_request.call_count == 2
        assert mock_request.call_args_list[0].args[0] == "POST"
        assert mock_request.call_args_list[0].args[1] == ("https://open.tiktokapis.com/v2/post/publish/status/fetch/")
        assert mock_request.call_args_list[0].kwargs["json"] == {"publish_id": "v_pub_url~xxxx"}
        # Resolved video_id is the one passed to the analytics call.
        assert mock_request.call_args_list[1].kwargs["json"] == {"filters": {"video_ids": ["7234567890"]}}
        assert metrics.video_views == 100

    @patch.object(TikTokProvider, "_request")
    def test_publish_id_in_progress_returns_empty(self, mock_request):
        # While the publish is still processing, there's no video_id yet.
        # Return empty metrics so the sync layer treats it as "no data" and
        # tries again on the next cycle — no /v2/video/query/ call.
        mock_request.return_value = _make_response({"data": {"status": "PROCESSING_UPLOAD"}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "v_pub_url~pending")

        # Only the status fetch — never reaches the analytics endpoint.
        assert mock_request.call_count == 1
        assert mock_request.call_args.args[1] == ("https://open.tiktokapis.com/v2/post/publish/status/fetch/")
        assert metrics.video_views == 0

    @patch.object(TikTokProvider, "_request")
    def test_inbox_publish_handle_resolves_via_status_fetch(self, mock_request):
        # When direct-post audit downgrades a publish to the inbox flow,
        # TikTok returns a ``v_inbox_url~`` / ``v_inbox_file~`` handle
        # instead of ``v_pub_…``. The resolver uses a positive numeric
        # check (video IDs are 19-digit numerics) so any non-numeric
        # publish handle goes through status resolution.
        mock_request.side_effect = [
            _make_response(
                {
                    "data": {
                        "status": "PUBLISH_COMPLETE",
                        "publicaly_available_post_id": ["7234567890"],
                    }
                }
            ),
            _make_response({"data": {"videos": [{"id": "7234567890", "view_count": 5}]}}),
        ]

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "v_inbox_url~v2.xxxx")

        assert mock_request.call_count == 2
        # Status fetch first, with the raw inbox handle.
        assert mock_request.call_args_list[0].kwargs["json"] == {"publish_id": "v_inbox_url~v2.xxxx"}
        # Then video query with the resolved numeric video_id.
        assert mock_request.call_args_list[1].kwargs["json"] == {"filters": {"video_ids": ["7234567890"]}}
        assert metrics.video_views == 5

    @patch.object(TikTokProvider, "_request")
    def test_none_post_id_returns_empty_without_request(self, mock_request):
        # Defensive: a stored NULL/empty platform_post_id (legacy data or
        # publish that crashed pre-store) would AttributeError on
        # ``post_id.startswith(…)``; the resolver bails early instead.
        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "")

        assert metrics.video_views == 0
        mock_request.assert_not_called()

    @patch.object(TikTokProvider, "_request")
    def test_string_publicaly_available_post_id_defended(self, mock_request):
        # Defensive: some TikTok response variants have returned the
        # publicaly_available_post_id as a bare string rather than a list.
        # The resolver coerces it without indexing into a single character.
        mock_request.side_effect = [
            _make_response(
                {
                    "data": {
                        "status": "PUBLISH_COMPLETE",
                        "publicaly_available_post_id": "7234567890",
                    }
                }
            ),
            _make_response({"data": {"videos": [{"id": "7234567890", "view_count": 1}]}}),
        ]

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "v_pub_url~xxx")

        assert metrics.video_views == 1
        assert mock_request.call_args_list[1].kwargs["json"] == {"filters": {"video_ids": ["7234567890"]}}

    @patch.object(TikTokProvider, "_request")
    def test_null_counts_coerce_to_zero(self, mock_request):
        # Defensive: a null in JSON shouldn't blow up int() conversion.
        mock_request.return_value = _make_response(
            {
                "data": {
                    "videos": [
                        {
                            "id": "7234567890",
                            "view_count": None,
                            "like_count": None,
                            "comment_count": None,
                            "share_count": None,
                        }
                    ]
                }
            }
        )

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_post_metrics("token", "7234567890")

        assert metrics.video_views == 0
        assert metrics.likes == 0


class TestGetAccountMetrics:
    @patch.object(TikTokProvider, "_request")
    def test_request_shape(self, mock_request):
        mock_request.return_value = _make_response({"data": {"user": {}}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        provider.get_account_metrics("token-xyz", _date_range())

        assert mock_request.call_count == 1
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == "https://open.tiktokapis.com/v2/user/info/"
        assert kwargs["access_token"] == "token-xyz"
        # date_range is intentionally NOT sent — /v2/user/info/ returns
        # lifetime totals with no range filter. Only follower_count is
        # requested; the other user.info.stats fields (likes_count etc.)
        # are lifetime cumulatives that would inflate engagement_rate if
        # snapshotted as daily values.
        assert kwargs["params"] == {"fields": "follower_count"}

    @patch.object(TikTokProvider, "_request")
    def test_parses_followers(self, mock_request):
        mock_request.return_value = _make_response({"data": {"user": {"follower_count": 4200}}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 4200
        # No extras — TikTok's other lifetime counters would corrupt
        # engagement_rate if treated as per-day values, so they're not
        # surfaced until a daily-delta endpoint exists.
        assert metrics.extra == {}

    @patch.object(TikTokProvider, "_request")
    def test_zero_followers_still_returns_metrics(self, mock_request):
        # Brand-new accounts can legitimately have 0 followers; the
        # AccountMetrics object MUST still carry that value (not None) so
        # `_account_metrics_to_dict` writes a baseline snapshot.
        mock_request.return_value = _make_response({"data": {"user": {"follower_count": 0}}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 0

    @patch.object(TikTokProvider, "_request")
    def test_missing_user_block_returns_empty(self, mock_request):
        # Defensive: malformed response shouldn't raise — empty AccountMetrics
        # lets the sync layer treat it as "no data".
        mock_request.return_value = _make_response({})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 0
        assert metrics.extra == {}

    @patch.object(TikTokProvider, "_request")
    def test_non_numeric_follower_count_does_not_raise(self, mock_request):
        # Defensive: if TikTok ever returns a non-coercible value (legacy
        # locales have been seen to return abbreviated strings like "4.2K"),
        # the provider must not abort the whole sync — fall back to 0.
        mock_request.return_value = _make_response({"data": {"user": {"follower_count": "unavailable"}}})

        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        metrics = provider.get_account_metrics("token", _date_range())

        assert metrics.followers == 0

    @patch.object(TikTokProvider, "_request")
    def test_does_not_supports_date_range(self, _mock_request):
        # The sync layer reads this flag to skip the 3-day backfill loop
        # for providers whose stats endpoint ignores date_range — otherwise
        # TikTok's lifetime totals would be replayed into past dates as
        # if they were historical observations.
        provider = TikTokProvider({"client_key": "k", "client_secret": "s"})
        assert provider.account_metrics_supports_date_range is False


class TestAccountMetricsPersistence:
    """Integration check: TikTok ``AccountMetrics`` actually persist to snapshots.

    Without these checks, the provider can silently return well-formed
    ``AccountMetrics`` that the catalog mapper drops on the floor — exactly
    the Codex finding for issue 2.
    """

    def test_tiktok_followers_persists(self):
        from apps.analytics.tasks import _account_metrics_to_dict
        from providers.types import AccountMetrics

        metrics = AccountMetrics(followers=4200)

        out = _account_metrics_to_dict(metrics, "tiktok")

        # Total follower count snapshots under the ``followers`` key the
        # catalog mapper persists for platforms that list it.
        assert out["followers"] == 4200.0

    def test_tiktok_zero_followers_persists(self):
        # Brand-new TikTok account: 0 followers must still be persisted
        # so the chart series has a baseline (not a gap that jumps to
        # the first non-zero value).
        from apps.analytics.tasks import _account_metrics_to_dict
        from providers.types import AccountMetrics

        metrics = AccountMetrics(followers=0)

        out = _account_metrics_to_dict(metrics, "tiktok")

        assert out["followers"] == 0.0

    def test_followers_not_persisted_for_platforms_without_catalog_entry(self):
        # Instagram/Facebook providers populate ``AccountMetrics.followers``
        # with daily-delta values (Insights API ``follower_count`` /
        # ``page_fans``), not lifetime totals. Persisting them under the
        # ``followers`` key (which the catalog labels as a total) would
        # mislabel the data. The catalog-membership gate prevents that
        # leak today; this test pins the contract.
        from apps.analytics.tasks import _account_metrics_to_dict
        from providers.types import AccountMetrics

        metrics = AccountMetrics(followers=42)

        for platform in ("instagram", "facebook", "linkedin_company"):
            out = _account_metrics_to_dict(metrics, platform)
            assert "followers" not in out, f"unexpected followers leak for {platform}"

    def test_tiktok_follower_growth_metric_resolves(self):
        # Regression guard for the catalog-swap bug: when TikTok's catalog
        # was changed from ``follows`` to ``followers``, the existing
        # follower_growth_metric iteration over (``subscribers``, ``follows``)
        # returned None for TikTok, hiding the new follower data from the
        # analytics header.
        from apps.analytics.metrics import PLATFORM_METRICS

        platform_metrics = PLATFORM_METRICS["tiktok"]
        assert any(m in platform_metrics for m in ("subscribers", "follows", "followers")), (
            "TikTok must list one of the account-level growth metrics for "
            "follower_growth_metric to surface follower data in the UI header"
        )
