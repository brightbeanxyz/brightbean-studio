"""Mastodon accepts media before processing it; acceptance is not readiness."""

from copy import deepcopy
from unittest.mock import Mock

import httpx
import pytest

from providers.exceptions import APIError
from providers.mastodon import MastodonProvider
from providers.types import PostType, PublishContent, PublishContext


def response(status, payload=None):
    return httpx.Response(status, json=payload) if payload is not None else httpx.Response(status)


@pytest.fixture
def provider():
    return MastodonProvider({"instance_url": "https://masto.example"})


def content_with_context(tmp_path, *, count=1):
    paths = []
    for index in range(count):
        path = tmp_path / f"media-{index}.mp4"
        path.write_bytes(b"streamed-media")
        paths.append(str(path))
    stored = []
    context = PublishContext(
        checkpoint={
            "attempt_id": "attempt-one",
            "phase": "uploading",
            "params": {"status": "hello", "visibility": "public"},
            "media": [{"source": str(i), "media_id": "", "ready": False} for i in range(count)],
        },
        save_checkpoint=lambda checkpoint: stored.append(deepcopy(checkpoint)),
    )
    return PublishContent(text="hello", media_files=paths, publish_context=context), context, stored


def test_text_only_publishes_with_idempotency_key(provider, monkeypatch):
    request = Mock(return_value=response(200, {"id": "status-1", "url": "https://masto.example/@me/1"}))
    monkeypatch.setattr(provider, "_request", request)
    result = provider.publish_post("token", PublishContent(text="hello"))
    assert result.platform_post_id == "status-1"
    assert result.deferred is False
    assert request.call_args.kwargs["data"] == {"status": "hello", "visibility": "public"}
    assert request.call_args.kwargs["headers"]["Idempotency-Key"].startswith("studio-mastodon-")


def test_ready_image_publishes_without_a_readiness_request(provider, tmp_path, monkeypatch):
    content, context, stored = content_with_context(tmp_path)
    request = Mock(side_effect=[response(200, {"id": "media-1", "url": "ready"}), response(200, {"id": "status-1"})])
    monkeypatch.setattr(provider, "_request", request)
    result = provider.publish_post("token", content)
    assert result.platform_post_id == "status-1"
    assert all(call.args[0] == "POST" for call in request.call_args_list)
    assert request.call_args.kwargs["data"]["media_ids[]"] == ["media-1"]
    assert any(row["media"][0]["media_id"] == "media-1" for row in stored[:-1])
    assert context.checkpoint["status_id"] == "status-1"


def test_video_yields_on_202_and_empty_206_then_publishes(provider, tmp_path, monkeypatch):
    content, context, stored = content_with_context(tmp_path)
    request = Mock(
        side_effect=[
            response(202, {"id": "media-1", "url": None, "preview_url": "thumbnail"}),
            response(206),
            response(200, {"id": "media-1", "url": "ready"}),
            response(200, {"id": "status-1"}),
        ]
    )
    monkeypatch.setattr(provider, "_request", request)
    assert provider.publish_post("token", content).deferred is True
    assert context.checkpoint["phase"] == "processing"
    assert provider.resume_publish("token", context).deferred is True
    assert provider.resume_publish("token", context).platform_post_id == "status-1"
    assert [call.args[0] for call in request.call_args_list] == ["POST", "GET", "GET", "POST"]
    assert stored[-1]["phase"] == "complete"


@pytest.mark.parametrize("status", [200, 202])
def test_null_url_is_pending_even_with_a_thumbnail(provider, tmp_path, monkeypatch, status):
    content, context, _ = content_with_context(tmp_path)
    monkeypatch.setattr(
        provider,
        "_request",
        Mock(return_value=response(status, {"id": "media-1", "url": None, "preview_url": "preview"})),
    )
    assert provider.publish_post("token", content).deferred is True
    assert context.checkpoint["media"][0]["ready"] is False


def test_multiple_attachments_skip_already_ready_media(provider, tmp_path, monkeypatch):
    content, context, _ = content_with_context(tmp_path, count=2)
    request = Mock(
        side_effect=[
            response(200, {"id": "image", "url": "ready"}),
            response(202, {"id": "video", "url": None}),
            response(200, {"id": "video", "url": "ready"}),
            response(200, {"id": "status-1"}),
        ]
    )
    monkeypatch.setattr(provider, "_request", request)
    assert provider.publish_post("token", content).deferred is True
    provider.resume_publish("token", context)
    assert request.call_args_list[2].args[1].endswith("/api/v1/media/video")
    assert request.call_args.kwargs["data"]["media_ids[]"] == ["image", "video"]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 415, 422])
def test_permanent_readiness_errors_do_not_trigger_new_uploads(provider, tmp_path, monkeypatch, status):
    content, context, _ = content_with_context(tmp_path)
    context.checkpoint["phase"] = "processing"
    context.checkpoint["media"][0]["media_id"] = "accepted"
    request = Mock(side_effect=APIError("not usable", status_code=status))
    monkeypatch.setattr(provider, "_request", request)
    with pytest.raises(APIError) as error:
        provider.resume_publish("token", context)
    assert error.value.retryable is False
    assert request.call_args.args[0] == "GET"


def test_processing_rejection_returns_to_checks_with_same_media(provider, tmp_path, monkeypatch):
    content, context, _ = content_with_context(tmp_path)
    error = APIError(
        "processing",
        status_code=422,
        raw_response={"error": "Cannot attach files that have not finished processing. Try again in a moment!"},
    )
    request = Mock(side_effect=[response(200, {"id": "media", "url": "ready"}), error])
    monkeypatch.setattr(provider, "_request", request)
    assert provider.publish_post("token", content).deferred is True
    assert context.checkpoint["phase"] == "processing"
    assert context.checkpoint["media"][0] == {"source": "0", "media_id": "media", "ready": False}
    assert "first_submission_at" not in context.checkpoint


def test_completed_checkpoint_does_not_make_another_request(provider, monkeypatch):
    context = PublishContext({"status_id": "status-1", "phase": "complete"}, Mock())
    request = Mock()
    monkeypatch.setattr(provider, "_request", request)
    assert provider.resume_publish("token", context).platform_post_id == "status-1"
    request.assert_not_called()


def test_budget_exhaustion_yields_without_posting(provider, tmp_path, monkeypatch):
    content, context, _ = content_with_context(tmp_path)
    context.checkpoint["phase"] = "processing"
    context.checkpoint["media"][0]["media_id"] = "accepted"
    context.deadline = 10
    monkeypatch.setattr("providers.mastodon.time.monotonic", lambda: 10)
    request = Mock()
    monkeypatch.setattr(provider, "_request", request)
    assert provider.resume_publish("token", context).deferred is True
    request.assert_not_called()


def test_status_payload_freezes_authored_fields_only(provider):
    params = provider.status_parameters(
        PublishContent(
            text="hello",
            post_type=PostType.POLL,
            extra={
                "visibility": "unlisted",
                "spoiler_text": "CW",
                "poll": {"options": ["a", "b"]},
                "runtime_secret": "ignore",
            },
        )
    )
    assert params["visibility"] == "unlisted"
    assert params["spoiler_text"] == "CW"
    assert params["poll[options][]"] == ["a", "b"]
    assert "runtime_secret" not in params
