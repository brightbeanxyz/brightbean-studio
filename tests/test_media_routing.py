"""Routing tests for user-uploaded media (``MEDIA_URL`` -> ``MEDIA_ROOT``).

Three separate regressions are pinned here.

The first is issue #130: ``config/urls.py`` used to mount media only under
``settings.DEBUG``, so a ``config.settings.production`` deployment with
``STORAGE_BACKEND=local`` returned 404 for every upload. That breaks more than
the thumbnails in the UI — ``apps/publisher/engine.py`` builds each attachment's
outbound URL as ``APP_URL + asset.file.url``, and Instagram, Threads, Facebook,
Pinterest, Google Business and dev.to fetch that URL server-side with no
byte-upload fallback, so publishing to them fails too.

The second is the shape of the route. ``MEDIA_URL`` is only assigned on the
local-storage branch of ``config/settings/base.py``; under ``STORAGE_BACKEND=s3``
Django normalises the unset default to ``"/"``, and a ``"/"`` prefix compiles to
``^(?P<path>.*)$`` — a catch-all appended after every real route, serving
whatever it matches out of the process CWD. That is how the dev server came to
answer ``GET /.env`` with the repo's own environment file.

The third is the middleware stack in front of the route. ``/media/`` is served
straight off disk with no view behind it, so ``TosAcceptanceMiddleware`` must
not redirect it — a user whose ``tos_accepted_at`` is NULL (every account made
with ``createsuperuser``) would otherwise get a 302 in place of every image.
"""

import importlib
import importlib.util
import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pytest
from django.conf import settings
from django.test import Client, override_settings
from django.urls import Resolver404, clear_url_caches, resolve
from django.utils import timezone
from django.views.static import serve

import config.urls
from apps.accounts.models import User
from config.urls import PUBLIC_MEDIA_PREFIXES, media_urlpatterns

BASE_SETTINGS_PATH = Path(config.urls.__file__).resolve().parent / "settings" / "base.py"


@contextmanager
def urlconf_built_with(**overrides):
    """Rebuild ``config.urls`` under ``overrides``, then restore the real one.

    ``override_settings`` on its own changes nothing here: the route is
    appended when the module first executes, so both ``SERVE_MEDIA`` and the
    ``document_root`` baked into the pattern are fixed at import time.
    """
    try:
        with override_settings(**overrides):
            importlib.reload(config.urls)
            clear_url_caches()
            yield
    finally:
        importlib.reload(config.urls)
        clear_url_caches()


def _base_settings_with_env(**environ):
    """Execute ``config/settings/base.py`` under ``environ`` as a throwaway module.

    Loaded under a private name so the real ``config.settings.base`` is left
    alone. ``base.py`` reads ``.env`` with ``overwrite=False``, so the values
    passed here win on a developer machine as well as in CI.
    """
    spec = importlib.util.spec_from_file_location("config.settings._probe", BASE_SETTINGS_PATH)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(os.environ, environ):
        spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The SERVE_MEDIA setting itself
# ---------------------------------------------------------------------------


def test_s3_backend_forces_serve_media_off():
    """Object storage hands out its own presigned URLs; this process serves nothing."""
    assert _base_settings_with_env(STORAGE_BACKEND="s3").SERVE_MEDIA is False


def test_s3_backend_ignores_an_explicit_serve_media():
    """The env var is documented as having no effect on the s3 branch."""
    assert _base_settings_with_env(STORAGE_BACKEND="s3", SERVE_MEDIA="true").SERVE_MEDIA is False


def test_local_backend_serves_media_by_default():
    base = _base_settings_with_env(STORAGE_BACKEND="local")

    assert base.SERVE_MEDIA is True
    assert base.MEDIA_URL == "/media/"


def test_local_backend_honours_serve_media_false():
    """The opt-out for deployments whose proxy or CDN serves MEDIA_ROOT instead."""
    assert _base_settings_with_env(STORAGE_BACKEND="local", SERVE_MEDIA="false").SERVE_MEDIA is False


# ---------------------------------------------------------------------------
# The helper that builds the route
# ---------------------------------------------------------------------------


def test_helper_builds_one_prefixed_route():
    with tempfile.TemporaryDirectory() as media_root:
        with override_settings(MEDIA_URL="/media/", MEDIA_ROOT=media_root):
            patterns = media_urlpatterns()

        assert len(patterns) == len(PUBLIC_MEDIA_PREFIXES)
        assert {p.callback for p in patterns} == {serve}
        assert {p.default_args["document_root"] for p in patterns} == {media_root}


@pytest.mark.parametrize("media_url", ["", "/"])
def test_helper_refuses_to_build_a_catch_all(media_url):
    """An empty prefix would match every unrouted URL — build nothing instead."""
    with (
        tempfile.TemporaryDirectory() as media_root,
        override_settings(MEDIA_URL=media_url, MEDIA_ROOT=media_root),
    ):
        assert media_urlpatterns() == []


def test_helper_ignores_an_absolute_media_url():
    """A CDN MEDIA_URL has nothing local to route; a pattern from it never matches."""
    with (
        tempfile.TemporaryDirectory() as media_root,
        override_settings(MEDIA_URL="https://cdn.example.com/media/", MEDIA_ROOT=media_root),
    ):
        assert media_urlpatterns() == []


def test_helper_warns_when_document_root_is_missing(caplog):
    """Without MEDIA_ROOT the route would serve relative to the process CWD."""
    with (
        override_settings(MEDIA_URL="/media/", MEDIA_ROOT=""),
        caplog.at_level(logging.WARNING, logger="config.urls"),
    ):
        assert media_urlpatterns() == []

    assert "MEDIA_ROOT is empty" in caplog.text


# ---------------------------------------------------------------------------
# The URLconf as actually built
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/media/media_library/2026/09/example.png",
        "/media/media_library/thumbs/2026/09/example.jpg",
        "/media/media_library/versions/2026/09/example.jpg",
        "/media/avatars/2026/09/me.png",
        "/media/workspaces/icons/2026/09/logo.png",
    ],
)
def test_public_prefixes_are_routed_with_debug_off(path):
    """The regression from #130: DEBUG is False here, the route still exists."""
    assert settings.DEBUG is False

    match = resolve(path)

    assert match.func is serve
    assert match.kwargs["path"] == path.removeprefix("/media/")


@pytest.mark.parametrize(
    "path",
    [
        "/media/comment_attachments/2026/09/private.png",
        "/media/csv_imports/leads.csv",
        "/media/some_future_prefix/thing.bin",
    ],
)
def test_non_public_prefixes_are_not_routed(path):
    """PUBLIC_MEDIA_PREFIXES is an allowlist, so anything unlisted has no route.

    comment_attachments/ is the one that matters today: PostComment.visibility
    can be "internal", which apps/client_portal/views.py filters out of what a
    portal client is shown, so a public URL would leak exactly that.
    """
    with pytest.raises(Resolver404):
        resolve(path)


def test_serve_media_off_removes_the_route():
    with urlconf_built_with(SERVE_MEDIA=False), pytest.raises(Resolver404):
        resolve("/media/media_library/2026/09/example.png")


@pytest.mark.parametrize("path", ["/.env", "/requirements.txt", "/config/settings/base.py"])
def test_urlconf_has_no_catch_all(path):
    """Nothing outside /media/ may fall through to the static file server."""
    with pytest.raises(Resolver404):
        resolve(path)


def test_media_file_is_served():
    with tempfile.TemporaryDirectory() as media_root:
        probe = Path(media_root) / "media_library" / "2026" / "09" / "routing-probe.png"
        probe.parent.mkdir(parents=True)
        probe.write_bytes(b"probe-bytes")

        with urlconf_built_with(SERVE_MEDIA=True, MEDIA_URL="/media/", MEDIA_ROOT=media_root):
            response = Client().get("/media/media_library/2026/09/routing-probe.png")

            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"probe-bytes"


def test_a_file_outside_the_public_prefixes_is_not_served():
    """Present on disk, reachable by no URL — the comment_attachments/ case."""
    with tempfile.TemporaryDirectory() as media_root:
        probe = Path(media_root) / "comment_attachments" / "2026" / "09" / "private.png"
        probe.parent.mkdir(parents=True)
        probe.write_bytes(b"internal-only")

        with urlconf_built_with(SERVE_MEDIA=True, MEDIA_URL="/media/", MEDIA_ROOT=media_root):
            response = Client().get("/media/comment_attachments/2026/09/private.png")

            assert response.status_code == 404


@pytest.mark.django_db
def test_media_is_exempt_from_the_tos_redirect():
    """A user who hasn't accepted the ToS still gets the bytes, not a 302.

    Every account created by ``manage.py createsuperuser`` has a NULL
    ``tos_accepted_at``, and the accept-terms page itself renders avatars and
    workspace icons out of MEDIA_ROOT.
    """
    user = User.objects.create_user(email="no-tos@example.com", password="testpass123")
    assert user.tos_accepted_at is None

    with tempfile.TemporaryDirectory() as media_root:
        probe = Path(media_root) / "avatars" / "2026" / "09" / "avatar.png"
        probe.parent.mkdir(parents=True)
        probe.write_bytes(b"png-bytes")

        with urlconf_built_with(SERVE_MEDIA=True, MEDIA_URL="/media/", MEDIA_ROOT=media_root):
            client = Client()
            client.force_login(user)

            response = client.get("/media/avatars/2026/09/avatar.png")

            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"png-bytes"


@pytest.mark.django_db
def test_tos_redirect_still_applies_off_the_media_prefix():
    """The exemption is scoped to /media/ — it must not disarm the middleware."""
    user = User.objects.create_user(email="also-no-tos@example.com", password="testpass123")
    client = Client()
    client.force_login(user)

    response = client.get("/")

    assert response.status_code == 302
    assert response["Location"] == "/accounts/accept-terms/"

    user.tos_accepted_at = timezone.now()
    user.save(update_fields=["tos_accepted_at"])

    # The dashboard forwards to the user's workspace, so assert on where it
    # does *not* send them rather than on a bare 200.
    assert client.get("/").get("Location", "") != "/accounts/accept-terms/"
