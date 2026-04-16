import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.analytics.models import PostSnapshot, RefreshLog


@pytest.mark.django_db
class TestPostSnapshot:
    def test_create_snapshot(self, workspace, social_account):
        snapshot = PostSnapshot.objects.create(
            workspace=workspace,
            social_account=social_account,
            platform_post_id="post_123",
            post_url="https://instagram.com/p/post_123",
            post_text="New drop preview",
            post_type="image",
            posted_at=timezone.now() - timedelta(days=1),
            likes=100,
            comments=20,
            shares=10,
            saves=30,
            engagements=160,
            impressions=2000,
            fetched_at=timezone.now(),
        )
        assert snapshot.id is not None
        assert snapshot.likes == 100
        assert snapshot.engagement_rate == pytest.approx(8.0)

    def test_engagement_rate_zero_impressions(self, workspace, social_account):
        snapshot = PostSnapshot(
            workspace=workspace,
            social_account=social_account,
            platform_post_id="post_456",
            engagements=50,
            impressions=0,
            posted_at=timezone.now(),
            fetched_at=timezone.now(),
        )
        assert snapshot.engagement_rate == 0.0

    def test_unique_constraint(self, workspace, social_account):
        now = timezone.now()
        PostSnapshot.objects.create(
            workspace=workspace,
            social_account=social_account,
            platform_post_id="post_789",
            posted_at=now,
            fetched_at=now,
        )
        with pytest.raises(IntegrityError):
            PostSnapshot.objects.create(
                workspace=workspace,
                social_account=social_account,
                platform_post_id="post_789",
                posted_at=now,
                fetched_at=now,
            )

    def test_upsert_updates_existing(self, workspace, social_account):
        now = timezone.now()
        PostSnapshot.objects.create(
            workspace=workspace,
            social_account=social_account,
            platform_post_id="post_upsert",
            posted_at=now,
            fetched_at=now,
            likes=10,
        )
        PostSnapshot.objects.update_or_create(
            social_account=social_account,
            platform_post_id="post_upsert",
            defaults={
                "workspace": workspace,
                "posted_at": now,
                "fetched_at": timezone.now(),
                "likes": 50,
            },
        )
        assert PostSnapshot.objects.filter(platform_post_id="post_upsert").count() == 1
        assert PostSnapshot.objects.get(platform_post_id="post_upsert").likes == 50


@pytest.mark.django_db
class TestRefreshLog:
    def test_create_success_log(self, workspace, social_account):
        now = timezone.now()
        log = RefreshLog.objects.create(
            workspace=workspace,
            social_account=social_account,
            status="success",
            posts_fetched=15,
            started_at=now,
            completed_at=now + timedelta(seconds=3),
        )
        assert log.status == "success"
        assert log.posts_fetched == 15

    def test_create_error_log(self, workspace, social_account):
        now = timezone.now()
        log = RefreshLog.objects.create(
            workspace=workspace,
            social_account=social_account,
            status="error",
            posts_fetched=0,
            error_message="API returned 401",
            started_at=now,
            completed_at=now + timedelta(seconds=1),
        )
        assert log.status == "error"
        assert "401" in log.error_message
