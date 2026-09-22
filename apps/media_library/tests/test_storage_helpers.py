"""Tests for the object-storage seam in ``apps.media_library.storage``."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.cache import caches
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings

from apps.media_library import storage
from apps.media_library.storage import download_to_path, is_s3_backend


class IsS3BackendTest(SimpleTestCase):
    """``default_storage`` is a LazyObject, which ``type()`` sees straight through.

    Reading ``type(default_storage).__module__`` returns the DefaultStorage
    wrapper's module on every deployment, so this returned False even on S3 —
    silently disabling the MCP presigned-upload tools and the media proxy's
    range-GET path. Only ``__class__`` is proxied to the real backend.
    """

    def test_false_on_local_filesystem_storage(self):
        with override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            }
        ):
            assert is_s3_backend() is False

    def test_the_suite_itself_runs_on_local_storage(self):
        """config.settings.test must not inherit an S3 backend from a dev .env."""
        assert is_s3_backend() is False

    def test_true_when_the_configured_backend_is_s3(self):
        with override_settings(
            STORAGES={
                "default": {"BACKEND": "storages.backends.s3.S3Storage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            }
        ):
            assert is_s3_backend() is True

    def test_does_not_read_through_the_lazy_wrapper(self):
        """Guards the exact mistake: ``type()`` must not be what decides this."""
        from django.core.files.storage import default_storage

        assert type(default_storage).__module__ == "django.core.files.storage"


class DownloadToPathLocalTest(SimpleTestCase):
    """The local-filesystem branch; the S3 branch is boto3's managed transfer."""

    def test_copies_the_object_byte_for_byte(self):
        from django.core.files.storage import default_storage

        payload = os.urandom(64 * 1024 + 7)  # deliberately not a chunk multiple
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            key = default_storage.save("download_probe.bin", ContentFile(payload))
            try:
                dest = os.path.join(media_root, "out.bin")

                class _Field:
                    name = key

                    def open(self, mode="rb"):
                        return default_storage.open(key, mode)

                download_to_path(_Field(), dest)
                with open(dest, "rb") as f:
                    assert f.read() == payload
            finally:
                default_storage.delete(key)


class DownloadToPathS3BranchTest(SimpleTestCase):
    """The boto3 branch, which the suite's local storage never reaches."""

    def _fake_client(self, payload):
        client = MagicMock()

        def _download_fileobj(bucket, key, fh):
            fh.write(payload)

        client.download_fileobj.side_effect = _download_fileobj
        return client

    def test_streams_through_boto3_rather_than_opening_the_field_file(self):
        payload = os.urandom(4096)
        client = self._fake_client(payload)
        field = MagicMock()
        field.name = "media_library/2026/09/v.mp4"

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(storage, "is_s3_backend", return_value=True),
            patch.object(storage, "_client_and_bucket", return_value=(client, "bucket")),
            patch.object(storage, "_normalize", side_effect=lambda k: f"prefix/{k}"),
        ):
            dest = os.path.join(tmpdir, "out.mp4")
            storage.download_to_path(field, dest)

            with open(dest, "rb") as f:
                assert f.read() == payload

        # The whole point: never routed through the FieldFile, whose read
        # materializes the entire object in the process heap.
        field.open.assert_not_called()
        # And the key is normalized, so it matches what presign/HEAD address.
        assert client.download_fileobj.call_args.args[1] == "prefix/media_library/2026/09/v.mp4"

    def test_a_failed_download_propagates(self):
        client = MagicMock()
        client.download_fileobj.side_effect = RuntimeError("bucket gone")

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch.object(storage, "is_s3_backend", return_value=True),
            patch.object(storage, "_client_and_bucket", return_value=(client, "bucket")),
            patch.object(storage, "_normalize", side_effect=lambda k: k),
            self.assertRaises(RuntimeError),
        ):
            storage.download_to_path(MagicMock(name="f"), os.path.join(tmpdir, "out.bin"))


class OpenObjectRangeTest(SimpleTestCase):
    def _patched(self, client):
        return (
            patch.object(storage, "_client_and_bucket", return_value=(client, "bucket")),
            patch.object(storage, "_normalize", side_effect=lambda k: k),
        )

    def test_builds_an_inclusive_http_range(self):
        client = MagicMock()
        client.get_object.return_value = {"Body": "body"}
        a, b = self._patched(client)
        with a, b:
            assert storage.open_object_range("k", 100, 199) == "body"

        assert client.get_object.call_args.kwargs["Range"] == "bytes=100-199"

    def test_open_ended_range(self):
        client = MagicMock()
        client.get_object.return_value = {"Body": "body"}
        a, b = self._patched(client)
        with a, b:
            storage.open_object_range("k", 100)

        assert client.get_object.call_args.kwargs["Range"] == "bytes=100-"

    def test_no_range_header_when_no_offsets_given(self):
        client = MagicMock()
        client.get_object.return_value = {"Body": "body"}
        a, b = self._patched(client)
        with a, b:
            storage.open_object_range("k")

        assert "Range" not in client.get_object.call_args.kwargs

    def test_a_missing_object_becomes_filenotfounderror(self):
        """Callers shouldn't need botocore to tell 'gone' from 'broken'."""
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        a, b = self._patched(client)
        with a, b, self.assertRaises(FileNotFoundError):
            storage.open_object_range("k", 0, 10)

    def test_other_client_errors_propagate_unchanged(self):
        from botocore.exceptions import ClientError

        client = MagicMock()
        client.get_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
        a, b = self._patched(client)
        with a, b, self.assertRaises(ClientError):
            storage.open_object_range("k", 0, 10)


class SupportsPresignedPostTest(SimpleTestCase):
    """R2 answers S3's POST Object with 501, so "is it S3" isn't the question."""

    def _s3(self, endpoint):
        return override_settings(
            STORAGES={
                "default": {"BACKEND": "storages.backends.s3.S3Storage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
            AWS_S3_ENDPOINT_URL=endpoint,
        )

    def test_false_on_local_storage(self):
        assert storage.supports_presigned_post() is False

    def test_false_on_cloudflare_r2(self):
        with self._s3("https://abc123.r2.cloudflarestorage.com"):
            assert storage.supports_presigned_post() is False

    def test_true_on_plain_s3(self):
        with self._s3("https://s3.eu-central-1.amazonaws.com"):
            assert storage.supports_presigned_post() is True

    def test_setting_overrides_the_heuristic(self):
        with (
            self._s3("https://abc123.r2.cloudflarestorage.com"),
            override_settings(MEDIA_LIBRARY_PRESIGNED_POST_SUPPORTED=True),
        ):
            assert storage.supports_presigned_post() is True


class FilmstripCacheAliasTest(SimpleTestCase):
    """The filmstrip alias must be valid for whichever backend is configured.

    It was originally spread from ``default`` with ``LOCATION`` overridden to
    the string "filmstrip". That reads as a namespace to LocMemCache but as the
    *connection URL* to RedisCache, which hands it to
    ``ConnectionPool.from_url`` — so every frame-picker request on a
    Redis-backed deployment would have raised at the cache lookup.
    """

    def test_alias_exists(self):
        assert "filmstrip" in settings.CACHES

    def test_location_is_a_real_server_url_when_the_backend_is_redis(self):
        alias = settings.CACHES["filmstrip"]
        if "redis" not in alias["BACKEND"].lower():
            self.skipTest("not a Redis-backed deployment")
        assert alias["LOCATION"] == settings.CACHES["default"]["LOCATION"]
        assert alias.get("KEY_PREFIX"), "Redis aliases share a server, so they need a key prefix"

    def test_locmem_alias_is_explicitly_bounded(self):
        alias = settings.CACHES["filmstrip"]
        if "locmem" not in alias["BACKEND"].lower():
            self.skipTest("not a LocMem-backed deployment")
        # In-process and per worker: the 300-entry default would be tens of MB
        # of base64 JPEGs resident on a box already tight for memory.
        assert alias["OPTIONS"]["MAX_ENTRIES"] <= 64
        assert alias["LOCATION"] != settings.CACHES["default"].get("LOCATION")

    def test_the_alias_round_trips(self):
        cache = caches["filmstrip"]
        cache.set("probe", {"frames": [1, 2]}, 30)
        try:
            assert cache.get("probe") == {"frames": [1, 2]}
        finally:
            cache.delete("probe")
