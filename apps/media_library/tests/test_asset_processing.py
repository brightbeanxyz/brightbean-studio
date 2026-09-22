"""End-to-end coverage for ``process_media_asset``.

The unit tests around the Pillow helpers pass happily while the task built on
them does the wrong thing: an over-limit image used to be saved COMPLETED with
0x0 dimensions and no thumbnail, because both helpers swallowed the failure.
Nothing composed the two calls the way ``_process_image`` does, so nothing
caught it. These tests assert on the asset row, which is what the UI reads.
"""

import io

import pytest
from django.core.files.base import ContentFile
from django.test import override_settings
from PIL import Image

from apps.media_library.models import MediaAsset, MediaAssetVersion
from apps.media_library.tasks import process_media_asset


def _stored_names_containing(fragment):
    """Every stored file under the media library whose name contains ``fragment``.

    Walks rather than guessing a path: the versions directory is date-stamped
    and the storage backend may add a uniqueness suffix.
    """
    from django.core.files.storage import default_storage

    found = []
    pending = ["media_library"]
    while pending:
        current = pending.pop()
        try:
            dirs, files = default_storage.listdir(current)
        except (FileNotFoundError, OSError):
            continue
        pending.extend(f"{current}/{d}" for d in dirs)
        found.extend(f for f in files if fragment in f)
    return found


def _png_bytes(width, height, mode="RGBA"):
    buf = io.BytesIO()
    Image.new(mode, (width, height), (10, 200, 90, 128)[: 4 if mode == "RGBA" else 3]).save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_bytes(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (100, 50, 25)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def asset(db, organization, user):
    from apps.workspaces.models import Workspace

    workspace = Workspace.objects.create(name="Media WS", organization=organization)

    def _make(data, filename="image.png"):
        media = MediaAsset.objects.create(
            organization=organization,
            workspace=workspace,
            uploaded_by=user,
            filename=filename,
            media_type=MediaAsset.MediaType.IMAGE,
            file_size=len(data),
        )
        media.file.save(filename, ContentFile(data), save=True)
        return media

    return _make


@pytest.mark.django_db
def test_normal_image_completes_with_dimensions_and_thumbnail(asset):
    media = asset(_png_bytes(600, 400))

    process_media_asset.now(str(media.id))

    media.refresh_from_db()
    assert media.processing_status == MediaAsset.ProcessingStatus.COMPLETED
    assert (media.width, media.height) == (600, 400)
    assert media.thumbnail


@pytest.mark.django_db
def test_over_limit_image_is_marked_failed_not_completed(asset):
    """The bug: this used to land in COMPLETED with nothing in it."""
    media = asset(_png_bytes(600, 400))

    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
        process_media_asset.now(str(media.id))

    media.refresh_from_db()
    assert media.processing_status == MediaAsset.ProcessingStatus.FAILED
    assert not media.thumbnail


@pytest.mark.django_db
def test_over_limit_image_still_records_the_dimensions_that_caused_it(asset):
    """Keeping these is what lets the library explain the rejection."""
    media = asset(_png_bytes(600, 400))

    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
        process_media_asset.now(str(media.id))

    media.refresh_from_db()
    assert (media.width, media.height) == (600, 400)


@pytest.mark.django_db
def test_large_jpeg_completes_with_real_dimensions_and_a_thumbnail(asset):
    """A 40MP JPEG drafts down cheaply, so it must not be treated as over-limit.

    Regression: metadata judged the header size while the thumbnail judged the
    drafted size, so this combination produced a working thumbnail alongside
    width=0, height=0.
    """
    media = asset(_jpeg_bytes(8000, 5000), filename="big.jpg")

    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=30_000_000):
        process_media_asset.now(str(media.id))

    media.refresh_from_db()
    assert media.processing_status == MediaAsset.ProcessingStatus.COMPLETED
    assert (media.width, media.height) == (8000, 5000)
    assert media.thumbnail


@pytest.mark.django_db
def test_unreadable_file_completes_without_a_thumbnail(asset):
    """Unreadable stays a soft failure, unlike over-limit.

    Only "too large" propagates. "Pillow could not read this" keeps the
    pre-existing best-effort behaviour: the asset completes with no thumbnail
    and zero dimensions. Pinned here so the distinction stays deliberate.
    """
    media = asset(b"this is not an image", filename="broken.png")

    process_media_asset.now(str(media.id))

    media.refresh_from_db()
    assert media.processing_status == MediaAsset.ProcessingStatus.COMPLETED
    assert not media.thumbnail
    assert (media.width, media.height) == (0, 0)


@pytest.mark.django_db
def test_rejected_edit_removes_the_version_and_rewinds_current(asset, user):
    """A failed edit must not leave a version that will never materialize.

    ``create_version`` seeds the row with a copy of the source and points the
    asset at it, so swallowing the failure left what looks like an unchanged
    duplicate version. The asset's ``current_version`` FK is SET_NULL, so the
    rewind matters: deleting without it strands the asset with no current
    version at all.
    """
    from apps.media_library.models import MediaAssetVersion
    from apps.media_library.services import create_version
    from apps.media_library.tasks import process_image_edit

    media = asset(_png_bytes(600, 400))
    first = create_version(asset=media, file=media.file, change_description="v1", created_by=user)
    second = create_version(asset=media, file=media.file, change_description="v2", created_by=user)

    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
        process_image_edit.now(str(second.id), {"rotate": 90})

    media.refresh_from_db()
    assert not MediaAssetVersion.objects.filter(pk=second.pk).exists()
    assert media.current_version_id == first.pk


@pytest.mark.django_db
def test_rejected_edit_on_a_first_version_leaves_no_current(asset, user):
    """Nothing to rewind to is a legitimate state, not an error."""
    from apps.media_library.models import MediaAssetVersion
    from apps.media_library.services import create_version
    from apps.media_library.tasks import process_image_edit

    media = asset(_png_bytes(600, 400))
    only = create_version(asset=media, file=media.file, change_description="v1", created_by=user)

    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
        process_image_edit.now(str(only.id), {"rotate": 90})

    media.refresh_from_db()
    assert not MediaAssetVersion.objects.filter(pk=only.pk).exists()
    assert media.current_version_id is None


@pytest.mark.django_db
def test_rejected_edit_deletes_the_file_it_generated(asset, user):
    """Django does not delete FileField objects when a row goes.

    Reachable: ``apply_image_edits`` checks the SOURCE size, so an upscaling
    resize succeeds and then produces output too large to thumbnail — by which
    point ``version.file`` has already been written to storage.
    """

    from apps.media_library.services import create_version
    from apps.media_library.tasks import process_image_edit

    media = asset(_png_bytes(400, 400))
    version = create_version(asset=media, file=media.file, change_description="v1", created_by=user)
    version_id = str(version.id)

    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=30_000_000):
        # Upscales past the ceiling: the edit itself succeeds and is written,
        # then thumbnailing the result raises.
        process_image_edit.now(version_id, {"resize": {"width": 7000, "height": 7000}})

    assert not MediaAssetVersion.objects.filter(pk=version.pk).exists()
    assert not _stored_names_containing(version_id), "edited file left behind in storage"


@pytest.mark.django_db
def test_rejected_edit_preserves_the_shared_source_file(asset, user):
    """``create_version`` copies the asset's file NAME, not its bytes.

    Until the edit is written the version and the asset point at the same
    stored object, so a naive cleanup would delete the asset's own file.
    """
    from django.core.files.storage import default_storage

    from apps.media_library.services import create_version
    from apps.media_library.tasks import process_image_edit

    media = asset(_png_bytes(600, 400))
    version = create_version(asset=media, file=media.file, change_description="v1", created_by=user)
    assert version.file.name == media.file.name

    # Fails inside apply_image_edits, before anything is written.
    with override_settings(MEDIA_LIBRARY_MAX_IMAGE_PIXELS=200_000):
        process_image_edit.now(str(version.id), {"rotate": 90})

    media.refresh_from_db()
    assert media.file.name
    assert default_storage.exists(media.file.name)
