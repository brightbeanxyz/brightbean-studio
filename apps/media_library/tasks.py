"""Background tasks for media processing."""

import logging
import tempfile

from background_task import background
from django.core.files.base import File

from .models import MediaAsset, MediaAssetVersion
from .services import (
    ImageTooLargeError,
    apply_image_edits,
    extract_image_metadata,
    extract_video_metadata,
    generate_image_thumbnail,
    generate_video_thumbnail,
    trim_video,
)
from .storage import download_to_path

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
    except ImageTooLargeError as exc:
        # Determinate, and the user can act on it, so say so at WARNING with the
        # dimensions rather than dumping a traceback. Still FAILED — an asset we
        # cannot thumbnail is not a processed asset. Keep the dimensions we did
        # read, so the library can show what was wrong with it.
        logger.warning("Media asset %s rejected: %s", asset_id, exc)
        asset.processing_status = MediaAsset.ProcessingStatus.FAILED
        asset.save(update_fields=["processing_status", "width", "height", "updated_at"])
    except Exception:
        logger.exception("Failed to process media asset %s", asset_id)
        asset.processing_status = MediaAsset.ProcessingStatus.FAILED
        asset.save(update_fields=["processing_status"])


def _process_image(asset):
    """Extract metadata and generate thumbnail for an image.

    ``ImageTooLargeError`` is allowed to propagate to ``process_media_asset``,
    which marks the asset FAILED. Swallowing it left the asset COMPLETED with
    0x0 dimensions and no thumbnail, which reads as "this worked" everywhere
    in the UI.
    """
    metadata = extract_image_metadata(asset.file)
    asset.width = metadata.get("width", 0)
    asset.height = metadata.get("height", 0)

    thumbnail = generate_image_thumbnail(asset.file)
    if thumbnail:
        asset.thumbnail.save(f"thumb_{asset.id}.jpg", thumbnail, save=False)


def _process_video(asset):
    """Extract metadata and generate thumbnail for a video."""
    with tempfile.NamedTemporaryFile(suffix=f".{asset.file_extension}", delete=False) as tmp:
        tmp_path = tmp.name
    download_to_path(asset.file, tmp_path)

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

    # ``create_version`` seeds the row by assigning the asset's own FieldFile,
    # which copies the NAME rather than the bytes — until the edit is written,
    # version.file and asset.file are the same stored object. Remember it so the
    # cleanup below can tell "a file this task generated" from "the shared
    # source", and never delete the latter out from under the asset.
    source_name = version.file.name

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

    except ImageTooLargeError as exc:
        # The version row exists only to hold the edit result — ``create_version``
        # seeds it with a copy of the source file — so a deterministic failure
        # would otherwise leave a version that looks like an unchanged duplicate
        # and will never become anything else. Retrying cannot help: the image is
        # the size it is.
        #
        # ``create_version`` also pointed the asset at this row, and the FK is
        # SET_NULL, so rewind to the version it superseded first. Deleting
        # without that would leave an edited asset with no current version at
        # all, which is a worse state than the one we are cleaning up.
        logger.warning("Image edit for version %s rejected: %s", version_id, exc)
        asset = version.media_asset

        # Django does not delete FileField objects when a row goes, so dropping
        # the version without this strands whatever was already written. It is
        # reachable: ``apply_image_edits`` checks the SOURCE size, so an
        # upscaling resize can succeed and then produce output too large to
        # thumbnail, by which point version.file is already saved.
        if version.thumbnail:
            version.thumbnail.delete(save=False)
        if version.file and version.file.name != source_name:
            version.file.delete(save=False)

        previous = asset.versions.exclude(pk=version.pk).order_by("-version_number").first()
        version.delete()
        asset.current_version = previous
        asset.save(update_fields=["current_version", "updated_at"])
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
            input_path = tmp_in.name
        download_to_path(asset.file, input_path)

        output_path = f"{input_path}_trimmed.mp4"

        try:
            trim_video(input_path, output_path, start_seconds, end_seconds)

            # Wrapped, not read: ContentFile(f.read()) held the whole trimmed
            # video in memory on its way back to storage, which the upload
            # streams from disk perfectly well without.
            with open(output_path, "rb") as f:
                version.file.save(f"trimmed_{version.id}.mp4", File(f, name=f"trimmed_{version.id}.mp4"), save=False)
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


# How often the recurring orphaned-media sweep runs; registered on a repeating
# schedule by apps.media_library.apps.MediaLibraryConfig. Replaces the daily
# docker-compose ``maintenance`` loop so it runs on every deploy target.
ORPHANED_MEDIA_SWEEP_INTERVAL_SECONDS = 24 * 60 * 60  # daily


@background(schedule=0)
def run_orphaned_media_sweep():
    """Delete media assets no longer referenced by any post, idea, or template.

    Wraps ``services.sweep_orphaned_media`` (the same code path as the
    ``cleanup_orphaned_media`` command) so the cleanup runs on the shared
    ``process_tasks`` worker everywhere, not just the VPS maintenance container.
    """
    from .services import sweep_orphaned_media

    # min_age_days falls through to services.ORPHANED_MEDIA_MIN_AGE_DAYS (the
    # single source), matching the management command's default.
    sweep_orphaned_media(log=logger.info)
