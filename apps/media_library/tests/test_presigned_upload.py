"""Service-level tests for the presigned direct-to-storage upload path.

The S3/R2 object operations live behind ``apps.media_library.storage``; here we
monkeypatch that seam so the validation chokepoint (``inspect_uploaded_object``)
and the DB step (``register_uploaded_asset``) can be exercised without a live
bucket. Both import the seam lazily, so patching the module attribute is picked
up at call time.
"""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.media_library import storage as ml_storage
from apps.media_library.models import MediaAsset, PendingUpload
from apps.media_library.quotas import StorageQuotaExceededError
from apps.media_library.services import inspect_uploaded_object, register_uploaded_asset
from apps.media_library.validators import MAX_FILE_SIZES
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace

# Magic-byte heads the sniffer recognises (first 32 bytes are enough).
MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
NOT_MEDIA = b"<html><body>not a media file</body></html>"


def _make_pending(*, filename="clip.mp4"):
    org = Organization.objects.create(name="Org")
    ws = Workspace.objects.create(organization=org, name="WS")
    return PendingUpload.objects.create(
        organization=org,
        workspace=ws,
        created_by=None,
        storage_key=ml_storage.generate_storage_key(filename),
        declared_content_type="video/mp4",
        declared_filename=filename,
        max_bytes=MAX_FILE_SIZES["video"],
        expires_at=timezone.now() + timedelta(seconds=900),
    )


def test_generate_storage_key_is_safe_against_traversal():
    # Filename never reaches the path: a UUID basename, no traversal, no
    # disallowed extension leaks through.
    traversal = ml_storage.generate_storage_key("../../etc/passwd")
    assert traversal.startswith("media_library/")
    assert ".." not in traversal

    double_ext = ml_storage.generate_storage_key("evil.mp4.exe")
    assert not double_ext.endswith(".exe")

    # An allowlisted extension is preserved (cosmetic only).
    assert ml_storage.generate_storage_key("clip.mp4").endswith(".mp4")


def test_normalize_uses_existing_backend_api(monkeypatch):
    # Regression guard: _normalize must NOT call default_storage._clean_name,
    # which was removed in django-storages 1.14 (cleaning is now the module-level
    # storages.utils.clean_name). The fake mirrors the real S3 backend: it has
    # _normalize_name but no _clean_name, so a regression raises AttributeError.
    class _FakeS3Backend:
        def _normalize_name(self, name):
            return f"prefix/{name}"

    monkeypatch.setattr(ml_storage, "default_storage", _FakeS3Backend())
    assert ml_storage._normalize("media_library/2026/06/abc.mp4") == "prefix/media_library/2026/06/abc.mp4"


@pytest.mark.django_db
def test_inspect_then_register_happy_path(monkeypatch):
    pending = _make_pending()
    size = 5_000_000
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: size)
    monkeypatch.setattr(ml_storage, "read_object_head_bytes", lambda key, n=32: MP4[:n])

    inspected = inspect_uploaded_object(pending)
    assert inspected == {"size": size, "media_type": "video", "mime": "video/mp4"}

    asset = register_uploaded_asset(pending=pending, inspected=inspected, uploaded_by=None)
    assert asset.media_type == MediaAsset.MediaType.VIDEO
    assert asset.mime_type == "video/mp4"
    assert asset.file_size == size
    assert asset.processing_status == MediaAsset.ProcessingStatus.PENDING
    # The FileField points at the existing key …
    assert asset.file.name == pending.storage_key
    # … and no bytes were re-uploaded (the key never materialised locally).
    assert not default_storage.exists(pending.storage_key)


@pytest.mark.django_db
def test_inspect_spoofed_content_rejected_and_object_deleted(monkeypatch):
    pending = _make_pending()
    deleted = []
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: 1234)
    monkeypatch.setattr(ml_storage, "read_object_head_bytes", lambda key, n=32: NOT_MEDIA[:n])
    monkeypatch.setattr(ml_storage, "delete_object", lambda key: deleted.append(key))

    with pytest.raises(ValidationError):
        inspect_uploaded_object(pending)

    assert deleted == [pending.storage_key]
    assert not MediaAsset.objects.exists()


@pytest.mark.django_db
def test_inspect_oversize_rejected_and_object_deleted(monkeypatch):
    pending = _make_pending()
    deleted = []
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: MAX_FILE_SIZES["video"] + 1)
    monkeypatch.setattr(ml_storage, "read_object_head_bytes", lambda key, n=32: MP4[:n])
    monkeypatch.setattr(ml_storage, "delete_object", lambda key: deleted.append(key))

    with pytest.raises(ValidationError):
        inspect_uploaded_object(pending)

    assert deleted == [pending.storage_key]


@pytest.mark.django_db
def test_inspect_quota_exceeded_rejected_and_object_deleted(monkeypatch):
    pending = _make_pending()
    deleted = []
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: 5_000_000)
    monkeypatch.setattr(ml_storage, "read_object_head_bytes", lambda key, n=32: MP4[:n])
    monkeypatch.setattr(ml_storage, "delete_object", lambda key: deleted.append(key))

    def _exceeded(org, incoming):
        raise StorageQuotaExceededError(used=10, limit=20, attempted=incoming)

    monkeypatch.setattr("apps.media_library.quotas.enforce_storage_quota", _exceeded)

    with pytest.raises(StorageQuotaExceededError):
        inspect_uploaded_object(pending)

    assert deleted == [pending.storage_key]


@pytest.mark.django_db
def test_inspect_delete_failure_does_not_mask_original_error(monkeypatch):
    # On a rejection the cleanup delete is best-effort; a storage error there
    # must NOT replace the real ValidationError the handler maps to a clean message.
    pending = _make_pending()
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: 1234)
    monkeypatch.setattr(ml_storage, "read_object_head_bytes", lambda key, n=32: NOT_MEDIA[:n])

    def _boom(key):
        raise RuntimeError("R2 unavailable")

    monkeypatch.setattr(ml_storage, "delete_object", _boom)

    with pytest.raises(ValidationError):
        inspect_uploaded_object(pending)


@pytest.mark.django_db
def test_inspect_missing_or_empty_object_raises(monkeypatch):
    pending = _make_pending()

    # Missing object (HEAD 404 → None): the agent never completed the upload.
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: None)
    with pytest.raises(FileNotFoundError):
        inspect_uploaded_object(pending)

    # 0-byte object: treated as incomplete, and guards against a 416 range-GET.
    monkeypatch.setattr(ml_storage, "head_object_size", lambda key: 0)
    with pytest.raises(FileNotFoundError):
        inspect_uploaded_object(pending)

    assert not MediaAsset.objects.exists()
