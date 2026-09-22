"""S3/R2 helpers for presigned direct-to-storage uploads.

Isolates the boto3 / django-storages specifics (presigning, HEAD, range-GET,
delete, download) behind a small seam so the rest of the media-library code —
and the tests — never import boto3 directly. The object-level functions
(:func:`presign_upload`, :func:`head_object_size`, :func:`read_object_head_bytes`,
:func:`download_to_path`, :func:`open_object_range`, :func:`delete_object`) are
the monkeypatch points the test suite swaps in for a live bucket.
"""

from __future__ import annotations

import shutil
import threading
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from .validators import ALL_ALLOWED_EXTENSIONS

# Copy buffer for the local-filesystem branch of ``download_to_path``. Sized to
# match boto3's own transfer chunk so both branches behave alike.
_COPY_CHUNK_SIZE = 1024 * 1024

# One boto3 client for the whole process. See ``_client_and_bucket``.
_client_lock = threading.Lock()
_cached_client = None


def is_s3_backend() -> bool:
    """True when ``default_storage`` is the S3/R2 backend (presigning works).

    Detected by module path rather than ``isinstance`` so we never import the
    S3 backend (and transitively boto3) on local-filesystem deployments.

    ``__class__`` rather than ``type()``: ``default_storage`` is a ``LazyObject``,
    and ``type()`` sees straight through to the ``DefaultStorage`` wrapper —
    ``django.core.files.storage`` — no matter which backend is configured. Only
    ``__class__`` is proxied to the real backend. This returned False on every
    S3 deployment until it was fixed, which silently disabled the MCP presigned
    upload tools and the media proxy's range-GET path.
    """
    return default_storage.__class__.__module__.startswith("storages.backends.s3")


# Cloudflare R2 does not implement S3's POST Object API — a presigned POST
# answers 501 Not Implemented (verified against a live R2 bucket; presigned PUT
# to the same bucket answers 200). R2 is this project's default object store,
# so "S3-compatible" is not enough to assume presigned POST works.
_NO_PRESIGNED_POST_ENDPOINTS = ("r2.cloudflarestorage.com",)


def supports_presigned_post() -> bool:
    """Whether the configured bucket implements S3's POST Object API.

    Separate from :func:`is_s3_backend` on purpose. Handing an agent a presigned
    POST that the bucket answers 501 to is worse than refusing up front, so the
    MCP upload tools gate on this rather than on "is it S3".

    Overridable with ``MEDIA_LIBRARY_PRESIGNED_POST_SUPPORTED`` for S3-compatible
    stores this heuristic doesn't know about.
    """
    if not is_s3_backend():
        return False
    override = getattr(settings, "MEDIA_LIBRARY_PRESIGNED_POST_SUPPORTED", None)
    if override is not None:
        return bool(override)
    endpoint = (getattr(settings, "AWS_S3_ENDPOINT_URL", "") or "").lower()
    return not any(host in endpoint for host in _NO_PRESIGNED_POST_ENDPOINTS)


def _client_and_bucket():
    """Return ``(boto3_client, bucket_name)`` for the configured S3/R2 bucket.

    The client is memoized for the life of the process, which is the whole
    point of this function. ``default_storage.connection`` is backed by a
    ``threading.local()`` in django-storages, so reaching through it builds a
    fresh ``boto3.Session()`` and ``session.resource()`` on *every thread* that
    touches storage — and a fresh session means botocore re-parsing the S3
    service model and endpoint ruleset, several MB of Python dicts each time.
    The publisher creates a new ThreadPoolExecutor every 15-second cycle
    (``apps.publisher.engine``) and boto3's own managed transfer adds ten more
    threads per download, so the worker was building and discarding those
    clients all day into an allocator that never hands the pages back.

    Safe to share: boto3 *clients* are documented thread-safe (resources are
    not), and every caller here uses client methods only. Credential refresh is
    handled inside the client.
    """
    global _cached_client

    bucket = default_storage.bucket_name
    client = _cached_client
    if client is None:
        with _client_lock:
            # Re-check under the lock: two threads can race the None test.
            if _cached_client is None:
                _cached_client = default_storage.connection.meta.client
            client = _cached_client
    return client, bucket


def reset_cached_client() -> None:
    """Drop the memoized client so the next call rebuilds it.

    For tests: without it the first one to touch S3 pins its client for the
    rest of the run and every later ``override_settings`` on a bucket, endpoint
    or credential is silently ignored. An autouse fixture in ``conftest.py``
    calls this between tests.

    Deliberately not wired to the ``setting_changed`` signal. That put a
    global receiver in every web and worker process to serve a concern that
    only exists under ``override_settings``, matched setting names by string
    prefix (so a new storage setting would silently stop resetting), and could
    fire *during* a call — ``_client_and_bucket`` reads the cache before taking
    the lock, so a concurrent reset could be missed and a stale client
    returned. Called explicitly between tests, none of that applies.
    """
    global _cached_client

    with _client_lock:
        _cached_client = None


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


def download_to_path(file_field, dest_path: str) -> None:
    """Stream a stored object to ``dest_path`` without buffering it in memory.

    The obvious ``for chunk in file_field.chunks()`` spelling does NOT do this:
    django-storages materializes the entire object into its spool before the
    first chunk is yielded, so the chunk loop only ever paginates a buffer that
    is already fully resident. ``AWS_S3_MAX_MEMORY_SIZE`` keeps that spool on
    disk, but it is still a needless second copy — boto3's managed transfer
    writes straight to the destination file.

    Falls back to a plain copy on local-filesystem deployments, where
    ``file_field.open()`` is just an ``open()`` and nothing is buffered.
    """
    with open(dest_path, "wb") as dest:
        if is_s3_backend():
            client, bucket = _client_and_bucket()
            client.download_fileobj(bucket, _normalize(file_field.name), dest)
            return
        with file_field.open("rb") as src:
            shutil.copyfileobj(src, dest, _COPY_CHUNK_SIZE)


def open_object_range(storage_key: str, start: int | None = None, end: int | None = None):
    """Range-GET an object and return boto3's streaming ``Body``.

    ``start``/``end`` are inclusive byte offsets, matching the HTTP Range header
    (omit both for the whole object). The caller owns the returned stream and
    must close it. Used by the media proxy so serving a 64 KiB window costs a
    64 KiB read instead of downloading the whole video.

    Raises ``FileNotFoundError`` when the object is gone — a stdlib exception so
    callers don't have to import botocore to tell "missing" from "broken", which
    is the whole point of this module.
    """
    from botocore.exceptions import ClientError

    client, bucket = _client_and_bucket()
    params = {"Bucket": bucket, "Key": _normalize(storage_key)}
    if start is not None:
        params["Range"] = f"bytes={start}-{'' if end is None else end}"
    try:
        return client.get_object(**params)["Body"]
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchKey", "NotFound"):
            raise FileNotFoundError(storage_key) from exc
        raise


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
