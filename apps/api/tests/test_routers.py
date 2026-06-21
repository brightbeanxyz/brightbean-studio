"""Phase 2 smoke tests — exercise the Agent API end-to-end through Django's
test client so the auth → router → service path is wired correctly.

This is intentionally narrow: it doesn't try to cover every branch of
every route (Phase 5 owns that). It does cover:

* Auth class accepts a valid bearer and rejects missing / malformed / wrong.
* The membership shim flows ``effective_permissions`` through to
  ``_require_perm`` so 403 fires when the key lacks ``create_posts``.
* ``/me`` and ``/accounts`` echo the right scope.
* ``POST /posts`` produces one ``Post`` + one ``PlatformPost`` with the
  right ``status`` for both ``draft`` and ``schedule`` actions.
* Targeting a ``social_account_id`` outside the key's allowlist → 403.
* Idempotency replays a stored response when the key+body match, and
  422s when the body diverges.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.api_keys import services
from apps.composer.models import PlatformPost, Post
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="agent-owner@example.com",
        password="testpass123",
        name="Agent Owner",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def organization(db):
    from apps.organizations.models import Organization

    return Organization.objects.create(name="Test Org")


@pytest.fixture
def workspace(db, organization):
    from apps.workspaces.models import Workspace

    return Workspace.objects.create(name="Workspace A", organization=organization)


@pytest.fixture
def owner_memberships(db, user, organization, workspace):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
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
        platform="linkedin_personal",
        account_platform_id="li-abc",
        account_name="My LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def foreign_account(db, organization):
    """Account in a *different* workspace inside the same org."""
    from apps.social_accounts.models import SocialAccount
    from apps.workspaces.models import Workspace

    other = Workspace.objects.create(name="Other WS", organization=organization)
    return SocialAccount.objects.create(
        workspace=other,
        platform="linkedin_personal",
        account_platform_id="li-other",
        account_name="Other LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def issued_key(db, user, owner_memberships, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="smoke",
        permissions=list(PERMISSION_KEYS),
    )


class _SecureClient(Client):
    """Django test client that forces every request to ``secure=True``.

    Django's ``Client.get/post`` always pass an explicit ``secure=False``
    to ``generic`` (overriding any default we set on init), so we
    intercept at ``generic`` and force the flag on. Satisfies the
    production HTTPS guard in ``ApiKeyAuth`` without requiring each
    test to remember the kwarg.
    """

    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def client_with_token(issued_key):
    """A Django test client preconfigured with the bearer token and HTTPS."""
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuth:
    def test_missing_authorization_header_returns_401(self):
        c = _SecureClient()
        r = c.get("/api/v1/me/")
        assert r.status_code == 401

    def test_malformed_token_returns_401(self):
        c = _SecureClient(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        r = c.get("/api/v1/me/")
        assert r.status_code == 401

    def test_valid_token_authenticates(self, client_with_token):
        r = client_with_token.get("/api/v1/me/")
        assert r.status_code == 200, r.content


# ---------------------------------------------------------------------------
# /me + /accounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReadOnlyEndpoints:
    def test_me_echoes_scope(self, client_with_token, workspace, issued_key, social_account):
        r = client_with_token.get("/api/v1/me/")
        assert r.status_code == 200
        body = r.json()
        assert body["workspace_id"] == str(workspace.id)
        assert body["api_key_id"] == str(issued_key.api_key.id)
        assert {a["id"] for a in body["allowlisted_accounts"]} == {str(social_account.id)}
        # Permissions reflect intersection of granted + issuer's owner role.
        assert "create_posts" in body["permissions"]

    def test_accounts_lists_allowlisted_only(self, client_with_token, social_account):
        r = client_with_token.get("/api/v1/accounts/")
        assert r.status_code == 200
        ids = {a["id"] for a in r.json()["accounts"]}
        assert ids == {str(social_account.id)}


# ---------------------------------------------------------------------------
# POST /posts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreatePost:
    def test_create_draft(self, client_with_token, social_account):
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "Hello from agents.",
                    "action": "draft",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["caption"] == "Hello from agents."
        assert len(body["platform_posts"]) == 1
        assert body["platform_posts"][0]["status"] == "draft"
        # DB-side asserts.
        assert Post.objects.count() == 1
        assert PlatformPost.objects.filter(status="draft").count() == 1

    def test_create_draft_with_internal_notes(self, client_with_token, social_account):
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "Has a private note.",
                    "internal_notes": "Approved by legal; ship Monday.",
                    "action": "draft",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["internal_notes"] == "Approved by legal; ship Monday."
        # Persisted on the model; the team note never leaks into the public caption.
        post = Post.objects.get(id=body["id"])
        assert post.internal_notes == "Approved by legal; ship Monday."
        assert post.caption == "Has a private note."

    def test_create_scheduled_requires_scheduled_at(self, client_with_token, social_account):
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "Will fail.",
                    "action": "schedule",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 422

    def test_create_scheduled(self, client_with_token, social_account):
        when = (timezone.now() + timedelta(hours=2)).isoformat()
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "See you in 2h.",
                    "action": "schedule",
                    "scheduled_at": when,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["platform_posts"][0]["status"] == "scheduled"

    def test_account_outside_allowlist_is_403(self, client_with_token, foreign_account):
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(foreign_account.id),
                    "caption": "should not be allowed",
                    "action": "draft",
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 403
        assert "allowlist" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# internal_notes visibility
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestInternalNotesVisibility:
    """``internal_notes`` is a team-only field. The shared ``PostResponse``
    serializer must redact it for callers without ``create_posts`` — the API
    analogue of the composer hiding it from client/viewer roles — even though
    reads aren't otherwise permission-gated.
    """

    def _post_with_note(self, workspace, user, social_account, note="eyes only"):
        post = Post.objects.create(workspace=workspace, author=user, caption="public", internal_notes=note)
        PlatformPost.objects.create(post=post, social_account=social_account, status="draft")
        return post

    def test_create_posts_caller_sees_internal_notes(self, client_with_token, workspace, user, social_account):
        post = self._post_with_note(workspace, user, social_account)
        r = client_with_token.get(f"/api/v1/posts/{post.id}")
        assert r.status_code == 200, r.content
        assert r.json()["internal_notes"] == "eyes only"

    def test_caller_without_create_posts_gets_redacted_notes(self, user, owner_memberships, workspace, social_account):
        # A key that can read posts (allowlisted) but lacks create_posts — the
        # API analogue of a client/viewer-role member.
        readonly = services.issue_api_key(
            workspace=workspace,
            social_accounts=[social_account],
            issued_by=user,
            name="readonly",
            permissions=["view_analytics"],  # deliberately omits create_posts
        )
        client = _SecureClient(HTTP_AUTHORIZATION=f"Bearer {readonly.plaintext_token}")
        post = self._post_with_note(workspace, user, social_account)
        r = client.get(f"/api/v1/posts/{post.id}")
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["internal_notes"] == ""  # redacted
        assert body["caption"] == "public"  # other fields unaffected


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestIdempotency:
    def test_same_key_same_body_replays(self, client_with_token, social_account):
        body = {
            "social_account_id": str(social_account.id),
            "caption": "Idempotent.",
            "action": "draft",
            "idempotency_key": "abc-123",
        }
        r1 = client_with_token.post("/api/v1/posts/", data=json.dumps(body), content_type="application/json")
        assert r1.status_code == 201
        r2 = client_with_token.post("/api/v1/posts/", data=json.dumps(body), content_type="application/json")
        assert r2.status_code == 201
        # Replay returns the same Post ID — only one row was actually created.
        assert r1.json()["id"] == r2.json()["id"]
        assert Post.objects.count() == 1

    def test_same_key_different_body_is_422(self, client_with_token, social_account):
        common_key = "abc-456"
        r1 = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "first body",
                    "action": "draft",
                    "idempotency_key": common_key,
                }
            ),
            content_type="application/json",
        )
        assert r1.status_code == 201
        r2 = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "DIFFERENT body",
                    "action": "draft",
                    "idempotency_key": common_key,
                }
            ),
            content_type="application/json",
        )
        assert r2.status_code == 422

    def test_in_flight_claim_returns_409(self, client_with_token, social_account, issued_key):
        """Regression test for Codex P2: when a peer holds the idempotency
        slot in the 'pending' state, a concurrent identical POST must 409,
        not run create_post again.

        We simulate the concurrent peer by pre-inserting a placeholder row
        (response_status=0 → PENDING_STATUS_SENTINEL) with a fingerprint
        computed *exactly* the way the route does — i.e. from the
        Pydantic schema's canonical dict (including defaulted fields),
        not from the raw client body.
        """
        from apps.api.middleware import PENDING_STATUS_SENTINEL, fingerprint_request
        from apps.api.models import IdempotencyRecord
        from apps.api.schemas import CreatePostRequest

        body = {
            "social_account_id": str(social_account.id),
            "caption": "race",
            "action": "draft",
            "idempotency_key": "race-789",
        }
        # Route computes fingerprint over ``payload.dict(by_alias=True)``
        # AFTER Pydantic has filled in defaults (title, first_comment,
        # media_asset_ids, scheduled_at). Build the same dict here so
        # the pre-inserted fingerprint matches what the route will see.
        canonical = CreatePostRequest(**body).dict(by_alias=True)
        fp = fingerprint_request("POST", "/api/v1/posts/", canonical)
        IdempotencyRecord.objects.create(
            api_key=issued_key.api_key,
            key="race-789",
            request_fingerprint=fp,
            response_status=PENDING_STATUS_SENTINEL,
            response_body={},
        )

        r = client_with_token.post("/api/v1/posts/", data=json.dumps(body), content_type="application/json")
        assert r.status_code == 409
        # And nothing was actually created — the peer hasn't finished yet.
        assert Post.objects.count() == 0

    def test_create_failure_releases_claim(self, client_with_token, foreign_account, issued_key):
        """If the create path fails AFTER claiming the slot, the placeholder
        must be released so the agent's next retry can succeed.

        We trigger a 403 by targeting an out-of-allowlist SocialAccount;
        that path happens after the claim. The IdempotencyRecord row should
        not survive.
        """
        from apps.api.models import IdempotencyRecord

        body = {
            "social_account_id": str(foreign_account.id),
            "caption": "should release",
            "action": "draft",
            "idempotency_key": "release-001",
        }
        r = client_with_token.post("/api/v1/posts/", data=json.dumps(body), content_type="application/json")
        assert r.status_code == 403
        # The claim row must NOT linger — otherwise the legitimate retry
        # would 409 on the now-permanent placeholder.
        assert not IdempotencyRecord.objects.filter(api_key=issued_key.api_key, key="release-001").exists()


# ---------------------------------------------------------------------------
# P1 — Allowlist enforcement on read / mutate paths
# ---------------------------------------------------------------------------


@pytest.fixture
def second_account(db, workspace):
    """Second account in the SAME workspace that the key is NOT scoped to.

    Used to construct a Post whose only PlatformPost targets an account
    outside the bearer's allowlist — exactly the confused-deputy
    scenario Codex flagged.
    """
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-second",
        account_name="Second LinkedIn",
        connection_status="connected",
    )


@pytest.fixture
def out_of_scope_post(db, workspace, second_account, user):
    """A Post whose only child PlatformPost targets ``second_account``.

    The bearer in ``client_with_token`` only allowlists ``social_account``,
    so it must NOT be able to read or mutate this post — even though it
    lives in the same workspace.
    """
    from apps.composer.models import PlatformPost, Post

    post = Post.objects.create(workspace=workspace, author=user, caption="not for you")
    PlatformPost.objects.create(post=post, social_account=second_account, status="draft")
    return post


@pytest.mark.django_db
class TestAllowlistGate:
    def test_retrieve_foreign_account_post_is_404(self, client_with_token, out_of_scope_post):
        r = client_with_token.get(f"/api/v1/posts/{out_of_scope_post.id}")
        assert r.status_code == 404

    def test_patch_foreign_account_post_is_404(self, client_with_token, out_of_scope_post):
        r = client_with_token.patch(
            f"/api/v1/posts/{out_of_scope_post.id}",
            data=json.dumps({"caption": "tampered"}),
            content_type="application/json",
        )
        assert r.status_code == 404
        out_of_scope_post.refresh_from_db()
        # Caption MUST be untouched.
        assert out_of_scope_post.caption == "not for you"

    def test_schedule_foreign_account_post_is_404(self, client_with_token, out_of_scope_post):
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = client_with_token.post(
            f"/api/v1/posts/{out_of_scope_post.id}/schedule",
            data=json.dumps({"scheduled_at": when}),
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_cancel_foreign_account_post_is_404(self, client_with_token, out_of_scope_post):
        r = client_with_token.post(f"/api/v1/posts/{out_of_scope_post.id}/cancel")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# P3 — Draft rows do not consume the per-account platform quota
# ---------------------------------------------------------------------------


@pytest.fixture
def ig_account(db, workspace):
    """Instagram account — its 25/24h cap is the lowest, so it's the
    cheapest platform to exercise the quota path against.
    """
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="instagram",
        account_platform_id="ig-123",
        account_name="IG Test",
        connection_status="connected",
    )


@pytest.fixture
def ig_key(db, user, owner_memberships, workspace, ig_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[ig_account],
        issued_by=user,
        name="ig",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def ig_client(ig_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {ig_key.plaintext_token}")


@pytest.mark.django_db
class TestPlatformQuota:
    def test_drafts_do_not_consume_quota(self, ig_client, ig_account):
        """Codex P3 regression: 25 IG drafts must not block the 26th schedule.

        IG's cap is 25/24h — but drafts haven't pressured the platform
        yet, so they should NOT be counted. Before the fix this would
        429 the schedule attempt.
        """
        # Create 25 IG drafts.
        for i in range(25):
            r = ig_client.post(
                "/api/v1/posts/",
                data=json.dumps(
                    {
                        "social_account_id": str(ig_account.id),
                        "caption": f"draft {i}",
                        "action": "draft",
                    }
                ),
                content_type="application/json",
            )
            assert r.status_code == 201

        # Now schedule one — must succeed.
        when = (timezone.now() + timedelta(hours=1)).isoformat()
        r = ig_client.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(ig_account.id),
                    "caption": "this one should succeed",
                    "action": "schedule",
                    "scheduled_at": when,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content

    def test_scheduled_rows_do_count_against_quota(self, ig_client, ig_account):
        """Sanity check: once the 25 scheduled rows exist, the 26th 429s.

        Exercises the upper bound of the new filtered count so the
        regression test above can't pass just because counting is broken.
        """
        # Pre-populate 25 scheduled rows for ig_account directly.
        from apps.composer.models import PlatformPost, Post

        for i in range(25):
            p = Post.objects.create(workspace=ig_account.workspace, caption=f"pre {i}")
            PlatformPost.objects.create(
                post=p,
                social_account=ig_account,
                status="scheduled",
                scheduled_at=timezone.now() + timedelta(hours=2),
            )

        when = (timezone.now() + timedelta(hours=3)).isoformat()
        r = ig_client.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(ig_account.id),
                    "caption": "should 429",
                    "action": "schedule",
                    "scheduled_at": when,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 429
        body = r.json()
        assert body["error"] == "rate_limited"
        assert body["tier"] == "platform_quota:instagram"


# ---------------------------------------------------------------------------
# P4 — Failed-auth throttle short-circuits without paying HMAC cost
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFailedAuthThrottle:
    def test_blocked_ip_short_circuits_before_verify_token(self, monkeypatch):
        """Codex P4 regression: once the failed-auth budget is exhausted,
        further attempts from the same IP must NOT call verify_token
        (which does HMAC work). The 401 response shape is unchanged so
        an attacker can't detect the throttle.

        Note on isolation: pytest-django wraps every test in a DB
        transaction, but the Django cache (which our throttle uses)
        is process-wide and NOT reset between tests. Earlier auth tests
        in this file already incremented the counter for 127.0.0.1, so
        we explicitly clear the failed-auth bucket before counting.
        """
        from django.core.cache import cache

        from apps.api import auth as auth_module
        from apps.api.limits import _AUTH_FAIL_LIMIT

        # Wipe any failed-auth state from earlier tests in this process.
        cache.delete("agent_api:auth_fail:127.0.0.1")

        call_count = {"n": 0}

        def counting_verify(token):
            call_count["n"] += 1
            return None  # always-fail simulation

        monkeypatch.setattr(auth_module, "verify_token", counting_verify)

        c = _SecureClient(HTTP_AUTHORIZATION="Bearer bb_studio_fake-token-aaaaaaaaaaaaaaaaa_00000000")

        # The first _AUTH_FAIL_LIMIT attempts increment the counter and
        # call verify_token; the (limit+1)-th must short-circuit BEFORE
        # verify_token.
        for _ in range(_AUTH_FAIL_LIMIT):
            r = c.get("/api/v1/me/")
            assert r.status_code == 401
        assert call_count["n"] == _AUTH_FAIL_LIMIT

        # (limit+1)-th attempt — verify_token must NOT be called.
        r = c.get("/api/v1/me/")
        assert r.status_code == 401
        assert call_count["n"] == _AUTH_FAIL_LIMIT, "verify_token was called past the throttle threshold"


# ---------------------------------------------------------------------------
# proposed_publish_at — optional draft-stage suggestion on /posts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProposedPublishAt:
    _WHEN = "2027-09-01T09:00:00Z"

    def _create_draft(self, client, social_account, **extra):
        payload = {
            "social_account_id": str(social_account.id),
            "caption": "hi",
            "action": "draft",
            **extra,
        }
        return client.post("/api/v1/posts/", data=json.dumps(payload), content_type="application/json")

    def test_create_draft_echoes_and_persists_proposed(self, client_with_token, social_account):
        r = self._create_draft(client_with_token, social_account, proposed_publish_at=self._WHEN)
        assert r.status_code == 201, r.content
        body = r.json()
        assert body["proposed_publish_at"] == self._WHEN
        assert Post.objects.get(id=body["id"]).proposed_publish_at is not None

    def test_create_draft_defaults_proposed_to_null(self, client_with_token, social_account):
        body = self._create_draft(client_with_token, social_account).json()
        assert body["proposed_publish_at"] is None

    def test_schedule_action_ignores_proposed(self, client_with_token, social_account):
        when = (timezone.now() + timedelta(hours=3)).isoformat()
        r = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "hi",
                    "action": "schedule",
                    "scheduled_at": when,
                    "proposed_publish_at": self._WHEN,
                }
            ),
            content_type="application/json",
        )
        assert r.status_code == 201, r.content
        # A scheduled post carries a real time, not a proposal.
        assert r.json()["proposed_publish_at"] is None

    def test_retrieve_returns_proposed(self, client_with_token, social_account):
        pid = self._create_draft(client_with_token, social_account, proposed_publish_at=self._WHEN).json()["id"]
        body = client_with_token.get(f"/api/v1/posts/{pid}").json()
        assert body["proposed_publish_at"] == self._WHEN

    def test_patch_sets_proposed(self, client_with_token, social_account):
        pid = self._create_draft(client_with_token, social_account).json()["id"]
        r = client_with_token.patch(
            f"/api/v1/posts/{pid}",
            data=json.dumps({"proposed_publish_at": self._WHEN}),
            content_type="application/json",
        )
        assert r.status_code == 200, r.content
        assert r.json()["proposed_publish_at"] == self._WHEN

    def test_schedule_route_clears_proposed(self, client_with_token, social_account):
        pid = self._create_draft(client_with_token, social_account, proposed_publish_at=self._WHEN).json()["id"]
        when = (timezone.now() + timedelta(hours=3)).isoformat()
        r = client_with_token.post(
            f"/api/v1/posts/{pid}/schedule",
            data=json.dumps({"scheduled_at": when}),
            content_type="application/json",
        )
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["scheduled_at"] is not None
        # A committed schedule supersedes the proposal — they never coexist.
        assert body["proposed_publish_at"] is None

    def test_patch_proposed_on_scheduled_post_is_dropped(self, client_with_token, social_account):
        when = (timezone.now() + timedelta(hours=3)).isoformat()
        pid = client_with_token.post(
            "/api/v1/posts/",
            data=json.dumps(
                {
                    "social_account_id": str(social_account.id),
                    "caption": "hi",
                    "action": "schedule",
                    "scheduled_at": when,
                }
            ),
            content_type="application/json",
        ).json()["id"]
        r = client_with_token.patch(
            f"/api/v1/posts/{pid}",
            data=json.dumps({"proposed_publish_at": self._WHEN}),
            content_type="application/json",
        )
        assert r.status_code == 200, r.content
        body = r.json()
        assert body["scheduled_at"] is not None
        assert body["proposed_publish_at"] is None
