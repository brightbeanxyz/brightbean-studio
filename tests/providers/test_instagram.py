from datetime import UTC, datetime
from unittest.mock import MagicMock, call

import pytest

from providers.exceptions import APIError, PublishError
from providers.instagram import InstagramProvider
from providers.instagram_login import InstagramLoginProvider
from providers.meta_comments import INSTAGRAM_COMMENT_FIELD_SETS
from providers.types import PostType, PublishContent


def _resp(data):
    return MagicMock(json=MagicMock(return_value=data))


def test_get_user_pages_returns_linked_instagram_business_accounts():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Facebook Page",
                            "access_token": "page-token",
                            "category": "Creator",
                            "picture": {"data": {"url": "https://example.com/page.jpg"}},
                            "instagram_business_account": {
                                "id": "17841400000000000",
                                "username": "brightbean",
                                "name": "Brightbean",
                                "profile_picture_url": "https://example.com/ig.jpg",
                                "followers_count": 42,
                            },
                        },
                        {
                            "id": "page-2",
                            "name": "No Instagram Here",
                            "access_token": "unused-token",
                        },
                    ]
                }
            )
        )
    )

    accounts = provider.get_user_pages("user-token")

    assert accounts == [
        {
            "id": "17841400000000000",
            "name": "Brightbean",
            "handle": "brightbean",
            "access_token": "page-token",
            "category": "Creator",
            "picture": "https://example.com/ig.jpg",
            "followers_count": 42,
            "page_id": "page-1",
            "page_name": "Facebook Page",
        }
    ]
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v25.0/me/accounts",
        access_token="user-token",
        params={
            "fields": (
                "id,name,access_token,category,picture,"
                "instagram_business_account{id,username,name,profile_picture_url,followers_count,media_count}"
            ),
        },
    )


def test_get_user_pages_omits_blank_page_access_token():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})

    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Facebook Page",
                            "access_token": "",
                            "instagram_business_account": {
                                "id": "17841400000000000",
                                "username": "brightbean",
                                "name": "Brightbean",
                            },
                        },
                    ]
                }
            )
        )
    )

    accounts = provider.get_user_pages("user-token")

    assert len(accounts) == 1
    assert "access_token" not in accounts[0]


def test_account_metrics_use_current_instagram_insights_metrics():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"name": "reach", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "views", "period": "day", "total_value": {"value": 67}}]}),
            _resp({"data": [{"name": "accounts_engaged", "values": [{"value": 8}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 9}]}]}),
            _resp({"followers_count": 34}),
        ]
    )

    metrics = provider.get_account_metrics(
        "page-token",
        (
            datetime(2026, 6, 18, tzinfo=UTC),
            datetime(2026, 6, 19, tzinfo=UTC),
        ),
    )

    assert metrics.impressions == 0
    assert metrics.reach == 12
    assert metrics.followers == 34
    assert metrics.extra["views"] == 67
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "reach",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "views",
                    "period": "day",
                    "metric_type": "total_value",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "accounts_engaged",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1/insights",
                access_token="page-token",
                params={
                    "metric": "total_interactions",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.facebook.com/v25.0/ig-1",
                access_token="page-token",
                params={"fields": "id,username,name,profile_picture_url,followers_count,media_count"},
            ),
        ]
    )


def test_instagram_media_metrics_use_current_metrics_and_field_fallbacks():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"id": "ig-media-1", "like_count": 12, "comments_count": 3}),
            _resp({"data": [{"name": "reach", "values": [{"value": 250}]}]}),
            _resp({"data": [{"name": "views", "values": [{"value": 400}]}]}),
            _resp({"data": [{"name": "likes", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "comments", "values": [{"value": 3}]}]}),
            _resp({"data": [{"name": "saved", "values": [{"value": 5}]}]}),
            _resp({"data": [{"name": "shares", "values": [{"value": 2}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 22}]}]}),
        ]
    )

    metrics = provider.get_post_metrics("page-token", "ig-media-1")

    assert metrics.video_views == 400
    assert metrics.reach == 250
    assert metrics.likes == 12
    assert metrics.comments == 3
    assert metrics.saves == 5
    assert metrics.shares == 2
    assert metrics.extra["total_interactions"] == 22


def test_instagram_login_account_metrics_use_current_insights_metrics():
    provider = InstagramLoginProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"name": "reach", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "views", "period": "day", "total_value": {"value": 67}}]}),
            _resp({"data": [{"name": "accounts_engaged", "values": [{"value": 8}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 9}]}]}),
            _resp({"followers_count": 34}),
        ]
    )

    metrics = provider.get_account_metrics(
        "ig-token",
        (
            datetime(2026, 6, 18, tzinfo=UTC),
            datetime(2026, 6, 19, tzinfo=UTC),
        ),
    )

    assert metrics.impressions == 0
    assert metrics.reach == 12
    assert metrics.followers == 34
    assert metrics.extra["views"] == 67
    provider._request.assert_has_calls(
        [
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "reach",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "views",
                    "period": "day",
                    "metric_type": "total_value",
                    "since": 1781740800,
                    "until": 1781827200,
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "accounts_engaged",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me/insights",
                access_token="ig-token",
                params={
                    "metric": "total_interactions",
                    "period": "day",
                    "since": 1781740800,
                    "until": 1781827200,
                    "metric_type": "total_value",
                },
            ),
            call(
                "GET",
                "https://graph.instagram.com/v25.0/me",
                access_token="ig-token",
                params={"fields": "user_id,username,name,profile_picture_url,followers_count,media_count"},
            ),
        ]
    )


def test_account_metrics_followers_none_when_profile_fetch_fails():
    """A transient profile-fetch failure must yield followers=None (not 0) so the
    analytics layer can skip it instead of writing a poisoning 0 snapshot for a
    real account."""
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1"})
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [{"name": "reach", "values": [{"value": 12}]}]}),
            _resp({"data": [{"name": "views", "period": "day", "total_value": {"value": 67}}]}),
            _resp({"data": [{"name": "accounts_engaged", "values": [{"value": 8}]}]}),
            _resp({"data": [{"name": "total_interactions", "values": [{"value": 9}]}]}),
            APIError("(#190) Error validating access token", platform="Instagram"),
        ]
    )

    metrics = provider.get_account_metrics(
        "page-token",
        (datetime(2026, 6, 18, tzinfo=UTC), datetime(2026, 6, 19, tzinfo=UTC)),
    )

    assert metrics.followers is None
    assert metrics.reach == 12


# ----------------------------------------------------------------------
# First comment
# ----------------------------------------------------------------------

IG_CREDS = {"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1", "account_handle": "pinklion.xyz"}
IG_LOGIN_CREDS = {"client_id": "id", "client_secret": "secret", "ig_user_id": "ig-1", "account_handle": "pinklion.xyz"}

# (provider factory, host, media edge) — the comment surface is identical on
# both connections and differs only in where it lives.
IG_PROVIDERS = [
    pytest.param(
        lambda: InstagramProvider(IG_CREDS),
        "https://graph.facebook.com/v25.0",
        "https://graph.facebook.com/v25.0/ig-1/media",
        id="facebook-login",
    ),
    pytest.param(
        lambda: InstagramLoginProvider(IG_LOGIN_CREDS),
        "https://graph.instagram.com/v25.0",
        "https://graph.instagram.com/v25.0/me/media",
        id="instagram-login",
    ),
]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_publish_comment_sends_no_fields_param(make_provider, host, media_url):
    """Meta creates the comment and *then* rejects a ``fields`` param on this
    edge (code 20 / subcode 1772107). The 400 reads as a clean rejection, the
    retry queue re-sends it, and the account collects one comment per attempt.
    """
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"id": "comment-1"}))

    result = provider.publish_comment("token", "media-1", "First!")

    assert result.platform_comment_id == "comment-1"
    provider._request.assert_called_once_with(
        "POST",
        f"{host}/media-1/comments",
        access_token="token",
        json={"message": "First!"},
    )


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_find_own_comment_matches_the_accounts_own_comment_by_text(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp(
            {
                "data": [
                    {"id": "c-1", "text": "Someone else", "from": {"id": "ig-2"}},
                    {"id": "c-2", "text": "First!", "from": {"id": "ig-1"}},
                ]
            }
        )
    )

    assert provider.find_own_comment("token", "media-1", "First!") == "c-2"
    provider._request.assert_called_once_with(
        "GET",
        f"{host}/media-1/comments",
        access_token="token",
        params={"fields": "id,text,from", "limit": 50},
    )


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_find_own_comment_ignores_the_same_text_from_someone_else(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp({"data": [{"id": "c-1", "text": "First!", "from": {"id": "ig-999"}}]})
    )

    assert provider.find_own_comment("token", "media-1", "First!") is None


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_find_own_comment_keeps_a_comment_whose_author_is_unreadable(make_provider, host, media_url):
    """Instagram omits ``from`` on third-party comments in some permission
    combinations. Erring toward "ours" costs one skipped comment; erring the
    other way posts a duplicate on a live account, which cannot be taken back.
    """
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [{"id": "c-1", "text": "First!"}]}))

    assert provider.find_own_comment("token", "media-1", "First!") == "c-1"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_find_own_comment_matches_on_handle_when_the_author_id_is_missing(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp({"data": [{"id": "c-1", "text": "First!", "from": {"username": "PinkLion.xyz"}}]})
    )

    assert provider.find_own_comment("token", "media-1", "First!") == "c-1"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_find_own_comment_returns_none_when_nothing_matches(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp({"data": [{"id": "c-1", "text": "Other", "from": {"id": "ig-1"}}]})
    )

    assert provider.find_own_comment("token", "media-1", "First!") is None


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_find_own_comment_raises_when_the_comments_edge_cannot_be_read(make_provider, host, media_url):
    """ "Unknown" is not "not there": returning None here would tell the caller
    it is safe to post again."""
    provider = make_provider()
    provider._request = MagicMock(side_effect=APIError("boom", status_code=500, platform="Instagram"))

    with pytest.raises(APIError):
        provider.find_own_comment("token", "media-1", "First!")


# ----------------------------------------------------------------------
# Comment polling
# ----------------------------------------------------------------------


def _poll_comments(provider, since=None):
    """Run just the comment half, whichever connection this is.

    ``InstagramLoginProvider.get_messages`` also polls DMs, which would consume
    the same ``_request`` mock and shift every call index below.
    """
    if isinstance(provider, InstagramLoginProvider):
        return provider._fetch_media_comments("token", since)
    return provider.get_messages("token", since=since)


def _media(comments=None, media_id="media-1", **extra):
    item = {"id": media_id, "timestamp": "2026-08-07T09:00:00+0000", "permalink": "https://instagr.am/p/abc/"}
    item.update(extra)
    if comments is not None:
        item["comments"] = comments
    return item


def _ig_comment(comment_id="c-1", text="Nice one", author_id="ig-2", username="curious", **extra):
    comment = {"id": comment_id, "text": text, "timestamp": "2026-08-07T10:00:00+0000", "username": username}
    if author_id:
        comment["from"] = {"id": author_id, "username": username}
    comment.update(extra)
    return comment


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_does_not_pass_the_callers_since_to_the_media_edge(make_provider, host, media_url):
    """``since`` on /media filters by MEDIA timestamp, so passing the caller's
    value would hide every new comment on an older post."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [_media({"data": [_ig_comment()]})]}))

    since = datetime(2026, 8, 7, 9, 30, tzinfo=UTC)
    messages = _poll_comments(provider, since)

    assert [m.platform_message_id for m in messages] == ["c-1"]
    args, kwargs = provider._request.call_args
    assert args[1] == media_url
    assert kwargs["params"]["since"] != int(since.timestamp())
    assert "replies" in kwargs["params"]["fields"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_keeps_comments_older_than_since_within_the_lookback(make_provider, host, media_url):
    """The inbox passes the newest received_at across all message types, so a
    DM would otherwise hide every comment that arrived just before it."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [_media({"data": [_ig_comment()]})]}))

    # 6h after the comment — inside the 24h overlap.
    messages = _poll_comments(provider, datetime(2026, 8, 7, 16, 0, tzinfo=UTC))

    assert [m.platform_message_id for m in messages] == ["c-1"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_drops_comments_older_than_the_lookback(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [_media({"data": [_ig_comment()]})]}))

    messages = _poll_comments(provider, datetime(2026, 8, 9, 12, 0, tzinfo=UTC))

    assert messages == []


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_accepts_a_naive_since(make_provider, host, media_url):
    """A naive cutoff compared against an aware Graph timestamp is a TypeError."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [_media({"data": [_ig_comment()]})]}))

    messages = _poll_comments(provider, datetime(2026, 8, 7, 16, 0))  # noqa: DTZ001

    assert [m.platform_message_id for m in messages] == ["c-1"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_excludes_the_accounts_own_comments_by_id(make_provider, host, media_url):
    """Our own first comment must not come back as an inbound customer message."""
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp(
            {
                "data": [
                    _media(
                        {
                            "data": [
                                _ig_comment("c-ours", "First!", author_id="ig-1", username="pinklion.xyz"),
                                _ig_comment("c-theirs"),
                            ]
                        }
                    )
                ]
            }
        )
    )

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-theirs"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_excludes_own_comments_by_username_when_from_is_withheld(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp(
            {
                "data": [
                    _media(
                        {
                            "data": [
                                _ig_comment("c-ours", "First!", author_id=None, username="PinkLion.xyz"),
                                _ig_comment("c-theirs", author_id=None, username="curious"),
                            ]
                        }
                    )
                ]
            }
        )
    )

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-theirs"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_carries_the_media_id_the_inbox_links_on(make_provider, host, media_url):
    """PlatformPost stores the IG media id unprefixed, so both keys the inbox
    tries are that same id."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [_media({"data": [_ig_comment()]})]}))

    (message,) = _poll_comments(provider)

    assert message.extra["post_id"] == "media-1"
    assert message.extra["stored_post_id"] == "media-1"
    assert message.extra["reply_edge"] == "comment"
    assert message.extra["source"] == "poll"
    assert message.message_type == "comment"
    assert message.timestamp.tzinfo is not None


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_ingests_replies_and_records_their_parent(make_provider, host, media_url):
    """A customer answering our own first comment is exactly the message we
    must not lose, so a skipped parent does not skip its replies."""
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp(
            {
                "data": [
                    _media(
                        {
                            "data": [
                                _ig_comment(
                                    "c-ours",
                                    "First!",
                                    author_id="ig-1",
                                    username="pinklion.xyz",
                                    replies={"data": [_ig_comment("r-1", "Answering you")]},
                                )
                            ]
                        }
                    )
                ]
            }
        )
    )

    (message,) = _poll_comments(provider)

    assert message.platform_message_id == "r-1"
    assert message.extra["parent_id"] == "c-ours"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_follows_paging_up_to_the_cap(make_provider, host, media_url):
    provider = make_provider()
    page = {"data": [_ig_comment("c-1")], "paging": {"next": f"{host}/media-1/comments?after=x"}}
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [_media(page)]}),
            _resp({"data": [_ig_comment("c-2")], "paging": {"next": f"{host}/media-1/comments?after=y"}}),
            _resp({"data": [_ig_comment("c-3")], "paging": {"next": f"{host}/media-1/comments?after=z"}}),
            _resp({"data": [_ig_comment("c-4")], "paging": {"next": f"{host}/media-1/comments?after=w"}}),
        ]
    )

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-1", "c-2", "c-3", "c-4"]
    # The token is re-sent on every cursor: _request authenticates with a
    # header, so Graph builds paging.next from a query string that has none.
    for paged_call in provider._request.call_args_list[1:]:
        assert paged_call.kwargs["access_token"] == "token"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_ignores_an_off_host_paging_url(make_provider, host, media_url):
    provider = make_provider()
    page = {"data": [_ig_comment("c-1")], "paging": {"next": "https://evil.example.com/steal"}}
    provider._request = MagicMock(return_value=_resp({"data": [_media(page)]}))

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-1"]
    provider._request.assert_called_once()


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_skips_a_comment_with_an_unparseable_timestamp(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp(
            {"data": [_media({"data": [_ig_comment("c-1", timestamp="not a date"), _ig_comment("c-2")]})]}
        )
    )

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-2"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_keeps_earlier_media_when_a_later_one_fails(make_provider, host, media_url):
    provider = make_provider()
    broken = _media({"data": [_ig_comment("c-2")], "paging": {"next": f"{host}/media-2/comments?after=x"}}, "media-2")
    provider._request = MagicMock(
        side_effect=[
            _resp({"data": [_media({"data": [_ig_comment("c-1")]}), broken]}),
            APIError("boom", status_code=500, platform="Instagram"),
        ]
    )

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-1", "c-2"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_degrades_the_field_set_when_graph_rejects_it(make_provider, host, media_url):
    """Graph fails the whole call on one unknown or unpermitted field."""
    provider = make_provider()
    provider._request = MagicMock(
        side_effect=[
            APIError("(#100) unknown field replies", status_code=400, platform="Instagram"),
            _resp({"data": [_media({"data": [_ig_comment()]})]}),
        ]
    )

    messages = _poll_comments(provider)

    assert [m.platform_message_id for m in messages] == ["c-1"]
    assert "replies" in provider._request.call_args_list[0].kwargs["params"]["fields"]
    assert "replies" not in provider._request.call_args_list[1].kwargs["params"]["fields"]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_does_not_degrade_after_a_server_error(make_provider, host, media_url):
    """A 5xx fails identically however few fields are asked for."""
    provider = make_provider()
    provider._request = MagicMock(side_effect=APIError("boom", status_code=500, platform="Instagram"))

    with pytest.raises(APIError):
        _poll_comments(provider)

    provider._request.assert_called_once()


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_raises_when_every_field_set_is_rejected(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(side_effect=APIError("(#100) nope", status_code=400, platform="Instagram"))

    with pytest.raises(APIError):
        _poll_comments(provider)

    assert provider._request.call_count == len(INSTAGRAM_COMMENT_FIELD_SETS)


def test_comment_poll_refuses_to_run_without_an_owner():
    """Without an owner the own-comment filter cannot recognise our own
    activity, and every first comment we post would be ingested as inbound."""
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock()

    assert provider.get_messages("token") == []
    provider._request.assert_not_called()


def test_instagram_login_returns_dms_even_when_the_comment_poll_fails():
    provider = InstagramLoginProvider(IG_LOGIN_CREDS)
    provider._fetch_direct_messages = MagicMock(return_value=["a dm"])
    provider._fetch_media_comments = MagicMock(side_effect=APIError("nope", status_code=403, platform="Instagram"))

    assert provider.get_messages("token") == ["a dm"]


def test_instagram_login_get_messages_raises_when_both_halves_fail():
    provider = InstagramLoginProvider(IG_LOGIN_CREDS)
    provider._fetch_direct_messages = MagicMock(side_effect=APIError("dm", status_code=403, platform="Instagram"))
    provider._fetch_media_comments = MagicMock(side_effect=APIError("comment", status_code=403, platform="Instagram"))

    with pytest.raises(APIError, match="dm"):
        provider.get_messages("token")


# ----------------------------------------------------------------------
# Reply targeting
# ----------------------------------------------------------------------


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_a_reply_is_answered_on_its_parent_comment(make_provider, host, media_url):
    """A reply has no ``replies`` edge of its own — Instagram threads one level
    deep, and posting to the reply is rejected."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"id": "r-2"}))

    provider.reply_to_comment("token", "r-1", "Thanks!", extra={"parent_id": "c-1", "reply_edge": "comment"})

    assert provider._request.call_args.args[1] == f"{host}/c-1/replies"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_a_parent_id_naming_the_media_is_ignored(make_provider, host, media_url):
    """Targeting the media would publish a new top-level comment instead of a
    threaded reply."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"id": "r-2"}))

    provider.reply_to_comment(
        "token",
        "c-1",
        "Thanks!",
        extra={"parent_id": "media-1", "post_id": "media-1", "reply_edge": "comment"},
    )

    assert provider._request.call_args.args[1] == f"{host}/c-1/replies"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_a_caption_mention_is_answered_on_the_media(make_provider, host, media_url):
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"id": "c-9"}))

    provider.reply_to_comment("token", "media-1", "Thanks!", extra={"reply_edge": "media"})

    assert provider._request.call_args.args[1] == f"{host}/media-1/comments"


# ----------------------------------------------------------------------
# Webhook subscription
# ----------------------------------------------------------------------

# The Page object's own field list, quoted from Meta's rejection of the old
# call: "(#100) Param subscribed_fields[0] must be one of {feed, mention, ...}".
PAGE_ONLY_WEBHOOK_FIELDS = {"feed", "mention", "name", "picture", "category", "conversations", "standby"}


def test_subscribing_targets_the_instagram_user_with_instagram_fields():
    """comments/mentions belong to Meta's Instagram object, not to a Page.

    Sending them to a Page is rejected outright, which is what left every
    Instagram inbox deaf to comments. Posting Page fields from here would be
    just as wrong: subscribed_apps replaces a field list rather than merging,
    so it would silently drop a co-connected Facebook Page's mention and
    message subscriptions.
    """
    provider = InstagramProvider(IG_CREDS)
    provider._request = MagicMock(return_value=_resp({"success": True}))

    assert provider.subscribe_webhooks("token", "ig-1") is True

    args, kwargs = provider._request.call_args
    assert args[1] == "https://graph.facebook.com/v25.0/ig-1/subscribed_apps"
    sent = set(kwargs["params"]["subscribed_fields"].split(","))
    assert sent == {"comments", "mentions"}
    assert not sent & PAGE_ONLY_WEBHOOK_FIELDS


def test_instagram_never_subscribes_to_messages():
    """This OAuth flow never requests instagram_manage_messages, so Meta would
    reject the subscription outright."""
    from providers.instagram import INSTAGRAM_WEBHOOK_FIELDS

    assert "messages" not in INSTAGRAM_WEBHOOK_FIELDS


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_reports_the_author_id_as_the_handle(make_provider, host, media_url):
    """The webhook path stores the platform user ID in sender_handle, and
    _upsert_message rewrites that column on every re-poll — emitting the
    username here would silently overwrite the IGSID a few minutes later."""
    provider = make_provider()
    provider._request = MagicMock(return_value=_resp({"data": [_media({"data": [_ig_comment()]})]}))

    (message,) = _poll_comments(provider)

    assert message.extra["sender_handle"] == "ig-2"
    assert message.sender_id == "ig-2"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_keeps_the_username_as_instagram_spelled_it(make_provider, host, media_url):
    """Case-folding is for comparison only; it must not reach a display field."""
    provider = make_provider()
    provider._request = MagicMock(
        return_value=_resp({"data": [_media({"data": [_ig_comment(username="LenaSorensen")]})]})
    )

    (message,) = _poll_comments(provider)

    assert message.sender_name == "LenaSorensen"


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_keeps_replies_when_only_the_author_field_is_rejected(make_provider, host, media_url):
    """Dropping ``from`` and ``replies`` together would lose every reply on an
    account that could read replies perfectly well — including a customer
    answering our own first comment."""
    provider = make_provider()
    reply = _ig_comment("r-1", "Answering you", author_id=None, username="curious")
    parent = _ig_comment("c-1", "First!", author_id=None, username="pinklion.xyz", replies={"data": [reply]})
    provider._request = MagicMock(
        side_effect=[
            APIError("(#100) unknown field from", status_code=400, platform="Instagram"),
            APIError("(#100) unknown field from", status_code=400, platform="Instagram"),
            _resp({"data": [_media({"data": [parent]})]}),
        ]
    )

    messages = _poll_comments(provider)

    # The parent is ours and skipped; its reply is not, and must survive.
    assert [m.platform_message_id for m in messages] == ["r-1"]
    sent = [c.kwargs["params"]["fields"] for c in provider._request.call_args_list]
    assert "replies" in sent[2]
    assert "from{" not in sent[2]


@pytest.mark.parametrize(("make_provider", "host", "media_url"), IG_PROVIDERS)
def test_comment_poll_keeps_the_author_when_only_replies_are_rejected(make_provider, host, media_url):
    """``from`` carries the author id the own-comment filter prefers, so it is
    given up last."""
    provider = make_provider()
    provider._request = MagicMock(
        side_effect=[
            APIError("(#100) unknown field replies", status_code=400, platform="Instagram"),
            _resp({"data": [_media({"data": [_ig_comment()]})]}),
        ]
    )

    (message,) = _poll_comments(provider)

    assert message.sender_id == "ig-2"
    sent = provider._request.call_args_list[1].kwargs["params"]["fields"]
    assert "from{" in sent
    assert "replies" not in sent


class TestMediaRequired:
    """A media-less publish must fail with a clear, non-retryable error —
    not a raw IndexError (production incident: text-only post to Instagram
    crashed with 'list index out of range' and burned the retry schedule)."""

    def _content(self, post_type):
        return PublishContent(text="hello", post_type=post_type, extra={"ig_user_id": "17841400000000000"})

    def _assert_clean_media_error(self, post_type):
        provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
        provider._request = MagicMock()  # any API call would be a bug here
        with pytest.raises(PublishError) as excinfo:
            provider.publish_post("token", self._content(post_type))
        assert "media" in str(excinfo.value).lower() or "image or video" in str(excinfo.value).lower()
        assert excinfo.value.retryable is False
        provider._request.assert_not_called()

    def test_image_post_without_media_raises_publish_error(self):
        self._assert_clean_media_error(PostType.IMAGE)

    def test_reel_without_media_raises_publish_error(self):
        self._assert_clean_media_error(PostType.REEL)

    def test_carousel_without_media_raises_publish_error(self):
        self._assert_clean_media_error(PostType.CAROUSEL)
