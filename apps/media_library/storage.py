"""S3/R2 helpers for presigned direct-to-storage uploads.

Isolates the boto3 / django-storages specifics (presigning, HEAD, range-GET,
delete) behind a small seam so the rest of the media-library code — and the
tests — never import boto3 directly. The four object-level functions
(:func:`presign_upload`, :func:`head_object_size`, :func:`read_object_head_bytes`,
:func:`delete_object`) are the monkeypatch points the test suite swaps in for a
live bucket.
"""

from __future__ import annotations

import uuid

from django.core.files.storage import default_storage
from django.utils import timezone

from .validators import ALL_ALLOWED_EXTENSIONS


def is_s3_backend() -> bool:
    """True when ``default_storage`` is the S3/R2 backend (presigning works).

    Detected by module path rather than ``isinstance`` so we never import the
    S3 backend (and transitively boto3) on local-filesystem deployments.
    """
    return type(default_storage).__module__.startswith("storages.backends.s3")


def _client_and_bucket():
    """Return ``(boto3_client, bucket_name)`` for the configured S3/R2 bucket."""
    return default_storage.connection.meta.client, default_storage.bucket_name


def _normalize(storage_key: str) -> str:
    """Apply the backend's LOCATION prefix + ``safe_join`` traversal guard.

    Keeps presign / HEAD / range-GET in agreement on the exact key the object
    actually lives at. Mirrors S3Storage's own ``_normalize_name(clean_name(...))``
    idiom — ``clean_name`` is a module-level helper in django-storages 1.14+
    (the old ``Storage._clean_name`` method was removed), so we import it rather
    than call a backend method that no longer exists.
    """
    from storages.utils import clean_name

    # ``_normalize_name`` lives on the S3 backend (this is only called when
    # ``is_s3_backend()``), not on the base ``Storage`` type mypy infers here.
    return default_storage._normalize_name(clean_name(storage_key))  # type: ignore[attr-defined]


def generate_storage_key(declared_filename: str) -> str:
    """A server-chosen key mirroring ``MediaAsset.file``'s ``upload_to``.

    The basename is a fresh UUID — the agent's filename never reaches the path,
    so it can't traverse directories or collide with another object. The
    extension is copied from the declared name only when it's in our allowlist
    (purely cosmetic; the content is re-sniffed at finalize), else dropped.
    """
    ext = ""
    if "." in declared_filename:
        candidate = declared_filename.rsplit(".", 1)[-1].lower()
        if candidate in ALL_ALLOWED_EXTENSIONS:
            ext = f".{candidate}"
    now = timezone.now()
    return f"media_library/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"


def presign_upload(storage_key: str, *, content_type: str, max_bytes: int, expires_in: int) -> dict:
    """Presigned POST for a single object, size-capped at the edge.

    Returns ``{"method", "url", "fields"}`` — the client submits ``fields`` (which
    includes the object key) verbatim with the binary body. The POST policy pins
    the key and content-type and bounds the body with a ``content-length-range``
    so R2 rejects an oversize or mistyped upload before a byte lands in the bucket.
    """
    client, bucket = _client_and_bucket()
    presigned = client.generate_presigned_post(
        Bucket=bucket,
        Key=_normalize(storage_key),
        Fields={"Content-Type": content_type},
        Conditions=[
            ["content-length-range", 1, int(max_bytes)],
            ["eq", "$Content-Type", content_type],
        ],
        ExpiresIn=int(expires_in),
    )
    return {
        "method": "POST",
        "url": presigned["url"],
        "fields": presigned["fields"],
    }


def head_object_size(storage_key: str) -> int | None:
    """ContentLength of the stored object, or ``None`` if it doesn't exist.

    ``None`` means the agent never completed the upload — the caller turns that
    into a clear "upload not found" error.
    """
    from botocore.exceptions import ClientError

    client, bucket = _client_and_bucket()
    try:
        resp = client.head_object(Bucket=bucket, Key=_normalize(storage_key))
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return int(resp["ContentLength"])


def read_object_head_bytes(storage_key: str, n: int = 32) -> bytes:
    """Range-GET the first ``n`` bytes for server-side magic-byte sniffing."""
    client, bucket = _client_and_bucket()
    resp = client.get_object(Bucket=bucket, Key=_normalize(storage_key), Range=f"bytes=0-{n - 1}")
    return resp["Body"].read()


def delete_object(storage_key: str) -> None:
    """Best-effort delete of an orphaned object (rejected or expired upload).

    Delegates to ``default_storage`` so the same key normalization applies.
    """
    default_storage.delete(storage_key)
