"""MCP presigned large-upload tools: request_media_upload + finalize_media_upload.

Reuses the OAuth harness from ``test_oauth_auth`` and monkeypatches the
``apps.media_library.storage`` seam (the four object ops + ``is_s3_backend``) so
the flow runs without a live R2 bucket. Test storage is local, so without the
patch the tools correctly refuse — exercised by ``test_*_local_storage``.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.mcp.protocol import INVALID_PARAMS
from apps.mcp.tests.test_oauth_auth import (
    _make_user_with_workspace,
    _mint_oauth_token,
    _post,
    _rpc,
    _SecureClient,
)
from apps.media_library import storage as ml_storage
from apps.media_library import tasks as ml_tasks
from apps.media_library.models import MediaAsset, PendingUpload
from apps.members.models import WorkspaceMembership

MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"

OWNER = WorkspaceMembership.WorkspaceRole.OWNER


def _client(user):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")


def _call(client, name, arguments):
    return _post(client, _rpc("tools/call", {"name": name, "arguments": arguments}))


def _text(body):
    return json.loads(body["result"]["content"][0]["text"])


@pytest.fixture
def s3_seam(monkeypatch):
    """Make the presigned tools behave as if S3/R2 storage is configured."""
    monkeypatch.setattr(ml_storage, "is_s3_backend", lambda: True)
    monkeypatch.setattr(
        ml_storage,
        "presign_upload",
        lambda key, *, content_type, max_bytes, expires_in: {
            "method": "POST",
            "url": "https://r2.example.com/bucket",
            "fields": {"key": key, "Content-Type": content_type},
        },
    )
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: 5_000_000)
    monkeypatch.setattr(ml_storage, "read_object_head_bytes", lambda key, n=32: MP4[:n])
    monkeypatch.setattr(ml_storage, "delete_object", lambda key: None)
    # Record (rather than run) processing enqueues so tests can assert finalize
    # actually queues the background task instead of silently stubbing it out.
    process_calls: list = []
    monkeypatch.setattr(ml_tasks, "process_media_asset", lambda *a, **k: process_calls.append(a[0] if a else None))
    monkeypatch.process_calls = process_calls
    return monkeypatch


def _request_upload(client):
    status, body = _call(
        client,
        "request_media_upload",
        {"filename": "clip.mp4", "media_type": "video", "content_type": "video/mp4"},
    )
    assert status == 200, body
    return _text(body)


@pytest.mark.django_db
class TestRequestMediaUpload:
    def test_returns_presigned_post_and_creates_pending(self, s3_seam):
        user, ws, _sa = _make_user_with_workspace("req-oauth@example.com", OWNER)
        payload = _request_upload(_client(user))

        assert payload["url"]
        assert "fields" in payload
        assert payload["method"] == "POST"
        pending = PendingUpload.objects.get(id=payload["upload_id"])
        assert pending.workspace_id == ws.id
        assert pending.finalized_at is None

    def test_disabled_on_local_storage(self):
        # No s3_seam fixture → is_s3_backend() is the real (local) value.
        user, _ws, _sa = _make_user_with_workspace("req-local@example.com", OWNER)
        _status, body = _call(_client(user), "request_media_upload", {"filename": "clip.mp4", "media_type": "video"})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "local mode" in body["error"]["message"].lower()

    def test_rejects_disallowed_content_type(self, s3_seam):
        # content_type is pinned into the POST policy and becomes the stored
        # object's Content-Type, so a non-allowlisted (e.g. renderable) type is
        # rejected up front rather than failing opaquely at the storage edge.
        user, _ws, _sa = _make_user_with_workspace("ct-oauth@example.com", OWNER)
        _status, body = _call(
            _client(user),
            "request_media_upload",
            {"filename": "x.html", "media_type": "image", "content_type": "text/html"},
        )
        assert body["error"]["code"] == INVALID_PARAMS
        assert "content_type" in body["error"]["message"]


@pytest.mark.django_db
class TestFinalizeMediaUpload:
    def test_happy_path_registers_asset_in_oauth_workspace(self, s3_seam):
        user, ws, _sa = _make_user_with_workspace("fin-oauth@example.com", OWNER)
        client = _client(user)
        upload_id = _request_upload(client)["upload_id"]

        status, body = _call(client, "finalize_media_upload", {"upload_id": upload_id})
        assert status == 200
        assert body["result"]["isError"] is False
        media = _text(body)
        assert media["media_type"] == "video"
        assert media["workspace_id"] == str(ws.id)
        assert media["processing_status"] == "pending"

        asset = MediaAsset.objects.get(id=media["id"])
        assert asset.workspace_id == ws.id
        assert asset.file.name  # points at the stored key
        # finalize must enqueue background processing exactly once for the asset.
        assert s3_seam.process_calls == [media["id"]]

    def test_cross_tenant_upload_id_is_not_found(self, s3_seam):
        user_a, _ws_a, _sa_a = _make_user_with_workspace("ten-a@example.com", OWNER)
        user_b, _ws_b, _sa_b = _make_user_with_workspace("ten-b@example.com", OWNER)
        upload_id = _request_upload(_client(user_a))["upload_id"]

        _status, body = _call(_client(user_b), "finalize_media_upload", {"upload_id": upload_id})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "not found" in body["error"]["message"].lower()
        # A's pending row is untouched; no asset was created for B.
        assert not MediaAsset.objects.exists()

    def test_finalize_is_idempotent(self, s3_seam):
        user, _ws, _sa = _make_user_with_workspace("idem-oauth@example.com", OWNER)
        client = _client(user)
        upload_id = _request_upload(client)["upload_id"]

        _s1, b1 = _call(client, "finalize_media_upload", {"upload_id": upload_id})
        _s2, b2 = _call(client, "finalize_media_upload", {"upload_id": upload_id})

        assert _text(b1)["id"] == _text(b2)["id"]
        assert MediaAsset.objects.count() == 1

    def test_expired_upload_rejected(self, s3_seam):
        user, _ws, _sa = _make_user_with_workspace("exp-oauth@example.com", OWNER)
        client = _client(user)
        upload_id = _request_upload(client)["upload_id"]
        PendingUpload.objects.filter(id=upload_id).update(expires_at=timezone.now() - timedelta(seconds=1))

        _status, body = _call(client, "finalize_media_upload", {"upload_id": upload_id})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "expired" in body["error"]["message"].lower()

    def test_missing_object_reports_incomplete_upload(self, s3_seam):
        user, _ws, _sa = _make_user_with_workspace("miss-oauth@example.com", OWNER)
        client = _client(user)
        upload_id = _request_upload(client)["upload_id"]
        # Simulate the agent never completing the PUT.
        s3_seam.setattr(ml_storage, "head_object_size", lambda key: None)

        _status, body = _call(client, "finalize_media_upload", {"upload_id": upload_id})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "not found" in body["error"]["message"].lower()

    def test_finalize_after_asset_deleted_does_not_recreate(self, s3_seam):
        user, _ws, _sa = _make_user_with_workspace("del-oauth@example.com", OWNER)
        client = _client(user)
        upload_id = _request_upload(client)["upload_id"]
        asset_id = _text(_call(client, "finalize_media_upload", {"upload_id": upload_id})[1])["id"]
        # Asset deleted later → PendingUpload.media_asset becomes NULL (SET_NULL).
        MediaAsset.objects.filter(id=asset_id).delete()

        _status, body = _call(client, "finalize_media_upload", {"upload_id": upload_id})
        assert body["error"]["code"] == INVALID_PARAMS
        assert "no longer exists" in body["error"]["message"].lower()
        assert MediaAsset.objects.count() == 0


@pytest.mark.django_db
class TestPresignedEndToEnd:
    def test_upload_then_create_draft_all_over_oauth(self, s3_seam):
        # The headline case: large media uploaded over MCP (no REST shell key)
        # and attached to a draft, all on one OAuth connection → one workspace,
        # so create_post's workspace-scoped media lookup matches.
        from apps.composer.models import PostMedia

        user, _ws, sa = _make_user_with_workspace("e2e-oauth@example.com", OWNER)
        client = _client(user)

        upload_id = _request_upload(client)["upload_id"]
        _s, fbody = _call(client, "finalize_media_upload", {"upload_id": upload_id})
        asset_id = _text(fbody)["id"]

        status, body = _call(
            client,
            "create_draft",
            {"social_account_id": str(sa.id), "caption": "with video", "media_asset_ids": [asset_id]},
        )
        assert status == 200
        assert body["result"]["isError"] is False
        assert PostMedia.objects.filter(media_asset_id=asset_id).exists()


@pytest.mark.django_db
def test_tools_list_advertises_presigned_tools():
    user, _ws, _sa = _make_user_with_workspace("list-oauth@example.com", OWNER)
    _status, body = _post(_client(user), _rpc("tools/list"))
    names = {t["name"] for t in body["result"]["tools"]}
    assert {"request_media_upload", "finalize_media_upload"} <= names
