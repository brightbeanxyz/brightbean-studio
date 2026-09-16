from __future__ import annotations

import json
import shutil

import pytest
from django.conf import settings as django_settings
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.composer.models import PlatformPost, Post, PostMedia
from apps.media_library.models import MediaAsset
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    user = User.objects.create_user(
        email="metodo3r@example.com",
        password="testpass123",
        name="Metodo 3R",
        tos_accepted_at=timezone.now(),
    )
    membership = user.org_memberships.first()
    membership.org_role = OrgMembership.OrgRole.OWNER
    membership.save(update_fields=["org_role"])
    return user


@pytest.fixture
def organization(user):
    return user.org_memberships.first().organization


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Metodo 3R WS", organization=organization)


@pytest.fixture
def workspace_owner(db, user, workspace):
    return WorkspaceMembership.objects.create(
        user=user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
    )


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-metodo3r",
        account_name="Metodo 3R Instagram",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.fixture
def issued_key(db, user, workspace_owner, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="metodo3r-import",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def client_with_token(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


def _payload():
    return {
        "project": "piloto-metodo3r",
        "brand": "Metodo 3R",
        "presenter": "Cassia Saito",
        "language": "pt-BR",
        "humanGate": "required_before_publish",
        "item": {
            "id": "launch-d01-v02",
            "type": "alc",
            "title": "suspiro-ar-alc",
            "video": "aprovados/launch-d01-v02/launch-d01-v02.mp4",
            "selectedImage": "aprovados/launch-d01-v02/launch-d01-v02.jpg",
            "alternateImages": [],
            "qaNotes": ["Video v10 assistido integralmente e aprovado para agendamento."],
            "durationSeconds": 27,
        },
        "schedule": {
            "platforms": ["instagram"],
            "scheduledAt": "2026-09-16T12:00:00Z",
            "timezone": "America/Sao_Paulo",
            "caption": "Video v10 aprovado para agendamento.",
        },
        "idempotencyKey": "metodo3r-launch-d01-v02",
    }


@pytest.mark.django_db
class TestMetodo3RImport:
    def test_import_creates_draft_with_proposed_publish_time(self, client_with_token, social_account):
        social_account.platform = "instagram"
        social_account.save(update_fields=["platform"])

        response = client_with_token.post(
            "/api/v1/posts/imports/metodo3r/",
            data=json.dumps(_payload()),
            content_type="application/json",
        )

        assert response.status_code == 201, response.content
        body = response.json()
        assert body["status"] == "draft"
        assert body["imported_platforms"] == ["instagram"]
        assert body["scheduled_at"] is None
        assert body["proposed_publish_at"] == "2026-09-16T12:00:00Z"
        assert body["status_url"].startswith("/api/v1/posts/")

        post = Post.objects.get()
        platform_post = PlatformPost.objects.get(post=post)
        assert post.origin == Post.Origin.IMPORT
        assert post.title == "suspiro-ar-alc"
        assert post.caption == "Video v10 aprovado para agendamento."
        assert post.scheduled_at is None
        assert post.proposed_publish_at is not None
        assert platform_post.status == PlatformPost.Status.DRAFT
        assert platform_post.platform_extra["source"] == "metodo3r"
        assert platform_post.platform_extra["video_path"] == "aprovados/launch-d01-v02/launch-d01-v02.mp4"

    def test_import_replays_idempotency_key(self, client_with_token, social_account):
        social_account.platform = "instagram"
        social_account.save(update_fields=["platform"])
        payload = _payload()

        first = client_with_token.post(
            "/api/v1/posts/imports/metodo3r/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        second = client_with_token.post(
            "/api/v1/posts/imports/metodo3r/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert first.status_code == 201, first.content
        assert second.status_code == 201, second.content
        assert first.json()["post_id"] == second.json()["post_id"]
        assert first.json()["status_url"] == second.json()["status_url"]
        assert Post.objects.count() == 1
        assert PlatformPost.objects.count() == 1

    def test_import_attaches_local_media_when_import_root_is_configured(self, client_with_token, settings, social_account):
        social_account.platform = "instagram"
        social_account.save(update_fields=["platform"])
        import_root = django_settings.BASE_DIR / ".tmp_metodo3r_import_test"
        if import_root.exists():
            shutil.rmtree(import_root)
        media_dir = import_root / "aprovados" / "launch-d01-v02"
        media_dir.mkdir(parents=True)
        video = media_dir / "launch-d01-v02.mp4"
        image = media_dir / "launch-d01-v02.jpg"
        video.write_bytes(b"video-bytes")
        image.write_bytes(b"image-bytes")
        settings.METODO3R_IMPORT_ROOT = str(import_root)
        payload = _payload()
        payload["idempotencyKey"] = "metodo3r-launch-d01-v02-with-media"

        try:
            response = client_with_token.post(
                "/api/v1/posts/imports/metodo3r/",
                data=json.dumps(payload),
                content_type="application/json",
            )

            assert response.status_code == 201, response.content
            post = Post.objects.get()
            attachments = list(PostMedia.objects.filter(post=post).select_related("media_asset").order_by("position"))
            assert [attachment.media_asset.filename for attachment in attachments] == [
                "launch-d01-v02.mp4",
                "launch-d01-v02.jpg",
            ]
            assert attachments[0].media_asset.media_type == MediaAsset.MediaType.VIDEO
            assert attachments[0].media_asset.duration == 27
            assert attachments[1].media_asset.media_type == MediaAsset.MediaType.IMAGE
            platform_post = PlatformPost.objects.get(post=post)
            assert platform_post.platform_extra["media_asset_ids"] == [
                str(attachments[0].media_asset_id),
                str(attachments[1].media_asset_id),
            ]
        finally:
            shutil.rmtree(import_root, ignore_errors=True)

    def test_import_rejects_platform_without_allowlisted_account(self, client_with_token):
        payload = _payload()
        payload["schedule"]["platforms"] = ["youtube_shorts"]

        response = client_with_token.post(
            "/api/v1/posts/imports/metodo3r/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert response.status_code == 422
        assert Post.objects.count() == 0
