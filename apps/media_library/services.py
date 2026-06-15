"""Business logic for media library operations."""

import io
import logging
import os
import subprocess
import tempfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

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

    Enforces the org-level storage quota before persisting; raises
    ``StorageQuotaExceededError`` (mapped to HTTP 413 by the API layer) when
    the upload would push usage over the cap.
    """
    from .quotas import enforce_storage_quota
    from .validators import sniff_mime  # local import to avoid validator import cycle on the test path

    file_type, errors = validate_file(uploaded_file)
    if errors:
        raise ValidationError(errors)

    enforce_storage_quota(organization, getattr(uploaded_file, "size", 0) or 0)

    sniffed_mime = sniff_mime(uploaded_file) or ""

    asset = MediaAsset(
        organization=organization,
        workspace=workspace,
        folder=folder,
        filename=uploaded_file.name,
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


def register_uploaded_asset(*, pending, inspected, uploaded_by, folder=None, alt_text: str = "", title: str = "", tags=None):
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


def extract_image_metadata(file_path_or_file):
    """Extract dimensions from an image file using Pillow."""
    try:
        from PIL import Image

        if hasattr(file_path_or_file, "read"):
            file_path_or_file.seek(0)
            img = Image.open(file_path_or_file)
        else:
            img = Image.open(file_path_or_file)
        width, height = img.size
        return {"width": width, "height": height}
    except Exception:
        logger.exception("Failed to extract image metadata")
        return {}


def generate_image_thumbnail(file_path_or_file):
    """Generate a thumbnail from an image file using Pillow."""
    try:
        from PIL import Image

        thumb_size = getattr(settings, "MEDIA_LIBRARY_THUMBNAIL_SIZE", (400, 400))

        if hasattr(file_path_or_file, "read"):
            file_path_or_file.seek(0)
            img = Image.open(file_path_or_file)
        else:
            img = Image.open(file_path_or_file)

        # Convert to RGB if necessary (e.g., RGBA PNGs, CMYK)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        img.thumbnail(thumb_size, Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        return ContentFile(buffer.read(), name="thumbnail.jpg")
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

    if hasattr(file_path_or_file, "read"):
        file_path_or_file.seek(0)
        img = Image.open(file_path_or_file)
    else:
        img = Image.open(file_path_or_file)

    # Apply crop
    crop = operations.get("crop")
    if crop:
        left = int(crop["x"])
        top = int(crop["y"])
        right = left + int(crop["width"])
        bottom = top + int(crop["height"])
        img = img.crop((left, top, right, bottom))

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

    # Save to buffer
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
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"edited.{ext}"), img.size


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
