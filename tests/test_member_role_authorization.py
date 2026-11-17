"""Workspace membership is not authorization.

Eight reports against ``1d11c52`` shared one shape: a view checked that the
caller belonged to the workspace and stopped there, so the role model's
``False`` flags were never consulted. A built-in viewer — or a client-portal
user, whose magic link is an ordinary Django login — could rename the
workspace and plant an HTML "logo" on the app's origin, swap another author's
post media, force a post's publish status, delete posts, cancel queued posts,
and a contributor could read analytics. Two comment paths had their own
scoping gaps: internal replies reached clients, and a manager of one workspace
could delete comments in any other by id.

Each test drives the real route as the role that used to get through, and
checks the database (or the response body) as well as the status code.
"""

import base64
import inspect
import io
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import PostComment
from apps.calendar.models import Queue, QueueEntry
from apps.composer.models import ContentCategory, PlatformPost, Post, PostMedia, PostTemplate, Tag
from apps.media_library.models import MediaAsset
from apps.media_library.validators import sniff_mime
from apps.members.models import CustomRole, OrgMembership, WorkspaceMembership
from apps.notifications.models import EventType, Notification
from apps.organizations.models import Organization
from apps.social_accounts.models import AnalyticsPlatformConfig, SocialAccount
from apps.workspaces.models import Workspace

TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="bb-test-role-authz-")

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
HTML_PAGE = b"<!doctype html><script>document.title='pwned'</script>"


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def _png(size=(1, 1)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def _user(email):
    return User.objects.create_user(email=email, password="pw-123456", tos_accepted_at=timezone.now())


def _member(user, workspace, role):
    OrgMembership.objects.get_or_create(
        user=user, organization=workspace.organization, defaults={"org_role": OrgMembership.OrgRole.MEMBER}
    )
    WorkspaceMembership.objects.create(user=user, workspace=workspace, workspace_role=role)
    return user


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class RoleAuthorizationBase(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org")
        self.ws = Workspace.objects.create(organization=self.org, name="Original name")
        self.account = SocialAccount.objects.create(
            workspace=self.ws,
            platform="linkedin_personal",
            account_platform_id="li-1",
            account_name="Brand",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        self.author = _member(_user("author@x.test"), self.ws, "manager")

    def _as(self, role, email=None):
        user = _member(_user(email or f"{role}@x.test"), self.ws, role)
        self.client.force_login(user)
        return user

    def _post(self, status="draft", author=None, **post_fields):
        post = Post.objects.create(workspace=self.ws, author=author or self.author, caption="hi", **post_fields)
        pp = PlatformPost.objects.create(post=post, social_account=self.account, status=status)
        return post, pp


# ---------------------------------------------------------------------------
# Report 1 — workspace name/logo, and executable uploads on the app's origin
# ---------------------------------------------------------------------------


class WorkspaceSettingsTests(RoleAuthorizationBase):
    def _settings_url(self):
        return reverse("workspaces:settings", kwargs={"workspace_id": self.ws.id})

    def test_viewer_cannot_rename_or_replace_the_logo(self):
        for role in ("viewer", "client", "editor"):
            with self.subTest(role=role):
                self._as(role)
                logo = SimpleUploadedFile("logo.png", PNG_1PX, content_type="image/png")

                response = self.client.post(self._settings_url(), {"name": "Renamed", "icon": logo})

                self.ws.refresh_from_db()
                assert response.status_code == 403
                assert self.ws.name == "Original name"
                assert not self.ws.icon

    def test_viewer_still_sees_the_settings_page_read_only(self):
        self._as("viewer")

        response = self.client.get(self._settings_url())

        assert response.status_code == 200
        assert b"Save Changes" not in response.content
        assert b"Upload Logo" not in response.content

    def test_manager_logo_is_judged_by_its_bytes_and_renamed_to_match(self):
        self.client.force_login(self.author)
        html = SimpleUploadedFile("probe.html", HTML_PAGE, content_type="image/jpeg")

        self.client.post(self._settings_url(), {"icon": html})
        self.ws.refresh_from_db()
        assert not self.ws.icon, "HTML claimed as image/jpeg must be refused"

        disguised = SimpleUploadedFile("probe.html", PNG_1PX, content_type="image/png")
        self.client.post(self._settings_url(), {"icon": disguised})
        self.ws.refresh_from_db()
        assert self.ws.icon.name.endswith("/probe.png")

    def test_avatar_polyglot_cannot_keep_an_html_name(self):
        user = _user("me@x.test")
        self.client.force_login(user)
        avatar = SimpleUploadedFile("me.html", _png((200, 200)), content_type="image/png")

        self.client.post(reverse("accounts:settings"), {"action": "update_photo", "avatar": avatar})

        user.refresh_from_db()
        assert user.avatar.name.endswith("/me.png")


# ---------------------------------------------------------------------------
# Report 2 — composer media routes
# ---------------------------------------------------------------------------


class ComposerMediaTests(RoleAuthorizationBase):
    def test_viewer_cannot_upload_to_another_authors_post(self):
        post, pp = self._post(status="approved")
        self._as("viewer")
        upload = SimpleUploadedFile("a.png", PNG_1PX, content_type="image/png")

        response = self.client.post(
            reverse("composer:upload_media_post", kwargs={"workspace_id": self.ws.id, "post_id": post.id}),
            {"file": upload},
        )

        pp.refresh_from_db()
        assert response.status_code == 403
        assert not MediaAsset.objects.filter(workspace=self.ws).exists()
        assert not PostMedia.objects.filter(post=post).exists()
        assert pp.status == "approved"

    def test_contributor_can_upload_to_own_post_but_not_anothers(self):
        contributor = self._as("contributor")
        own, _ = self._post(author=contributor)
        theirs, _ = self._post()

        def upload(post):
            return self.client.post(
                reverse("composer:upload_media_post", kwargs={"workspace_id": self.ws.id, "post_id": post.id}),
                {"file": SimpleUploadedFile("a.png", PNG_1PX, content_type="image/png")},
            )

        assert upload(own).status_code == 200
        assert upload(theirs).status_code == 403
        assert PostMedia.objects.filter(post=own).count() == 1
        assert not PostMedia.objects.filter(post=theirs).exists()

    def test_composer_upload_refuses_html_whatever_it_claims(self):
        self.client.force_login(self.author)

        response = self.client.post(
            reverse("composer:upload_media", kwargs={"workspace_id": self.ws.id}),
            {"file": SimpleUploadedFile("probe.html", HTML_PAGE, content_type="image/png")},
        )

        assert response.status_code == 400
        assert not MediaAsset.objects.filter(workspace=self.ws).exists()

    def test_composer_upload_stores_under_the_sniffed_extension(self):
        self.client.force_login(self.author)

        response = self.client.post(
            reverse("composer:upload_media", kwargs={"workspace_id": self.ws.id}),
            {"file": SimpleUploadedFile("probe.html", PNG_1PX, content_type="text/html")},
        )

        asset = MediaAsset.objects.get(workspace=self.ws)
        assert response.status_code == 200
        assert Path(asset.file.name).suffix == ".png"
        assert asset.mime_type == "image/png"
        assert asset.filename == "probe.html"

    def test_viewer_cannot_attach_or_remove_media(self):
        post, _ = self._post()
        asset = MediaAsset.objects.create(
            organization=self.org,
            workspace=self.ws,
            file=SimpleUploadedFile("a.png", PNG_1PX),
            filename="a.png",
            media_type=MediaAsset.MediaType.IMAGE,
        )
        attachment = PostMedia.objects.create(post=post, media_asset=asset, position=1)
        self._as("viewer")

        attach = self.client.post(
            reverse("composer:attach_media", kwargs={"workspace_id": self.ws.id, "post_id": post.id}),
            {"media_asset_id": str(asset.id)},
        )
        remove = self.client.post(
            reverse(
                "composer:remove_media",
                kwargs={"workspace_id": self.ws.id, "post_id": post.id, "media_id": attachment.id},
            )
        )

        assert attach.status_code == 403
        assert remove.status_code == 403
        assert PostMedia.objects.filter(id=attachment.id).exists()

    def test_viewer_cannot_upload_a_thumbnail(self):
        self._as("viewer")

        response = self.client.post(
            reverse("composer:thumbnail_upload", kwargs={"workspace_id": self.ws.id}),
            {"file": SimpleUploadedFile("t.png", PNG_1PX, content_type="image/png")},
        )

        assert response.status_code == 403
        assert not MediaAsset.objects.filter(workspace=self.ws).exists()


# ---------------------------------------------------------------------------
# Report 3 — per-account status transitions
# ---------------------------------------------------------------------------


class TransitionTests(RoleAuthorizationBase):
    def _transition(self, post, pp, target):
        return self.client.post(
            reverse(
                "composer:transition_platform_post",
                kwargs={"workspace_id": self.ws.id, "post_id": post.id, "platform_post_id": pp.id},
            ),
            {"target_status": target},
        )

    def test_viewer_and_client_cannot_unschedule_another_authors_post(self):
        post, pp = self._post(status="scheduled")
        for role in ("viewer", "client", "contributor"):
            with self.subTest(role=role):
                self._as(role)

                response = self._transition(post, pp, "draft")

                pp.refresh_from_db()
                assert response.status_code == 403
                assert pp.status == "scheduled"

    def test_nobody_can_mark_a_post_published_by_hand(self):
        post, pp = self._post(status="publishing")
        self.client.force_login(self.author)

        for target in ("published", "failed"):
            response = self._transition(post, pp, target)
            pp.refresh_from_db()
            assert response.status_code == 400
            assert pp.status == "publishing"
            assert pp.published_at is None

    def test_author_can_still_move_own_post_to_draft(self):
        post, pp = self._post(status="scheduled")
        self.client.force_login(self.author)

        response = self._transition(post, pp, "draft")

        pp.refresh_from_db()
        assert response.status_code == 200
        assert pp.status == "draft"


# ---------------------------------------------------------------------------
# Report 4 — post deletion
# ---------------------------------------------------------------------------


class PostDeleteTests(RoleAuthorizationBase):
    def _delete(self, post):
        return self.client.post(
            reverse("composer:post_delete", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
        )

    def test_viewer_client_and_contributor_cannot_delete_another_authors_post(self):
        for status in ("scheduled", "published"):
            post, pp = self._post(status=status)
            for role in ("viewer", "client", "contributor"):
                with self.subTest(status=status, role=role):
                    self._as(role, email=f"{role}-{status}@x.test")

                    response = self._delete(post)

                    assert response.status_code == 403
                    assert Post.objects.filter(id=post.id).exists()
                    assert PlatformPost.objects.filter(id=pp.id).exists()

    def test_contributor_can_delete_own_post(self):
        contributor = self._as("contributor")
        post, _ = self._post(author=contributor)

        assert self._delete(post).status_code == 204
        assert not Post.objects.filter(id=post.id).exists()


# ---------------------------------------------------------------------------
# Report 5 — publishing queues
# ---------------------------------------------------------------------------


class QueueTests(RoleAuthorizationBase):
    def setUp(self):
        super().setUp()
        when = timezone.now() + timedelta(days=2)
        self.post, self.pp = self._post(status="scheduled", scheduled_at=when)
        PlatformPost.objects.filter(id=self.pp.id).update(scheduled_at=when)
        self.queue = Queue.objects.create(workspace=self.ws, name="Q", social_account=self.account)
        self.entry = QueueEntry.objects.create(
            queue=self.queue, post=self.post, position=1, assigned_slot_datetime=when
        )

    def _url(self, name, **extra):
        return reverse(f"calendar:{name}", kwargs={"workspace_id": self.ws.id, **extra})

    def test_viewer_cannot_cancel_a_queued_post(self):
        self._as("viewer")

        response = self.client.post(self._url("queue_entry_remove", queue_id=self.queue.id, entry_id=self.entry.id))

        self.pp.refresh_from_db()
        assert response.status_code == 403
        assert QueueEntry.objects.filter(id=self.entry.id).exists()
        assert self.pp.status == "scheduled"

    def test_viewer_cannot_create_delete_reorder_or_reslot_queues(self):
        self._as("viewer")

        responses = {
            "create": self.client.post(
                self._url("queue_create"), {"name": "New", "social_account_id": str(self.account.id)}
            ),
            "delete": self.client.post(self._url("queue_delete", queue_id=self.queue.id)),
            "reorder": self.client.post(
                self._url("queue_reorder", queue_id=self.queue.id), {"entry_ids": str(self.entry.id)}
            ),
            "reslot": self.client.post(self._url("queue_entry_reslot", queue_id=self.queue.id, entry_id=self.entry.id)),
        }

        assert {name: r.status_code for name, r in responses.items()} == dict.fromkeys(responses, 403)
        assert Queue.objects.filter(workspace=self.ws).count() == 1

    def test_author_can_remove_own_post_from_the_queue(self):
        self.client.force_login(self.author)

        response = self.client.post(self._url("queue_entry_remove", queue_id=self.queue.id, entry_id=self.entry.id))

        assert response.status_code == 200
        assert not QueueEntry.objects.filter(id=self.entry.id).exists()

    def test_queue_page_hides_controls_the_viewer_cannot_use(self):
        self._as("viewer")

        listing = self.client.get(self._url("queue_list"))
        detail = self.client.get(self._url("queue_detail", queue_id=self.queue.id))

        create_url = self._url("queue_create")
        delete_url = self._url("queue_delete", queue_id=self.queue.id)
        assert create_url.encode() not in listing.content
        assert delete_url.encode() not in listing.content
        remove_url = self._url("queue_entry_remove", queue_id=self.queue.id, entry_id=self.entry.id)
        assert remove_url.encode() not in detail.content


# ---------------------------------------------------------------------------
# Report 6 — analytics behind view_analytics
# ---------------------------------------------------------------------------


class AnalyticsTests(RoleAuthorizationBase):
    def setUp(self):
        super().setUp()
        AnalyticsPlatformConfig.objects.update_or_create(platform="instagram", defaults={"is_enabled": True})
        self.ig = SocialAccount.objects.create(
            workspace=self.ws,
            platform="instagram",
            account_platform_id="ig-1",
            account_name="SecretBrandIG",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )

    def test_contributor_without_view_analytics_is_refused(self):
        self._as("contributor")
        post, _ = self._post()

        urls = [
            reverse("analytics:index", kwargs={"workspace_id": self.ws.id}),
            reverse("analytics:account", kwargs={"workspace_id": self.ws.id, "account_id": self.ig.id}),
            reverse("analytics:status", kwargs={"workspace_id": self.ws.id, "account_id": self.ig.id}),
            reverse("analytics:post_detail", kwargs={"workspace_id": self.ws.id, "post_id": post.id}),
        ]

        assert [self.client.get(url).status_code for url in urls] == [403] * len(urls)

    def test_viewer_with_view_analytics_still_gets_in(self):
        self._as("viewer")

        response = self.client.get(
            reverse("analytics:account", kwargs={"workspace_id": self.ws.id, "account_id": self.ig.id})
        )

        assert response.status_code == 200
        assert b"SecretBrandIG" in response.content


# ---------------------------------------------------------------------------
# Reports 7 and 8 — comment visibility and scoping
# ---------------------------------------------------------------------------


class CommentTests(RoleAuthorizationBase):
    def test_client_never_receives_an_internal_reply(self):
        post, _ = self._post()
        root = PostComment.objects.create(post=post, author=self.author, body="external root", visibility="external")
        PostComment.objects.create(
            post=post, author=self.author, parent_comment=root, body="CANARY-INTERNAL-REPLY", visibility="internal"
        )
        self._as("client")

        response = self.client.post(
            reverse("approvals:add_comment", kwargs={"workspace_id": self.ws.id, "post_id": post.id}),
            {"body": "looks good", "visibility": "external"},
        )

        assert response.status_code == 200
        assert b"external root" in response.content
        assert b"CANARY-INTERNAL-REPLY" not in response.content

    def test_team_still_sees_internal_replies(self):
        post, _ = self._post()
        root = PostComment.objects.create(post=post, author=self.author, body="external root", visibility="external")
        PostComment.objects.create(
            post=post, author=self.author, parent_comment=root, body="CANARY-INTERNAL-REPLY", visibility="internal"
        )
        self.client.force_login(self.author)

        response = self.client.post(
            reverse("approvals:add_comment", kwargs={"workspace_id": self.ws.id, "post_id": post.id}),
            {"body": "noted", "visibility": "internal"},
        )

        assert b"CANARY-INTERNAL-REPLY" in response.content

    def test_client_cannot_fetch_an_internal_comments_attachment(self):
        post, _ = self._post()
        comment = PostComment.objects.create(
            post=post,
            author=self.author,
            body="internal",
            visibility="internal",
            attachment=SimpleUploadedFile("note.png", PNG_1PX, content_type="image/png"),
        )
        self._as("client")

        response = self.client.get(
            reverse(
                "approvals:comment_attachment",
                kwargs={"workspace_id": self.ws.id, "post_id": post.id, "comment_id": comment.id},
            )
        )

        assert response.status_code == 404

    def test_manager_cannot_delete_comments_outside_their_workspace(self):
        other_ws = Workspace.objects.create(organization=self.org, name="B")
        other_org_ws = Workspace.objects.create(organization=Organization.objects.create(name="Org C"), name="C")
        victims = []
        for ws in (other_ws, other_org_ws):
            author = _member(_user(f"author-{ws.name}@x.test"), ws, "manager")
            victim_post = Post.objects.create(workspace=ws, author=author, caption="x")
            victims.append(
                (
                    victim_post,
                    PostComment.objects.create(post=victim_post, author=author, body="b", visibility="internal"),
                )
            )

        # Manager of the URL's workspace, viewer in B, nothing at all in C.
        attacker = self._as("manager", email="attacker@x.test")
        _member(attacker, other_ws, "viewer")
        own_post, _ = self._post(author=attacker)

        for victim_post, comment in victims:
            for post_in_url in (own_post, victim_post):
                with self.subTest(workspace=victim_post.workspace.name, post=str(post_in_url.id)):
                    self.client.post(
                        reverse(
                            "approvals:delete_comment",
                            kwargs={"workspace_id": self.ws.id, "post_id": post_in_url.id, "comment_id": comment.id},
                        )
                    )

                    comment.refresh_from_db()
                    assert comment.deleted_at is None

    def test_manager_can_still_moderate_their_own_workspace(self):
        post, _ = self._post()
        commenter = _member(_user("commenter@x.test"), self.ws, "editor")
        comment = PostComment.objects.create(post=post, author=commenter, body="b", visibility="internal")
        self.client.force_login(self.author)

        response = self.client.post(
            reverse(
                "approvals:delete_comment",
                kwargs={"workspace_id": self.ws.id, "post_id": post.id, "comment_id": comment.id},
            )
        )

        comment.refresh_from_db()
        assert response.status_code == 200
        assert comment.deleted_at is not None


# ---------------------------------------------------------------------------
# Review follow-ups: gaps the per-report fixes left open
# ---------------------------------------------------------------------------


class PendingMediaRemovalTests(RoleAuthorizationBase):
    def _asset(self, uploaded_by):
        return MediaAsset.objects.create(
            organization=self.org,
            workspace=self.ws,
            uploaded_by=uploaded_by,
            file=SimpleUploadedFile("a.png", PNG_1PX),
            filename="a.png",
            media_type=MediaAsset.MediaType.IMAGE,
        )

    def _remove(self, asset_id):
        return self.client.post(
            reverse("composer:remove_pending_media", kwargs={"workspace_id": self.ws.id, "asset_id": asset_id})
        )

    def _set_pending(self, *asset_ids):
        session = self.client.session
        session[f"pending_media_{self.ws.id}"] = [str(a) for a in asset_ids]
        session.save()

    def test_contributor_cannot_delete_a_teammates_asset_by_id(self):
        theirs = self._asset(self.author)
        self._as("contributor")

        self._remove(theirs.id)

        assert MediaAsset.objects.filter(id=theirs.id).exists()

    def test_a_library_asset_picked_as_pending_is_only_unqueued(self):
        contributor = self._as("contributor")
        mine = self._asset(contributor)
        post, _ = self._post()
        PostMedia.objects.create(post=post, media_asset=mine, position=1)
        self._set_pending(mine.id)

        self._remove(mine.id)

        assert MediaAsset.objects.filter(id=mine.id).exists()
        assert PostMedia.objects.filter(post=post, media_asset=mine).exists()
        assert str(mine.id) not in self.client.session[f"pending_media_{self.ws.id}"]

    def test_own_fresh_upload_is_still_deleted(self):
        self._as("contributor")
        self.client.post(
            reverse("composer:upload_media", kwargs={"workspace_id": self.ws.id}),
            {"file": SimpleUploadedFile("a.png", PNG_1PX, content_type="image/png")},
        )
        asset = MediaAsset.objects.get(workspace=self.ws)

        self._remove(asset.id)

        assert not MediaAsset.objects.filter(id=asset.id).exists()


class MentionVisibilityTests(RoleAuthorizationBase):
    def setUp(self):
        super().setUp()
        self.client_user = _member(_user("acme.client@x.test"), self.ws, "client")
        self.post, _ = self._post()
        self.client.force_login(self.author)

    def _comment(self, body, visibility, parent=None):
        data = {"body": body, "visibility": visibility}
        if parent is not None:
            data["parent_id"] = str(parent.id)
        return self.client.post(
            reverse("approvals:add_comment", kwargs={"workspace_id": self.ws.id, "post_id": self.post.id}), data
        )

    def _client_mentions(self):
        return Notification.objects.filter(user=self.client_user, event_type=EventType.COMMENT_MENTION)

    def test_internal_comment_does_not_notify_a_mentioned_client(self):
        self._comment("@acme.client is overpaying, keep quiet", "internal")

        assert not self._client_mentions().exists()

    def test_reply_in_an_internal_thread_does_not_notify_a_client(self):
        root = PostComment.objects.create(post=self.post, author=self.author, body="team only", visibility="internal")

        self._comment("@acme.client see above", "external", parent=root)

        assert not self._client_mentions().exists()

    def test_external_comment_still_notifies_the_client(self):
        self._comment("@acme.client please review", "external")

        assert self._client_mentions().count() == 1


class TransitionFollowUpTests(RoleAuthorizationBase):
    def _transition(self, post, pp, target):
        return self.client.post(
            reverse(
                "composer:transition_platform_post",
                kwargs={"workspace_id": self.ws.id, "post_id": post.id, "platform_post_id": pp.id},
            ),
            {"target_status": target},
        )

    def test_a_draft_cannot_skip_required_approval(self):
        self.ws.approval_workflow_mode = Workspace.ApprovalWorkflowMode.REQUIRED_INTERNAL_AND_CLIENT
        self.ws.save(update_fields=["approval_workflow_mode"])
        post, pp = self._post(status="draft")
        self.client.force_login(self.author)

        for target in ("scheduled", "publishing"):
            response = self._transition(post, pp, target)
            pp.refresh_from_db()
            assert response.status_code == 400
            assert pp.status == "draft"

    def test_an_approved_post_can_still_be_scheduled_under_required_approval(self):
        self.ws.approval_workflow_mode = Workspace.ApprovalWorkflowMode.REQUIRED_INTERNAL
        self.ws.save(update_fields=["approval_workflow_mode"])
        post, pp = self._post(status="approved", proposed_publish_at=timezone.now() + timedelta(days=3))
        self.client.force_login(self.author)

        response = self._transition(post, pp, "scheduled")

        pp.refresh_from_db()
        assert response.status_code == 200
        assert pp.status == "scheduled"

    def test_moving_to_draft_frees_the_schedule_and_the_queue_slot(self):
        when = timezone.now() + timedelta(days=2)
        post, pp = self._post(status="scheduled", scheduled_at=when)
        PlatformPost.objects.filter(id=pp.id).update(scheduled_at=when)
        queue = Queue.objects.create(workspace=self.ws, name="Q", social_account=self.account)
        entry = QueueEntry.objects.create(queue=queue, post=post, position=1, assigned_slot_datetime=when)
        self.client.force_login(self.author)

        response = self._transition(post, pp, "draft")

        pp.refresh_from_db()
        post.refresh_from_db()
        assert response.status_code == 200
        assert pp.status == "draft"
        assert pp.scheduled_at is None
        assert post.scheduled_at is None
        assert not QueueEntry.objects.filter(id=entry.id).exists()
        # The intended time survives as the draft-stage proposal.
        assert post.proposed_publish_at == when

    def test_drafting_then_rescheduling_restores_a_time_the_publisher_can_see(self):
        from apps.publisher.engine import PublishEngine

        when = timezone.now() + timedelta(days=2)
        post, pp = self._post(status="scheduled", scheduled_at=when)
        PlatformPost.objects.filter(id=pp.id).update(scheduled_at=when)
        self.client.force_login(self.author)

        assert self._transition(post, pp, "draft").status_code == 200
        response = self._transition(post, pp, "scheduled")

        pp.refresh_from_db()
        post.refresh_from_db()
        assert response.status_code == 200
        assert pp.status == "scheduled"
        assert pp.scheduled_at == when
        assert post.scheduled_at == when
        assert post.proposed_publish_at is None
        # Once due, the publisher's own query must find it.
        PlatformPost.objects.filter(id=pp.id).update(scheduled_at=timezone.now() - timedelta(minutes=1))
        assert pp.id in {due.id for due in PublishEngine()._get_due_platform_posts()}

    def test_scheduling_with_no_time_anywhere_is_refused(self):
        post, pp = self._post(status="draft")
        self.client.force_login(self.author)

        response = self._transition(post, pp, "scheduled")

        pp.refresh_from_db()
        assert response.status_code == 400
        assert pp.status == "draft"

    def test_drafting_one_child_keeps_a_siblings_inherited_time(self):
        # The chip's schedule path commits a child without its own time; it
        # publishes at the parent's. Drafting a sibling must not clear that.
        when = timezone.now() + timedelta(days=2)
        post = Post.objects.create(workspace=self.ws, author=self.author, caption="hi", scheduled_at=when)
        other = SocialAccount.objects.create(
            workspace=self.ws,
            platform="threads",
            account_platform_id="th-1",
            account_name="Brand threads",
            connection_status=SocialAccount.ConnectionStatus.CONNECTED,
        )
        leaning = PlatformPost.objects.create(post=post, social_account=other, status="scheduled")
        drafted = PlatformPost.objects.create(
            post=post, social_account=self.account, status="scheduled", scheduled_at=when
        )
        self.client.force_login(self.author)

        response = self._transition(post, drafted, "draft")

        post.refresh_from_db()
        leaning.refresh_from_db()
        assert response.status_code == 200
        assert leaning.scheduled_at is None
        assert post.scheduled_at == when


class SharedContentTests(RoleAuthorizationBase):
    def setUp(self):
        super().setUp()
        self.category = ContentCategory.objects.create(workspace=self.ws, name="Educational", color="#3B82F6")
        self.template = PostTemplate.objects.create(
            workspace=self.ws, name="Weekly", template_data={"caption": "x"}, created_by=self.author
        )

    def _url(self, name, **extra):
        return reverse(f"composer:{name}", kwargs={"workspace_id": self.ws.id, **extra})

    def test_viewer_cannot_change_categories_templates_or_tags(self):
        post, _ = self._post()
        self._as("viewer")

        responses = {
            "category_create": self.client.post(self._url("category_create"), {"name": "New", "color": "#000000"}),
            "category_edit": self.client.post(
                self._url("category_edit", category_id=self.category.id), {"name": "Renamed", "color": "#000000"}
            ),
            "category_delete": self.client.post(self._url("category_delete", category_id=self.category.id)),
            "template_delete": self.client.post(self._url("template_delete", template_id=self.template.id)),
            "save_as_template": self.client.post(
                self._url("save_as_template", post_id=post.id), {"template_name": "Mine"}
            ),
            "tag_create": self.client.post(self._url("tag_create"), {"name": "launch"}),
            "preview": self.client.post(self._url("preview"), {"caption": "x"}),
            "clone_post": self.client.post(self._url("clone_post", post_id=post.id)),
        }

        assert {name: r.status_code for name, r in responses.items()} == dict.fromkeys(responses, 403)
        self.category.refresh_from_db()
        assert self.category.name == "Educational"
        assert PostTemplate.objects.filter(id=self.template.id).exists()
        assert not Tag.objects.filter(workspace=self.ws, name="launch").exists()

    def test_contributor_can_add_a_category_but_not_remove_one(self):
        self._as("contributor")

        created = self.client.post(self._url("category_create"), {"name": "Behind the scenes", "color": "#000000"})
        deleted = self.client.post(self._url("category_delete", category_id=self.category.id))

        assert created.status_code != 403
        assert ContentCategory.objects.filter(workspace=self.ws, name="Behind the scenes").exists()
        assert deleted.status_code == 403
        assert ContentCategory.objects.filter(id=self.category.id).exists()

    def test_template_deletion_follows_ownership(self):
        contributor = self._as("contributor")
        own = PostTemplate.objects.create(workspace=self.ws, name="Mine", template_data={}, created_by=contributor)

        theirs = self.client.post(self._url("template_delete", template_id=self.template.id))
        mine = self.client.post(self._url("template_delete", template_id=own.id))

        assert theirs.status_code == 403
        assert PostTemplate.objects.filter(id=self.template.id).exists()
        assert mine.status_code == 204
        assert not PostTemplate.objects.filter(id=own.id).exists()

    def test_editor_can_remove_a_category(self):
        self._as("editor")

        response = self.client.post(self._url("category_delete", category_id=self.category.id))

        assert response.status_code != 403
        assert not ContentCategory.objects.filter(id=self.category.id).exists()


class QueueManagementTests(RoleAuthorizationBase):
    def test_editor_can_still_create_and_delete_queues(self):
        self._as("editor")

        created = self.client.post(
            reverse("calendar:queue_create", kwargs={"workspace_id": self.ws.id}),
            {"name": "Evergreen", "social_account_id": str(self.account.id)},
        )
        queue = Queue.objects.get(workspace=self.ws, name="Evergreen")
        deleted = self.client.post(
            reverse("calendar:queue_delete", kwargs={"workspace_id": self.ws.id, "queue_id": queue.id})
        )

        assert created.status_code in (204, 302)
        assert deleted.status_code in (204, 302)
        assert not Queue.objects.filter(id=queue.id).exists()


class WorkspaceSettingsPermissionTests(RoleAuthorizationBase):
    def test_custom_role_with_manage_workspace_settings_can_rename(self):
        from apps.members.models import BUILTIN_ROLE_PERMISSIONS

        role = CustomRole.objects.create(
            organization=self.org,
            name="Brand admin",
            permissions={**BUILTIN_ROLE_PERMISSIONS["editor"], "manage_workspace_settings": True},
        )
        user = _member(_user("brand.admin@x.test"), self.ws, "editor")
        WorkspaceMembership.objects.filter(user=user, workspace=self.ws).update(custom_role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse("workspaces:settings", kwargs={"workspace_id": self.ws.id}), {"name": "Renamed"}
        )

        self.ws.refresh_from_db()
        assert response.status_code == 302
        assert self.ws.name == "Renamed"


class PostDeleteInputTests(RoleAuthorizationBase):
    def test_malformed_account_id_is_a_400_not_a_500(self):
        post, _ = self._post()
        self.client.force_login(self.author)

        response = self.client.post(
            reverse("composer:post_delete", kwargs={"workspace_id": self.ws.id, "post_id": post.id}) + "?account=abc"
        )

        assert response.status_code == 400
        assert Post.objects.filter(id=post.id).exists()

    def test_bulk_delete_needs_create_posts_even_for_own_posts(self):
        # A former contributor downgraded to viewer still authors their old posts.
        viewer = self._as("viewer")
        post, pp = self._post(author=viewer)

        self.client.post(
            reverse("calendar:bulk_platform_action", kwargs={"workspace_id": self.ws.id}),
            {"action": "delete", "platform_post_ids": [str(pp.id)]},
        )

        assert PlatformPost.objects.filter(id=pp.id).exists()


class ApprovalWorkflowGateTests(RoleAuthorizationBase):
    """In the required approval modes no path may hand an unreviewed draft to the publisher."""

    def setUp(self):
        super().setUp()
        self.ws.approval_workflow_mode = Workspace.ApprovalWorkflowMode.REQUIRED_INTERNAL
        self.ws.save(update_fields=["approval_workflow_mode"])
        self.when = (timezone.now() + timedelta(days=30)).replace(microsecond=0)

    def _save(self, action, post=None, **extra):
        url = (
            reverse("composer:save_post_edit", kwargs={"workspace_id": self.ws.id, "post_id": post.id})
            if post
            else reverse("composer:save_post", kwargs={"workspace_id": self.ws.id})
        )
        data = {
            "action": action,
            "caption": "hi",
            "tags": "",
            "selected_accounts": str(self.account.id),
            "scheduled_date": "2027-09-01",
            "scheduled_time": "09:00",
            **extra,
        }
        return self.client.post(url, data)

    def test_contributor_cannot_schedule_or_queue_an_unreviewed_draft(self):
        contributor = self._as("contributor")
        post, pp = self._post(author=contributor)

        for action in ("schedule", "add_to_queue", "add_to_queue_priority", "publish_now"):
            response = self._save(action, post)
            pp.refresh_from_db()
            assert response.status_code in (400, 403), action
            assert pp.status == "draft", action

    def test_a_new_post_cannot_be_created_already_scheduled(self):
        self._as("contributor")

        response = self._save("schedule")

        assert response.status_code == 400
        assert not Post.objects.filter(workspace=self.ws, caption="hi").exists()

    def test_manager_cannot_skip_review_either(self):
        post, pp = self._post()
        self.client.force_login(self.author)

        response = self._save("publish_now", post)

        pp.refresh_from_db()
        assert response.status_code == 400
        assert pp.status == "draft"

    def test_an_approved_post_is_scheduled_by_its_author(self):
        contributor = self._as("contributor")
        post, pp = self._post(status="approved", author=contributor)

        response = self._save("schedule", post)

        pp.refresh_from_db()
        assert response.status_code in (200, 204, 302)
        assert pp.status == "scheduled"

    def test_optional_review_still_lets_a_contributor_schedule(self):
        self.ws.approval_workflow_mode = Workspace.ApprovalWorkflowMode.OPTIONAL
        self.ws.save(update_fields=["approval_workflow_mode"])
        contributor = self._as("contributor")
        post, pp = self._post(author=contributor)

        response = self._save("schedule", post)

        pp.refresh_from_db()
        assert response.status_code in (200, 204, 302)
        assert pp.status == "scheduled"

    def test_calendar_drop_and_bulk_publish_cannot_promote_a_draft(self):
        post, pp = self._post()
        self.client.force_login(self.author)

        dropped = self.client.post(
            reverse("calendar:reschedule", kwargs={"workspace_id": self.ws.id}),
            {"platform_post_id": str(pp.id), "new_datetime": self.when.strftime("%Y-%m-%dT%H:%M:%S")},
        )
        bulk = self.client.post(
            reverse("calendar:bulk_platform_action", kwargs={"workspace_id": self.ws.id}),
            {"action": "publish", "platform_post_ids": [str(pp.id)]},
        )

        pp.refresh_from_db()
        assert dropped.status_code == 400
        assert bulk.status_code == 400
        assert pp.status == "draft"

    def test_csv_import_keeps_dated_rows_as_drafts(self):
        self._as("contributor")
        session = self.client.session
        session[f"csv_import_{self.ws.id}"] = {"rows": [["From the CSV", "2027-09-01", "10:00", "linkedin_personal"]]}
        session[f"csv_mapping_{self.ws.id}"] = {"caption": 0, "date": 1, "time": 2, "platforms": 3}
        session.save()

        response = self.client.post(reverse("composer:csv_confirm_import", kwargs={"workspace_id": self.ws.id}))

        pp = PlatformPost.objects.get(post__caption="From the CSV", social_account=self.account)
        assert response.status_code == 200
        assert pp.status == "draft"
        assert pp.scheduled_at is not None
        assert b"requires approval" in response.content


def test_heic_and_avif_are_not_mistaken_for_video():
    for brand in (b"heic", b"mif1", b"avif"):
        head = b"\x00\x00\x00\x18ftyp" + brand + b"\x00" * 20
        assert sniff_mime(io.BytesIO(head)) is None


def test_legacy_quicktime_without_ftyp_is_recognised():
    for atom in (b"moov", b"mdat", b"wide"):
        head = b"\x00\x00\x00\x08" + atom + b"\x00" * 24
        assert sniff_mime(io.BytesIO(head)) == "video/quicktime"


# ---------------------------------------------------------------------------
# Structural guard: no POST-only workspace view on membership alone
# ---------------------------------------------------------------------------

# Decorators that consult the caller's role or permissions. Identified by the
# wrapper's code object, which functools.wraps leaves alone.
_PERMISSION_DECORATORS = (
    "require_permission",
    "require_workspace_role",
    "require_org_role",
    "require_org_permission",
)

# POST-only workspace views that authorise per object, inline, instead of with
# a decorator. Adding a view here is a claim that it does — say how.
INLINE_AUTHZ_VIEWS = {
    "apps.calendar.views.bulk_platform_action": "keeps only rows can_edit_post allows; publish needs publish_directly",
    "apps.calendar.views.reschedule_post": "can_edit_post on the row; promoting a draft needs publish_directly",
    "apps.onboarding.views.dismiss_checklist": "a per-user UI preference; changes nothing shared",
}


def _wrapper_chain(view):
    chain = []
    while view is not None and view not in chain:
        chain.append(view)
        view = getattr(view, "__wrapped__", None)
    return chain


def _code_name(fn):
    code = getattr(fn, "__code__", None)
    return code.co_qualname if code else ""


def _allowed_methods(view):
    for layer in _wrapper_chain(view):
        if _code_name(layer).startswith("require_http_methods"):
            return inspect.getclosurevars(layer).nonlocals.get("request_method_list")
    return None


def _workspace_routes(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _workspace_routes(pattern.url_patterns, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern) and "workspace_id" in prefix + str(pattern.pattern):
            yield pattern.callback


def test_every_post_only_workspace_view_checks_more_than_membership():
    """Each app's _get_workspace() only proves membership, which viewers and
    portal clients have. A new POST view that relies on it alone is the bug
    behind every report this module pins; this keeps the next one from shipping.
    """
    unguarded = set()
    for view in _workspace_routes(get_resolver().url_patterns):
        methods = _allowed_methods(view)
        if methods is None or "GET" in methods:
            continue
        if not any(_code_name(layer).startswith(_PERMISSION_DECORATORS) for layer in _wrapper_chain(view)):
            unguarded.add(f"{view.__module__}.{view.__name__}")

    assert unguarded == set(INLINE_AUTHZ_VIEWS)
