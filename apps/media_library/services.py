"""Business logic for media library operations."""

import contextlib
import io
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import connection
from django.db.models import Sum
from django.utils import timezone

from .models import MediaAsset, MediaAssetVersion, MediaFolder
from .validators import validate_file

logger = logging.getLogger(__name__)


class ProtectedAssetError(Exception):
    """Raised when trying to delete an asset referenced by scheduled posts."""

    def __init__(self, referencing_posts=None):
        self.referencing_posts = referencing_posts or []
        super().__init__("Asset is referenced by scheduled posts.")


def check_folder_depth(parent_folder):
    """Validate that adding a child to parent_folder won't exceed 3 levels."""
    if parent_folder is None:
        return 0
    depth = 1
    current = parent_folder
    while current.parent_folder_id:
        depth += 1
        current = current.parent_folder
        if depth >= 3:
            raise ValidationError("Folders cannot be nested more than 3 levels deep.")
    return depth


def create_folder(organization, workspace, name, parent_folder=None):
    """Create a new media folder."""
    if parent_folder:
        check_folder_depth(parent_folder)
    folder = MediaFolder(
        organization=organization,
        workspace=workspace,
        parent_folder=parent_folder,
        name=name,
    )
    folder.full_clean()
    folder.save()
    return folder


def create_asset(
    organization,
    workspace,
    uploaded_file,
    uploaded_by,
    folder=None,
    *,
    alt_text: str = "",
    title: str = "",
    tags: list[str] | None = None,
):
    """Create a new media asset from an uploaded file.

    The stored mime_type is taken from a magic-byte sniff, NOT from the
    client-supplied Content-Type header — defends against attackers uploading
    e.g. an SVG/HTML payload labelled as image/jpeg, which on local-storage
    deployments would be served back with the spoofed type and execute script
    in the viewer's browser.

    The *stored filename* gets the same treatment, because the sniff alone does
    not close that hole: a file whose first bytes are a valid PNG header sails
    through validation, and if it is still named "poc.html" on disk then both
    django.views.static.serve and Caddy's file_server will hand it back as
    text/html. ``filename`` keeps the uploader's name for display; the key on
    disk gets the extension the bytes justify.

    Enforces the org-level storage quota before persisting; raises
    ``StorageQuotaExceededError`` (mapped to HTTP 413 by the API layer) when
    the upload would push usage over the cap.
    """
    from .quotas import enforce_storage_quota
    from .validators import (  # local import to avoid validator import cycle on the test path
        sniff_mime,
        storage_filename,
    )

    file_type, errors = validate_file(uploaded_file)
    if errors:
        raise ValidationError(errors)

    enforce_storage_quota(organization, getattr(uploaded_file, "size", 0) or 0)

    sniffed_mime = sniff_mime(uploaded_file) or ""

    display_name = uploaded_file.name
    uploaded_file.name = storage_filename(display_name, sniffed_mime)

    asset = MediaAsset(
        organization=organization,
        workspace=workspace,
        folder=folder,
        filename=display_name,
        file=uploaded_file,
        media_type=file_type,
        mime_type=sniffed_mime,
        file_size=uploaded_file.size,
        uploaded_by=uploaded_by,
        processing_status=MediaAsset.ProcessingStatus.PENDING,
        alt_text=alt_text or "",
        title=title or "",
        tags=list(tags) if tags else [],
    )
    asset.save()
    return asset


def create_pending_upload(
    *,
    organization,
    workspace,
    created_by,
    declared_filename: str,
    content_type: str,
    requested_media_type: str,
):
    """Choose a server key, presign a direct upload, and persist a PendingUpload.

    Backs the MCP ``request_media_upload`` tool: the agent uploads bytes straight
    to object storage with the returned presigned POST, then calls
    ``finalize_media_upload``. ``max_bytes`` is derived from the requested
    media_type purely to cap the edge POST — it is NOT trusted for the final
    asset, whose real size/type ``inspect_uploaded_object`` re-derives from the
    stored bytes at finalize.

    Returns ``(pending_upload, presigned_dict)``.
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import PendingUpload
    from .storage import generate_storage_key, presign_upload
    from .validators import MAX_FILE_SIZES

    max_bytes = int(MAX_FILE_SIZES.get(requested_media_type, MAX_FILE_SIZES["image"]))
    storage_key = generate_storage_key(declared_filename)
    expires_in = int(getattr(settings, "MEDIA_LIBRARY_PRESIGN_EXPIRE", 900))
    presigned = presign_upload(
        storage_key,
        content_type=content_type or "application/octet-stream",
        max_bytes=max_bytes,
        expires_in=expires_in,
    )
    pending = PendingUpload.objects.create(
        organization=organization,
        workspace=workspace,
        created_by=created_by,
        storage_key=storage_key,
        declared_content_type=content_type or "",
        declared_filename=declared_filename,
        max_bytes=max_bytes,
        expires_at=timezone.now() + timedelta(seconds=expires_in),
    )
    return pending, presigned


class _HeadProbe:
    """File-like over head bytes plus a ``size`` attribute.

    Lets ``validate_file`` — which sniffs via ``read``/``seek`` and size-checks via
    ``.size`` — validate an object whose real size came from a storage HEAD rather
    than a local upload, so the presigned path reuses the exact allowlist + per-type
    size policy as the REST/base64 uploads instead of duplicating it.
    """

    def __init__(self, head: bytes, size: int):
        self._buf = io.BytesIO(head)
        self.size = size

    def read(self, n=-1):
        return self._buf.read(n)

    def seek(self, *args):
        return self._buf.seek(*args)


def inspect_uploaded_object(pending) -> dict:
    """Validate an out-of-band-uploaded object SERVER-SIDE; return its metadata.

    The validation chokepoint for presigned uploads, mirroring ``create_asset``'s
    guarantees for bytes the server never received directly: it re-derives the
    size (HEAD) and the MIME (range-GET + magic-byte sniff) from the stored
    object — never trusting the agent's declared values — runs the same
    ``validate_file`` allowlist + per-type size policy the REST/base64 uploads
    use, and enforces the org storage quota. On any validation/quota failure the
    orphaned object is deleted (best-effort, so the cleanup error can't mask the
    real reason) before re-raising.

    Does NO database writes and acquires no lock, so the caller runs it OUTSIDE
    the finalize transaction — keeping the per-row lock off the remote round-trips.
    Returns ``{"size": int, "media_type": str, "mime": str}``.
    """
    import contextlib

    from .quotas import StorageQuotaExceededError, enforce_storage_quota
    from .storage import delete_object, head_object_size, read_object_head_bytes
    from .validators import sniff_mime

    key = pending.storage_key
    size = head_object_size(key)
    if not size:
        # None → object missing (upload never completed); 0 → empty/incomplete.
        # Guarding 0 here also avoids a 416 InvalidRange on the range-GET below.
        raise FileNotFoundError("Uploaded object not found or empty; the upload may not have completed.")

    try:
        head = read_object_head_bytes(key, 32)
        # Reuse the shared validate_file chokepoint (allowlist + per-type cap) so
        # the presigned path can't drift from REST/base64 uploads. ``.size`` is the
        # real HEAD-derived size, so the cap is enforced on the actual object.
        file_type, errors = validate_file(_HeadProbe(head, size))
        if errors:
            raise ValidationError(errors)
        mime = sniff_mime(io.BytesIO(head)) or ""
        enforce_storage_quota(pending.organization, size)
    except (ValidationError, StorageQuotaExceededError):
        with contextlib.suppress(Exception):
            delete_object(key)
        raise

    return {"size": size, "media_type": file_type, "mime": mime}


def register_uploaded_asset(
    *, pending, inspected, uploaded_by, folder=None, alt_text: str = "", title: str = "", tags=None
):
    """Create a ``MediaAsset`` for an already-stored object from validated metadata.

    ``inspected`` is the dict returned by :func:`inspect_uploaded_object`. This
    does only DB work (no remote I/O), so the caller can wrap it in a short row
    lock. The asset points at the existing key WITHOUT re-uploading: assigning a
    *string* to the FileField leaves it committed, so ``save()`` writes only the
    path column — ``storage.save()`` (a re-upload of bytes) is never called.
    """
    asset = MediaAsset(
        organization=pending.organization,
        workspace=pending.workspace,
        folder=folder,
        filename=pending.declared_filename,
        media_type=inspected["media_type"],
        mime_type=inspected["mime"],
        file_size=inspected["size"],
        uploaded_by=uploaded_by,
        processing_status=MediaAsset.ProcessingStatus.PENDING,
        alt_text=alt_text or "",
        title=title or "",
        tags=list(tags) if tags else [],
    )
    asset.file = pending.storage_key
    asset.save()
    return asset


def create_version(asset, file, change_description, created_by):
    """Create a new version of an asset."""
    latest = asset.versions.order_by("-version_number").first()
    next_version = (latest.version_number + 1) if latest else 1

    version = MediaAssetVersion(
        media_asset=asset,
        version_number=next_version,
        file=file,
        change_description=change_description,
        file_size=file.size if hasattr(file, "size") else 0,
        created_by=created_by,
    )
    version.save()

    asset.current_version = version
    asset.save(update_fields=["current_version", "updated_at"])
    return version


def restore_version(asset, version, restored_by):
    """Restore a previous version by creating a new version from its file."""
    new_version = create_version(
        asset=asset,
        file=version.file,
        change_description=f"Restored from version {version.version_number}",
        created_by=restored_by,
    )
    # Update asset's main file and metadata to match restored version
    asset.file = version.file
    asset.thumbnail = version.thumbnail
    asset.file_size = version.file_size
    asset.width = version.width
    asset.height = version.height
    asset.duration = version.duration or 0
    asset.save(
        update_fields=[
            "file",
            "thumbnail",
            "file_size",
            "width",
            "height",
            "duration",
            "updated_at",
        ]
    )
    return new_version


def delete_asset(asset):
    """Delete a media asset, checking for post references first."""
    # Check for post references (placeholder for when posts app exists)
    # When the composer/posts app is built, this will query:
    # PostMedia.objects.filter(media_asset=asset, post__status="scheduled")
    referencing_posts = _check_post_references(asset)
    if referencing_posts:
        raise ProtectedAssetError(referencing_posts)

    # Delete the file and thumbnail from storage
    if asset.file:
        asset.file.delete(save=False)
    if asset.thumbnail:
        asset.thumbnail.delete(save=False)

    # Delete version files
    for version in asset.versions.all():
        if version.file:
            version.file.delete(save=False)
        if version.thumbnail:
            version.thumbnail.delete(save=False)

    asset.delete()


def _check_post_references(asset):
    """Check if an asset is referenced by any scheduled or publishing posts.

    Returns a list of post descriptions if referenced, empty list otherwise.
    """
    from apps.composer.models import PostMedia

    # Status now lives on PlatformPost — a Post is "in flight" if any of its
    # children are scheduled or publishing.
    scheduled_refs = (
        PostMedia.objects.filter(
            media_asset=asset,
            post__platform_posts__status__in=("scheduled", "publishing"),
        )
        .select_related("post")
        .distinct()
    )
    return [{"id": str(ref.post_id), "caption": (ref.post.caption or "")[:80]} for ref in scheduled_refs]


class ImageTooLargeError(Exception):
    """An image would cost more memory to decode than we are willing to spend."""


@contextlib.contextmanager
def open_image(file_path_or_file, *, draft_size=None, enforce_limit=True):
    """Open an image, bound its decode cost, and close it afterwards.

    Every Pillow entry point in this module goes through here, because on a
    512 MB dyno the decode — not the file — is what kills the process. A 20 MB
    upload (``MEDIA_LIBRARY_MAX_IMAGE_SIZE``) says nothing about pixel count,
    and Pillow's own bomb check only *warns* between 1x and 2x its
    ``MAX_IMAGE_PIXELS``, so its default leaves a window that decodes to over
    500 MB.

    ``Image.open`` reads the header only, so both the draft and the guard run
    before a single pixel is decoded.

    ``draft_size`` is the size the caller ultimately wants, and asks the JPEG
    decoder to downscale during the read (DCT scaling at 1/2, 1/4, 1/8). An
    8000x6000 JPEG then decodes at roughly 1000x750, and the guard sees that
    reduced size — the honest measure of what the file costs us. We draft to
    twice the requested size, which is what ``Image.thumbnail`` does with its
    default ``reducing_gap=2.0``, so the later resample has the same source
    data to work with and output quality is unchanged. (``thumbnail`` calls
    ``draft`` itself; the second call is a documented no-op, guarded by
    ``if self.decoderconfig: return None``.)

    ``draft`` is defined on JpegImageFile only and documented as a no-op
    elsewhere, so PNG/WebP/GIF fall through to a full-size check — which is
    right, because those genuinely do decode full-size.

    ``enforce_limit=False`` opens without the ceiling, for callers that only
    read header attributes. ``Image.open`` decodes nothing, so reading
    ``img.size`` off a 500-megapixel file is free — refusing to answer would
    just mean storing 0x0 for an image whose dimensions we are holding.

    Raises ``ImageTooLargeError`` rather than returning None: the caller has to
    tell "this file is too big" from "Pillow could not read this", and the
    media asset needs a real reason to show the user.
    """
    from PIL import Image

    max_pixels = getattr(settings, "MEDIA_LIBRARY_MAX_IMAGE_PIXELS", 30_000_000)
    # Deliberately NOT assigning Image.MAX_IMAGE_PIXELS from that number.
    # Pillow evaluates its own ceiling inside Image.open(), before draft() has
    # had a chance to reduce anything, so pinning it here would reject large
    # JPEGs on their header dimensions — exactly the files draft() makes cheap.
    # Pillow's default stays as the outer backstop; the check below is the
    # operative limit, and it runs on the drafted size.

    if hasattr(file_path_or_file, "seek"):
        file_path_or_file.seek(0)

    try:
        opened = Image.open(file_path_or_file)
    except Image.DecompressionBombError as exc:
        # Pillow's own backstop fired first (above 2x MAX_IMAGE_PIXELS). Speak
        # with one voice so callers only have to handle our exception.
        raise ImageTooLargeError(str(exc)) from exc

    with opened as img:
        if draft_size is not None:
            img.draft("RGB", (draft_size[0] * 2, draft_size[1] * 2))
        pixels = img.width * img.height
        if enforce_limit and pixels > max_pixels:
            raise ImageTooLargeError(
                f"Image is {img.width}x{img.height} ({pixels / 1_000_000:.1f} megapixels); "
                f"the limit is {max_pixels / 1_000_000:g} megapixels."
            )
        yield img


def extract_image_metadata(file_path_or_file):
    """Extract dimensions from an image file using Pillow.

    Deliberately exempt from the pixel ceiling, and not drafted. Reading
    ``img.size`` decodes nothing, so there is no memory to save by refusing —
    and refusing would be actively wrong, since the width and height we would
    withhold are the very numbers the guard just read to make its decision.
    Enforcing here stored 0x0 on assets whose thumbnails generated fine, because
    the thumbnail path drafts the image down and this one does not, so the two
    judged the same file against different pixel counts.
    """
    try:
        with open_image(file_path_or_file, enforce_limit=False) as img:
            width, height = img.size
        return {"width": width, "height": height}
    except Exception:
        logger.exception("Failed to extract image metadata")
        return {}


def generate_image_thumbnail(file_path_or_file):
    """Generate a thumbnail from an image file using Pillow.

    Order matters here, and it used to be wrong. Flattening alpha or converting
    a colour space BEFORE the resize does that work at full resolution — a
    white background allocated at the source's size, then pasted onto, all to
    produce a 400x400 JPEG. Shrinking first makes both operations free.
    Measured on a 6000x4000 RGBA PNG: peak RSS +196 MB before, +104 MB after.

    It also keeps ``thumbnail()``'s own internal ``draft()`` call effective.
    Converting first replaces the JpegImageFile with a plain Image, and the DCT
    downscale is lost with it — which is what made CMYK JPEGs so expensive.
    """
    try:
        from PIL import Image

        thumb_size = getattr(settings, "MEDIA_LIBRARY_THUMBNAIL_SIZE", (400, 400))

        with open_image(file_path_or_file, draft_size=thumb_size) as src:
            # Palette images resample badly — Pillow forces NEAREST on mode "P"
            # — so promote to RGBA first. That is the one conversion worth
            # doing at full size, and it is 4 bytes/px against the 8 the old
            # order cost.
            img = src.convert("RGBA") if src.mode == "P" else src

            img.thumbnail(thumb_size, Image.LANCZOS)

            # Now at thumbnail size, so flattening and converting are free.
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return ContentFile(buffer.getvalue(), name="thumbnail.jpg")
    except ImageTooLargeError:
        # Propagates on purpose, unlike every other failure here. "Too large" is
        # determinate and worth telling the user about, so the caller can fail
        # the asset; returning None would mark it COMPLETED with no thumbnail,
        # no dimensions and nothing on screen to explain either.
        raise
    except Exception:
        logger.exception("Failed to generate image thumbnail")
        return None


def extract_video_metadata(file_path):
    """Extract video metadata using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {}

        import json

        data = json.loads(result.stdout)
        metadata = {}

        # Extract duration from format
        if "format" in data and "duration" in data["format"]:
            metadata["duration_seconds"] = float(data["format"]["duration"])

        # Extract dimensions from video stream
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                metadata["width"] = stream.get("width")
                metadata["height"] = stream.get("height")
                break

        return metadata
    except Exception:
        logger.exception("Failed to extract video metadata")
        return {}


def generate_video_thumbnail(file_path):
    """Generate a thumbnail from a video file using ffmpeg."""
    fd = None
    thumb_path = None
    try:
        fd, thumb_path = tempfile.mkstemp(suffix=".jpg", prefix="brightbean_thumb_")
        # Close the fd immediately - ffmpeg will write to the path directly
        os.close(fd)
        fd = None

        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(file_path),
                "-ss",
                "00:00:01",
                "-vframes",
                "1",
                "-vf",
                "scale=400:-1",
                "-y",
                thumb_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0:
            with open(thumb_path, "rb") as f:
                return ContentFile(f.read(), name="thumbnail.jpg")
        return None
    except Exception:
        logger.exception("Failed to generate video thumbnail")
        return None
    finally:
        # Clean up temp file
        if thumb_path:
            import contextlib

            with contextlib.suppress(OSError):
                os.unlink(thumb_path)


def extract_video_frames(source, timestamps, *, width=160, timeout=None):
    """Extract one JPEG per timestamp from a video using ffmpeg input-seeking.

    ``source`` is a local path or an http(s) URL (ffmpeg seeks remote inputs
    via byte-range requests, so this stays cheap even for object storage).
    Putting ``-ss`` before ``-i`` makes ffmpeg jump to the nearest keyframe
    without decoding the whole file. Returns a list aligned with
    ``timestamps``; entries are JPEG ``bytes`` or ``None`` on failure.
    """
    import contextlib

    per_frame_timeout = timeout or getattr(settings, "MEDIA_LIBRARY_FFMPEG_TIMEOUT", 300)
    frames = []
    for t in timestamps:
        fd, out_path = tempfile.mkstemp(suffix=".jpg", prefix="brightbean_frame_")
        os.close(fd)
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-ss",
                    f"{max(0.0, float(t)):.3f}",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={int(width)}:-1",
                    "-q:v",
                    "5",
                    "-y",
                    out_path,
                ],
                capture_output=True,
                timeout=per_frame_timeout,
            )
            if result.returncode == 0 and os.path.getsize(out_path) > 0:
                with open(out_path, "rb") as f:
                    frames.append(f.read())
            else:
                frames.append(None)
        except Exception:
            logger.exception("Failed to extract video frame at %ss", t)
            frames.append(None)
        finally:
            with contextlib.suppress(OSError):
                os.unlink(out_path)
    return frames


def apply_image_edits(file_path_or_file, operations):
    """Apply image edits (crop, resize, rotate, flip) using Pillow.

    operations: dict with optional keys:
        crop: {x, y, width, height} in pixels
        rotate: degrees (90, 180, 270)
        flip: "horizontal" or "vertical"
        resize: {width, height} in pixels
    """
    from PIL import Image

    # No draft here: crop and rotate operate on the original pixels, so this
    # path genuinely needs full resolution and the guard's full-size check is
    # the right one. ``ImageTooLargeError`` propagates to the caller, which
    # fails the version rather than taking the dyno down with it.
    with open_image(file_path_or_file) as src:
        # Crop first when we have one — every later step then works on a
        # smaller buffer.
        crop = operations.get("crop")
        if crop:
            left = int(crop["x"])
            top = int(crop["y"])
            right = left + int(crop["width"])
            bottom = top + int(crop["height"])
            img = src.crop((left, top, right, bottom))
        else:
            img = src

        # Apply rotation
        rotate = operations.get("rotate")
        if rotate:
            img = img.rotate(-int(rotate), expand=True)

        # Apply flip
        flip = operations.get("flip")
        if flip == "horizontal":
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        elif flip == "vertical":
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        # Apply resize
        resize = operations.get("resize")
        if resize:
            img = img.resize((int(resize["width"]), int(resize["height"])), Image.LANCZOS)

        # Save to buffer. Inside the ``with`` on purpose: when ``operations`` is
        # empty, ``img`` IS the opened image, and leaving the block closes its
        # file pointer before it has ever been loaded.
        if img.mode in ("RGBA", "LA", "P"):
            format_str = "PNG"
            ext = "png"
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            format_str = "JPEG"
            ext = "jpg"

        buffer = io.BytesIO()
        img.save(buffer, format=format_str, quality=90)
        return ContentFile(buffer.getvalue(), name=f"edited.{ext}"), img.size


def trim_video(input_path, output_path, start_seconds, end_seconds):
    """Trim a video using ffmpeg."""
    timeout = getattr(settings, "MEDIA_LIBRARY_FFMPEG_TIMEOUT", 300)
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(input_path),
            "-ss",
            str(start_seconds),
            "-to",
            str(end_seconds),
            "-c",
            "copy",
            "-y",
            str(output_path),
        ],
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg trim failed: {result.stderr.decode()}")


# Minimum asset age (days) the orphaned-media sweep considers — the single source
# shared by the management command's default and the recurring background task.
ORPHANED_MEDIA_MIN_AGE_DAYS = 14


def sweep_orphaned_media(
    *, min_age_days=ORPHANED_MEDIA_MIN_AGE_DAYS, batch_size=100, dry_run=False, log=None, should_continue=None
):
    """Detect and delete media assets not referenced by any post, idea, or template.

    Orphans are ``MediaAsset`` rows older than ``min_age_days`` that no foreign
    key or JSON field points at. Shared by the ``cleanup_orphaned_media``
    management command and the recurring background task so the two never drift.

    Args:
        min_age_days: only consider assets older than this (default 14).
        batch_size: delete in batches of this many.
        dry_run: when True, report candidates without deleting.
        log: optional ``callable(str)`` for progress lines (defaults to the
            module logger at debug level).
        should_continue: optional ``callable() -> bool``; deletion stops early
            when it returns False (lets the command honor SIGINT/SIGTERM).

    Returns a dict: ``{orphaned, deleted, skipped, errors, bytes}``.
    """
    emit = log or (lambda msg: logger.debug("%s", msg))
    keep_going = should_continue or (lambda: True)

    cutoff = timezone.now() - timedelta(days=min_age_days)
    emit(f"Scanning assets older than {min_age_days} days (cutoff: {cutoff:%Y-%m-%d %H:%M})")

    referenced = _fk_referenced_asset_ids() | _json_referenced_asset_ids()
    emit(f"Referenced assets: {len(referenced)}")

    orphaned_qs = MediaAsset.objects.filter(created_at__lt=cutoff).exclude(id__in=referenced)
    orphaned_ids = list(orphaned_qs.values_list("id", flat=True))
    total = len(orphaned_ids)
    total_bytes = orphaned_qs.aggregate(total=Sum("file_size"))["total"] or 0

    result = {"orphaned": total, "deleted": 0, "skipped": 0, "errors": 0, "bytes": total_bytes}

    if total == 0:
        emit("No orphaned assets found.")
        return result

    emit(f"Orphaned candidates: {total} (~{total_bytes / (1024 * 1024):.1f} MB)")

    if dry_run:
        for asset in MediaAsset.objects.filter(id__in=orphaned_ids[:50]):
            emit(
                f"  Would delete: {asset.id} ({asset.filename}, {asset.media_type}, "
                f"{asset.file_size / (1024 * 1024):.1f} MB, created {asset.created_at:%Y-%m-%d})"
            )
        if total > 50:
            emit(f"  ... and {total - 50} more")
        return result

    for i in range(0, total, batch_size):
        if not keep_going():
            emit("Interrupted, stopping...")
            break
        for asset in MediaAsset.objects.filter(id__in=orphaned_ids[i : i + batch_size]):
            if not keep_going():
                break
            try:
                asset_info = f"{asset.id} ({asset.filename})"
                delete_asset(asset)
                result["deleted"] += 1
                emit(f"Deleted: {asset_info}")
            except ProtectedAssetError:
                result["skipped"] += 1
                emit(f"Skipped (protected): {asset.id}")
            except Exception as exc:
                result["errors"] += 1
                emit(f"Error deleting {asset.id}: {exc}")

    emit(
        f"Complete: {result['deleted']} deleted, {result['skipped']} skipped, "
        f"{result['errors']} errors (of {total} orphaned)"
    )
    return result


def _fk_referenced_asset_ids():
    """Collect all asset IDs referenced via foreign keys."""
    from apps.composer.models import Idea, IdeaMedia, PostMedia

    referenced = set()
    referenced.update(PostMedia.objects.values_list("media_asset_id", flat=True))
    referenced.update(IdeaMedia.objects.values_list("media_asset_id", flat=True))
    referenced.update(Idea.objects.filter(media_asset__isnull=False).values_list("media_asset_id", flat=True))
    return referenced


def _json_referenced_asset_ids():
    """Collect all asset IDs embedded in JSON fields."""
    if connection.vendor == "postgresql":
        return _json_referenced_asset_ids_postgres()
    return _json_referenced_asset_ids_python()


def _json_referenced_asset_ids_postgres():
    """Extract asset IDs from JSON fields using PostgreSQL jsonb functions."""
    referenced = set()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT platform_extra->>'thumbnail_asset_id'
            FROM composer_platform_post
            WHERE platform_extra IS NOT NULL
              AND platform_extra->>'thumbnail_asset_id' IS NOT NULL
        """)
        for (val,) in cursor.fetchall():
            referenced.add(_to_uuid(val))

        cursor.execute("""
            SELECT DISTINCT platform_extra->>'cover_image_asset_id'
            FROM composer_platform_post
            WHERE platform_extra IS NOT NULL
              AND platform_extra->>'cover_image_asset_id' IS NOT NULL
        """)
        for (val,) in cursor.fetchall():
            referenced.add(_to_uuid(val))

        cursor.execute("""
            SELECT DISTINCT elem::text
            FROM composer_platform_post,
                 jsonb_array_elements_text(platform_specific_media) AS elem
            WHERE platform_specific_media IS NOT NULL
              AND jsonb_typeof(platform_specific_media) = 'array'
        """)
        for (val,) in cursor.fetchall():
            referenced.add(_to_uuid(val))

        cursor.execute("""
            SELECT DISTINCT elem::text
            FROM composer_post_template,
                 jsonb_array_elements_text(template_data->'media_asset_ids') AS elem
            WHERE template_data IS NOT NULL
              AND template_data ? 'media_asset_ids'
              AND jsonb_typeof(template_data->'media_asset_ids') = 'array'
        """)
        for (val,) in cursor.fetchall():
            referenced.add(_to_uuid(val))

    referenced.discard(None)
    return referenced


def _json_referenced_asset_ids_python():
    """Extract asset IDs from JSON fields by iterating in Python (SQLite fallback)."""
    from apps.composer.models import PlatformPost, PostTemplate

    referenced = set()

    for pp in PlatformPost.objects.exclude(platform_extra=None).only("platform_extra"):
        extra = pp.platform_extra or {}
        if extra.get("thumbnail_asset_id"):
            referenced.add(_to_uuid(extra["thumbnail_asset_id"]))
        if extra.get("cover_image_asset_id"):
            referenced.add(_to_uuid(extra["cover_image_asset_id"]))

    for pp in PlatformPost.objects.exclude(platform_specific_media=None).only("platform_specific_media"):
        if isinstance(pp.platform_specific_media, list):
            for val in pp.platform_specific_media:
                referenced.add(_to_uuid(val))

    for tmpl in PostTemplate.objects.exclude(template_data=None).only("template_data"):
        data = tmpl.template_data or {}
        for val in data.get("media_asset_ids", []):
            referenced.add(_to_uuid(val))

    referenced.discard(None)
    return referenced


def _to_uuid(val):
    """Safely convert a string to UUID, returning None on failure."""
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return None
