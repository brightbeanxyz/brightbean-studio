"""The per-account cap is a window around the PUBLISH time, not the write time.

``PLATFORM_DAILY_POST_LIMIT`` mirrors what each platform allows to be
*published* per rolling 24 h. Counting rows by when they were written instead
turns a planned schedule into a burst: load a month of Instagram posts in one
sitting and the 26th is refused, even though the account will publish at most
one per day and has spent none of the platform's real budget.

Re-timing is the other half. ``PATCH /posts/{id}`` moves the publish moment,
which is the anchor itself, so it has to be checked too or the cap is only
enforced against callers who schedule honestly the first time.
"""

from __future__ import annotations

import datetime as dt
import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.composer.models import PlatformPost, Post
from apps.media_library.models import MediaAsset
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def workspace(db):
    from apps.organizations.models import Organization
    from apps.workspaces.models import Workspace

    org = Organization.objects.create(name="Quota Org")
    return Workspace.objects.create(name="Quota WS", organization=org)


@pytest.fixture
def instagram(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram_login",
        account_platform_id="ig-quota",
        account_name="quota",
        connection_status="connected",
    )


@pytest.fixture
def api(db, workspace, instagram):
    from apps.accounts.models import User

    user = User.objects.create_user(
        email="quota@example.com", password="x", name="Quota", tos_accepted_at=timezone.now()
    )
    OrgMembership.objects.create(user=user, organization=workspace.organization, org_role=OrgMembership.OrgRole.OWNER)
    WorkspaceMembership.objects.create(
        user=user, workspace=workspace, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    key = services.issue_api_key(
        workspace=workspace,
        social_accounts=[instagram],
        issued_by=user,
        name="quota",
        permissions=list(PERMISSION_KEYS),
    )
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {key.plaintext_token}")


def _iso(when):
    return when.isoformat().replace("+00:00", "Z")


def _image(workspace, name):
    return MediaAsset.objects.create(
        organization=workspace.organization,
        workspace=workspace,
        filename=f"{name}.jpg",
        media_type=MediaAsset.MediaType.IMAGE,
        mime_type="image/jpeg",
        file_size=1_000,
        processing_status=MediaAsset.ProcessingStatus.COMPLETED,
    )


def _schedule(api, workspace, instagram, when, caption):
    body = {
        "social_account_id": str(instagram.id),
        "caption": caption,
        "media_asset_ids": [str(_image(workspace, caption).id)],
        "action": "schedule",
        "scheduled_at": _iso(when),
    }
    return api.post("/api/v1/posts/", data=json.dumps(body), content_type="application/json")


def _patch(api, post_id, **body):
    return api.patch(f"/api/v1/posts/{post_id}", data=json.dumps(body), content_type="application/json")


class TestTheWindowFollowsThePublishTime:
    def test_a_month_of_posts_loaded_in_one_sitting_is_not_a_burst(self, api, workspace, instagram):
        base = timezone.now() + dt.timedelta(hours=2)

        for day in range(30):
            res = _schedule(api, workspace, instagram, base + dt.timedelta(days=day), f"p{day:02d}")
            assert res.status_code == 201, f"day {day}: {res.status_code} {res.content}"

        assert PlatformPost.objects.filter(social_account=instagram, status="scheduled").count() == 30

    def test_the_twenty_sixth_post_in_one_window_is_still_refused(self, api, workspace, instagram):
        base = timezone.now() + dt.timedelta(hours=2)
        for slot in range(25):
            assert (
                _schedule(api, workspace, instagram, base + dt.timedelta(minutes=slot), f"s{slot:02d}").status_code
                == 201
            )

        res = _schedule(api, workspace, instagram, base + dt.timedelta(minutes=25), "s25")

        assert res.status_code == 429, res.content
        assert res.json()["limit"] == 25

    def test_a_slot_outside_the_full_window_is_accepted(self, api, workspace, instagram):
        base = timezone.now() + dt.timedelta(hours=2)
        for slot in range(25):
            assert (
                _schedule(api, workspace, instagram, base + dt.timedelta(minutes=slot), f"t{slot:02d}").status_code
                == 201
            )

        res = _schedule(api, workspace, instagram, base + dt.timedelta(hours=25), "t25")

        assert res.status_code == 201, res.content

    def test_a_row_that_can_never_publish_spends_nothing(self, workspace, instagram):
        """No time on the row and none on its post means no publish moment, and
        ``effective_at__lte=now`` never matches NULL: the publisher ignores it
        forever. Charging it against the cap would refuse real posts on behalf
        of one that cannot go out.
        """
        from apps.api.limits import count_publishes_in_window

        post = Post.objects.create(workspace=workspace, caption="timeless")
        pp = PlatformPost.objects.create(post=post, social_account=instagram, status="draft")
        PlatformPost.objects.filter(pk=pp.pk).update(status="scheduled", updated_at=timezone.now())

        assert count_publishes_in_window(instagram, timezone.now()) == 0


class TestReTimingIsCheckedToo:
    def test_a_patch_cannot_walk_a_post_into_a_full_window(self, api, workspace, instagram):
        base = timezone.now() + dt.timedelta(hours=2)
        for slot in range(25):
            assert (
                _schedule(api, workspace, instagram, base + dt.timedelta(minutes=slot), f"w{slot:02d}").status_code
                == 201
            )
        spare = _schedule(api, workspace, instagram, base + dt.timedelta(days=5), "w99")
        assert spare.status_code == 201

        res = _patch(api, spare.json()["id"], scheduled_at=_iso(base + dt.timedelta(minutes=30)))

        assert res.status_code == 429, res.content
        assert PlatformPost.objects.get(post_id=spare.json()["id"]).scheduled_at > base + dt.timedelta(days=4)

    def test_a_post_can_be_nudged_inside_a_window_it_already_fills(self, api, workspace, instagram):
        """The row being moved must not count against itself."""
        base = timezone.now() + dt.timedelta(hours=2)
        first = None
        for slot in range(25):
            res = _schedule(api, workspace, instagram, base + dt.timedelta(minutes=slot), f"n{slot:02d}")
            assert res.status_code == 201
            first = first or res.json()["id"]

        res = _patch(api, first, scheduled_at=_iso(base + dt.timedelta(minutes=40)))

        assert res.status_code == 200, res.content
