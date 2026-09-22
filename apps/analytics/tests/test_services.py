"""Tests for analytics read-side services."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.social_accounts.models import SocialAccount


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Analytics Services WS", organization=organization)


@pytest.fixture
def facebook_account(workspace):
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="facebook",
        account_platform_id="page-1",
        account_name="Facebook Page",
        oauth_access_token="token",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


def _published_platform_post(account):
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=account.workspace, caption="hello")
    return PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.PUBLISHED,
        published_at=timezone.now(),
        platform_post_id="post-1",
    )


@pytest.mark.django_db
def test_account_bundle_prefers_fresher_post_fallback_for_content_metrics(facebook_account):
    """Per-post Facebook analytics can refresh hourly while account snapshots are
    daily. The main graph should use the fresher post-derived value instead of
    leaving the overall insight chip/card stuck on the stale account row.
    """
    from apps.analytics.models import AccountInsightsSnapshot, PostInsightsSnapshot
    from apps.analytics.services import account_analytics_bundle

    today = timezone.now().date()
    old_capture = timezone.now() - timedelta(hours=2)
    new_capture = timezone.now()
    platform_post = _published_platform_post(facebook_account)

    account_row = AccountInsightsSnapshot.objects.create(
        social_account=facebook_account,
        metric_key="views",
        date=today,
        value=10,
    )
    AccountInsightsSnapshot.objects.filter(id=account_row.id).update(captured_at=old_capture)

    post_row = PostInsightsSnapshot.objects.create(
        platform_post=platform_post,
        metric_key="views",
        date=today,
        value=42,
    )
    PostInsightsSnapshot.objects.filter(id=post_row.id).update(captured_at=new_capture)

    series = account_analytics_bundle(facebook_account, 7)["series_map"]["views"]

    assert series[-1] == 42


@pytest.mark.django_db
def test_account_bundle_keeps_account_reach_instead_of_summing_post_reach(facebook_account):
    from apps.analytics.models import AccountInsightsSnapshot, PostInsightsSnapshot
    from apps.analytics.services import account_analytics_bundle

    today = timezone.now().date()
    platform_post = _published_platform_post(facebook_account)

    AccountInsightsSnapshot.objects.create(
        social_account=facebook_account,
        metric_key="reach",
        date=today,
        value=10,
    )
    PostInsightsSnapshot.objects.create(
        platform_post=platform_post,
        metric_key="reach",
        date=today,
        value=42,
    )

    series = account_analytics_bundle(facebook_account, 7)["series_map"]["reach"]

    assert series[-1] == 10


@pytest.mark.django_db
def test_latest_post_stats_takes_the_newest_row_per_metric(facebook_account):
    """The dedup moved from a Python ``seen`` set into Postgres ``DISTINCT ON``.

    The ordering prefix is what makes that correct — ``date DESC`` inside the
    ORDER BY is the only reason the newest row survives — so pin it here rather
    than trusting the clause to keep meaning what it means.
    """
    from apps.analytics.models import PostInsightsSnapshot
    from apps.analytics.services import _latest_post_stats

    post = _published_platform_post(facebook_account)
    today = timezone.now().date()
    for offset, value in ((2, 10.0), (1, 20.0), (0, 30.0)):
        PostInsightsSnapshot.objects.create(
            platform_post=post,
            metric_key="likes",
            date=today - timedelta(days=offset),
            value=value,
        )

    assert _latest_post_stats([post.id], ["likes"]) == {post.id: {"likes": 30.0}}


@pytest.mark.django_db
def test_latest_post_stats_keeps_metrics_and_posts_separate(facebook_account):
    from apps.analytics.models import PostInsightsSnapshot
    from apps.analytics.services import _latest_post_stats

    first = _published_platform_post(facebook_account)
    second = _published_platform_post(facebook_account)
    today = timezone.now().date()
    for post, metric, value in (
        (first, "likes", 1.0),
        (first, "comments", 2.0),
        (second, "likes", 3.0),
    ):
        PostInsightsSnapshot.objects.create(platform_post=post, metric_key=metric, date=today, value=value)

    assert _latest_post_stats([first.id, second.id], ["likes", "comments"]) == {
        first.id: {"likes": 1.0, "comments": 2.0},
        second.id: {"likes": 3.0},
    }


@pytest.mark.django_db
def test_latest_post_stats_ignores_metrics_not_asked_for(facebook_account):
    from apps.analytics.models import PostInsightsSnapshot
    from apps.analytics.services import _latest_post_stats

    post = _published_platform_post(facebook_account)
    today = timezone.now().date()
    PostInsightsSnapshot.objects.create(platform_post=post, metric_key="likes", date=today, value=1.0)
    PostInsightsSnapshot.objects.create(platform_post=post, metric_key="shares", date=today, value=9.0)

    assert _latest_post_stats([post.id], ["likes"]) == {post.id: {"likes": 1.0}}


@pytest.mark.django_db
def test_latest_post_stats_short_circuits_on_no_posts(django_assert_num_queries):
    from apps.analytics.services import _latest_post_stats

    with django_assert_num_queries(0):
        assert _latest_post_stats([], ["likes"]) == {}


@pytest.mark.django_db
def test_latest_post_stats_runs_one_query_regardless_of_history(facebook_account, django_assert_num_queries):
    """No JSON is decoded and no model is hydrated: three columns, one query.

    ``PostInsightsSnapshot`` carries two JSONFields — ``raw`` is the whole
    provider response — that Django decodes eagerly on hydration. Reading these
    as models ran a ``json.loads`` per payload per row to fetch three numbers
    that are not in the JSON, which is what pushed the web dyno to 88% of a
    512 MB quota.
    """
    from apps.analytics.models import PostInsightsSnapshot
    from apps.analytics.services import _latest_post_stats

    post = _published_platform_post(facebook_account)
    today = timezone.now().date()
    bulky = {"payload": "x" * 2000}
    for offset in range(30):
        PostInsightsSnapshot.objects.create(
            platform_post=post,
            metric_key="likes",
            date=today - timedelta(days=offset),
            value=float(offset),
            raw=bulky,
        )

    with django_assert_num_queries(1):
        result = _latest_post_stats([post.id], ["likes"])
    assert result == {post.id: {"likes": 0.0}}


@pytest.mark.django_db
def test_latest_post_stats_dedups_without_distinct_on(facebook_account, monkeypatch):
    """SQLite has no DISTINCT ON, and the README supports SQLite deployments.

    Django's base ``distinct_sql`` raises ``NotSupportedError`` as soon as a
    field is passed, so the whole analytics surface 500s on SQLite if the
    clause is applied unconditionally. Force the fallback and assert it picks
    the same rows.
    """
    from django.db import connections

    from apps.analytics.models import PostInsightsSnapshot
    from apps.analytics.services import _latest_post_stats

    post = _published_platform_post(facebook_account)
    today = timezone.now().date()
    for offset, value in ((2, 10.0), (1, 20.0), (0, 30.0)):
        PostInsightsSnapshot.objects.create(
            platform_post=post,
            metric_key="likes",
            date=today - timedelta(days=offset),
            value=value,
        )
    PostInsightsSnapshot.objects.create(platform_post=post, metric_key="comments", date=today, value=7.0)

    monkeypatch.setattr(connections["default"].features, "can_distinct_on_fields", False, raising=False)

    assert _latest_post_stats([post.id], ["likes", "comments"]) == {post.id: {"likes": 30.0, "comments": 7.0}}


@pytest.mark.django_db
def test_latest_post_stats_agrees_across_both_dedup_paths(facebook_account, monkeypatch):
    """The two branches must be interchangeable, not merely both plausible."""
    from django.db import connections

    from apps.analytics.models import PostInsightsSnapshot
    from apps.analytics.services import _latest_post_stats

    first = _published_platform_post(facebook_account)
    second = _published_platform_post(facebook_account)
    today = timezone.now().date()
    for post in (first, second):
        for offset, metric in ((0, "likes"), (3, "likes"), (1, "comments")):
            PostInsightsSnapshot.objects.create(
                platform_post=post,
                metric_key=metric,
                date=today - timedelta(days=offset),
                value=float(offset),
            )

    ids = [first.id, second.id]
    with_distinct_on = _latest_post_stats(ids, ["likes", "comments"])
    monkeypatch.setattr(connections["default"].features, "can_distinct_on_fields", False, raising=False)
    without_distinct_on = _latest_post_stats(ids, ["likes", "comments"])

    assert with_distinct_on == without_distinct_on
