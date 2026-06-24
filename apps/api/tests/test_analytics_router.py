"""End-to-end tests for the ``/api/v1/analytics/*`` REST surface.

Mirrors the structure of ``test_routers.py`` (Django test client + pytest
fixtures). Covers the agent polling workflow:

* Channel summary with snapshots → derived metrics + freshness fields.
* Just-connected channel → empty payload + soon ``next_sync_eta``.
* Platforms in ``NO_ANALYTICS_PLATFORMS`` → ``analytics_available: false``.
* Disconnected channel → still returns data with status surfaced.
* Allowlist enforcement (403 on account, 404 on post).
* ``days`` query-param validation.
* Drafts and scheduled posts → empty metric tiles, not an error.
* Mixed-platform posts → per-child ``unavailable_reason``.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="analytics-owner@example.com",
        password="testpass123",
        name="Analytics Owner",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Analytics Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Analytics WS", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
    return WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )


@pytest.fixture
def instagram_account(db, workspace):
    """Instagram account — has a full analytics surface."""
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-analytics",
        account_name="IG Analytics",
        account_handle="ig.analytics",
        follower_count=1000,
        connection_status="connected",
    )


@pytest.fixture
def linkedin_personal_account(db, workspace):
    """LinkedIn Personal — in NO_ANALYTICS_PLATFORMS."""
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-personal",
        account_name="My LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def disconnected_instagram_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-disconnected",
        account_name="IG Disconnected",
        connection_status="disconnected",
    )


@pytest.fixture
def foreign_account(db, organization):
    """Account in a sibling workspace — not in the bearer's allowlist."""
    from apps.social_accounts.models import SocialAccount
    from apps.workspaces.models import Workspace

    other = Workspace.objects.create(name="Other WS", organization=organization)
    return SocialAccount.objects.create(
        workspace=other,
        platform="instagram",
        account_platform_id="ig-foreign",
        account_name="Foreign IG",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, instagram_account, linkedin_personal_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[instagram_account, linkedin_personal_account],
        issued_by=user,
        name="analytics-smoke",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def no_view_analytics_key(db, user, owner_memberships, workspace, instagram_account):
    """Key granted every permission EXCEPT view_analytics.

    Exercises the ``_require_perm(request, "view_analytics")`` gate the
    router enforces in front of both analytics endpoints.
    """
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[instagram_account],
        issued_by=user,
        name="analytics-no-perm",
        permissions=[p for p in PERMISSION_KEYS if p != "view_analytics"],
    )


@pytest.fixture
def issued_key_with_disconnected(db, user, owner_memberships, workspace, disconnected_instagram_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[disconnected_instagram_account],
        issued_by=user,
        name="analytics-disconnected",
        permissions=list(PERMISSION_KEYS),
    )


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


@pytest.fixture
def disconnected_client(issued_key_with_disconnected):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key_with_disconnected.plaintext_token}")


@pytest.fixture
def client_without_view_analytics(no_view_analytics_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {no_view_analytics_key.plaintext_token}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_account_snapshots(account, *, days: int = 30, base_value: float = 100.0):
    """Write a contiguous ``2 * days``-long account snapshot history.

    We need 2× the requested window so the derive helper's previous-period
    delta has data to subtract against.
    """
    from apps.analytics.metrics import PLATFORM_METRICS
    from apps.analytics.models import AccountInsightsSnapshot

    end = timezone.now().date()
    for metric in PLATFORM_METRICS.get(account.platform, []):
        for offset in range(2 * days):
            day = end - timedelta(days=2 * days - 1 - offset)
            AccountInsightsSnapshot.objects.create(
                social_account=account,
                metric_key=metric,
                date=day,
                value=base_value + offset,
            )


def _seed_post_snapshots(platform_post, *, days: int = 5, base_value: float = 10.0):
    """Write a since-publish snapshot history for every post-level metric."""
    from apps.analytics.metrics import post_metrics_for
    from apps.analytics.models import PostInsightsSnapshot

    end = timezone.now().date()
    for metric in post_metrics_for(platform_post.social_account.platform):
        for offset in range(days):
            day = end - timedelta(days=days - 1 - offset)
            PostInsightsSnapshot.objects.create(
                platform_post=platform_post,
                metric_key=metric,
                date=day,
                value=base_value + offset,
            )


# ---------------------------------------------------------------------------
# GET /analytics/accounts/{account_id}
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAccountAnalytics:
    def test_happy_path_returns_derived_metrics(self, client_with_token, instagram_account):
        _seed_account_snapshots(instagram_account, days=30)
        r = client_with_token.get(f"/api/v1/analytics/accounts/{instagram_account.id}?days=30")
        assert r.status_code == 200, r.content
        body = r.json()

        assert body["account_id"] == str(instagram_account.id)
        assert body["platform"] == "instagram"
        assert body["connection_status"] == "connected"
        assert body["days"] == 30
        assert body["analytics_available"] is True
        assert body["unavailable_reason"] is None

        # Hero metrics carry the wire shape from DerivedMetricResponse.
        assert isinstance(body["hero_metrics"], list)
        assert body["hero_metrics"], "expected at least one hero metric"
        for metric in body["hero_metrics"]:
            assert {"key", "label", "kind", "value", "delta", "series"} <= set(metric)
            assert isinstance(metric["series"], list)

        # Instagram qualifies for the engagement card.
        assert body["engagement"] is not None
        assert body["engagement"]["rate"]["kind"] == "percent"
        # Follower growth available on Instagram (followers total, derived to a delta).
        assert body["follower_growth"] is not None
        assert body["follower_growth"]["key"] == "followers"

        # Freshness fields populated for an account with snapshots.
        assert body["captured_at"] is not None
        assert body["next_sync_eta"] is not None

    def test_just_connected_account_returns_empty_with_soon_eta(self, client_with_token, instagram_account):
        # No snapshots seeded — represents a freshly-connected account.
        r = client_with_token.get(f"/api/v1/analytics/accounts/{instagram_account.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["analytics_available"] is True
        # Hero metrics still listed (per platform catalog) but with zero values.
        for metric in body["hero_metrics"]:
            assert metric["value"] == 0
            assert metric["series"] == [] or all(v == 0 for v in metric["series"])
        assert body["captured_at"] is None
        # First-poll ETA: shortly from now (we asked for +5 min).
        assert body["next_sync_eta"] is not None

    def test_unavailable_platform_returns_reason(self, client_with_token, linkedin_personal_account):
        r = client_with_token.get(f"/api/v1/analytics/accounts/{linkedin_personal_account.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["analytics_available"] is False
        assert "LinkedIn" in body["unavailable_reason"]
        assert body["hero_metrics"] == []
        assert body["engagement"] is None
        assert body["follower_growth"] is None
        assert body["captured_at"] is None
        assert body["next_sync_eta"] is None

    def test_disconnected_account_still_returns_data(self, disconnected_client, disconnected_instagram_account):
        _seed_account_snapshots(disconnected_instagram_account, days=7)
        r = disconnected_client.get(f"/api/v1/analytics/accounts/{disconnected_instagram_account.id}?days=7")
        assert r.status_code == 200
        body = r.json()
        assert body["connection_status"] == "disconnected"
        assert body["analytics_available"] is True
        assert body["captured_at"] is not None

    def test_account_not_in_allowlist_is_403(self, client_with_token, foreign_account):
        r = client_with_token.get(f"/api/v1/analytics/accounts/{foreign_account.id}")
        assert r.status_code == 403

    def test_days_below_minimum_is_422(self, client_with_token, instagram_account):
        r = client_with_token.get(f"/api/v1/analytics/accounts/{instagram_account.id}?days=5")
        assert r.status_code == 422

    def test_days_above_maximum_is_422(self, client_with_token, instagram_account):
        r = client_with_token.get(f"/api/v1/analytics/accounts/{instagram_account.id}?days=180")
        assert r.status_code == 422

    def test_unknown_account_is_403(self, client_with_token):
        import uuid

        r = client_with_token.get(f"/api/v1/analytics/accounts/{uuid.uuid4()}")
        # Unknown == not-in-allowlist (we don't leak existence).
        assert r.status_code == 403

    def test_key_without_view_analytics_is_403(self, client_without_view_analytics, instagram_account):
        """Locks in the ``view_analytics`` permission gate the router enforces."""
        r = client_without_view_analytics.get(f"/api/v1/analytics/accounts/{instagram_account.id}")
        assert r.status_code == 403
        assert "view_analytics" in r.json()["detail"]


# ---------------------------------------------------------------------------
# GET /analytics/posts/{post_id}
# ---------------------------------------------------------------------------


@pytest.fixture
def published_post(db, workspace, instagram_account):
    """Post + one published PlatformPost on Instagram, with snapshots."""
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=workspace, caption="hello world")
    published_at = timezone.now() - timedelta(hours=6)
    pp = PlatformPost.objects.create(
        post=post,
        social_account=instagram_account,
        status="published",
        published_at=published_at,
        platform_post_id="ig-shortcode-xyz",
    )
    _seed_post_snapshots(pp, days=5)
    return post, pp


@pytest.fixture
def draft_post(db, workspace, instagram_account):
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=workspace, caption="draft only")
    PlatformPost.objects.create(post=post, social_account=instagram_account, status="draft")
    return post


@pytest.fixture
def mixed_platform_post(db, workspace, instagram_account, linkedin_personal_account):
    """Post with one Instagram child (analytics) + one LinkedIn Personal child (no analytics)."""
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=workspace, caption="cross-posted")
    published_at = timezone.now() - timedelta(hours=2)
    ig_pp = PlatformPost.objects.create(
        post=post,
        social_account=instagram_account,
        status="published",
        published_at=published_at,
        platform_post_id="ig-shortcode-mix",
    )
    PlatformPost.objects.create(
        post=post,
        social_account=linkedin_personal_account,
        status="published",
        published_at=published_at,
        platform_post_id="li-urn-mix",
    )
    _seed_post_snapshots(ig_pp, days=3)
    return post


@pytest.fixture
def out_of_scope_post(db, organization, foreign_account):
    """Post in a workspace the bearer can't see."""
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=foreign_account.workspace, caption="hidden")
    PlatformPost.objects.create(post=post, social_account=foreign_account, status="published")
    return post


@pytest.mark.django_db
class TestPostAnalytics:
    def test_published_post_returns_metric_tiles(self, client_with_token, published_post):
        post, pp = published_post
        r = client_with_token.get(f"/api/v1/analytics/posts/{post.id}")
        assert r.status_code == 200, r.content
        body = r.json()

        assert body["post_id"] == str(post.id)
        assert len(body["platform_posts"]) == 1
        child = body["platform_posts"][0]
        assert child["platform_post_id"] == str(pp.id)
        assert child["platform"] == "instagram"
        assert child["status"] == "published"
        assert child["analytics_available"] is True
        assert child["unavailable_reason"] is None
        assert child["metric_tiles"], "expected metric tiles for a published post"
        for tile in child["metric_tiles"]:
            assert {"key", "label", "kind", "value", "series", "is_primary"} <= set(tile)
        # Exactly one tile is the platform-primary (views for IG was reach; ``views``/``reach`` are non-primary in PLATFORM_PRIMARY).
        primary_flags = [tile["is_primary"] for tile in child["metric_tiles"]]
        assert primary_flags.count(True) == 1
        assert child["captured_at"] is not None
        assert child["next_sync_eta"] is not None

    def test_draft_post_returns_empty_metric_tiles(self, client_with_token, draft_post):
        r = client_with_token.get(f"/api/v1/analytics/posts/{draft_post.id}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["platform_posts"]) == 1
        child = body["platform_posts"][0]
        assert child["status"] == "draft"
        assert child["published_at"] is None
        assert child["analytics_available"] is True
        assert child["metric_tiles"] == []
        assert child["captured_at"] is None
        assert child["next_sync_eta"] is None

    def test_mixed_platform_post_reports_per_child(self, client_with_token, mixed_platform_post):
        r = client_with_token.get(f"/api/v1/analytics/posts/{mixed_platform_post.id}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["platform_posts"]) == 2

        by_platform = {child["platform"]: child for child in body["platform_posts"]}
        ig_child = by_platform["instagram"]
        li_child = by_platform["linkedin_personal"]

        assert ig_child["analytics_available"] is True
        assert ig_child["metric_tiles"], "instagram child should have tiles"

        assert li_child["analytics_available"] is False
        assert li_child["unavailable_reason"] is not None
        assert li_child["metric_tiles"] == []
        assert li_child["captured_at"] is None

    def test_post_outside_allowlist_is_404(self, client_with_token, out_of_scope_post):
        r = client_with_token.get(f"/api/v1/analytics/posts/{out_of_scope_post.id}")
        assert r.status_code == 404

    def test_key_without_view_analytics_is_403(self, client_without_view_analytics, published_post):
        """Permission gate fires before the post lookup — even own posts are 403."""
        post, _pp = published_post
        r = client_without_view_analytics.get(f"/api/v1/analytics/posts/{post.id}")
        assert r.status_code == 403
        assert "view_analytics" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Platform config gate — a platform disabled in AnalyticsPlatformConfig must
# report analytics_available: false (no sync runs, so no data ever lands).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPlatformConfigGating:
    def test_account_unavailable_when_platform_disabled(self, client_with_token, instagram_account):
        from apps.social_accounts.models import AnalyticsPlatformConfig

        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram", defaults={"is_enabled": False})
        _seed_account_snapshots(instagram_account, days=7)
        r = client_with_token.get(f"/api/v1/analytics/accounts/{instagram_account.id}?days=7")
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["analytics_available"] is False
        assert body["unavailable_reason"]
        assert body["hero_metrics"] == []
        assert body["next_sync_eta"] is None

    def test_post_child_unavailable_when_platform_disabled(self, client_with_token, published_post):
        from apps.social_accounts.models import AnalyticsPlatformConfig

        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram", defaults={"is_enabled": False})
        post, _pp = published_post
        r = client_with_token.get(f"/api/v1/analytics/posts/{post.id}")
        assert r.status_code == 200, r.content
        child = r.json()["platform_posts"][0]
        assert child["analytics_available"] is False
        assert child["unavailable_reason"]
        assert child["metric_tiles"] == []
        assert child["next_sync_eta"] is None
