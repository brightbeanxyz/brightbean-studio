"""``_media_handle`` must never materialize media as ``bytes``.

The local-path branch is bounded by the 20 MB image cap, but the HTTP(S)
branch fetched an arbitrary URL with ``resp.content`` — an unbounded read
straight into the worker's heap, on a dyno with 512 MB total.
"""

import httpx
import pytest

from providers.exceptions import PublishError
from providers.linkedin import MAX_REMOTE_MEDIA_BYTES, LinkedInProvider


class TestLocalPathBranch:
    def test_yields_a_readable_file_object(self, tmp_path):
        media = tmp_path / "image.png"
        media.write_bytes(b"pixels" * 100)
        with LinkedInProvider._media_handle(str(media)) as handle:
            assert handle.read() == b"pixels" * 100

    def test_closes_the_handle_on_exit(self, tmp_path):
        media = tmp_path / "image.png"
        media.write_bytes(b"x")
        with LinkedInProvider._media_handle(str(media)) as handle:
            pass
        assert handle.closed


class TestUrlBranch:
    def _transport(self, body, status=200):
        return httpx.MockTransport(lambda request: httpx.Response(status, content=body))

    def test_spools_a_url_to_disk_and_yields_a_file(self, monkeypatch):
        body = b"remote-bytes" * 5000
        transport = self._transport(body)
        original = httpx.Client

        def client(*args, **kwargs):
            kwargs["transport"] = transport
            return original(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", client)

        with LinkedInProvider._media_handle("https://cdn.example/photo.jpg") as handle:
            # A real file on disk, not an in-memory buffer.
            assert handle.fileno() > 0
            assert handle.read() == body

    def test_starts_at_offset_zero(self, monkeypatch):
        """The spool is written then rewound; forgetting the seek uploads nothing."""
        body = b"abcdef"
        transport = self._transport(body)
        original = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda *a, **k: original(*a, **{**k, "transport": transport}))

        with LinkedInProvider._media_handle("https://cdn.example/photo.jpg") as handle:
            assert handle.tell() == 0

    def test_raises_on_an_http_error(self, monkeypatch):
        transport = self._transport(b"", status=404)
        original = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda *a, **k: original(*a, **{**k, "transport": transport}))

        with (
            pytest.raises(httpx.HTTPStatusError),
            LinkedInProvider._media_handle("https://cdn.example/missing.jpg"),
        ):
            pass


class TestUrlBranchSizeCap:
    """A caller-supplied URL has no size we control.

    Streaming it to disk unchecked just moves an unbounded read off the heap
    and onto the dyno's shared ephemeral disk, which affects every process on
    that dyno rather than only this publish.
    """

    def _patch(self, monkeypatch, handler):
        transport = httpx.MockTransport(handler)
        original = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda *a, **k: original(*a, **{**k, "transport": transport}))

    def test_the_rejection_is_not_retryable(self, monkeypatch):
        """The file at that URL is the same size on every attempt.

        Left retryable, the publish engine walks the full backoff ladder and
        re-downloads it each time to fail identically, delaying the moment the
        user is told anything. ``apps.publisher.engine`` reads this via
        ``getattr(e, "retryable", True)``, so the default is the wrong one.
        """
        over = MAX_REMOTE_MEDIA_BYTES + 1
        self._patch(monkeypatch, lambda request: httpx.Response(200, headers={"Content-Length": str(over)}))
        with (
            pytest.raises(PublishError) as excinfo,
            LinkedInProvider._media_handle("https://cdn.example/huge.jpg"),
        ):
            pass
        assert excinfo.value.retryable is False

    def test_rejects_on_a_content_length_over_the_cap(self, monkeypatch):
        over = MAX_REMOTE_MEDIA_BYTES + 1

        def handler(request):
            return httpx.Response(200, headers={"Content-Length": str(over)}, content=b"")

        self._patch(monkeypatch, handler)
        with (
            pytest.raises(PublishError, match="exceeds"),
            LinkedInProvider._media_handle("https://cdn.example/huge.jpg"),
        ):
            pass

    def test_rejects_a_body_that_outgrows_a_missing_content_length(self, monkeypatch):
        """Content-Length is the server's claim, and chunked responses omit it."""
        body = b"x" * (MAX_REMOTE_MEDIA_BYTES + 1024)

        def handler(request):
            return httpx.Response(200, content=body)

        self._patch(monkeypatch, handler)
        with (
            pytest.raises(PublishError, match="exceeds"),
            LinkedInProvider._media_handle("https://cdn.example/lying.jpg"),
        ):
            pass

    def test_allows_media_under_the_cap(self, monkeypatch):
        body = b"y" * 2048
        self._patch(monkeypatch, lambda request: httpx.Response(200, content=body))
        with LinkedInProvider._media_handle("https://cdn.example/fine.jpg") as handle:
            assert handle.read() == body

    def test_a_local_path_is_not_subject_to_the_remote_cap(self, tmp_path):
        """Local files came from our own upload path and were sized there."""
        media = tmp_path / "big.png"
        media.write_bytes(b"z" * (MAX_REMOTE_MEDIA_BYTES + 10))
        with LinkedInProvider._media_handle(str(media)) as handle:
            assert len(handle.read()) == MAX_REMOTE_MEDIA_BYTES + 10
