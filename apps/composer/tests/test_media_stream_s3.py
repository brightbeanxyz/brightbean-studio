"""Coverage for ``media_stream``'s object-storage branch.

The suite runs on local filesystem storage (``config.settings.test``), so the
remote path — the only one that runs in production — is otherwise never
executed by any test. These fake the storage seam rather than a live bucket.
"""

import tempfile
from unittest.mock import MagicMock

import pytest
from django.core.files.base import ContentFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.media_library import storage as ml_storage
from apps.media_library.models import MediaAsset
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

PAYLOAD = bytes(range(256)) * 8  # 2 KiB, byte-addressable so slices are exact


class _FakeBody:
    """Stands in for botocore's StreamingBody, recording whether it was closed."""

    def __init__(self, data):
        self.data = data
        self.closed = False

    def iter_chunks(self, chunk_size):
        # Mirrors botocore: a bare generator with no try/finally of its own, so
        # the caller is solely responsible for closing the body.
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i : i + chunk_size]

    def close(self):
        self.closed = True


@pytest.fixture
def media_root():
    with tempfile.TemporaryDirectory() as path, override_settings(MEDIA_ROOT=path):
        yield path


@pytest.fixture
def asset(db, media_root):
    org = Organization.objects.create(name="O")
    ws = Workspace.objects.create(organization=org, name="W")
    user = User.objects.create_user(
        email="s3-stream@example.com", password="pw", name="S", tos_accepted_at=timezone.now()
    )
    OrgMembership.objects.create(user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER)
    WorkspaceMembership.objects.create(user=user, workspace=ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER)
    a = MediaAsset.objects.create(
        organization=org,
        workspace=ws,
        filename="v.mp4",
        media_type="video",
        mime_type="video/mp4",
        file_size=len(PAYLOAD),
        uploaded_by=user,
    )
    a.file.save("v.mp4", ContentFile(PAYLOAD), save=True)
    a.workspace_obj, a.user_obj = ws, user
    return a


@pytest.fixture
def remote(monkeypatch):
    """Force the S3 branch and capture the ranges it asks storage for."""
    monkeypatch.setattr(ml_storage, "is_s3_backend", lambda: True)
    calls = []
    bodies = []

    def _open_object_range(key, start=None, end=None):
        calls.append((key, start, end))
        data = PAYLOAD if start is None else PAYLOAD[start : (end + 1) if end is not None else None]
        body = _FakeBody(data)
        bodies.append(body)
        return body

    monkeypatch.setattr(ml_storage, "open_object_range", _open_object_range)
    return MagicMock(calls=calls, bodies=bodies)


def _get(asset, **kwargs):
    client = Client()
    client.force_login(asset.user_obj)
    url = reverse(
        "composer:media_stream",
        kwargs={"workspace_id": asset.workspace_obj.id, "asset_id": asset.id},
    )
    return client.get(url, **kwargs)


def test_range_request_asks_storage_for_exactly_that_window(asset, remote):
    resp = _get(asset, headers={"range": "bytes=100-199"})
    body = b"".join(resp.streaming_content)

    assert resp.status_code == 206
    assert resp["Content-Range"] == f"bytes 100-199/{len(PAYLOAD)}"
    assert body == PAYLOAD[100:200]
    # The point of the change: a 100-byte window costs a 100-byte read, not a
    # full download of the video.
    assert remote.calls == [(asset.file.name, 100, 199)]


def test_suffix_range(asset, remote):
    resp = _get(asset, headers={"range": "bytes=-50"})
    body = b"".join(resp.streaming_content)

    assert resp.status_code == 206
    assert body == PAYLOAD[-50:]


def test_full_request_streams_the_whole_object(asset, remote):
    resp = _get(asset)
    body = b"".join(resp.streaming_content)

    assert resp.status_code == 200
    assert body == PAYLOAD
    assert resp["Content-Length"] == str(len(PAYLOAD))
    assert resp["Accept-Ranges"] == "bytes"


def test_unsatisfiable_range_is_416_and_opens_nothing(asset, remote):
    resp = _get(asset, headers={"range": "bytes=999999-"})

    assert resp.status_code == 416
    assert resp["Content-Range"] == f"bytes */{len(PAYLOAD)}"
    assert remote.calls == []


def test_body_is_closed_when_the_response_closes(asset, remote):
    """An aborted range request must not leak the storage connection.

    botocore's iter_chunks has no try/finally, and Django only closes the
    generator — so without the wrapper the underlying connection is never
    returned to the pool, and a seeking <video> aborts these constantly.
    """
    resp = _get(asset, headers={"range": "bytes=0-9"})
    next(iter(resp.streaming_content))  # start it, then abandon it
    resp.close()

    assert remote.bodies[0].closed is True


def test_body_is_closed_after_a_full_read(asset, remote):
    resp = _get(asset)
    b"".join(resp.streaming_content)
    resp.close()

    assert remote.bodies[0].closed is True


def test_a_vanished_object_is_a_404(asset, monkeypatch, remote):
    def _gone(key, start=None, end=None):
        raise FileNotFoundError(key)

    monkeypatch.setattr(ml_storage, "open_object_range", _gone)

    assert _get(asset).status_code == 404


def test_an_unexpected_error_is_not_masked_as_404(asset, monkeypatch, remote):
    """A bug in this view must reach the logs, not read as 'asset not found'."""

    def _boom(key, start=None, end=None):
        raise RuntimeError("bucket misconfigured")

    monkeypatch.setattr(ml_storage, "open_object_range", _boom)

    with pytest.raises(RuntimeError):
        _get(asset)
