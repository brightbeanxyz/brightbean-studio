"""Gap 1 + 1a + 1b: media upload, storage quota, discovery list.

Exercises the agent surface end-to-end:

* POST /api/v1/media/ — multipart upload, ``upload_media`` permission,
  storage-quota 413 with X-Storage-* headers, alt_text/title/tags
  persistence.
* GET /api/v1/media/{id} — detail with ``last_used_at`` annotated.
* GET /api/v1/media/ — recency default, filter composition, workspace
  scoping (other-workspace assets in the same org are not visible
  unless they're org-shared).
"""

from __future__ import annotations

import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="media@example.com",
        password="testpass123",
        name="Media",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Media Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Media WS", organization=organization)


@pytest.fixture
def other_workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Other WS", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
    return WorkspaceMembership.objects.create(
        user=user, workspace=workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-media",
        account_name="Media LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="media",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


# A 1x1 PNG (smallest valid image). Used as the upload payload everywhere.
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c63600000000005000156a168320000000049454e44ae426082"
)


def _png(content: bytes = PNG_1X1, name: str = "hero.png"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name=name, content=content, content_type="image/png")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestUpload:
    def test_uploads_an_image(self, client_with_token):
        r = client_with_token.post(
            "/api/v1/media/",
            data={"file": _png(), "alt_text": "tiny test png", "tags": "test,smoke"},
        )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["filename"] == "hero.png"
        assert body["media_type"] == "image"
        assert body["alt_text"] == "tiny test png"
        assert sorted(body["tags"]) == ["smoke", "test"]
        assert body["processing_status"] in {"pending", "processing", "completed"}
        # MediaAsset row exists.
        from apps.media_library.models import MediaAsset

        assert MediaAsset.objects.count() == 1

    def test_unauthenticated_returns_401(self):
        c = _SecureClient()
        r = c.post("/api/v1/media/", data={"file": _png()})
        assert r.status_code == 401

    def test_without_upload_media_permission_returns_403(self, db, user, owner_memberships, workspace, social_account):
        perms = [p for p in PERMISSION_KEYS if p != "upload_media"]
        key = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=user,
            name="no-upload",
            permissions=perms,
        )
        c = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")
        r = c.post("/api/v1/media/", data={"file": _png()})
        assert r.status_code == 403
        assert "upload_media" in r.json()["detail"]

    def test_idempotency_replays_the_same_response(self, client_with_token):
        first = client_with_token.post(
            "/api/v1/media/",
            data={"file": _png(), "idempotency_key": "abc-1"},
        )
        assert first.status_code == 201, first.content
        second = client_with_token.post(
            "/api/v1/media/",
            data={"file": _png(), "idempotency_key": "abc-1"},
        )
        assert second.status_code == 201
        # Same asset ID — no duplicate row.
        assert first.json()["id"] == second.json()["id"]
        from apps.media_library.models import MediaAsset

        assert MediaAsset.objects.count() == 1


# ---------------------------------------------------------------------------
# Storage quota (Gap 1a)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestStorageQuota:
    def test_413_when_quota_exceeded(self, settings, client_with_token):
        # Cap at 100 bytes so the small PNG (~70 bytes) plus a tiny
        # pre-existing asset trips the limit on the next upload.
        settings.STORAGE_QUOTA_TIERS = {}
        settings.STORAGE_QUOTA_DEFAULT = 100
        # Seed an asset that already consumes ~70 bytes so the next
        # upload would push us above 100.
        from apps.media_library.models import MediaAsset

        MediaAsset.objects.create(
            organization=client_with_token.cookies and None,  # unused; positional below
        ) if False else None  # placeholder, real seed below

        # Create a real seed asset via the service so file_size is set.
        from apps.media_library.services import create_asset

        api_key = MediaAsset.objects.model._meta  # noqa: F841 — ensure import works
        # Resolve the workspace + organization via the issued key.
        from apps.api_keys.models import ApiKey

        keys = ApiKey.objects.all()
        api_key = keys.get()
        ws = api_key.workspace
        create_asset(
            organization=ws.organization,
            workspace=ws,
            uploaded_file=_png(name="seed.png"),
            uploaded_by=None,
        )

        r = client_with_token.post("/api/v1/media/", data={"file": _png(name="next.png")})
        assert r.status_code == 413, r.content
        body = r.json()
        assert body["error"] == "storage_quota_exceeded"
        assert body["used_bytes"] > 0
        assert body["limit_bytes"] == 100
        assert body["attempted_bytes"] > 0
        # Headers.
        assert r["X-Storage-Limit"] == "100"
        assert r["X-Storage-Used"] == str(body["used_bytes"])
        assert r["X-Storage-Remaining"] == str(max(100 - body["used_bytes"], 0))

    def test_org_setting_override_takes_precedence(self, settings, client_with_token):
        settings.STORAGE_QUOTA_TIERS = {"hobby": 100}
        settings.STORAGE_QUOTA_DEFAULT = 100
        # Apply an override large enough that the upload succeeds.
        from apps.api_keys.models import ApiKey
        from apps.settings_manager.models import OrgSetting

        api_key = ApiKey.objects.get()
        OrgSetting.objects.create(
            organization=api_key.workspace.organization,
            key="media.storage_quota_bytes_override",
            value=10_000_000,
        )
        r = client_with_token.post("/api/v1/media/", data={"file": _png()})
        assert r.status_code == 201, r.content

    def test_quota_disabled_skips_enforcement(self, settings, client_with_token):
        settings.STORAGE_QUOTA_ENABLED = False
        settings.STORAGE_QUOTA_DEFAULT = 1  # would otherwise fail instantly
        r = client_with_token.post("/api/v1/media/", data={"file": _png()})
        assert r.status_code == 201, r.content

    def test_me_endpoint_surfaces_storage_block(self, client_with_token):
        body = client_with_token.get("/api/v1/me/").json()
        assert "storage" in body
        s = body["storage"]
        assert s["limit_bytes"] > 0
        assert s["used_bytes"] >= 0
        assert s["remaining_bytes"] == max(s["limit_bytes"] - s["used_bytes"], 0)


# ---------------------------------------------------------------------------
# List + filters (Gap 1b)
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_assets(db, workspace, other_workspace):
    """A grab-bag of assets exercising every filter path."""
    from apps.media_library.models import MediaAsset

    org = workspace.organization

    def _seed(workspace, *, name, media_type="image", tags=None, is_starred=False, status="completed"):
        f = _png(name=name)
        a = MediaAsset(
            organization=org,
            workspace=workspace,
            filename=name,
            file=f,
            media_type=media_type,
            mime_type="image/png",
            file_size=f.size,
            tags=tags or [],
            is_starred=is_starred,
            processing_status=status,
        )
        a.save()
        return a

    return {
        "current": _seed(workspace, name="current.png", tags=["hero", "launch"]),
        "starred": _seed(workspace, name="starred.png", is_starred=True, tags=["hero"]),
        "video": _seed(workspace, name="clip.mp4", media_type="video", tags=["launch"]),
        "pending": _seed(workspace, name="pending.png", status="pending"),
        "shared": _seed(None, name="shared.png", tags=["brand"]),  # org-shared (workspace=NULL)
        "foreign": _seed(other_workspace, name="foreign.png", tags=["hero"]),
    }


@pytest.mark.django_db
class TestList:
    def test_default_returns_completed_workspace_and_shared_only(self, client_with_token, seeded_assets):
        body = client_with_token.get("/api/v1/media/").json()
        names = {item["filename"] for item in body["items"]}
        # Visible: current, starred, video, shared. Hidden: pending (status), foreign (workspace).
        assert "current.png" in names
        assert "starred.png" in names
        assert "clip.mp4" in names
        assert "shared.png" in names
        assert "pending.png" not in names
        assert "foreign.png" not in names

    def test_media_type_filter(self, client_with_token, seeded_assets):
        body = client_with_token.get("/api/v1/media/?media_type=video").json()
        names = {item["filename"] for item in body["items"]}
        assert names == {"clip.mp4"}

    def test_is_starred_filter(self, client_with_token, seeded_assets):
        body = client_with_token.get("/api/v1/media/?is_starred=true").json()
        names = {item["filename"] for item in body["items"]}
        assert names == {"starred.png"}

    def test_tags_filter_is_and_semantics(self, client_with_token, seeded_assets):
        # ``hero,launch`` → only current.png has BOTH.
        body = client_with_token.get("/api/v1/media/?tags=hero,launch").json()
        names = {item["filename"] for item in body["items"]}
        assert names == {"current.png"}

    def test_processing_status_any_includes_pending(self, client_with_token, seeded_assets):
        body = client_with_token.get("/api/v1/media/?processing_status=any").json()
        names = {item["filename"] for item in body["items"]}
        assert "pending.png" in names

    def test_cursor_pagination(self, client_with_token, seeded_assets):
        page1 = client_with_token.get("/api/v1/media/?limit=2").json()
        assert len(page1["items"]) == 2
        assert page1["next_cursor"] is not None
        page2 = client_with_token.get(f"/api/v1/media/?limit=2&cursor={page1['next_cursor']}").json()
        # No overlap between pages.
        ids1 = {i["id"] for i in page1["items"]}
        ids2 = {i["id"] for i in page2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_legacy_asset_with_null_organization_serializes(self, client_with_token, workspace):
        """Regression: ``MediaAsset.organization`` is nullable (legacy /
        pre-migration rows can have org=NULL). The list endpoint hit a
        500 on staging on 2026-06-01 because ``MediaAssetResponse``
        declared ``organization_id: uuid.UUID`` instead of ``UUID | None``,
        so Pydantic rejected any row whose org was None.
        """
        from apps.media_library.models import MediaAsset

        MediaAsset.objects.create(
            organization=None,  # the bug
            workspace=workspace,
            filename="legacy.png",
            file=_png(name="legacy.png"),
            media_type="image",
            mime_type="image/png",
            file_size=68,
            processing_status="completed",
        )
        r = client_with_token.get("/api/v1/media/")
        assert r.status_code == 200, r.content
        body = r.json()
        names = {item["filename"] for item in body["items"]}
        assert "legacy.png" in names
        legacy = next(i for i in body["items"] if i["filename"] == "legacy.png")
        assert legacy["organization_id"] is None

    def test_last_used_at_populated_when_referenced(self, client_with_token, seeded_assets, user):
        """The annotation must walk through PostMedia → Post.created_at
        because PostMedia has no created_at of its own.
        """
        from apps.composer.models import Post, PostMedia

        target = seeded_assets["current"]
        post = Post.objects.create(workspace=target.workspace, author=user, caption="uses current")
        PostMedia.objects.create(post=post, media_asset=target, position=0)

        body = client_with_token.get(f"/api/v1/media/{target.id}").json()
        assert body["last_used_at"] is not None
        # ISO 8601 with Z suffix (Gap 5 format).
        assert body["last_used_at"].endswith("Z")

    def test_last_used_at_null_when_never_referenced(self, client_with_token, seeded_assets):
        unused = seeded_assets["current"]
        body = client_with_token.get(f"/api/v1/media/{unused.id}").json()
        assert body["last_used_at"] is None


# ---------------------------------------------------------------------------
# MCP parity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMcpParity:
    def _mcp(self, client, name, args):
        r = client.post(
            "/api/v1/mcp/",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": name, "arguments": args},
                    "id": 1,
                }
            ),
            content_type="application/json",
        )
        envelope = r.json()
        if "error" in envelope:
            return None, envelope["error"]
        return json.loads(envelope["result"]["content"][0]["text"]), None

    def test_search_media_returns_completed_assets(self, client_with_token, seeded_assets):
        body, err = self._mcp(client_with_token, "search_media", {})
        assert err is None, err
        names = {item["filename"] for item in body["items"]}
        assert "pending.png" not in names
        assert "current.png" in names

    def test_get_media_matches_rest_detail(self, client_with_token, seeded_assets):
        target = seeded_assets["current"]
        rest = client_with_token.get(f"/api/v1/media/{target.id}").json()
        mcp_body, err = self._mcp(client_with_token, "get_media", {"media_id": str(target.id)})
        assert err is None
        assert mcp_body == rest

    def test_upload_media_via_base64(self, client_with_token):
        import base64

        encoded = base64.b64encode(PNG_1X1).decode()
        body, err = self._mcp(
            client_with_token,
            "upload_media",
            {"filename": "mcp.png", "content_base64": encoded, "alt_text": "via mcp"},
        )
        assert err is None, err
        assert body["filename"] == "mcp.png"
        assert body["alt_text"] == "via mcp"

    def test_upload_media_rejects_oversize_base64(self, client_with_token):
        """Sending just over the 1 MB raw cap (~1.4 MB base64) — comfortably
        under Django's 2.5 MB DATA_UPLOAD_MAX_MEMORY_SIZE so our explicit
        JSON-RPC check fires first.
        """
        import base64

        oversize_raw = b"x" * (1024 * 1024 + 1024)  # 1 MB + 1 KB
        oversize_b64 = base64.b64encode(oversize_raw).decode()
        body, err = self._mcp(
            client_with_token,
            "upload_media",
            {"filename": "big.bin", "content_base64": oversize_b64},
        )
        assert err is not None
        assert "MCP upload limit" in err["message"]
