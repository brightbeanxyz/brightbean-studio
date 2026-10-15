"""MCP tool: upload_media_file — the host-attached-file path.

This is the route that actually works for ChatGPT: it declares a file parameter
via ``_meta["openai/fileParams"]``, so ChatGPT uploads the bytes itself and hands
the server a short-lived ``download_url`` to fetch. ChatGPT cannot produce base64
and exposes no public link, so neither upload_media nor upload_media_from_url can
be driven from a ChatGPT conversation — this tool is the answer to that gap.

The ``download_url`` is a bearer credential, so several tests here assert it does
NOT come back in the tool result.
"""

from __future__ import annotations

import json
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
from apps.mcp.tests.test_upload_from_url import (
    PNG_1X1,
    PUBLIC_HOST,
    PUBLIC_IP,
    FakeResp,
)
from apps.media_library.models import MediaAsset
from apps.members.models import WorkspaceMembership

OWNER = WorkspaceMembership.WorkspaceRole.OWNER
VIEWER = WorkspaceMembership.WorkspaceRole.VIEWER

# A signed, expiring bearer URL — the shape ChatGPT supplies.
SIGNED_URL = (
    f"https://{PUBLIC_HOST}/file-abc123?se=2026-10-15T00%3A00%3A00Z&sp=r&sv=2024-11-04&sr=b&sig=SUPERSECRETSIGNATURE"
)


def _client(user):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {_mint_oauth_token(user)}")


def _call(client, name, arguments):
    _status, body = _post(client, _rpc("tools/call", {"name": name, "arguments": arguments}))
    return body


def _error(body):
    return body["error"]["message"]


@pytest.fixture
def dns(monkeypatch):
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
    def install(responses):
        queue = list(responses)

        def _get(url, **kwargs):
            if not queue:
                raise AssertionError(f"unexpected extra fetch of {url!r}")
            return queue.pop(0)

        monkeypatch.setattr("requests.get", _get)

    return install


def _file_response(body=PNG_1X1):
    return FakeResp(
        200,
        {"Content-Type": "image/png", "Content-Length": str(len(body))},
        body,
    )


def _file_param(**over):
    base = {"download_url": SIGNED_URL, "file_id": "file-abc123"}
    base.update(over)
    return base


# --------------------------------------------------------------------------
# happy path
# --------------------------------------------------------------------------


def test_uploads_host_attached_file(db, dns, fetch):
    user, ws, _sa = _make_user_with_workspace("file-happy@example.com", OWNER)
    fetch([_file_response()])

    body = _call(_client(user), "upload_media_file", {"file": _file_param()})
    assert "error" not in body, body
    asset = MediaAsset.objects.get(workspace=ws)
    assert asset.file_type == "image"
    assert asset.file.name.endswith(".png")


def test_filename_precedence(db, dns, fetch):
    """explicit filename > host file_name > URL path."""
    user, ws, _sa = _make_user_with_workspace("file-name@example.com", OWNER)
    client = _client(user)
    fetch([_file_response(), _file_response(), _file_response()])

    _call(
        client,
        "upload_media_file",
        {"file": _file_param(file_name="from-host.png")},
    )
    assert MediaAsset.objects.filter(workspace=ws, filename="from-host.png").exists()

    _call(
        client,
        "upload_media_file",
        {"file": _file_param(file_name="ignored.png"), "filename": "explicit.png"},
    )
    assert MediaAsset.objects.filter(workspace=ws, filename="explicit.png").exists()


def test_metadata_is_stored(db, dns, fetch):
    user, ws, _sa = _make_user_with_workspace("file-meta@example.com", OWNER)
    fetch([_file_response()])

    body = _call(
        _client(user),
        "upload_media_file",
        {
            "file": _file_param(file_name="cat.png"),
            "alt_text": "a cat",
            "title": "Cat",
            "tags": ["pets"],
        },
    )
    assert "error" not in body, body
    asset = MediaAsset.objects.get(workspace=ws)
    assert asset.alt_text == "a cat"
    assert asset.title == "Cat"


# --------------------------------------------------------------------------
# the signed URL must not leak
# --------------------------------------------------------------------------


def test_signed_url_is_not_echoed_in_the_result(db, dns, fetch):
    """download_url is a bearer credential — it must never come back out."""
    user, _ws, _sa = _make_user_with_workspace("file-leak@example.com", OWNER)
    fetch([_file_response()])

    body = _call(_client(user), "upload_media_file", {"file": _file_param()})
    serialized = json.dumps(body)
    assert "SUPERSECRETSIGNATURE" not in serialized, serialized[:400]
    assert "sig=" not in serialized


def test_fetch_error_names_host_but_not_the_signature(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-err@example.com", OWNER)
    fetch([FakeResp(403, {"Content-Type": "text/html"}, b"denied")])

    body = _call(_client(user), "upload_media_file", {"file": _file_param()})
    msg = _error(body)
    assert PUBLIC_HOST in msg, msg
    assert "SUPERSECRETSIGNATURE" not in msg
    assert "sig=" not in msg


# --------------------------------------------------------------------------
# SSRF guards still apply to the supplied URL
# --------------------------------------------------------------------------


def test_private_address_is_refused(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-ssrf@example.com", OWNER)
    dns[PUBLIC_HOST] = "169.254.169.254"
    fetch([])

    body = _call(_client(user), "upload_media_file", {"file": _file_param()})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "non-public" in _error(body)


def test_non_https_download_url_is_refused(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-http@example.com", OWNER)
    fetch([])

    body = _call(
        _client(user),
        "upload_media_file",
        {"file": _file_param(download_url="http://files.example.com/a.png")},
    )
    assert body["error"]["code"] == INVALID_PARAMS
    assert "https" in _error(body)


# --------------------------------------------------------------------------
# input contract
# --------------------------------------------------------------------------


def test_missing_file_object_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-nofile@example.com", OWNER)
    fetch([])
    body = _call(_client(user), "upload_media_file", {})
    assert body["error"]["code"] == INVALID_PARAMS


def test_missing_file_id_is_rejected(db, dns, fetch):
    """ChatGPT always sends file_id; requiring it catches malformed callers."""
    user, _ws, _sa = _make_user_with_workspace("file-noid@example.com", OWNER)
    fetch([])
    body = _call(
        _client(user),
        "upload_media_file",
        {"file": {"download_url": SIGNED_URL}},
    )
    assert body["error"]["code"] == INVALID_PARAMS
    assert "file_id" in _error(body)


def test_missing_download_url_is_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-nourl@example.com", OWNER)
    fetch([])
    body = _call(_client(user), "upload_media_file", {"file": {"file_id": "file-abc123"}})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "download_url" in _error(body)


def test_mislabelled_content_type_is_still_rejected(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-spoof@example.com", OWNER)
    payload = b"<html>not an image</html>"
    fetch(
        [
            FakeResp(
                200,
                {"Content-Type": "image/png", "Content-Length": str(len(payload))},
                payload,
            )
        ]
    )
    body = _call(_client(user), "upload_media_file", {"file": _file_param()})
    assert "error" in body, body


def test_viewer_without_upload_media_is_denied(db, dns, fetch):
    user, _ws, _sa = _make_user_with_workspace("file-viewer@example.com", VIEWER)
    fetch([])
    body = _call(_client(user), "upload_media_file", {"file": _file_param()})
    assert body["error"]["code"] == INVALID_PARAMS
    assert "Permission denied" in _error(body)


# --------------------------------------------------------------------------
# the discovery contract ChatGPT needs
# --------------------------------------------------------------------------


def test_tools_list_declares_openai_file_params(db):
    """Without this _meta ChatGPT won't offer the tool a file to attach."""
    user, _ws, _sa = _make_user_with_workspace("file-list@example.com", OWNER)
    _status, body = _post(_client(user), _rpc("tools/list", {}))
    tools = {t["name"]: t for t in body["result"]["tools"]}

    assert "upload_media_file" in tools, sorted(tools)
    tool = tools["upload_media_file"]
    assert tool["_meta"]["openai/fileParams"] == ["file"]

    field = tool["inputSchema"]["properties"]["file"]
    assert field["required"] == ["download_url", "file_id"]
    for key in ("download_url", "file_id", "mime_type", "file_name"):
        assert key in field["properties"], key


def test_tools_without_meta_do_not_gain_one(db):
    """The _meta field is opt-in — adding it must not alter every other tool."""
    user, _ws, _sa = _make_user_with_workspace("file-meta-others@example.com", OWNER)
    _status, body = _post(_client(user), _rpc("tools/list", {}))
    tools = {t["name"]: t for t in body["result"]["tools"]}

    assert "_meta" not in tools["upload_media"]
    assert "_meta" not in tools["upload_media_from_url"]
