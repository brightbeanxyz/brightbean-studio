"""MCP tool: upload_media_from_url — the server-side URL fetch uploader.

Built for MCP clients that cannot send binary payloads (ChatGPT can pass an
image URL but has no bytes to base64). Because the server makes an outbound
request to a caller-supplied URL, the SSRF guards are the important part of this
file: most of these tests assert that something is *refused*.

``requests.get`` and ``socket.getaddrinfo`` are patched so no real network is
touched. DNS is faked explicitly because the whole point is that a hostname's
resolved address decides whether the fetch proceeds.
"""

from __future__ import annotations

import base64
import socket

import pytest

from apps.mcp.protocol import INVALID_PARAMS
from apps.mcp.tests.test_oauth_auth import (
    _make_user_with_workspace,
    _mint_oauth_token,
    _post,
    _rpc,
    _SecureClient,
)
from apps.media_library.models import MediaAsset
from apps.members.models import WorkspaceMembership

# A real 1x1 PNG — magic-byte validation in create_asset must accept it.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
)

PUBLIC_HOST = "files.example.com"
PUBLIC_IP = "93.184.216.34"

OWNER = WorkspaceMembership.WorkspaceRole.OWNER
VIEWER = WorkspaceMembership.WorkspaceRole.VIEWER


def _client(user):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")


def _call(client, name, arguments):
    """POST a tools/call and return just the JSON body.

    ``_post`` returns ``(status_code, body)`` — unpack so tests can index the body.
    """
    _status, body = _post(client, _rpc("tools/call", {"name": name, "arguments": arguments}))
    return body


def _error(body):
    return body["error"]["message"]


class FakeResp:
    """Minimal stand-in for requests.Response with the bits the tool uses."""

    def __init__(self, status_code=200, headers=None, body=b"", chunk=48):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body
        self._chunk = chunk
        self.closed = False

    def iter_content(self, chunk_size=1):
        step = min(chunk_size or 1, self._chunk)
        for i in range(0, len(self._body), step):
            yield self._body[i : i + step]

    def close(self):
        self.closed = True


@pytest.fixture
def dns(monkeypatch):
    """Fake DNS. Tests override the map to control what a host resolves to."""

    mapping = {PUBLIC_HOST: PUBLIC_IP}

    def _getaddrinfo(host, port, *a, **kw):
        ip = mapping.get(host)
        if ip is None:
            raise socket.gaierror(f"fake DNS: no such host {host!r}")
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (ip, port or 443),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
    return mapping


@pytest.fixture
def fetch(monkeypatch):
    """Patch requests.get. Returns a callable to install responses.

    Provide a list of responses for a redirect chain, or a single response.
    """

    calls: list[str] = []

    def install(responses):
        queue = list(responses)

        def _get(url, **kwargs):
            calls.append(url)
            if not queue:
                raise AssertionError(f"unexpected extra fetch of {url!r}")
            return queue.pop(0)

        monkeypatch.setattr("requests.get", _get)
        return calls

    return install


def _png_response(url_body=PNG_1X1):
    return FakeResp(
        200,
        {"Content-Type": "image/png", "Content-Length": str(len(url_body))},
        url_body,
    )


# --------------------------------------------------------------------------
# happy path
# --------------------------------------------------------------------------


def test_creates_asset_from_url(db, dns, fetch):
    user, ws, _sa = _make_user_with_workspace("url-happy@example.com", OWNER)
    fetch([_png_response()])

    body = _call(
        _client(user),
        "upload_media_from_url",
        {"url": f"https://{PUBLIC_HOST}/pics/cat.png"},
    )

    assert "error" not in body, body
    asset = MediaAsset.objects.get(workspace=ws)
    assert asset.file_type == "image"
    # filename derived from the last path segment
    assert asset.filename == "cat.png"
    assert asset.file.name.endswith(".png")


def test_filename_derived_from_url_and_can_be_overridden(db, dns, fetch):
    user, ws, _sa = _make_user_with_workspace("url-name@example.com", OWNER)
    # Mint the client ONCE: _mint_oauth_token is deterministic, so two calls for
    # the same user collide on the access-token checksum unique constraint.
    client = _client(user)
    fetch([_png_response(), _png_response()])

    b1 = _call(
        client,
        "upload_media_from_url",
        {"url": f"https://{PUBLIC_HOST}/deep/path/photo.png?token=abc"},
    )
    assert "error" not in b1, b1
    assert MediaAsset.objects.filter(workspace=ws, filename="photo.png").exists()

    b2 = _call(
        client,
        "upload_media_from_url",
        {"url": f"https://{PUBLIC_HOST}/x.png", "filename": "custom-name.png"},
    )
    assert "error" not in b2, b2
    assert MediaAsset.objects.filter(workspace=ws, filename="custom-name.png").exists()


def test_alt_text_and_tags_are_stored(db, dns, fetch):
    user, ws, _sa = _make_user_with_workspace("url-meta@example.com", OWNER)
    fetch([_png_response()])

    body = _call(
        _client(user),
        "upload_media_from_url",
        {
            "url": f"https://{PUBLIC_HOST}/a.png",
            "alt_text": "a cat",
            "title": "Cat",
            "tags": ["pets", "cats"],
        },
    )
    assert "error" not in body, body
    asset = MediaAsset.objects.get(workspace=ws)
    assert asset.alt_text == "a cat"
    assert asset.title == "Cat"


# --------------------------------------------------------------------------
# SSRF: scheme + address guards
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://files.example.com/a.png",
        "ftp://files.example.com/a.png",
        "file:///etc/passwd",
        "gopher://files.example.com/a.png",
    ],
)
def test_rejects_non_https_schemes(db, dns, fetch, url):
    user, _ws, _sa = _make_user_with_workspace("url-scheme@example.com", OWNER)
    fetch([])

    body = _call(_client(user), "upload_media_from_url", {"url": url})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "https" in _error(body)


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.0.0.5",  # RFC1918
        "192.168.1.10",  # RFC1918
        "172.16.0.9",  # RFC1918
        "169.254.169.254",  # cloud metadata
        "0.0.0.0",  # unspecified
        "::1",  # IPv6 loopback
        "fd00::1",  # IPv6 ULA
    ],
)
def test_rejects_non_public_resolved_addresses(db, dns, fetch, ip):
    """The decisive guard: a public-looking hostname pointing inward is refused."""
    user, _ws, _sa = _make_user_with_workspace(f"url-{ip.replace(':', '_')}@example.com", OWNER)
    dns[PUBLIC_HOST] = ip
    fetch([])

    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "non-public" in _error(body)


def test_unresolvable_host_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-nxdomain@example.com", OWNER)
    fetch([])

    body = _call(_client(user), "upload_media_from_url", {"url": "https://nope.invalid/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "resolve" in _error(body)


def test_url_without_host_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-nohost@example.com", OWNER)
    fetch([])
    body = _call(_client(user), "upload_media_from_url", {"url": "https:///a.png"})
    assert body["error"]["code"] == INVALID_PARAMS


# --------------------------------------------------------------------------
# SSRF: redirect handling
# --------------------------------------------------------------------------


def test_redirect_to_private_address_is_blocked(db, dns, fetch):
    """A public URL that 302s inward must not be followed. This is THE bypass."""
    user, _ws, _sa = _make_user_with_workspace("url-redir@example.com", OWNER)
    fetch(
        [
            FakeResp(302, {"Location": "https://internal.example.com/a.png"}),
        ]
    )
    dns["internal.example.com"] = "127.0.0.1"

    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "non-public" in _error(body)


def test_redirect_chain_is_followed_within_limit(db, dns, fetch):
    user, ws, _sa = _make_user_with_workspace("url-redir-ok@example.com", OWNER)
    fetch(
        [
            FakeResp(302, {"Location": f"https://{PUBLIC_HOST}/hop1.png"}),
            FakeResp(307, {"Location": f"https://{PUBLIC_HOST}/hop2.png"}),
            _png_response(),
        ]
    )

    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/start.png"})
    assert "error" not in body, body
    assert MediaAsset.objects.filter(workspace=ws).count() == 1


def test_too_many_redirects_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-redir-loop@example.com", OWNER)
    # 6 redirects; the limit is 5.
    fetch([FakeResp(302, {"Location": f"https://{PUBLIC_HOST}/loop{i}.png"}) for i in range(6)])
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "redirect" in _error(body)


# --------------------------------------------------------------------------
# size + type limits
# --------------------------------------------------------------------------


def test_rejects_disallowed_content_type(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-type@example.com", OWNER)
    fetch(
        [
            FakeResp(
                200,
                {"Content-Type": "text/html", "Content-Length": "12"},
                b"<html></html>",
            )
        ]
    )
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/x.html"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "content-type" in _error(body).lower()


def test_rejects_oversized_declared_length_without_downloading(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-big@example.com", OWNER)
    fetch(
        [
            FakeResp(
                200,
                {"Content-Type": "image/png", "Content-Length": str(50 * 1024 * 1024)},
                b"",
            )
        ]
    )
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/big.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "cap" in _error(body)


def test_rejects_body_exceeding_cap_when_length_header_absent(db, dns, fetch):
    """Content-Length can lie or be missing; the streamed cap must still bite."""
    user, _ws, _sa = _make_user_with_workspace("url-stream@example.com", OWNER)
    fetch(
        [
            FakeResp(
                200,
                {"Content-Type": "image/png"},
                b"\x89PNG\r\n\x1a\n" + b"\x00" * (30 * 1024 * 1024),
                chunk=1024 * 1024,
            )
        ]
    )
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/big.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "cap" in _error(body)


def test_upstream_http_error_is_surfaced(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-404@example.com", OWNER)
    fetch([FakeResp(404, {"Content-Type": "text/html"}, b"nope")])
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "404" in _error(body)


def test_upstream_error_names_the_host(db, dns, fetch):
    """A bare 'HTTP 429' reads as if BrightBean throttled the call. It must say
    whose 429 it was — that ambiguity cost real debugging time on Wikimedia."""
    user, _ws, _sa = _make_user_with_workspace("url-429@example.com", OWNER)
    fetch([FakeResp(429, {"Content-Type": "text/html"}, b"slow down")])
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    msg = _error(body)
    assert body["error"]["code"] == INVALID_PARAMS
    assert PUBLIC_HOST in msg, msg
    assert "429" in msg
    assert "upstream" in msg
    assert "not BrightBean" in msg


def test_upstream_retry_after_is_surfaced(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-retry@example.com", OWNER)
    fetch(
        [
            FakeResp(
                429,
                {"Content-Type": "text/html", "Retry-After": "120"},
                b"slow down",
            )
        ]
    )
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert "120" in _error(body)


def test_upstream_5xx_is_surfaced(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-503@example.com", OWNER)
    fetch([FakeResp(503, {"Content-Type": "text/html"}, b"down")])
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "503" in _error(body)


def test_outbound_user_agent_is_descriptive(db, dns, fetch, monkeypatch):
    """Large CDNs throttle generic User-Agents; ours must carry a contact URL."""
    seen = {}

    def _get(url, **kwargs):
        seen.update(kwargs.get("headers") or {})
        return _png_response()

    monkeypatch.setattr("requests.get", _get)
    user, _ws, _sa = _make_user_with_workspace("url-ua@example.com", OWNER)

    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert "error" not in body, body
    ua = seen.get("User-Agent", "")
    assert "BrightBeanStudio" in ua
    assert "+http" in ua, f"User-Agent should carry a contact URL, got {ua!r}"


def test_outbound_user_agent_is_configurable(db, dns, fetch, monkeypatch, settings):
    seen = {}

    def _get(url, **kwargs):
        seen.update(kwargs.get("headers") or {})
        return _png_response()

    monkeypatch.setattr("requests.get", _get)
    settings.MCP_MEDIA_FETCH_USER_AGENT = "CustomAgent/9.9 (contact@example.com)"

    user, _ws, _sa = _make_user_with_workspace("url-ua-cfg@example.com", OWNER)
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert "error" not in body, body
    assert seen.get("User-Agent") == "CustomAgent/9.9 (contact@example.com)"


def test_mislabelled_content_type_is_still_rejected_by_magic_bytes(db, dns, fetch):
    """Claims image/png, is actually HTML — create_asset sniffs and refuses."""
    user, _ws, _sa = _make_user_with_workspace("url-spoof@example.com", OWNER)
    payload = b"<html><body>not an image</body></html>"
    fetch(
        [
            FakeResp(
                200,
                {"Content-Type": "image/png", "Content-Length": str(len(payload))},
                payload,
            )
        ]
    )
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/evil.png"})
    assert "error" in body, body


# --------------------------------------------------------------------------
# permissions + tool registration
# --------------------------------------------------------------------------


def test_viewer_without_upload_media_is_denied(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-viewer@example.com", VIEWER)
    fetch([])  # must not even attempt the fetch
    body = _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "Permission denied" in _error(body)


def test_tool_is_advertised_in_tools_list(db):
    user, _ws, _sa = _make_user_with_workspace("url-list@example.com", OWNER)
    _status, body = _post(_client(user), _rpc("tools/list", {}))
    names = {t["name"] for t in body["result"]["tools"]}
    assert "upload_media_from_url" in names


def test_missing_url_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-missing@example.com", OWNER)
    fetch([])
    body = _call(_client(user), "upload_media_from_url", {})
    assert body["error"]["code"] == INVALID_PARAMS


def test_blank_url_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("url-blank@example.com", OWNER)
    fetch([])
    body = _call(_client(user), "upload_media_from_url", {"url": "   "})
    assert body["error"]["code"] == INVALID_PARAMS


def test_response_is_closed_on_error(db, dns, fetch):
    """Sockets must not leak when the fetch fails."""
    user, _ws, _sa = _make_user_with_workspace("url-close@example.com", OWNER)
    resp = FakeResp(500, {"Content-Type": "text/html"}, b"boom")
    fetch([resp])
    _call(_client(user), "upload_media_from_url", {"url": f"https://{PUBLIC_HOST}/a.png"})
    assert resp.closed is True
