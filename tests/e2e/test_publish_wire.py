"""End-to-end: each supported platform puts the RIGHT BYTES on the wire.

Rule 8 - every supported platform must be tested end to end where possible,
preferring official testing aids, then community ones, and falling back to
tests written from the official API documentation.

WHY THIS IS SEPARATE FROM test_publish_path.py. That module proves the whole
chain for one platform in depth: the schedule fires, the engine claims, media
is downloaded and cleaned up, retries land, the first comment defers. This one
proves a SINGLE property for MANY platforms - that the provider builds the
request the platform's API actually documents - and is shaped so that adding a
platform is adding a case, not a file.

WHAT IS REAL AND WHAT IS NOT. Real: the production command, the schedule, the
engine, credential resolution, and the provider's own request building and
response parsing. Faked: the wire, and only the wire, via httpx's MockTransport.

The seam is at the wire on purpose. A test that patches
PublishEngine._dispatch_to_provider never runs the provider at all, so a
malformed payload passes unnoticed - which is why deleting the facet parsing
from the Bluesky provider left every status-level test green.

transaction=True is REQUIRED, not incidental: poll_and_publish fans out over a
ThreadPoolExecutor whose threads open their own connections, so under the
default wrapping they would see an empty database and publish nothing - the
test would pass while proving nothing.
"""

from datetime import timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.composer.models import PlatformPost, Post
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

CAPTION = "shipped by the worker"


class WireRecorder:
    """Answers the calls a provider makes, and keeps every request it made.

    `routes` maps a URL-path SUFFIX to a handler taking the request and
    returning an httpx.Response. Anything unrouted is recorded as unexpected
    and answered 404 rather than quietly satisfied, so a provider reaching for
    an endpoint this test did not predict SHOWS UP instead of passing silently.
    """

    def __init__(self, routes):
        self.routes = routes
        self.requests: list[httpx.Request] = []
        self.unexpected: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for suffix, responder in self.routes.items():
            if request.url.path.endswith(suffix):
                return responder(request)
        self.unexpected.append(f"{request.method} {request.url.path}")
        return httpx.Response(404, json={"error": "unrouted in this test"})

    def call(self, suffix: str) -> httpx.Request | None:
        for request in self.requests:
            if request.url.path.endswith(suffix):
                return request
        return None

    def form(self, suffix: str) -> dict:
        """The form body of the first request to `suffix`, as a flat dict."""
        request = self.call(suffix)
        assert request is not None, f"the provider never called {suffix}"
        return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


@pytest.fixture
def wire(monkeypatch):
    """Install a WireRecorder over every httpx.Client this process builds.

    providers/base.py constructs `httpx.Client(timeout=...)` inline per request,
    so there is no transport to inject - the class itself is replaced. That is
    deliberately process-wide, because the engine's worker threads build their
    own clients.
    """
    real_client = httpx.Client

    def install(routes) -> WireRecorder:
        recorder = WireRecorder(routes)

        def client_with_mock_transport(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(recorder.handle)
            return real_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "Client", client_with_mock_transport)
        return recorder

    return install


#: The worker has no --once; `process_tasks` loops until killed, so a duration
#: is the only way to get it to return.
WORKER_SECONDS = "5"


def run_the_worker():
    """Enqueue the publish cycle and run the REAL worker until it drains.

    Enqueued explicitly rather than waited for. `post_migrate` registers the
    cycle at repeat=15, so a test COULD sit and hope the recurring row comes
    due inside the worker's lifetime - which makes every assertion below depend
    on wall-clock timing against a fifteen-second cadence, and that is how a
    suite becomes intermittently red for reasons nobody can reproduce.

    Calling a @background function IS the enqueue, so this is the same row the
    scheduler would have written; only its arrival is made deterministic.
    """
    from apps.publisher.tasks import run_publish_cycle

    run_publish_cycle()
    call_command("process_tasks", "--duration", WORKER_SECONDS)


def schedule_a_post(*, platform, platform_id, token, instance_url="", caption=CAPTION):
    """One account on `platform` with one post due a minute ago."""
    organization = Organization.objects.create(name=f"E2E {platform} Org")
    workspace = Workspace.objects.create(name=f"E2E {platform} WS", organization=organization)
    account = SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=platform_id,
        account_name=f"Brightbean {platform}",
        oauth_access_token=token,
        instance_url=instance_url,
        connection_status=SocialAccount.ConnectionStatus.CONNECTED,
    )
    post = Post.objects.create(workspace=workspace, caption=caption)
    return PlatformPost.objects.create(
        post=post,
        social_account=account,
        status=PlatformPost.Status.SCHEDULED,
        scheduled_at=timezone.now() - timedelta(minutes=1),
    )


def assert_published(platform_post, expected_id):
    platform_post.refresh_from_db()
    assert platform_post.status == PlatformPost.Status.PUBLISHED, (
        f"still {platform_post.status!r}; publish_error={platform_post.publish_error!r}"
    )
    assert platform_post.platform_post_id == expected_id
    assert platform_post.published_at is not None


# ---------------------------------------------------------------------------
# Mastodon - https://docs.joinmastodon.org/methods/statuses/#create
# ---------------------------------------------------------------------------

MASTODON_INSTANCE = "https://mastodon.example"
MASTODON_STATUS_ID = "109999999999999999"
MASTODON_TOKEN = "mastodon-access-token"


@pytest.mark.django_db(transaction=True)
def test_mastodon_posts_a_status_to_its_own_instance(wire, monkeypatch):
    """A Mastodon status is a form POST to the ACCOUNT'S OWN instance.

    Two things here are specific to Mastodon, and are what this test is for.

    The host is PER ACCOUNT, not a constant: the engine copies
    `account.instance_url` into the credentials and the provider builds every
    URL from it. A bug there publishes to the wrong server - or, if the value
    is dropped, to a relative URL that never leaves the process.

    And the body is FORM-encoded, not JSON. The API documents
    application/x-www-form-urlencoded for POST /api/v1/statuses, so asserting
    on parsed form fields is asserting the documented contract.

    `is_safe_url` is patched because it calls socket.getaddrinfo - a real DNS
    lookup. It is our own SSRF validator and has its own tests; leaving it live
    would make this a network-dependent test of somebody else's nameserver.
    """
    monkeypatch.setattr("apps.common.validators.is_safe_url", lambda url: True)

    recorder = wire(
        {
            "/api/v1/statuses": lambda request: httpx.Response(
                200,
                json={
                    "id": MASTODON_STATUS_ID,
                    "url": f"{MASTODON_INSTANCE}/@brightbean/{MASTODON_STATUS_ID}",
                    "content": CAPTION,
                },
            ),
            # NOT publishing, and routed anyway. The worker runs the WHOLE
            # recurring schedule, not just the publish cycle, so this account
            # also gets an inbox poll and an OAuth health check inside the same
            # window. Leaving them unrouted makes the recorder report them as
            # unpredicted and fails a test about publishing for a reason that
            # has nothing to do with publishing.
            "/api/v1/notifications": lambda request: httpx.Response(200, json=[]),
            "/api/v1/accounts/verify_credentials": lambda request: httpx.Response(
                200,
                json={
                    "id": "110000000000000001",
                    "username": "brightbean",
                    "acct": "brightbean",
                    "display_name": "Brightbean",
                    "followers_count": 7,
                },
            ),
        }
    )
    platform_post = schedule_a_post(
        platform="mastodon",
        platform_id="110000000000000001",
        token=MASTODON_TOKEN,
        instance_url=MASTODON_INSTANCE,
    )

    run_the_worker()

    assert recorder.unexpected == [], f"unpredicted API calls: {recorder.unexpected}"
    assert_published(platform_post, MASTODON_STATUS_ID)

    request = recorder.call("/api/v1/statuses")
    assert str(request.url).startswith(MASTODON_INSTANCE), (
        f"published to {request.url}, not to the account's own instance - the "
        f"per-account instance_url did not reach the provider"
    )
    assert request.headers["Authorization"] == f"Bearer {MASTODON_TOKEN}"

    body = recorder.form("/api/v1/statuses")
    assert body["status"] == CAPTION
    # The API defaults visibility to the account's own setting when the field
    # is absent, so sending it explicitly is what makes the outcome predictable.
    assert body["visibility"] == "public"
