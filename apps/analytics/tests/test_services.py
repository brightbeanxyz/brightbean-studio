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
