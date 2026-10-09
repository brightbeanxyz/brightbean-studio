"""Usage counters, the hourly / daily caps, and which calls earn an audit row.

Every authenticated call is counted in ``ApiKeyUsageHourly``; only writes and
non-429 failures also get an ``ApiKeyAuditLog`` row. The caps are read back
from the counters, so they survive deploys the cache would not.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid

import pytest
from django.test import Client
from django.utils import timezone

from apps.api.tasks import sweep_api_usage_records
from apps.api.usage import day_start, hour_start
from apps.api_keys import services
from apps.api_keys.models import ApiKey, ApiKeyAuditLog, ApiKeyUsageHourly
from apps.members.models import PERMISSION_KEYS, OrgMembership, WorkspaceMembership

MCP_URL = "/api/v1/mcp/"


class _SecureClient(Client):
    def generic(self, method, path, *args, **kwargs):
        kwargs["secure"] = True
        return super().generic(method, path, *args, **kwargs)


@pytest.fixture
def user(db):
    from apps.accounts.models import User

    u = User.objects.create_user(
        email="usage@example.com",
        password="testpass123",
        name="Usage",
        tos_accepted_at=timezone.now(),
    )
    om = u.org_memberships.first()
    om.org_role = OrgMembership.OrgRole.OWNER
    om.save(update_fields=["org_role"])
    return u


@pytest.fixture
def workspace(db, user):
    from apps.workspaces.models import Workspace

    ws = Workspace.objects.create(name="Usage WS", organization=user.org_memberships.first().organization)
    WorkspaceMembership.objects.create(user=user, workspace=ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER)
    return ws


@pytest.fixture
def social_account(db, workspace):
    from apps.social_accounts.models import SocialAccount

    return SocialAccount.objects.create(
        workspace=workspace,
        platform="linkedin_personal",
        account_platform_id="li-usage",
        account_name="LinkedIn Usage",
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )


@pytest.fixture
def issued_key(db, user, workspace, social_account):
    return services.issue_api_key(
        workspace=workspace,
        social_accounts=[social_account],
        issued_by=user,
        name="usage",
        permissions=list(PERMISSION_KEYS),
    )


@pytest.fixture
def api_key(issued_key) -> ApiKey:
    return issued_key.api_key


@pytest.fixture
def client(issued_key):
    return _SecureClient(HTTP_AUTHORIZATION=f"Bearer {issued_key.plaintext_token}")


def _set_caps(api_key: ApiKey, *, hourly=None, daily=None) -> None:
    # Before the key's first request: ``verify_token`` caches the row.
    ApiKey.objects.filter(pk=api_key.pk).update(rate_override_hourly=hourly, rate_override_daily=daily)


def _counts(api_key: ApiKey) -> dict[tuple[str, int], int]:
    return {
        (action, status): count
        for action, status, count in ApiKeyUsageHourly.objects.filter(api_key=api_key).values_list(
            "action", "status_code", "count"
        )
    }


def _seed(api_key: ApiKey, *, at: dt.datetime, count: int, status_code: int = 200) -> None:
    ApiKeyUsageHourly.objects.create(
        actor=f"key:{api_key.pk}",
        api_key=api_key,
        workspace_id=api_key.workspace_id,
        hour_start=hour_start(at),
        action="seeded",
        status_code=status_code,
        count=count,
        last_seen_at=at,
    )


def _mcp(client, method, params=None):
    msg = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        msg["params"] = params
    return client.post(MCP_URL, data=json.dumps(msg), content_type="application/json")


@pytest.mark.django_db
class TestCountedNotLogged:
    def test_rest_reads_are_counted_without_audit_rows(self, client, api_key):
        assert client.get("/api/v1/me/").status_code == 200
        assert client.get("/api/v1/me/").status_code == 200
        assert client.get("/api/v1/accounts/").status_code == 200

        assert _counts(api_key) == {("me.read", 200): 2, ("accounts.list", 200): 1}
        row = ApiKeyUsageHourly.objects.get(api_key=api_key, action="me.read")
        assert row.actor == f"key:{api_key.pk}"
        assert row.workspace_id == api_key.workspace_id
        assert not ApiKeyAuditLog.objects.filter(api_key=api_key).exists()

    def test_rest_write_is_counted_and_logged(self, client, api_key, social_account):
        r = client.post(
            "/api/v1/posts/",
            data=json.dumps({"social_account_id": str(social_account.id), "caption": "hi", "action": "draft"}),
            content_type="application/json",
        )
        assert r.status_code == 201
        assert _counts(api_key) == {("post.create.draft", 201): 1}
        assert ApiKeyAuditLog.objects.filter(api_key=api_key, action="post.create.draft").count() == 1

    def test_failed_read_keeps_its_audit_row(self, client, api_key):
        assert client.get(f"/api/v1/posts/{uuid.uuid4()}").status_code == 404
        assert _counts(api_key) == {("post.read.404", 404): 1}
        assert ApiKeyAuditLog.objects.filter(api_key=api_key, status_code=404).count() == 1

    def test_mcp_protocol_and_read_tools_are_counted_only(self, client, api_key):
        _mcp(client, "ping")
        _mcp(client, "tools/list")
        _mcp(client, "tools/call", {"name": "list_accounts", "arguments": {}})

        assert _counts(api_key) == {
            ("mcp.ping", 200): 1,
            ("mcp.tools/list", 200): 1,
            ("mcp.tools/call:list_accounts", 200): 1,
        }
        assert not ApiKeyAuditLog.objects.filter(api_key=api_key).exists()

    def test_mcp_write_tool_failure_is_logged(self, client, api_key):
        body = _mcp(client, "tools/call", {"name": "create_draft", "arguments": {}}).json()
        assert body["error"]["code"] == -32602
        row = ApiKeyAuditLog.objects.get(api_key=api_key)
        assert (row.action, row.status_code) == ("mcp.tools/call:create_draft", 422)

    def test_malformed_mcp_body_is_counted(self, client, api_key):
        # Returns before any JSON-RPC message is dispatched, so only the
        # catch-all middleware can count it.
        r = client.post(MCP_URL, data="{not json", content_type="application/json")
        assert r.status_code == 400
        assert _counts(api_key) == {("mcp.error.400", 400): 1}
        assert not ApiKeyAuditLog.objects.filter(api_key=api_key).exists()

    def test_idempotent_replay_is_counted(self, client, api_key, social_account):
        payload = json.dumps({"social_account_id": str(social_account.id), "caption": "once", "action": "draft"})
        for _ in range(2):
            r = client.post("/api/v1/posts/", data=payload, content_type="application/json", HTTP_IDEMPOTENCY_KEY="k-1")
            assert r.status_code == 201

        # The replay returns before ``log_audit_entry``: counted by the
        # catch-all, and no second audit row for a request that changed nothing.
        assert _counts(api_key) == {("post.create.draft", 201): 1, ("post.create.201", 201): 1}
        assert ApiKeyAuditLog.objects.filter(api_key=api_key).count() == 1

    def test_client_chosen_names_collapse_to_unknown(self, client, api_key):
        _mcp(client, "tools/call", {"name": f"made_up_{uuid.uuid4().hex}", "arguments": {}})
        _mcp(client, f"made/up/{uuid.uuid4().hex}")
        _mcp(client, "resources/list")

        actions = {action for action, _status in _counts(api_key)}
        assert actions == {"mcp.tools/call:unknown", "mcp.unknown", "mcp.resources/list"}


@pytest.mark.django_db
class TestHourlyAndDailyCaps:
    @pytest.fixture(autouse=True)
    def _limits_on(self, settings):
        # ``RATELIMIT_ENABLE`` is derived from the env's DEBUG in base settings,
        # so it is off on a dev machine even under the test settings.
        settings.RATELIMIT_ENABLE = True

    def test_hourly_cap_returns_429_until_the_next_hour(self, client, api_key):
        _set_caps(api_key, hourly=2)
        assert client.get("/api/v1/me/").status_code == 200
        assert client.get("/api/v1/me/").status_code == 200

        r = client.get("/api/v1/me/")
        assert r.status_code == 429
        body = r.json()
        assert body["tier"] == "per_key_hourly"
        assert body["limit"] == 2
        assert 1 <= int(r["Retry-After"]) <= 3600

        # The refusal is counted under its own status and earns no row.
        assert _counts(api_key)[("me.read.429", 429)] == 1
        assert not ApiKeyAuditLog.objects.filter(api_key=api_key).exists()

    def test_refused_calls_do_not_extend_the_lockout(self, client, api_key):
        _set_caps(api_key, hourly=1)
        client.get("/api/v1/me/")
        for _ in range(3):
            assert client.get("/api/v1/me/").status_code == 429
        # Three 429s on top of the one real call; only the real call is spent.
        assert _counts(api_key) == {("me.read", 200): 1, ("me.read.429", 429): 3}

    def test_daily_cap_counts_every_hour_of_the_utc_day(self, client, api_key):
        _set_caps(api_key, hourly=10_000, daily=5)
        _seed(api_key, at=day_start(timezone.now()), count=5)

        r = client.get("/api/v1/me/")
        assert r.status_code == 429
        assert r.json()["tier"] == "per_key_daily"
        assert int(r["Retry-After"]) <= 24 * 3600

    def test_yesterday_does_not_count(self, client, api_key):
        _set_caps(api_key, hourly=5, daily=5)
        _seed(api_key, at=day_start(timezone.now()) - dt.timedelta(minutes=30), count=500)
        assert client.get("/api/v1/me/").status_code == 200

    def test_earlier_429s_do_not_count(self, client, api_key):
        _set_caps(api_key, hourly=5, daily=5)
        _seed(api_key, at=timezone.now(), count=500, status_code=429)
        assert client.get("/api/v1/me/").status_code == 200

    def test_zero_override_freezes_the_key(self, client, api_key):
        _set_caps(api_key, daily=0)
        assert client.get("/api/v1/me/").status_code == 429

    def test_calls_that_return_early_spend_the_budget(self, client, api_key):
        _set_caps(api_key, hourly=2)
        for _ in range(2):
            assert client.post(MCP_URL, data="{not json", content_type="application/json").status_code == 400
        r = client.post(MCP_URL, data="{not json", content_type="application/json")
        assert r.status_code == 429
        assert r.json()["tier"] == "per_key_hourly"

    def test_mcp_is_capped_too(self, client, api_key):
        _set_caps(api_key, hourly=1)
        assert _mcp(client, "ping").status_code == 200
        r = _mcp(client, "ping")
        assert r.status_code == 429
        assert r.json()["tier"] == "per_key_hourly"
        assert _counts(api_key)[("mcp.error.429", 429)] == 1


@pytest.mark.django_db
class TestRetentionSweep:
    def test_sweep_deletes_only_rows_past_retention(self, api_key):
        now = timezone.now()
        old_audit = ApiKeyAuditLog.objects.create(
            api_key=api_key, action="post.create.draft", method="POST", path="/", status_code=201
        )
        ApiKeyAuditLog.objects.filter(pk=old_audit.pk).update(created_at=now - dt.timedelta(days=400))
        fresh_audit = ApiKeyAuditLog.objects.create(
            api_key=api_key, action="post.create.draft", method="POST", path="/", status_code=201
        )
        _seed(api_key, at=now - dt.timedelta(days=400), count=1)
        _seed(api_key, at=now, count=1)

        getattr(sweep_api_usage_records, "task_function", sweep_api_usage_records)()

        assert list(ApiKeyAuditLog.objects.values_list("pk", flat=True)) == [fresh_audit.pk]
        assert list(ApiKeyUsageHourly.objects.values_list("hour_start", flat=True)) == [hour_start(now)]
