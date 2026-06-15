"""Background tasks for media processing."""

import logging
import tempfile

from background_task import background

from .models import MediaAsset, MediaAssetVersion
from .services import (
    apply_image_edits,
    extract_image_metadata,
    extract_video_metadata,
    generate_image_thumbnail,
    generate_video_thumbnail,
    trim_video,
)

logger = logging.getLogger(__name__)


@background(schedule=0)
def process_media_asset(asset_id):
    """Process a newly uploaded media asset: extract metadata and generate thumbnail."""
    try:
        asset = MediaAsset.objects.get(pk=asset_id)
    except MediaAsset.DoesNotExist:
        logger.warning("MediaAsset %s not found for processing", asset_id)
        return

    asset.processing_status = MediaAsset.ProcessingStatus.PROCESSING
    asset.save(update_fields=["processing_status"])

    try:
        if asset.media_type in (MediaAsset.MediaType.IMAGE, MediaAsset.MediaType.GIF):
            _process_image(asset)
        elif asset.media_type == MediaAsset.MediaType.VIDEO:
            _process_video(asset)
        asset.processing_status = MediaAsset.ProcessingStatus.COMPLETED
        asset.save(update_fields=["processing_status", "width", "height", "duration", "thumbnail", "updated_at"])
    except Exception:
        logger.exception("Failed to process media asset %s", asset_id)
        asset.processing_status = MediaAsset.ProcessingStatus.FAILED
        asset.save(update_fields=["processing_status"])


def _process_image(asset):
    """Extract metadata and generate thumbnail for an image."""
    metadata = extract_image_metadata(asset.file)
    asset.width = metadata.get("width", 0)
    asset.height = metadata.get("height", 0)

    thumbnail = generate_image_thumbnail(asset.file)
    if thumbnail:
        asset.thumbnail.save(f"thumb_{asset.id}.jpg", thumbnail, save=False)


def _process_video(asset):
    """Extract metadata and generate thumbnail for a video."""
    with tempfile.NamedTemporaryFile(suffix=f".{asset.file_extension}", delete=False) as tmp:
        for chunk in asset.file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        metadata = extract_video_metadata(tmp_path)
        asset.width = metadata.get("width", 0)
        asset.height = metadata.get("height", 0)
        if "duration_seconds" in metadata:
            asset.duration = metadata["duration_seconds"]

        thumbnail = generate_video_thumbnail(tmp_path)
        if thumbnail:
            asset.thumbnail.save(f"thumb_{asset.id}.jpg", thumbnail, save=False)
    finally:
        import os

        os.unlink(tmp_path)


@background(schedule=0)
def process_image_edit(version_id, operations):
    """Apply image edits to create a new version file."""
    try:
        version = MediaAssetVersion.objects.select_related("media_asset").get(pk=version_id)
    except MediaAssetVersion.DoesNotExist:
        logger.warning("MediaAssetVersion %s not found", version_id)
        return

    try:
        edited_file, (width, height) = apply_image_edits(version.media_asset.file, operations)

        version.file.save(f"edited_{version.id}.jpg", edited_file, save=False)
        version.width = width
        version.height = height
        version.file_size = edited_file.size if hasattr(edited_file, "size") else len(edited_file.read())
        version.save(update_fields=["file", "width", "height", "file_size"])

        thumbnail = generate_image_thumbnail(version.file)
        if thumbnail:
            version.thumbnail.save(f"thumb_v{version.id}.jpg", thumbnail, save=False)
            version.save(update_fields=["thumbnail"])

        asset = version.media_asset
        asset.width = width
        asset.height = height
        asset.thumbnail = version.thumbnail
        asset.save(update_fields=["width", "height", "thumbnail", "updated_at"])

    except Exception:
        logger.exception("Failed to process image edit for version %s", version_id)


@background(schedule=0)
def process_video_trim(version_id, start_seconds, end_seconds):
    """Trim a video and update the version."""
    try:
        version = MediaAssetVersion.objects.select_related("media_asset").get(pk=version_id)
    except MediaAssetVersion.DoesNotExist:
        logger.warning("MediaAssetVersion %s not found", version_id)
        return

    asset = version.media_asset

    try:
        with tempfile.NamedTemporaryFile(suffix=f".{asset.file_extension}", delete=False) as tmp_in:
            for chunk in asset.file.chunks():
                tmp_in.write(chunk)
            input_path = tmp_in.name

        output_path = f"{input_path}_trimmed.mp4"

        try:
            trim_video(input_path, output_path, start_seconds, end_seconds)

            with open(output_path, "rb") as f:
                from django.core.files.base import ContentFile

                trimmed_file = ContentFile(f.read(), name=f"trimmed_{version.id}.mp4")

            version.file.save(f"trimmed_{version.id}.mp4", trimmed_file, save=False)
            version.duration = end_seconds - start_seconds

            metadata = extract_video_metadata(output_path)
            version.width = metadata.get("width", asset.width)
            version.height = metadata.get("height", asset.height)

            import os

            version.file_size = os.path.getsize(output_path)
            version.save(update_fields=["file", "duration", "width", "height", "file_size"])

            thumbnail = generate_video_thumbnail(output_path)
            if thumbnail:
                version.thumbnail.save(f"thumb_v{version.id}.jpg", thumbnail, save=False)
                version.save(update_fields=["thumbnail"])

            asset.duration = version.duration
            asset.thumbnail = version.thumbnail
            asset.save(update_fields=["duration", "thumbnail", "updated_at"])

        finally:
            import os

            os.unlink(input_path)
            if os.path.exists(output_path):
                os.unlink(output_path)

    except Exception:
        logger.exception("Failed to process video trim for version %s", version_id)


# How often the recurring pending-upload sweep runs; registered on a repeating
# schedule by apps.media_library.apps.MediaLibraryConfig.
PENDING_UPLOAD_SWEEP_INTERVAL_SECONDS = 60 * 60  # hourly


@background(schedule=0)
def sweep_pending_uploads():
    """Delete expired, never-finalized presigned uploads and their objects.

    ``request_media_upload`` presigns a key and writes a ``PendingUpload`` row; if
    the agent never finalizes, the row (and any partially-uploaded object) would
    linger. This reaps anything past its expiry that was never finalized. Object
    deletion is best-effort — the object may never have been uploaded at all.
    """
    import contextlib

    from django.utils import timezone

    from .models import PendingUpload
    from .storage import delete_object

    stale = PendingUpload.objects.filter(finalized_at__isnull=True, expires_at__lt=timezone.now())
    for pending in stale.iterator():
        with contextlib.suppress(Exception):
            delete_object(pending.storage_key)
        pending.delete()
