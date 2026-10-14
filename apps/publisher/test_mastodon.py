"""Durable publishing across worker restarts, races and ambiguous responses."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import Mock

import httpx
import pytest
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.api.schemas import PlatformPostSummary
from apps.composer.models import PlatformPost, Post, PostMedia
from apps.composer.services import clone_post
from apps.media_library.models import MediaAsset
from apps.organizations.models import Organization
from apps.publisher import engine as engine_module
from apps.publisher.engine import PublishEngine
from apps.publisher.mastodon import (
    CONTENT_CHANGED_MESSAGE,
    MEDIA_FAILED_MESSAGE,
    MEDIA_TIMEOUT_MESSAGE,
    LeaseLostError,
    _claim,
)
from apps.publisher.models import PublishLog
from apps.social_accounts.error_messages import (
    PUBLISH_RECONNECT_MESSAGE,
    PUBLISH_REJECTED_MESSAGE,
    PUBLISH_UNCONFIRMED_MESSAGE,
)
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from providers.exceptions import APIError, RateLimitError
from providers.mastodon import MastodonProvider

pytestmark = pytest.mark.django_db(transaction=True)


def response(status, payload=None):
    return httpx.Response(status, json=payload) if payload is not None else httpx.Response(status)


@pytest.fixture
def setup(tmp_path, settings, monkeypatch):
    settings.MEDIA_ROOT = tmp_path
    org = Organization.objects.create(name="Mastodon tests")
    workspace = Workspace.objects.create(organization=org, name="Test")
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="mastodon",
        account_platform_id="account-1",
        account_name="Test",
        instance_url="https://masto.example",
        oauth_access_token="test-token",
    )
    post = Post.objects.create(workspace=workspace, caption="hello")
    pp = PlatformPost.objects.create(post=post, social_account=account, status="publishing")
    provider = MastodonProvider({"instance_url": account.instance_url})
    monkeypatch.setattr(engine_module, "_provider_and_access_token", lambda _: (provider, "test-token"))
    return PublishEngine(), pp, provider, tmp_path


def attach(pp, tmp_path, *, count=1):
    for i in range(count):
        name = f"video-{i}.mp4"
        (tmp_path / name).write_bytes(b"streamed-video")
        asset = MediaAsset.objects.create(
            workspace=pp.post.workspace,
            filename=name,
            file=name,
            media_type="video",
            file_size=14,
        )
        PostMedia.objects.create(post=pp.post, media_asset=asset, position=i)


def due(pp, *, lease_expired=False):
    pp.refresh_from_db()
    checkpoint = pp.publish_checkpoint
    checkpoint["next_check_at"] = (timezone.now() - timedelta(seconds=1)).isoformat()
    if lease_expired and "lease" in checkpoint:
        checkpoint["lease"]["expires_at"] = (timezone.now() - timedelta(seconds=1)).isoformat()
    pp.save(update_fields=["publish_checkpoint"])


def defer_video(setup, monkeypatch):
    engine, pp, provider, tmp_path = setup
    attach(pp, tmp_path)
    request = Mock(return_value=response(202, {"id": "accepted", "url": None}))
    monkeypatch.setattr(provider, "_request", request)
    assert engine._publish_platform_post(pp)["deferred"] is True
    pp.refresh_from_db()
    return request


def test_media_progress_survives_repeated_sweeps_without_uploads_or_downloads(setup, monkeypatch):
    engine, pp, provider, _ = setup
    request = defer_video(setup, monkeypatch)
    assert pp.status == "publishing"
    assert pp.published_at is None
    assert pp.retry_count == 0
    assert pp.platform_post_id == ""
    assert pp.platform_extra == {}
    assert PublishLog.objects.filter(platform_post=pp).count() == 0
    download = Mock(side_effect=AssertionError("accepted media must not download again"))
    monkeypatch.setattr(engine_module, "download_to_path", download)
    request.side_effect = [
        response(206),
        response(200, {"id": "accepted", "url": "ready"}),
        response(200, {"id": "status-1"}),
    ]
    due(pp)
    assert engine.confirm_pending_publishes() == 0
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    pp.refresh_from_db()
    assert pp.status == "published"
    assert pp.published_at is not None
    assert pp.platform_post_id == "status-1"
    assert pp.publish_checkpoint == {}
    assert PublishLog.objects.get(platform_post=pp).status_code == 200
    assert [call.args[0] for call in request.call_args_list] == ["POST", "GET", "GET", "POST"]
    download.assert_not_called()


def test_next_check_is_respected_and_no_sleep_is_used(setup, monkeypatch):
    engine, pp, _, _ = setup
    request = defer_video(setup, monkeypatch)
    monkeypatch.setattr("providers.mastodon.time.sleep", Mock(side_effect=AssertionError("no processing waits")))
    assert engine.confirm_pending_publishes() == 0
    assert request.call_count == 1


def test_remote_requests_are_outside_database_transactions(setup, monkeypatch):
    engine, pp, provider, _ = setup

    def request(*args, **kwargs):
        assert not connection.in_atomic_block
        persisted = PlatformPost.objects.get(pk=pp.pk).publish_checkpoint
        assert persisted["phase"] == "submitting"
        assert persisted["first_submission_at"]
        return response(200, {"id": "status-1"})

    monkeypatch.setattr(provider, "_request", request)
    assert engine._publish_platform_post(pp)["success"] is True


def test_status_validation_failure_does_not_blame_nonexistent_media(setup, monkeypatch):
    engine, pp, provider, _ = setup
    monkeypatch.setattr(provider, "_request", Mock(side_effect=APIError("caption rejected", status_code=422)))
    engine._publish_platform_post(pp)
    pp.refresh_from_db()
    assert pp.publish_error == PUBLISH_REJECTED_MESSAGE


def test_reconnected_token_does_not_fail_an_old_request(setup, monkeypatch):
    engine, pp, provider, _ = setup
    defer_video(setup, monkeypatch)

    def request(*args, **kwargs):
        account = SocialAccount.objects.get(pk=pp.social_account_id)
        account.oauth_access_token = "reconnected-token"
        account.save(update_fields=["oauth_access_token"])
        raise APIError("old token refused", status_code=401)

    monkeypatch.setattr(provider, "_request", request)
    due(pp)
    assert engine.confirm_pending_publishes() == 0
    pp.refresh_from_db()
    assert pp.status == "publishing"
    assert pp.publish_checkpoint["media"][0]["media_id"] == "accepted"


def test_interrupted_partial_upload_reuses_only_accepted_attachments(setup, monkeypatch):
    engine, pp, provider, tmp_path = setup
    attach(pp, tmp_path, count=2)
    request = Mock(side_effect=[response(202, {"id": "first", "url": None}), httpx.ReadTimeout("lost upload")])
    monkeypatch.setattr(provider, "_request", request)
    assert engine._publish_platform_post(pp)["deferred"] is True
    pp.refresh_from_db()
    assert pp.publish_checkpoint["media"][0]["media_id"] == "first"
    assert pp.publish_checkpoint["media"][1]["media_id"] == ""
    original_download = engine_module.download_to_path
    downloaded = []

    def download(field, path):
        downloaded.append(field.name)
        return original_download(field, path)

    monkeypatch.setattr(engine_module, "download_to_path", download)
    request.side_effect = [response(202, {"id": "second", "url": None})]
    due(pp)
    assert engine.confirm_pending_publishes() == 0
    assert downloaded == ["video-1.mp4"]
    pp.refresh_from_db()
    assert [item["media_id"] for item in pp.publish_checkpoint["media"]] == ["first", "second"]


def test_lost_submission_response_reuses_key_and_frozen_payload(setup, monkeypatch):
    engine, pp, provider, _ = setup
    request = Mock(side_effect=[httpx.ReadTimeout("authorization=secret-token"), response(200, {"id": "status-1"})])
    monkeypatch.setattr(provider, "_request", request)
    assert engine._publish_platform_post(pp)["deferred"] is True
    pp.refresh_from_db()
    assert pp.publish_checkpoint["submission_uncertain"] is True
    key = request.call_args.kwargs["headers"]["Idempotency-Key"]
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    assert request.call_args.kwargs["headers"]["Idempotency-Key"] == key
    assert request.call_args_list[0].kwargs["data"] == request.call_args_list[1].kwargs["data"]


def test_interruption_after_remote_creation_finishes_locally(setup, monkeypatch):
    engine, pp, provider, _ = setup
    context = _claim(engine, pp, resume=False)
    assert context is not None
    request = Mock(return_value=response(200, {"id": "status-1"}))
    monkeypatch.setattr(provider, "_request", request)
    # Remote creation and its checkpoint succeed, but terminal persistence is
    # skipped as if the process died. A lease expiry allows the next worker.
    provider.resume_publish("test-token", context)
    due(pp, lease_expired=True)
    assert engine.confirm_pending_publishes() == 1
    assert request.call_count == 1
    pp.refresh_from_db()
    assert pp.status == "published"


def test_unconfirmed_submission_expires_without_reposting(setup, monkeypatch):
    engine, pp, provider, _ = setup
    request = Mock(side_effect=httpx.ReadTimeout("lost response"))
    monkeypatch.setattr(provider, "_request", request)
    engine._publish_platform_post(pp)
    pp.refresh_from_db()
    pp.publish_checkpoint["first_submission_at"] = (timezone.now() - timedelta(minutes=31)).isoformat()
    pp.save(update_fields=["publish_checkpoint"])
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    assert request.call_count == 1
    pp.refresh_from_db()
    assert pp.status == "failed"
    assert pp.publish_error == PUBLISH_UNCONFIRMED_MESSAGE
    assert pp.publish_checkpoint["attempt_id"]


def test_processing_deadline_does_not_move_with_updated_at(setup, monkeypatch):
    engine, pp, _, _ = setup
    request = defer_video(setup, monkeypatch)
    pp.publish_checkpoint["processing_started_at"] = (timezone.now() - timedelta(minutes=31)).isoformat()
    pp.save(update_fields=["publish_checkpoint", "updated_at"])
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    request.assert_called_once()
    pp.refresh_from_db()
    assert pp.publish_error == MEDIA_TIMEOUT_MESSAGE
    assert pp.publish_checkpoint == {}


@pytest.mark.parametrize(
    "status,message",
    [
        (401, PUBLISH_RECONNECT_MESSAGE),
        (403, PUBLISH_RECONNECT_MESSAGE),
        (404, MEDIA_FAILED_MESSAGE),
        (422, MEDIA_FAILED_MESSAGE),
    ],
)
def test_permanent_errors_fail_safely_without_raw_payload(setup, monkeypatch, status, message):
    engine, pp, provider, _ = setup
    defer_video(setup, monkeypatch)
    monkeypatch.setattr(
        provider, "_request", Mock(side_effect=APIError("private-response token=secret", status_code=status))
    )
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    pp.refresh_from_db()
    assert pp.publish_error == message
    assert pp.status == "failed"
    assert "secret" not in PublishLog.objects.get(platform_post=pp).error_message


def test_readiness_transient_errors_preserve_progress_and_do_not_spend_retries(setup, monkeypatch, caplog):
    engine, pp, provider, _ = setup
    defer_video(setup, monkeypatch)
    monkeypatch.setattr(provider, "_request", Mock(side_effect=APIError("access_token=secret", status_code=503)))
    due(pp)
    engine.confirm_pending_publishes()
    pp.refresh_from_db()
    assert pp.status == "publishing"
    assert pp.retry_count == 0
    assert pp.publish_checkpoint["media"][0]["media_id"] == "accepted"
    assert "secret" not in caplog.text


def test_rate_limit_honors_retry_after(setup, monkeypatch):
    engine, pp, provider, _ = setup
    defer_video(setup, monkeypatch)
    monkeypatch.setattr(provider, "_request", Mock(side_effect=RateLimitError("private", retry_after=180)))
    due(pp)
    engine.confirm_pending_publishes()
    pp.refresh_from_db()
    next_check = timezone.datetime.fromisoformat(pp.publish_checkpoint["next_check_at"])
    assert next_check >= timezone.now() + timedelta(seconds=175)
    assert pp.retry_count == 0


def test_active_lease_prevents_a_second_execution(setup):
    engine, pp, _, _ = setup
    first = _claim(engine, pp, resume=False)
    assert first is not None
    assert _claim(engine, pp, resume=False) is None


def test_expired_lease_fences_late_responses(setup):
    engine, pp, _, _ = setup
    first = _claim(engine, pp, resume=False)
    assert first is not None
    due(pp, lease_expired=True)
    second = _claim(engine, pp, resume=True)
    assert second is not None
    with pytest.raises(LeaseLostError):
        first.save()
    pp.refresh_from_db()
    assert pp.publish_checkpoint["lease"]["owner"] == second.checkpoint["lease"]["owner"]


def test_concurrent_claims_allow_one_owner(setup):
    engine, pp, _, _ = setup
    barrier = threading.Barrier(2)

    def claim():
        try:
            current = PlatformPost.objects.select_related("post", "social_account").get(pk=pp.pk)
            barrier.wait(timeout=5)
            return _claim(engine, current, resume=False)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert sum(context is not None for context in results) == 1


def test_manual_rescheduling_clears_checkpoint_and_fences_old_attempt(setup):
    engine, pp, _, _ = setup
    context = _claim(engine, pp, resume=False)
    assert context is not None
    pp.transition_to("scheduled")
    pp.save(update_fields=list(PlatformPost.TRANSITION_FIELDS))
    with pytest.raises(LeaseLostError):
        context.save()
    pp.refresh_from_db()
    assert pp.publish_checkpoint == {}


def test_copy_and_public_schema_exclude_runtime_progress(setup):
    engine, pp, _, _ = setup
    assert _claim(engine, pp, resume=False) is not None
    clone = clone_post(pp.post)
    assert clone.platform_posts.get().publish_checkpoint == {}
    assert "publish_checkpoint" not in PlatformPostSummary.from_platform_post(pp).model_dump()
    assert "test-token" not in json.dumps(pp.publish_checkpoint)


def test_changed_content_cannot_use_old_uploaded_media(setup, monkeypatch):
    engine, pp, _, _ = setup
    request = defer_video(setup, monkeypatch)
    Post.objects.filter(pk=pp.post_id).update(caption="changed")
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    request.assert_called_once()
    pp.refresh_from_db()
    assert pp.publish_error == CONTENT_CHANGED_MESSAGE


def test_local_cleanup_failure_never_resubmits_a_created_status(setup, monkeypatch):
    engine, pp, provider, _ = setup
    request = Mock(return_value=response(200, {"id": "status-1"}))
    monkeypatch.setattr(provider, "_request", request)
    monkeypatch.setattr(engine, "_sync_parent_published_at", Mock(side_effect=RuntimeError("db failure")))
    assert engine._publish_platform_post(pp)["success"] is True
    assert engine.confirm_pending_publishes() == 0
    request.assert_called_once()
    pp.refresh_from_db()
    assert pp.status == "published"


def test_invalid_checkpoint_version_fails_without_remote_calls(setup, monkeypatch):
    engine, pp, provider, _ = setup
    assert _claim(engine, pp, resume=False) is not None
    due(pp, lease_expired=True)
    pp.publish_checkpoint["version"] = 99
    pp.save(update_fields=["publish_checkpoint"])
    request = Mock()
    monkeypatch.setattr(provider, "_request", request)
    assert engine.confirm_pending_publishes() == 1
    request.assert_not_called()
    pp.refresh_from_db()
    assert pp.publish_error == PUBLISH_UNCONFIRMED_MESSAGE


def test_other_platform_publishes_while_mastodon_is_still_processing(setup, monkeypatch):
    engine, pp, provider, _ = setup
    defer_video(setup, monkeypatch)
    monkeypatch.setattr(provider, "_request", Mock(return_value=response(206)))
    account = SocialAccount.objects.create(
        workspace=pp.post.workspace, platform="tiktok", account_platform_id="tt", account_name="TT"
    )
    other = Post.objects.create(
        workspace=pp.post.workspace, caption="other", scheduled_at=timezone.now() - timedelta(seconds=1)
    )
    other_pp = PlatformPost.objects.create(post=other, social_account=account, status="scheduled")
    dispatch = Mock(return_value={"success": True, "platform_post_id": "tt-live", "async_publish": False})
    monkeypatch.setattr(engine, "_dispatch_to_provider", dispatch)
    due(pp)
    assert engine.confirm_pending_publishes() == 0
    assert engine.poll_and_publish() == 1
    other_pp.refresh_from_db()
    pp.refresh_from_db()
    assert other_pp.status == "published"
    assert pp.status == "publishing"


def test_pending_media_does_not_count_as_a_published_post(setup, monkeypatch):
    engine, pp, provider, tmp_path = setup
    attach(pp, tmp_path)
    pp.status = "scheduled"
    pp.scheduled_at = timezone.now() - timedelta(seconds=1)
    pp.save(update_fields=["status", "scheduled_at"])
    monkeypatch.setattr(provider, "_request", Mock(return_value=response(202, {"id": "accepted", "url": None})))
    assert engine.poll_and_publish() == 0
    pp.refresh_from_db()
    assert pp.status == "publishing"


def test_migration_preserves_existing_post_data(setup):
    _, pp, _, _ = setup
    before = [("composer", "0023_platformpost_youtube_video_checked_at")]
    after = [("composer", "0024_platformpost_publish_checkpoint")]
    try:
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        old = executor.loader.project_state(before).apps.get_model("composer", "PlatformPost")
        old.objects.filter(pk=pp.pk).update(publish_error="existing error", retry_count=2)
        executor = MigrationExecutor(connection)
        executor.migrate(after)
        new = executor.loader.project_state(after).apps.get_model("composer", "PlatformPost").objects.get(pk=pp.pk)
        assert new.publish_checkpoint == {}
        assert new.publish_error == "existing error"
        assert new.retry_count == 2
    finally:
        MigrationExecutor(connection).migrate(after)


def test_completion_cleans_queue_updates_parent_and_schedules_first_comment_once(setup, monkeypatch):
    from background_task.models import Task

    from apps.calendar.models import Queue, QueueEntry

    engine, pp, provider, _ = setup
    pp.post.first_comment = "first comment"
    pp.post.save(update_fields=["first_comment"])
    monkeypatch.setattr(SocialAccount, "supports_first_comment", lambda _: True)
    queue = Queue.objects.create(workspace=pp.post.workspace, social_account=pp.social_account, name="test")
    entry = QueueEntry.objects.create(queue=queue, post=pp.post, position=0, assigned_slot_datetime=timezone.now())
    defer_video(setup, monkeypatch)
    monkeypatch.setattr(
        provider,
        "_request",
        Mock(side_effect=[response(200, {"id": "accepted", "url": "ready"}), response(200, {"id": "status-1"})]),
    )
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    assert engine.confirm_pending_publishes() == 0
    pp.refresh_from_db()
    pp.post.refresh_from_db()
    assert pp.post.published_at == pp.published_at
    assert not QueueEntry.objects.filter(pk=entry.pk).exists()
    assert pp.first_comment_status == "pending"
    assert Task.objects.filter(task_name="apps.publisher.engine._post_first_comment_task").count() == 1


def test_retry_after_cannot_extend_processing_deadline(setup, monkeypatch):
    engine, pp, provider, _ = setup
    defer_video(setup, monkeypatch)
    started = timezone.now() - timedelta(minutes=29)
    pp.publish_checkpoint["processing_started_at"] = started.isoformat()
    pp.save(update_fields=["publish_checkpoint"])
    monkeypatch.setattr(provider, "_request", Mock(side_effect=RateLimitError("limited", retry_after=3600)))
    due(pp)
    engine.confirm_pending_publishes()
    pp.refresh_from_db()
    assert timezone.datetime.fromisoformat(pp.publish_checkpoint["next_check_at"]) == started + timedelta(minutes=30)


def test_ambiguous_submission_then_auth_failure_keeps_unknown_outcome(setup, monkeypatch):
    engine, pp, provider, _ = setup
    request = Mock(side_effect=[httpx.ReadTimeout("lost"), APIError("invalid token", status_code=401)])
    monkeypatch.setattr(provider, "_request", request)
    engine._publish_platform_post(pp)
    due(pp)
    assert engine.confirm_pending_publishes() == 1
    pp.refresh_from_db()
    assert pp.publish_error == PUBLISH_UNCONFIRMED_MESSAGE
    assert pp.publish_checkpoint["submission_uncertain"] is True


def test_stale_remote_success_cannot_overwrite_a_rescheduled_post(setup, monkeypatch):
    engine, pp, provider, _ = setup

    def request(*args, **kwargs):
        current = PlatformPost.objects.get(pk=pp.pk)
        current.transition_to("scheduled")
        current.save(update_fields=list(PlatformPost.TRANSITION_FIELDS))
        return response(200, {"id": "obsolete-status"})

    monkeypatch.setattr(provider, "_request", request)
    assert engine._publish_platform_post(pp).get("stale") is True
    pp.refresh_from_db()
    assert pp.status == "scheduled"
    assert pp.platform_post_id == ""
    assert pp.publish_checkpoint == {}


def test_sweep_budget_is_shared_and_next_sweep_advances_other_posts(setup, monkeypatch):
    from apps.publisher import mastodon as mastodon_module

    engine, pp, _, _ = setup
    second_post = Post.objects.create(workspace=pp.post.workspace, caption="second")
    second = PlatformPost.objects.create(post=second_post, social_account=pp.social_account, status="publishing")
    now = timezone.now()
    PlatformPost.objects.filter(pk=pp.pk).update(
        publish_checkpoint={"next_check_at": (now - timedelta(minutes=2)).isoformat()}
    )
    PlatformPost.objects.filter(pk=second.pk).update(
        publish_checkpoint={"next_check_at": (now - timedelta(minutes=1)).isoformat()}
    )
    clock = {"seconds": 0}
    monkeypatch.setattr(engine_module.time, "monotonic", lambda: clock["seconds"])
    handled = []

    def resume(engine, post, **kwargs):
        handled.append(post.pk)
        clock["seconds"] += 10
        PlatformPost.objects.filter(pk=post.pk).update(
            publish_checkpoint={"next_check_at": (now + timedelta(minutes=1)).isoformat()}
        )
        return {"settled": False}

    monkeypatch.setattr(mastodon_module, "publish_mastodon", resume)
    engine.confirm_pending_publishes()
    assert handled == [pp.pk]
    clock["seconds"] = 0
    engine.confirm_pending_publishes()
    assert handled == [pp.pk, second.pk]
