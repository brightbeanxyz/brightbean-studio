from unittest.mock import MagicMock

import pytest

from providers.exceptions import APIError
from providers.meta_insights import fetch_insights_safe, parse_insights_response


def _resp(data):
    return MagicMock(json=MagicMock(return_value=data))


def test_fetch_insights_safe_skips_invalid_metric_errors():
    request = MagicMock(
        side_effect=[
            APIError(
                "Meta API error 400: invalid metric",
                platform="Facebook",
                status_code=400,
                raw_response={"error": {"code": 100, "message": "Tried accessing nonexisting field insights"}},
            ),
            _resp({"data": [{"name": "page_media_view", "values": [{"value": 10}]}]}),
        ]
    )

    values, errors = fetch_insights_safe(
        request,
        platform="Facebook",
        endpoint="https://graph.facebook.com/v25.0/page-1/insights",
        access_token="page-token",
        metrics=["bad_metric", "page_media_view"],
    )

    assert values == {"page_media_view": 10}
    assert set(errors) == {"bad_metric"}


def test_fetch_insights_safe_reraises_permission_errors():
    permission_error = APIError(
        "Meta API error 400: missing permission",
        platform="Facebook",
        status_code=400,
        raw_response={
            "error": {
                "code": 200,
                "type": "OAuthException",
                "message": "Permissions error: read_insights is required.",
            }
        },
    )
    request = MagicMock(side_effect=permission_error)

    with pytest.raises(APIError) as excinfo:
        fetch_insights_safe(
            request,
            platform="Facebook",
            endpoint="https://graph.facebook.com/v25.0/page-1/insights",
            access_token="page-token",
            metrics=["page_media_view"],
        )

    assert excinfo.value is permission_error


def test_parse_insights_response_prefers_lifetime_when_metric_name_repeats():
    values = parse_insights_response(
        {
            "data": [
                {
                    "name": "post_media_view",
                    "period": "lifetime",
                    "values": [{"value": 32741}],
                },
                {
                    "name": "post_total_media_view_unique",
                    "period": "lifetime",
                    "values": [{"value": 21105}],
                },
                {
                    "name": "post_total_media_view_unique",
                    "period": "day",
                    "values": [
                        {"value": 0, "end_time": "2026-06-21T07:00:00+0000"},
                        {"value": 0, "end_time": "2026-06-22T07:00:00+0000"},
                    ],
                },
            ]
        }
    )

    assert values == {
        "post_media_view": 32741,
        "post_total_media_view_unique": 21105,
    }
