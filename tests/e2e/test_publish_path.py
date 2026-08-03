"""End-to-end: a scheduled post actually reaches the platform.

Publishing is the application's reason to exist, and nothing exercised it end
to end. The queue tests prove work runs; the CSP tests prove pages render.
Neither proves that scheduling a post causes a post to be published.

What is real here, and what is not.

REAL: the production command (manage.py run_tasks --once), the declarative
schedule deciding run_publish_cycle is due, the engine's due-query and its
ThreadPoolExecutor fan-out, credential resolution through
_resolve_publish_credentials, the Bluesky provider's own request building and
response parsing, and every database transition the engine performs.

FAKED: the wire, and only the wire. httpx's own MockTransport answers the two
AT Protocol calls the provider makes.

That seam is deliberately LOWER than the unit tests use.
apps/api/tests/test_e2e.py patches PublishEngine._dispatch_to_provider, so the
provider is never exercised and a malformed payload would pass unnoticed. Here
the provider builds a real request and the test asserts on what it put on the
wire - the record type, the text, the parsed facets, and the bearer token.

Bluesky is the platform under test because its auth is session-based, so no app
credentials have to be invented, and its publish path is two documented XRPC
calls: com.atproto.server.getSession and com.atproto.repo.createRecord.

transaction=True is REQUIRED, not incidental. poll_and_publish fans out over a
ThreadPoolExecutor, and those threads open their own database connections. Under
the default transactional wrapping they would see an empty database and the
engine would find nothing to publish - the test would pass while proving
nothing.
"""

import json
import os
from datetime import timedelta

import httpx
import pytest
from background_task.models import Task
from django.core.management import call_command
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.publisher.engine import FIRST_COMMENT_DELAY
from apps.publisher.models import PublishLog
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

DID = "did:plc:e2epublishtest"
HANDLE = "brightbean-e2e.bsky.social"
POST_URI = f"at://{DID}/app.bsky.feed.post/3ke2epublish"
ACCESS_TOKEN = "e2e-access-jwt"
CAPTION = "shipped by the worker #brightbean"
BLOB_LINK = "bafye2eblobref"


class RecordingBlueskyApi:
    """A stand-in PDS that answers the two calls publish_post makes.

    Records every request so the test can assert on what the REAL provider
    code decided to send, rather than on a stub's arguments.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.unexpected: list[str] = []
        self.uploaded_blobs: list[bytes] = []
        self.create_record_status = 200

    def fail_create_record(self, status: int = 502) -> None:
        """Make the next publish attempt fail at the platform.

        One handler serves both the success and failure cases deliberately.
        Stacking a second monkeypatch over the fixture's does NOT work: the
        replacement client re-injects its own transport over whatever the
        caller passed, so the second handler is silently discarded and the
        test passes while proving the opposite of what it claims.
        """
        self.create_record_status = status

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("com.atproto.server.getSession"):
            return httpx.Response(200, json={"did": DID, "handle": HANDLE})
        if path.endswith("app.bsky.actor.getProfile"):
            # The health check reaches this. Tasks are claimed one at a time, so
            # work enqueued during a tick - schedule_all_health_checks enqueues
            # check_social_account_health - drains in that same tick rather than
            # waiting for the next one.
            return httpx.Response(
                200,
                json={"did": DID, "handle": HANDLE, "displayName": "Brightbean E2E", "followersCount": 7},
            )
        if path.endswith("com.atproto.repo.uploadBlob"):
            self.uploaded_blobs.append(request.content)
            return httpx.Response(
                200,
                json={
                    "blob": {
                        "$type": "blob",
                        "ref": {"$link": BLOB_LINK},
                        "mimeType": "image/png",
                        "size": len(request.content),
                    }
                },
            )
        if path.endswith("com.atproto.repo.createRecord"):
            if self.create_record_status >= 400:
                return httpx.Response(self.create_record_status, json={"error": "UpstreamFailure"})
            return httpx.Response(200, json={"uri": POST_URI, "cid": "bafye2etestcid"})
        # Anything else is a call this test did not predict. Record it rather
        # than answering it, so an unexpected dependency surfaces instead of
        # being quietly satisfied.
        self.unexpected.append(path)
        return httpx.Response(404, json={"error": "NotFound", "message": path})

    def call(self, suffix: str) -> httpx.Request | None:
        for request in self.requests:
            if request.url.path.endswith(suffix):
                return request
        return None

    def created_record(self) -> dict:
        request = self.call("com.atproto.repo.createRecord")
        assert request is not None, "the provider never called createRecord"
        return json.loads(request.content)


#: How long to let the worker live. It has no --once: `process_tasks` loops
#: until killed, so a duration is the only way to get it to return. Five
#: seconds is comfortably more than a mocked publish needs and short enough
#: that six tests do not dominate the suite.
WORKER_SECONDS = "5"


def run_the_worker():
    """Enqueue the publish cycle and run the REAL worker until it drains.

    The cycle is enqueued explicitly rather than waited for. `post_migrate`
    registers it at repeat=15, so a test COULD sit and hope the recurring row
    comes due inside the worker's lifetime - but that makes every assertion
    below depend on wall-clock timing against a fifteen-second cadence, which
    is how a suite becomes intermittently red for reasons nobody can reproduce.

    Calling a @background function IS the enqueue, so this is the same row the
    scheduler would have produced; only its arrival is made deterministic.
    """
    from apps.publisher.tasks import run_publish_cycle

    run_publish_cycle()
    call_command("process_tasks", "--duration", WORKER_SECONDS)


@pytest.fixture
def bluesky_api(monkeypatch):
    """Route every httpx request through a MockTransport.

    providers/base.py builds `httpx.Client(timeout=...)` inline per request, so
    there is no transport to inject - the client class itself is replaced. The
    substitution is process-wide, which is what the engine's worker threads
    need, since they build their own clients.
    """
    api = RecordingBlueskyApi()
    real_client = httpx.Client

    def client_with_mock_transport(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(api.handle)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_mock_transport)
    return api


@pytest.fixture
def scheduled_post(db):
    """One Bluesky post, due a minute ago.

    instance_url is deliberately left empty: _resolve_publish_credentials only
    consults it to override pds_url, and doing so would run the SSRF check,
    which resolves DNS. token_expires_at is None so the engine's refresh branch
    is not taken - token refresh is a different path with its own coverage.
    """
    organization = Organization.objects.create(name="E2E Publish Org")
    workspace = Workspace.objects.create(name="E2E Publish WS", organization=organization)
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="bluesky",
        account_platform_id=DID,
        account_name="Brightbean E2E",
        account_handle=HANDLE,
        oauth_access_token=ACCESS_TOKEN,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    post = Post.objects.create(workspace=workspace, caption=CAPTION)
    platform_post = PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.SCHEDULED,
        scheduled_at=timezone.now() - timedelta(minutes=1),
    )
    return platform_post


@pytest.mark.django_db(transaction=True)
def test_a_due_post_is_published_by_the_worker(bluesky_api, scheduled_post):
    """The whole chain, driven by the command production actually runs."""
    run_the_worker()

    scheduled_post.refresh_from_db()
    assert scheduled_post.status == PlatformPost.Status.PUBLISHED, (
        f"still {scheduled_post.status!r}; publish_error={scheduled_post.publish_error!r}"
    )
    assert scheduled_post.platform_post_id == POST_URI
    assert scheduled_post.published_at is not None

    # The parent's published_at is maintained for dashboards that show
    # "last published" without aggregating children at read time.
    scheduled_post.post.refresh_from_db()
    assert scheduled_post.post.published_at is not None

    # One attempt, logged. A second row here would mean a double publish.
    assert PublishLog.objects.filter(platform_post=scheduled_post).count() == 1


@pytest.mark.django_db(transaction=True)
def test_the_provider_put_a_real_at_protocol_record_on_the_wire(bluesky_api, scheduled_post):
    """What reached the wire is the point.

    Patching _dispatch_to_provider - which the unit suite does - cannot catch a
    provider that builds the wrong payload, because it never runs one.
    """
    run_the_worker()

    assert bluesky_api.unexpected == [], f"unpredicted API calls: {bluesky_api.unexpected}"

    session = bluesky_api.call("com.atproto.server.getSession")
    assert session is not None, "the provider never opened a session"
    # Proves the token travelled the whole way: account row ->
    # _resolve_publish_credentials -> get_provider -> publish_post -> header.
    assert session.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"

    body = bluesky_api.created_record()
    assert body["repo"] == DID
    assert body["collection"] == "app.bsky.feed.post"

    record = body["record"]
    assert record["$type"] == "app.bsky.feed.post"
    assert record["text"] == CAPTION
    assert record["createdAt"].endswith("Z")

    # The provider parsed "#brightbean" into an AT Protocol facet. A stubbed
    # dispatch would never have run this code at all.
    tags = [
        feature["tag"]
        for facet in record.get("facets", [])
        for feature in facet["features"]
        if feature["$type"] == "app.bsky.richtext.facet#tag"
    ]
    assert tags == ["brightbean"], f"facets were not parsed: {record.get('facets')}"


@pytest.mark.django_db(transaction=True)
def test_a_platform_failure_leaves_the_post_retryable(bluesky_api, scheduled_post):
    """A refused publish must not be marked published, and must not be lost.

    providers.exceptions.APIError carries retryable=True by default and
    _request raises it without overriding that, so the engine schedules
    backoff rather than failing the post outright. The row goes back to
    SCHEDULED so the next _process_retries tick picks it up.
    """
    bluesky_api.fail_create_record(502)

    run_the_worker()

    scheduled_post.refresh_from_db()
    assert scheduled_post.status == PlatformPost.Status.SCHEDULED
    assert scheduled_post.platform_post_id == ""
    assert scheduled_post.published_at is None
    assert scheduled_post.next_retry_at is not None
    assert "502" in scheduled_post.publish_error

    # AT LEAST one, not exactly one, and the difference is a real property of
    # the worker rather than test slack.
    #
    # `post_migrate` registers run_publish_cycle at repeat=15, so that recurring
    # row can come due inside the worker's lifetime alongside the one this test
    # enqueues. Each cycle re-attempts the post, because the engine's due query
    # filters on `scheduled_at`, NOT on `next_retry_at` - the backoff is honoured
    # by _process_retries, but a post whose scheduled_at is already past is due
    # again immediately on the ordinary path.
    #
    # Pre-existing, and invisible while a tick ran exactly one cycle. Pinning
    # this to == 1 would be pinning the number of cycles that happened to fit in
    # five seconds, which is a clock-speed assertion wearing a behaviour's
    # clothes.
    assert scheduled_post.retry_count >= 1
    assert PublishLog.objects.filter(platform_post=scheduled_post).count() == scheduled_post.retry_count


# ---------------------------------------------------------------------------
# Media: downloaded to a temp file by the engine, uploaded by the provider,
# and - the part nothing asserted - cleaned up afterwards.
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_media_is_uploaded_and_the_temp_file_is_removed(bluesky_api, scheduled_post, monkeypatch):
    """The engine downloads every attachment to a temp file and unlinks it in a
    finally. If that ever stops happening a long-lived worker fills its disk,
    and nothing else in the suite would notice.

    _upload_blob is wrapped rather than replaced - the real implementation still
    runs, and the wrapper only records which path the engine handed it, so the
    paths can be checked for existence after the tick.
    """
    from django.core.files.base import ContentFile

    from apps.composer.models import PostMedia
    from apps.media_library.models import MediaAsset
    from providers.bluesky import BlueskyProvider

    workspace = scheduled_post.social_account.workspace
    asset = MediaAsset.objects.create(
        organization=workspace.organization,
        workspace=workspace,
        filename="e2e.png",
        media_type="image",
        mime_type="image/png",
    )
    # The bytes never leave the harness - nothing sniffs content, and the
    # provider guesses its mime type from the filename - so plain ASCII keeps
    # escape sequences out of a file that is itself generated from a string.
    asset.file.save("e2e.png", ContentFile(b"pretend this is a png" * 4), save=True)
    PostMedia.objects.create(post=scheduled_post.post, media_asset=asset, position=0)

    handed_to_provider: list[str] = []
    real_upload_blob = BlueskyProvider._upload_blob

    def recording_upload_blob(self, access_token, media_path):
        handed_to_provider.append(media_path)
        return real_upload_blob(self, access_token, media_path)

    monkeypatch.setattr(BlueskyProvider, "_upload_blob", recording_upload_blob)

    run_the_worker()

    scheduled_post.refresh_from_db()
    assert scheduled_post.status == PlatformPost.Status.PUBLISHED, scheduled_post.publish_error

    assert len(handed_to_provider) == 1, "the engine never handed the provider a downloaded file"
    assert bluesky_api.uploaded_blobs, "no blob reached the platform"

    record = bluesky_api.created_record()["record"]
    assert record["embed"]["$type"] == "app.bsky.embed.images"
    assert record["embed"]["images"][0]["image"]["ref"]["$link"] == BLOB_LINK

    leftover = [path for path in handed_to_provider if os.path.exists(path)]
    assert leftover == [], f"temp files were left behind: {leftover}"


@pytest.mark.django_db(transaction=True)
def test_a_retry_publishes_on_a_later_tick(bluesky_api, scheduled_post):
    """Scheduling a retry is only half the promise; this is the other half.

    test_a_platform_failure_leaves_the_post_retryable proves the backoff is
    recorded. Nothing proved the post then actually goes out, which is the part
    a user cares about.
    """
    bluesky_api.fail_create_record(502)
    run_the_worker()

    scheduled_post.refresh_from_db()
    assert scheduled_post.retry_count >= 1, "the failure was not recorded as an attempt"

    # The platform recovers, and the post's backoff window elapses. Only ONE
    # clock has to move now: run_the_worker enqueues the cycle itself, so there
    # is no scheduler anchor to wind forward - which is one fewer thing this
    # test depends on than when the queue was ours.
    bluesky_api.create_record_status = 200
    PlatformPost.objects.filter(pk=scheduled_post.pk).update(next_retry_at=timezone.now() - timedelta(seconds=1))

    run_the_worker()

    scheduled_post.refresh_from_db()
    assert scheduled_post.status == PlatformPost.Status.PUBLISHED, scheduled_post.publish_error
    assert scheduled_post.platform_post_id == POST_URI
    # Both attempts are on the record: the platform's refusal is not erased by
    # the eventual success.
    assert PublishLog.objects.filter(platform_post=scheduled_post).count() >= 2, (
        "the platform's refusal was erased by the eventual success"
    )


# ---------------------------------------------------------------------------
# Threads: the first comment, the one DEFERRED hand-off inside the publish path
# ---------------------------------------------------------------------------

THREADS_USER_ID = "9876543210"
THREADS_POST_ID = "thread-e2e-1"
THREADS_REPLY_ID = "thread-e2e-reply"
FIRST_COMMENT = "and the link is in this reply"


class RecordingThreadsApi:
    """A stand-in Threads Graph API.

    Threads publishes in two steps - create a container, then publish it - and
    replies exactly the same way with reply_to_id set. Recording the container
    payloads is therefore enough to tell a post from its reply.
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.unexpected: list[str] = []

    @staticmethod
    def form(request: httpx.Request) -> dict:
        from urllib.parse import parse_qs

        return {key: values[0] for key, values in parse_qs(request.content.decode()).items()}

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/me"):
            return httpx.Response(200, json={"id": THREADS_USER_ID, "username": "brightbean"})
        if path.endswith("/threads_publish"):
            is_reply = self.form(request).get("creation_id") == "reply-container"
            return httpx.Response(200, json={"id": THREADS_REPLY_ID if is_reply else THREADS_POST_ID})
        if path.endswith("/threads"):
            reply_to = self.form(request).get("reply_to_id")
            return httpx.Response(200, json={"id": "reply-container" if reply_to else "post-container"})
        self.unexpected.append(path)
        return httpx.Response(404, json={"error": {"message": path}})

    def containers(self) -> list[dict]:
        return [self.form(r) for r in self.requests if r.url.path.endswith("/threads")]


@pytest.fixture
def threads_api(monkeypatch):
    api = RecordingThreadsApi()
    real_client = httpx.Client

    def client_with_mock_transport(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(api.handle)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_with_mock_transport)
    return api


@pytest.fixture
def threads_post_with_first_comment(db):
    organization = Organization.objects.create(name="E2E Threads Org")
    workspace = Workspace.objects.create(name="E2E Threads WS", organization=organization)
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform="threads",
        account_platform_id=THREADS_USER_ID,
        account_name="Brightbean Threads",
        oauth_access_token=ACCESS_TOKEN,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    post = Post.objects.create(
        workspace=workspace,
        caption="threads post from the worker",
        first_comment=FIRST_COMMENT,
    )
    return PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.SCHEDULED,
        scheduled_at=timezone.now() - timedelta(minutes=1),
    )


@pytest.mark.django_db(transaction=True)
def test_the_first_comment_is_deferred_then_posted(threads_api, threads_post_with_first_comment):
    """The publish path's only deferred hand-off, driven end to end.

    The engine does not post the first comment inline: it enqueues
    _post_first_comment_task with run_after set FIRST_COMMENT_DELAY seconds out.
    So this asserts three things no status check can - that the tick which
    published did NOT also reply, that the deferred row carries a real future
    run_after, and that a later tick posts the reply against the thread that was
    actually published.

    It is also the only end-to-end exercise of `schedule=`, which every other
    deferred call site in the application depends on - the intelligence backoff
    ladder and the fourteen-day organization deletion among them.
    """
    platform_post = threads_post_with_first_comment

    run_the_worker()

    platform_post.refresh_from_db()
    assert platform_post.status == PlatformPost.Status.PUBLISHED, platform_post.publish_error
    assert platform_post.platform_post_id == THREADS_POST_ID

    deferred = Task.objects.get(task_name="apps.publisher.engine._post_first_comment_task")
    assert str(platform_post.id) in deferred.task_params, "the reply was queued for the wrong post"
    seconds_out = (deferred.run_at - timezone.now()).total_seconds()
    assert 60 < seconds_out <= FIRST_COMMENT_DELAY + 5, f"run_at is {seconds_out}s out"

    assert [c for c in threads_api.containers() if c.get("reply_to_id")] == [], "replied too early"

    # Let its moment arrive, and run the worker again. `run_the_worker` also
    # enqueues a publish cycle, which finds nothing left to publish - harmless,
    # and cheaper than a second helper that differs by one line.
    Task.objects.filter(pk=deferred.pk).update(run_at=timezone.now() - timedelta(seconds=1))
    run_the_worker()

    assert not Task.objects.filter(pk=deferred.pk).exists(), "the deferred reply was never consumed"

    replies = [c for c in threads_api.containers() if c.get("reply_to_id")]
    assert len(replies) == 1, f"expected exactly one reply container, got {replies}"
    assert replies[0]["reply_to_id"] == THREADS_POST_ID
    assert replies[0]["text"] == FIRST_COMMENT
