"""Retention boundaries, local deletion, migration compatibility and job races."""

import json
from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.analytics.models import AccountInsightsSnapshot, PostInsightsSnapshot, YouTubePeriodReport
from apps.analytics.tasks import _write_post_snapshot
from apps.analytics.youtube_reports import PACIFIC
from apps.composer.models import PlatformPost, Post
from apps.inbox.models import InboxMessage
from apps.inbox.tasks import InboxSyncEngine
from apps.media_library.models import MediaAsset
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.notifications.models import Notification
from apps.social_accounts.models import SocialAccount, YouTubeRevocation
from apps.social_accounts.views import _create_or_update_account
from apps.social_accounts.youtube_compliance import (
    attempt_revocation,
    check_connection,
    enforce_youtube_retention,
    purge_connection,
    retry_youtube_revocations,
)
from apps.workspaces.models import Workspace
from providers.exceptions import APIError, OAuthError, QuotaExceededError
from providers.types import AccountProfile, OAuthTokens, PostMetrics
from providers.types import InboxMessage as ProviderMessage

pytestmark = pytest.mark.django_db


@pytest.fixture
def channel(organization):
    workspace = Workspace.objects.create(organization=organization, name="Retention")
    return SocialAccount.objects.create(
        workspace=workspace,
        platform="youtube",
        account_platform_id="UCVerify",
        account_name="Channel",
        oauth_access_token="fictional-access",
        oauth_refresh_token="fictional-refresh",
    )


def provider_for(channel):
    provider = Mock()
    provider.credentials = {"client_id": "fictional", "client_secret": "fictional"}
    provider.get_profile.return_value = AccountProfile(
        platform_id=channel.account_platform_id, name="Verified", handle="@verified", follower_count=12
    )
    provider.get_post_metrics_batch.return_value = {}
    provider.get_comments_by_id.return_value = {}
    return provider


def video(channel, *, age=120):
    post = Post.objects.create(workspace=channel.workspace, caption="Original authored content")
    return PlatformPost.objects.create(
        post=post,
        social_account=channel,
        platform_post_id="old-video",
        status="published",
        published_at=timezone.now() - timedelta(days=age),
    )


def comment(channel, *, refreshed=None, identifier="comment-1", video_id="old-video"):
    return InboxMessage.objects.create(
        workspace=channel.workspace,
        social_account=channel,
        platform_message_id=identifier,
        body="API copy",
        sender_name="Sender",
        received_at=timezone.now() - timedelta(days=200),
        api_refreshed_at=refreshed,
        extra={"video_id": video_id},
    )


def test_legacy_authorizer_null_keeps_working_without_reconnect(channel):
    channel.connection_status = "error"
    channel.save(update_fields=["connection_status"])
    check_connection(channel, provider=provider_for(channel))
    channel.refresh_from_db()
    assert channel.youtube_authorized_by_id is None
    assert channel.youtube_authorization_checked_at is not None
    assert channel.connection_status == "connected"
    assert not channel.analytics_needs_reconnect


@pytest.mark.parametrize("day,retained", [(24, True), (28, True), (29, False)])
def test_success_timestamps_control_comment_expiry(channel, day, retained):
    now = timezone.now()
    message = comment(channel, refreshed=now - timedelta(days=day))
    provider = provider_for(channel)
    provider.get_post_metrics_batch.return_value = {"old-video": PostMetrics()}
    provider.get_comments_by_id.side_effect = APIError("Temporary failure", status_code=503)
    check_connection(channel, provider=provider, now=now)
    assert InboxMessage.objects.filter(pk=message.pk).exists() is retained
    if day == 24:
        provider.get_comments_by_id.assert_not_called()


def test_refresh_at_day_25_updates_edits_and_removes_old_notification_copies(channel, user):
    now = timezone.now()
    message = comment(channel, refreshed=now - timedelta(days=25))
    notice = Notification.objects.create(
        user=user,
        event_type="new_inbox_message",
        title="Old sender",
        body=message.body,
        data={"message_id": str(message.pk)},
    )
    provider = provider_for(channel)
    provider.get_post_metrics_batch.return_value = {"old-video": PostMetrics()}
    provider.get_comments_by_id.return_value = {
        "comment-1": {"textOriginal": "Edited", "authorDisplayName": "Current sender", "videoId": "old-video"}
    }
    check_connection(channel, provider=provider, now=now)
    message.refresh_from_db()
    assert message.body == "Edited"
    assert message.api_refreshed_at == now
    assert not Notification.objects.filter(pk=notice.pk).exists()


def test_deleted_comment_is_removed_after_successful_refresh(channel, user):
    message = comment(channel, refreshed=timezone.now() - timedelta(days=25))
    provider = provider_for(channel)
    provider.get_post_metrics_batch.return_value = {"old-video": PostMetrics()}
    check_connection(channel, provider=provider)
    assert not InboxMessage.objects.filter(pk=message.pk).exists()


def test_old_video_and_comment_only_video_are_verified_independently_of_analytics_cutoff(channel):
    old = video(channel, age=400)
    message = comment(channel, refreshed=timezone.now(), video_id="external-video")
    provider = provider_for(channel)
    provider.get_post_metrics_batch.return_value = {"old-video": PostMetrics(extra={"reported_metrics": {"views": 0}})}
    check_connection(channel, provider=provider)
    old.refresh_from_db()
    assert old.youtube_video_checked_at is not None
    assert PostInsightsSnapshot.objects.get(platform_post=old, metric_key="views").value == 0
    assert not InboxMessage.objects.filter(pk=message.pk).exists()
    provider.get_post_metrics_batch.assert_called_once_with("fictional-access", ["external-video", "old-video"])


def test_deleted_video_removes_copies_but_preserves_original_post_and_upload(channel):
    old = video(channel)
    authored = old.post
    asset = MediaAsset.objects.create(
        workspace=channel.workspace, filename="original.mp4", file="original.mp4", media_type="video"
    )
    message = comment(channel, refreshed=timezone.now())
    check_connection(channel, provider=provider_for(channel))
    assert not PlatformPost.objects.filter(pk=old.pk).exists()
    assert not InboxMessage.objects.filter(pk=message.pk).exists()
    assert Post.objects.filter(pk=authored.pk).exists()
    assert MediaAsset.objects.filter(pk=asset.pk).exists()


@pytest.mark.parametrize(
    "error", [QuotaExceededError("quota", quota_scope="data"), APIError("network", status_code=503)]
)
def test_retryable_errors_do_not_revoke_grants_or_extend_verification(channel, error):
    checked = timezone.now() - timedelta(days=28)
    channel.youtube_authorization_checked_at = checked
    channel.save(update_fields=["youtube_authorization_checked_at"])
    provider = provider_for(channel)
    provider.get_profile.side_effect = error
    check_connection(channel, provider=provider)
    channel.refresh_from_db()
    assert channel.youtube_authorization_checked_at == checked


def test_failed_verification_cannot_extend_retention_forever(channel):
    channel.youtube_authorization_checked_at = timezone.now() - timedelta(days=29)
    channel.save(update_fields=["youtube_authorization_checked_at"])
    provider = provider_for(channel)
    provider.get_profile.side_effect = APIError("network", status_code=503)
    check_connection(channel, provider=provider)
    assert not SocialAccount.objects.filter(pk=channel.pk).exists()


def test_confirmed_invalid_grant_purges_immediately(channel):
    channel.token_expires_at = timezone.now() - timedelta(hours=2)
    channel.save(update_fields=["token_expires_at"])
    provider = provider_for(channel)
    provider.refresh_token.side_effect = OAuthError("invalid grant", raw_response={"error": "invalid_grant"})
    check_connection(channel, provider=provider)
    assert not SocialAccount.objects.filter(pk=channel.pk).exists()


def test_missing_scope_is_retryable_and_does_not_force_existing_reconnection(channel):
    provider = provider_for(channel)
    provider.get_profile.side_effect = APIError(
        "Insufficient scope",
        status_code=403,
        raw_response={"error": {"errors": [{"reason": "insufficientPermissions"}]}},
    )
    check_connection(channel, provider=provider)
    channel.refresh_from_db()
    assert not channel.analytics_needs_reconnect
    assert channel.oauth_refresh_token == "fictional-refresh"


def test_history_keeps_180_days_and_drops_arbitrary_old_response_payloads(channel):
    now = timezone.now()
    today = now.astimezone(PACIFIC).date()
    old = AccountInsightsSnapshot.objects.create(
        social_account=channel, metric_key="views", date=today - timedelta(days=181), value=4
    )
    retained = AccountInsightsSnapshot.objects.create(
        social_account=channel,
        metric_key="views",
        date=today - timedelta(days=179),
        value=3,
        raw={"source": "youtube_analytics", "copied_profile": "Old"},
    )
    AccountInsightsSnapshot.objects.filter(pk=retained.pk).update(captured_at=now - timedelta(days=30))
    check_connection(channel, provider=provider_for(channel), now=now)
    assert not AccountInsightsSnapshot.objects.filter(pk=old.pk).exists()
    retained.refresh_from_db()
    assert retained.raw == {"source": "youtube_analytics"}
    assert retained.value == 3


def test_local_purge_is_idempotent_and_revocation_outbox_is_encrypted(channel, user):
    from background_task.models import Task

    old = video(channel)
    message = comment(channel)
    Notification.objects.create(
        user=user, event_type="new_inbox_message", title="Copy", data={"message_id": str(message.pk)}
    )
    Notification.objects.create(
        user=user, event_type="post_failed", title="API error copy", data={"platform_post_id": str(old.pk)}
    )
    AccountInsightsSnapshot.objects.create(
        social_account=channel, metric_key="views", date=timezone.now().date(), value=4
    )
    YouTubePeriodReport.objects.create(
        social_account=channel, start_date=timezone.now().date(), end_date=timezone.now().date(), metrics={"views": 4}
    )
    Task.objects.create(task_name="test", task_params='[["' + str(channel.pk) + '"], {}]', run_at=timezone.now())
    purge_connection(channel)
    purge_connection(channel)
    assert not SocialAccount.objects.filter(pk=channel.pk).exists()
    assert not AccountInsightsSnapshot.objects.exists()
    assert not YouTubePeriodReport.objects.exists()
    assert not Notification.objects.filter(data__message_id=str(message.pk)).exists()
    assert not Notification.objects.filter(data__platform_post_id=str(old.pk)).exists()
    assert not Task.objects.filter(task_name="test").exists()
    assert Post.objects.filter(pk=old.post_id).exists()
    retry = YouTubeRevocation.objects.get()
    with connection.cursor() as cursor:
        cursor.execute("SELECT token FROM social_accounts_youtuberevocation WHERE id = %s", [retry.pk])
        assert "fictional-refresh" not in cursor.fetchone()[0]
    with patch("providers.get_provider") as get_provider:
        get_provider.return_value.revoke_token.return_value = False
        attempt_revocation(retry.pk)
    retry.refresh_from_db()
    assert retry.attempts == 1
    retry.expires_at = timezone.now() - timedelta(seconds=1)
    retry.save(update_fields=["expires_at"])
    retry_youtube_revocations.now()
    assert not YouTubeRevocation.objects.exists()


def test_deleted_authorizer_purges_known_connection_but_does_not_guess_legacy_owner(channel, user):
    legacy = SocialAccount.objects.create(
        workspace=channel.workspace, platform="youtube", account_platform_id="UCLegacy"
    )
    channel.youtube_authorized_by = user
    channel.save(update_fields=["youtube_authorized_by"])
    user.delete()
    assert not SocialAccount.objects.filter(pk=channel.pk).exists()
    assert SocialAccount.objects.filter(pk=legacy.pk).exists()


def test_new_and_voluntary_reconnections_record_actual_authorizer(channel, user):
    profile = AccountProfile(platform_id=channel.account_platform_id, name="Renewed")
    with patch("apps.social_accounts.views.subscribe_account_webhooks_task"):
        connected = _create_or_update_account(
            workspace_id=channel.workspace_id,
            platform="youtube",
            profile=profile,
            access_token="renewed",
            authorizing_user=user,
        )
    assert connected.youtube_authorized_by_id == user.pk
    assert connected.youtube_data_generation > channel.youtube_data_generation


def test_pending_inbox_and_snapshot_writers_cannot_recreate_purged_data(channel):
    old = video(channel)
    request_generation = channel.youtube_data_generation
    purge_connection(channel)
    assert _write_post_snapshot(old, {"views": 100}, timezone.now().date(), youtube_generation=request_generation) == 0
    message = ProviderMessage(
        platform_message_id="pending",
        sender_id="sender",
        sender_name="Sender",
        text="Pending copy",
        timestamp=timezone.now(),
        message_type="comment",
        extra={},
    )
    InboxSyncEngine()._upsert_message(channel, message)
    assert not InboxMessage.objects.exists()


def test_org_request_purges_youtube_immediately_and_preserves_other_platforms(channel, user):
    org = channel.workspace.organization
    OrgMembership.objects.filter(user=user).delete()
    OrgMembership.objects.create(user=user, organization=org, org_role="owner")
    WorkspaceMembership.objects.create(user=user, workspace=channel.workspace, workspace_role="owner")
    user.last_workspace_id = channel.workspace_id
    user.save(update_fields=["last_workspace_id"])
    other = SocialAccount.objects.create(
        workspace=channel.workspace, platform="instagram_login", account_platform_id="IGKeep"
    )
    old = video(channel)
    other_post = PlatformPost.objects.create(post=old.post, social_account=other)
    client = Client()
    client.force_login(user)
    result = client.post(reverse("organizations:settings"), {"action": "delete_organization"})
    assert result.status_code == 302
    assert not SocialAccount.objects.filter(pk=channel.pk).exists()
    assert PlatformPost.objects.filter(pk=other_post.pk).exists()
    org.refresh_from_db()
    assert org.is_deletion_pending
    assert org.deletion_scheduled_for > timezone.now() + timedelta(days=13)
    page = client.get(reverse("organizations:settings"))
    assert "reconnecting YouTube" in page.content.decode()


def test_daily_task_covers_every_status_and_dry_run_is_read_only(channel, settings):
    settings.YOUTUBE_COMPLIANCE_ENFORCEMENT = True
    for status in SocialAccount.ConnectionStatus.values:
        SocialAccount.objects.create(
            workspace=channel.workspace, platform="youtube", account_platform_id=status, connection_status=status
        )
    with patch("apps.social_accounts.youtube_compliance.check_connection") as check:
        enforce_youtube_retention.now()
        assert check.call_count == 5
    output = StringIO()
    call_command("youtube_compliance_report", stdout=output)
    assert '"dry_run": true' in output.getvalue()
    assert SocialAccount.objects.filter(platform="youtube").count() == 5


def test_stale_grant_rejection_cannot_purge_a_voluntarily_renewed_connection(channel):
    provider = provider_for(channel)

    def rejected(*args, **kwargs):
        SocialAccount.objects.filter(pk=channel.pk).update(youtube_data_generation=1, oauth_access_token="renewed")
        raise OAuthError("old grant", raw_response={"error": "invalid_grant"})

    # Profile requests run outside the refresh lock, so a reconnect can finish
    # while the platform's rejection of the previous grant is still in flight.
    provider.get_profile.side_effect = rejected
    check_connection(channel, provider=provider)
    current = SocialAccount.objects.get(pk=channel.pk)
    assert current.oauth_access_token == "renewed"


def test_stale_token_refresh_cannot_overwrite_a_new_grant(channel):
    from providers.exceptions import TokenExpiredError

    provider = provider_for(channel)
    # A reconnect completes before the stale caller acquires the refresh lock.
    # A reconnect during the request waits for that lock (see test_oauth_refresh).
    SocialAccount.objects.filter(pk=channel.pk).update(youtube_data_generation=1, oauth_access_token="renewed")
    with pytest.raises(TokenExpiredError):
        channel.refresh_oauth_token(provider)
    provider.refresh_token.assert_not_called()
    channel.refresh_from_db()
    assert channel.oauth_access_token == "renewed"


@pytest.mark.parametrize("refresh", [False, True])
def test_youtube_health_metadata_preserves_a_later_publisher_refresh(channel, refresh):
    channel.token_expires_at = timezone.now() + timedelta(days=-1 if refresh else 30)
    channel.save(update_fields=["token_expires_at"])
    provider = provider_for(channel)
    profile = provider.get_profile.return_value
    provider.refresh_token.return_value = OAuthTokens(
        access_token="health-access", refresh_token="health-refresh", expires_in=3600
    )
    publisher = Mock()
    publisher.refresh_token.return_value = OAuthTokens(
        access_token="publisher-access", refresh_token="publisher-refresh", expires_in=7200
    )

    def get_profile(*args, **kwargs):
        current = SocialAccount.objects.get(pk=channel.pk)
        current.refresh_oauth_token(publisher, enqueue_backfill=False)
        return profile

    provider.get_profile.side_effect = get_profile
    check_connection(channel, provider=provider)
    channel.refresh_from_db()
    assert channel.oauth_access_token == "publisher-access"
    assert channel.oauth_refresh_token == "publisher-refresh"
    assert channel.token_expires_at > timezone.now() + timedelta(minutes=119)
    publisher.refresh_token.assert_called_once_with("health-refresh" if refresh else "fictional-refresh")


def test_deletion_pending_organization_cannot_recreate_youtube_connections(channel, user):
    from django.core.exceptions import PermissionDenied

    org = channel.workspace.organization
    org.deletion_requested_at = timezone.now()
    org.save(update_fields=["deletion_requested_at"])
    with pytest.raises(PermissionDenied):
        _create_or_update_account(
            workspace_id=channel.workspace_id,
            platform="youtube",
            profile=AccountProfile(platform_id="new-channel", name="New"),
            access_token="new",
            authorizing_user=user,
        )
    assert not SocialAccount.objects.filter(account_platform_id="new-channel").exists()


def test_staging_gate_prevents_automatic_retention_cleanup(channel):
    old = video(channel)
    message = comment(channel, refreshed=timezone.now() - timedelta(days=29))
    check_connection(channel, provider=provider_for(channel), enforce=False)
    assert PlatformPost.objects.filter(pk=old.pk).exists()
    assert InboxMessage.objects.filter(pk=message.pk).exists()


def test_latest_lifetime_statistic_survives_history_expiry_only_for_verified_video(channel):
    old = video(channel, age=400)
    now = timezone.now()
    current = PostInsightsSnapshot.objects.create(
        platform_post=old, metric_key="watch_time", date=now.date() - timedelta(days=190), value=240
    )
    previous = PostInsightsSnapshot.objects.create(
        platform_post=old, metric_key="watch_time", date=now.date() - timedelta(days=191), value=230
    )
    provider = provider_for(channel)
    provider.get_post_metrics_batch.return_value = {"old-video": PostMetrics(extra={"reported_metrics": {"views": 2}})}
    check_connection(channel, provider=provider, now=now)
    assert PostInsightsSnapshot.objects.filter(pk=current.pk).exists()
    assert not PostInsightsSnapshot.objects.filter(pk=previous.pk).exists()
    provider.get_post_metrics_batch.return_value = {}
    check_connection(channel, provider=provider, now=now)
    assert not PostInsightsSnapshot.objects.filter(pk=current.pk).exists()


def test_legacy_copy_ages_use_successful_retrieval_not_publication_or_migration(channel):
    now = timezone.now()
    message = comment(channel)
    InboxMessage.objects.filter(pk=message.pk).update(created_at=now - timedelta(days=29), received_at=now)
    SocialAccount.objects.filter(pk=channel.pk).update(connected_at=now - timedelta(days=29))
    provider = provider_for(channel)
    provider.get_profile.side_effect = APIError("network", status_code=503)
    check_connection(channel, provider=provider, now=now)
    assert not InboxMessage.objects.filter(pk=message.pk).exists()
    channel.refresh_from_db()
    assert channel.account_name == ""
    assert channel.oauth_refresh_token == "fictional-refresh"


def test_recent_legacy_statistics_retrieval_survives_old_migration_clock(channel):
    now = timezone.now()
    old = video(channel, age=400)
    SocialAccount.objects.filter(pk=channel.pk).update(
        youtube_authorization_checked_at=now,
        youtube_verification_started_at=now - timedelta(days=30),
    )
    PostInsightsSnapshot.objects.create(platform_post=old, metric_key="views", date=now.date(), value=2)
    provider = provider_for(channel)
    provider.get_profile.side_effect = APIError("network", status_code=503)
    check_connection(channel, provider=provider, now=now)
    assert PlatformPost.objects.filter(pk=old.pk).exists()


def test_upload_response_copies_and_old_logs_are_removed_without_losing_authored_settings(channel, user):
    from apps.publisher.models import PublishLog

    now = timezone.now()
    old = video(channel)
    old.platform_extra = {"privacy_status": "private", "tags": ["authored"], "snippet": {"title": "API copy"}}
    old.save(update_fields=["platform_extra"])
    log = PublishLog.objects.create(platform_post=old, response_body="API copy")
    PublishLog.objects.filter(pk=log.pk).update(created_at=now - timedelta(days=29))
    notice = Notification.objects.create(
        user=user, event_type="post_failed", title="API error", data={"platform_post_id": str(old.pk)}
    )
    Notification.objects.filter(pk=notice.pk).update(created_at=now - timedelta(days=29))
    provider = provider_for(channel)
    provider.get_post_metrics_batch.return_value = {"old-video": PostMetrics()}
    check_connection(channel, provider=provider, now=now)
    old.refresh_from_db()
    assert old.platform_extra == {"privacy_status": "private", "tags": ["authored"]}
    assert not PublishLog.objects.filter(pk=log.pk).exists()
    assert not Notification.objects.filter(pk=notice.pk).exists()


def test_project_inventory_records_resolution_without_disclosing_credentials(channel, settings):
    from apps.credentials.models import PlatformCredential

    settings.PLATFORM_CREDENTIALS_FROM_ENV = {
        "youtube": {"client_id": "594155589966-fictional.apps.googleusercontent.com", "client_secret": "env-secret"}
    }
    settings.GOOGLE_AUTH_CLIENT_ID = "123456-login.apps.googleusercontent.com"
    PlatformCredential.objects.create(
        organization=channel.workspace.organization,
        platform="youtube",
        credentials={"client_id": "987654-override.apps.googleusercontent.com", "client_secret": "org-secret"},
    )
    output = StringIO()
    call_command("youtube_project_inventory", environment="fixture staging", stdout=output)
    serialized = output.getvalue()
    assert "env-secret" not in serialized and "org-secret" not in serialized
    assert "fictional.apps.googleusercontent.com" not in serialized
    inventory = json.loads(serialized)
    assert inventory["runtime"][0]["candidate_project_number"] == "594155589966"
    assert inventory["runtime"][0]["project_number"] is None
    resolved = next(row for row in inventory["runtime"] if "organization_id" in row)
    assert resolved["organization_override_present"] is True
    assert resolved["organization_override_active"] is False
    assert resolved["credential_fingerprint"] == inventory["runtime"][0]["credential_fingerprint"]
    assert inventory["organization_overrides"][0]["candidate_project_number"] == "987654"
    assert inventory["organization_overrides"][0]["active"] is False


def test_clones_versions_and_purge_preserve_authored_content_without_api_payload_copies(channel, user):
    from apps.composer.models import PostVersion
    from apps.composer.services import clone_post
    from apps.composer.views import _save_version

    old = video(channel)
    old.platform_extra = {"privacy_status": "private", "tags": ["authored"], "snippet": {"title": "API copy"}}
    old.save(update_fields=["platform_extra"])
    other = SocialAccount.objects.create(
        workspace=channel.workspace, platform="instagram_login", account_platform_id="history-other"
    )
    historic = PostVersion.objects.create(
        post=old.post,
        version_number=1,
        snapshot={
            "caption": "Authored caption",
            "platform_posts": [
                {"social_account_id": str(channel.pk), "platform_extra": old.platform_extra},
                {"social_account_id": str(other.pk), "platform_extra": {"snippet": "Other platform content"}},
            ],
        },
    )
    cloned = clone_post(old.post)
    assert cloned.platform_posts.get().platform_extra == {"privacy_status": "private", "tags": ["authored"]}
    _save_version(old.post, user)
    assert old.post.versions.get(version_number=2).snapshot["platform_posts"][0]["platform_extra"] == {
        "privacy_status": "private",
        "tags": ["authored"],
    }
    purge_connection(channel)
    historic.refresh_from_db()
    assert historic.snapshot["caption"] == "Authored caption"
    assert historic.snapshot["platform_posts"][0]["platform_extra"] == {
        "privacy_status": "private",
        "tags": ["authored"],
    }
    assert historic.snapshot["platform_posts"][1]["platform_extra"] == {"snippet": "Other platform content"}
    assert Post.objects.filter(pk=cloned.pk).exists()
