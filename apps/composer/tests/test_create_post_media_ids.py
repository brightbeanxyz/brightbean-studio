"""create_post must match media ids regardless of the caller's id shape.

REST passes UUID objects (Pydantic list[uuid.UUID]); MCP passes UUID strings off
the JSON-RPC wire. create_post normalizes both to UUID, so a valid in-workspace
asset is matched even when the id arrives as a non-canonical (e.g. uppercase)
UUID string.
"""

import pytest

from apps.composer.models import PostMedia
from apps.composer.services import create_post
from apps.media_library.models import MediaAsset
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace


def _setup():
    org = Organization.objects.create(name="Org")
    ws = Workspace.objects.create(organization=org, name="WS")
    sa = SocialAccount.objects.create(
        workspace=ws,
        platform="linkedin_personal",
        account_platform_id="li-1",
        account_name="x",
        connection_status="connected",
    )
    asset = MediaAsset.objects.create(
        organization=org,
        workspace=ws,
        filename="a.mp4",
        media_type=MediaAsset.MediaType.VIDEO,
        file_size=1,
        processing_status=MediaAsset.ProcessingStatus.COMPLETED,
    )
    return ws, sa, asset


@pytest.mark.django_db
@pytest.mark.parametrize("make_id", [str, lambda a: str(a).upper(), lambda a: a])
def test_create_post_matches_media_id_in_any_form(make_id):
    ws, sa, asset = _setup()
    media_id = make_id(asset.id)
    post = create_post(workspace=ws, social_account=sa, caption="hi", media_asset_ids=[media_id], status="draft")
    assert PostMedia.objects.filter(post=post, media_asset=asset).exists()


@pytest.mark.django_db
def test_create_post_rejects_unknown_or_invalid_media_id():
    ws, sa, _asset = _setup()
    with pytest.raises(ValueError, match="not found in workspace"):
        create_post(workspace=ws, social_account=sa, caption="hi", media_asset_ids=["not-a-uuid"], status="draft")
