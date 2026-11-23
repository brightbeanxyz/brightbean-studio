"""Tests for Bluesky provider session handling."""

import base64
import json
import time
from unittest.mock import MagicMock, patch

from providers.bluesky import BlueskyProvider, _access_jwt_expires_in
from providers.exceptions import APIError


def _make_jwt(payload: dict) -> str:
    """Build a JWT-shaped string (header.payload.signature) — signature is unchecked."""

    def encode(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{encode({'alg': 'HS256'})}.{encode(payload)}.signature"


class TestAccessJwtExpiresIn:
    def test_returns_positive_for_future_exp(self):
        future = int(time.time()) + 3600
        jwt = _make_jwt({"exp": future})
        result = _access_jwt_expires_in(jwt)
        assert result is not None
        assert 3595 <= result <= 3600

    def test_returns_zero_for_past_exp(self):
        past = int(time.time()) - 300
        jwt = _make_jwt({"exp": past})
        assert _access_jwt_expires_in(jwt) == 0

    def test_returns_none_for_malformed_jwt(self):
        assert _access_jwt_expires_in("not-a-jwt") is None
        assert _access_jwt_expires_in("only.two") is None
        assert _access_jwt_expires_in("a.!!!notbase64!!!.c") is None

    def test_returns_none_when_exp_missing(self):
        jwt = _make_jwt({"sub": "did:plc:abc"})
        assert _access_jwt_expires_in(jwt) is None

    def test_returns_none_when_exp_not_numeric(self):
        jwt = _make_jwt({"exp": "tomorrow"})
        assert _access_jwt_expires_in(jwt) is None


class TestCreateSession:
    @patch.object(BlueskyProvider, "_request")
    def test_populates_expires_in_from_jwt(self, mock_request):
        future = int(time.time()) + 7200
        access_jwt = _make_jwt({"exp": future})
        mock_request.return_value = MagicMock(
            json=MagicMock(return_value={"accessJwt": access_jwt, "refreshJwt": "refresh"}),
        )

        provider = BlueskyProvider()
        tokens = provider.create_session("user.bsky.social", "app-pw")

        assert tokens.access_token == access_jwt
        assert tokens.refresh_token == "refresh"
        assert tokens.expires_in is not None
        assert 7195 <= tokens.expires_in <= 7200


PLC_DID = "did:plc:abcdefghijklmnopqrstuvwx"


def _fake_network(pds_endpoint: str, *, did: str = PLC_DID):
    """Answer the handle lookup, the DID document and createSession like the network."""
    access_jwt = _make_jwt({"exp": int(time.time()) + 7200})

    def respond(method, url, **kwargs):
        if url.endswith("/xrpc/com.atproto.identity.resolveHandle"):
            body = {"did": did}
        elif url.startswith("https://plc.directory/") or url.endswith("/.well-known/did.json"):
            body = {
                "id": did,
                "service": [
                    {
                        "id": "#atproto_pds",
                        "type": "AtprotoPersonalDataServer",
                        "serviceEndpoint": pds_endpoint,
                    }
                ],
            }
        elif url.endswith("/xrpc/com.atproto.server.createSession"):
            body = {"accessJwt": access_jwt, "refreshJwt": "refresh"}
        else:
            raise AssertionError(f"unexpected request: {method} {url}")
        return MagicMock(json=MagicMock(return_value=body))

    return respond


def _always_safe(url: str) -> bool:
    return True


class TestResolvePds:
    @patch.object(BlueskyProvider, "_request")
    def test_follows_the_plc_did_document(self, mock_request):
        mock_request.side_effect = _fake_network("https://eurosky.social")

        pds_url = BlueskyProvider().resolve_pds("me.eurosky.social", is_safe_url=_always_safe)

        assert pds_url == "https://eurosky.social"
        assert mock_request.call_args_list[1].args[1] == f"https://plc.directory/{PLC_DID}"

    @patch.object(BlueskyProvider, "_request")
    def test_reads_a_did_web_document_from_its_domain(self, mock_request):
        mock_request.side_effect = _fake_network("https://pds.example.org", did="did:web:example.org")

        pds_url = BlueskyProvider().resolve_pds("example.org", is_safe_url=_always_safe)

        assert pds_url == "https://pds.example.org"
        assert mock_request.call_args_list[1].args[1] == "https://example.org/.well-known/did.json"

    @patch.object(BlueskyProvider, "_request")
    def test_takes_a_did_without_looking_up_a_handle(self, mock_request):
        mock_request.side_effect = _fake_network("https://eurosky.social")

        assert BlueskyProvider().resolve_pds(PLC_DID, is_safe_url=_always_safe) == "https://eurosky.social"
        assert mock_request.call_count == 1

    @patch.object(BlueskyProvider, "_request")
    def test_does_not_resolve_an_email(self, mock_request):
        assert BlueskyProvider().resolve_pds("me@example.org", is_safe_url=_always_safe) is None
        mock_request.assert_not_called()

    @patch.object(BlueskyProvider, "_request")
    def test_drops_an_endpoint_the_ssrf_check_rejects(self, mock_request):
        mock_request.side_effect = _fake_network("https://10.0.0.5")

        pds_url = BlueskyProvider().resolve_pds("me.example.org", is_safe_url=lambda url: "10.0.0.5" not in url)

        assert pds_url is None

    @patch.object(BlueskyProvider, "_request")
    def test_never_fetches_a_did_web_document_from_a_rejected_host(self, mock_request):
        mock_request.side_effect = _fake_network("https://pds.example.org", did="did:web:internal.example")

        assert BlueskyProvider().resolve_pds("internal.example", is_safe_url=lambda url: False) is None
        assert mock_request.call_count == 1

    @patch.object(BlueskyProvider, "_request")
    def test_ignores_a_plain_http_endpoint(self, mock_request):
        mock_request.side_effect = _fake_network("http://pds.example.org")

        assert BlueskyProvider().resolve_pds("me.example.org", is_safe_url=_always_safe) is None

    @patch.object(BlueskyProvider, "_request")
    def test_does_not_build_a_url_from_a_malformed_did(self, mock_request):
        mock_request.side_effect = _fake_network("https://pds.example.org", did="did:plc:../../export")

        assert BlueskyProvider().resolve_pds("me.example.org", is_safe_url=_always_safe) is None
        assert mock_request.call_count == 1


class TestCreateSessionOnTheAccountPds:
    @patch.object(BlueskyProvider, "_request")
    def test_opens_the_session_on_a_third_party_pds(self, mock_request):
        mock_request.side_effect = _fake_network("https://eurosky.social")
        provider = BlueskyProvider()

        provider.create_session("me.eurosky.social", "app-pw", is_safe_url=_always_safe)

        assert mock_request.call_args.args[1] == "https://eurosky.social/xrpc/com.atproto.server.createSession"
        assert provider.pds_url == "https://eurosky.social"

    @patch.object(BlueskyProvider, "_request")
    def test_keeps_bsky_social_for_accounts_bluesky_hosts(self, mock_request):
        mock_request.side_effect = _fake_network("https://morel.us-east.host.bsky.network")
        provider = BlueskyProvider()

        provider.create_session("me.bsky.social", "app-pw", is_safe_url=_always_safe)

        assert mock_request.call_args.args[1] == "https://bsky.social/xrpc/com.atproto.server.createSession"
        assert provider.pds_url == "https://bsky.social"

    @patch.object(BlueskyProvider, "_request")
    def test_falls_back_to_bsky_social_when_the_lookup_fails(self, mock_request):
        access_jwt = _make_jwt({"exp": int(time.time()) + 7200})
        mock_request.side_effect = [
            APIError("Unable to resolve handle", status_code=400),
            MagicMock(json=MagicMock(return_value={"accessJwt": access_jwt, "refreshJwt": "refresh"})),
        ]
        provider = BlueskyProvider()

        tokens = provider.create_session("me.example.org", "app-pw", is_safe_url=_always_safe)

        assert tokens.access_token == access_jwt
        assert mock_request.call_args.args[1] == "https://bsky.social/xrpc/com.atproto.server.createSession"

    @patch.object(BlueskyProvider, "_request")
    def test_looks_nothing_up_without_an_ssrf_check(self, mock_request):
        mock_request.side_effect = _fake_network("https://eurosky.social")
        provider = BlueskyProvider()

        provider.create_session("me.eurosky.social", "app-pw")

        assert mock_request.call_count == 1
        assert provider.pds_url == "https://bsky.social"


class TestRefreshToken:
    @patch.object(BlueskyProvider, "_request")
    def test_populates_expires_in_from_jwt(self, mock_request):
        future = int(time.time()) + 3600
        access_jwt = _make_jwt({"exp": future})
        mock_request.return_value = MagicMock(
            json=MagicMock(return_value={"accessJwt": access_jwt, "refreshJwt": "new-refresh"}),
        )

        provider = BlueskyProvider()
        tokens = provider.refresh_token("old-refresh")

        assert tokens.access_token == access_jwt
        assert tokens.refresh_token == "new-refresh"
        assert tokens.expires_in is not None
        assert 3595 <= tokens.expires_in <= 3600


class TestUploadBlobStreams:
    """``_upload_blob`` is reached for VIDEO, where the file can be 1 GB.

    Reading it into a ``bytes`` object first put the whole file in the worker's
    RSS — on a 512 MB dyno that is an immediate OOM kill, not a slow leak.
    """

    def _provider(self):
        return BlueskyProvider(credentials={"pds_url": "https://pds.example"})

    def _call(self, tmp_path, payload=b"x" * 4096):
        media = tmp_path / "clip.mp4"
        media.write_bytes(payload)
        provider = self._provider()
        with patch.object(provider, "_request") as request:
            request.return_value = MagicMock(json=lambda: {"blob": {"$type": "blob"}})
            result = provider._upload_blob("token", str(media))
        return request, result

    def test_passes_a_file_object_not_bytes(self, tmp_path):
        request, _ = self._call(tmp_path)
        sent = request.call_args.kwargs["data"]
        assert not isinstance(sent, bytes | bytearray)
        assert hasattr(sent, "read")

    def test_sends_an_explicit_content_length(self, tmp_path):
        """Without it httpx falls back to chunked encoding, which some PDSs reject."""
        request, _ = self._call(tmp_path, payload=b"y" * 1234)
        assert request.call_args.kwargs["headers"]["Content-Length"] == "1234"

    def test_handle_is_open_and_positioned_at_zero_during_the_request(self, tmp_path):
        """The ``with open`` block must still be live when httpx reads the body.

        Reading it inside the mock is the only honest check: afterwards the
        block has closed the handle, which is correct but says nothing about
        whether the upload could have streamed.
        """
        media = tmp_path / "clip.mp4"
        media.write_bytes(b"z" * 32)
        provider = self._provider()
        seen = {}

        def capture(*args, **kwargs):
            seen["body"] = kwargs["data"].read()
            return MagicMock(json=lambda: {"blob": {}})

        with patch.object(provider, "_request", side_effect=capture):
            provider._upload_blob("token", str(media))

        assert seen["body"] == b"z" * 32

    def test_guesses_the_content_type_from_the_path(self, tmp_path):
        request, _ = self._call(tmp_path)
        assert request.call_args.kwargs["headers"]["Content-Type"] == "video/mp4"

    def test_returns_the_blob_reference(self, tmp_path):
        _, result = self._call(tmp_path)
        assert result == {"$type": "blob"}
