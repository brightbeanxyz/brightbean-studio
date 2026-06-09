"""Tests for platform credential resolution, derivation, the admin form, and the
removal of the dormant /credentials/ placeholder."""

import pytest
from django.test import override_settings
from django.urls import NoReverseMatch, Resolver404, resolve, reverse

from apps.credentials.forms import PlatformCredentialAdminForm
from apps.credentials.models import (
    PlatformCredential,
    derive_is_configured,
    resolve_app_secret,
    resolve_app_secrets,
    resolve_platform_credentials,
)

# ---------------------------------------------------------------------------
# derive_is_configured (pure function — no DB)
# ---------------------------------------------------------------------------


def test_derive_tiktok_requires_client_key():
    assert derive_is_configured("tiktok", {"client_key": "k", "client_secret": "s"}) is True
    # TikTok uses client_key, not client_id — client_id must NOT count.
    assert derive_is_configured("tiktok", {"client_id": "k", "client_secret": "s"}) is False


def test_derive_meta_accepts_app_id_aliases():
    assert derive_is_configured("facebook", {"app_id": "a", "app_secret": "b"}) is True
    assert derive_is_configured("facebook", {"client_id": "a", "client_secret": "b"}) is True


def test_derive_false_for_partial_or_empty():
    assert derive_is_configured("facebook", {"app_id": "a"}) is False
    assert derive_is_configured("youtube", {}) is False
    assert derive_is_configured("youtube", {"client_id": "", "client_secret": "  "}) is False
    # None values must not read as truthy ("None" string bug guard).
    assert derive_is_configured("youtube", {"client_id": None, "client_secret": None}) is False


def test_derive_false_for_credential_less_platforms():
    assert derive_is_configured("bluesky", {"anything": "x"}) is False
    assert derive_is_configured("mastodon", {"client_id": "x", "client_secret": "y"}) is False


# ---------------------------------------------------------------------------
# PlatformCredential.save() derives is_configured
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_sets_is_configured_from_credentials(organization):
    cred = PlatformCredential.objects.create(
        organization=organization,
        platform="youtube",
        credentials={"client_id": "cid", "client_secret": "csec"},
    )
    cred.refresh_from_db()
    assert cred.is_configured is True


@pytest.mark.django_db
def test_save_leaves_incomplete_row_inactive(organization):
    cred = PlatformCredential.objects.create(
        organization=organization,
        platform="youtube",
        credentials={"client_id": "cid"},  # no secret
        is_configured=True,  # should be overridden by save()
    )
    cred.refresh_from_db()
    assert cred.is_configured is False


# ---------------------------------------------------------------------------
# resolve_platform_credentials — .env dominant, DB fallback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_id": "ENV_ID", "app_secret": "ENV_SECRET"}})
def test_resolve_env_wins_over_db(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "DB_ID", "client_secret": "DB_SECRET"},
    )
    result = resolve_platform_credentials("facebook", organization.id)
    assert result == {"app_id": "ENV_ID", "app_secret": "ENV_SECRET"}


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
def test_resolve_falls_back_to_db_when_env_empty(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "DB_ID", "client_secret": "DB_SECRET"},
    )
    result = resolve_platform_credentials("facebook", organization.id)
    assert result == {"client_id": "DB_ID", "client_secret": "DB_SECRET"}


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
def test_resolve_returns_empty_when_nothing_configured(organization):
    assert resolve_platform_credentials("facebook", organization.id) == {}


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
def test_resolve_skips_incomplete_db_row(organization):
    # Incomplete row -> is_configured False -> resolver must not pick it up.
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "DB_ID"},
    )
    assert resolve_platform_credentials("facebook", organization.id) == {}


# ---------------------------------------------------------------------------
# resolve_app_secrets — union of env + admin secrets (for webhook verification)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_secret": "ENV_SEC"}})
def test_resolve_app_secrets_unions_env_and_db(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "x", "client_secret": "DB_SEC"},
    )
    secrets = resolve_app_secrets("facebook")
    assert secrets == ["ENV_SEC", "DB_SEC"]  # env first, then DB


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
def test_resolve_app_secrets_db_only(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="instagram_login",
        credentials={"app_id": "x", "app_secret": "ONLY_DB"},
    )
    assert resolve_app_secrets("instagram_login") == ["ONLY_DB"]


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
def test_resolve_app_secrets_dedupes_and_spans_platforms(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "x", "client_secret": "SHARED"},
    )
    PlatformCredential.objects.create(
        organization=organization,
        platform="instagram",
        credentials={"client_id": "y", "client_secret": "SHARED"},
    )
    # facebook + instagram share one Meta app; identical secret deduped to one.
    assert resolve_app_secrets("facebook", "instagram") == ["SHARED"]


# ---------------------------------------------------------------------------
# PlatformCredentialAdminForm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_form_round_trip_persists_dict_and_activates(organization):
    form = PlatformCredentialAdminForm(
        data={
            "organization": str(organization.pk),
            "platform": "youtube",
            "credentials": '{"client_id": "cid", "client_secret": "csec"}',
        }
    )
    assert form.is_valid(), form.errors
    obj = form.save()
    obj.refresh_from_db()
    # Stored as a real, decryptable dict (not a Python-repr string), and active.
    assert obj.credentials == {"client_id": "cid", "client_secret": "csec"}
    assert obj.is_configured is True


@pytest.mark.django_db
def test_admin_form_rejects_missing_required_keys(organization):
    form = PlatformCredentialAdminForm(
        data={
            "organization": str(organization.pk),
            "platform": "youtube",
            "credentials": '{"client_id": "cid"}',  # missing client_secret
        }
    )
    assert not form.is_valid()
    assert "credentials" in form.errors


@pytest.mark.django_db
def test_admin_form_rejects_non_object_json(organization):
    form = PlatformCredentialAdminForm(
        data={
            "organization": str(organization.pk),
            "platform": "youtube",
            "credentials": '"just a string"',
        }
    )
    assert not form.is_valid()
    assert "credentials" in form.errors


def test_admin_form_excludes_credential_less_platforms():
    choice_values = [value for value, _label in PlatformCredentialAdminForm().fields["platform"].choices]
    assert "youtube" in choice_values
    assert "bluesky" not in choice_values
    assert "mastodon" not in choice_values


# ---------------------------------------------------------------------------
# Dormant /credentials/ placeholder removed
# ---------------------------------------------------------------------------


def test_credentials_placeholder_url_removed():
    with pytest.raises(Resolver404):
        resolve("/credentials/")


def test_credentials_namespace_reverse_removed():
    with pytest.raises(NoReverseMatch):
        reverse("credentials:list")


# ---------------------------------------------------------------------------
# Django admin integration — editable credentials field, superuser-only gating
# ---------------------------------------------------------------------------

ADD_URL = "/admin/credentials/platformcredential/add/"


@pytest.mark.django_db
def test_admin_add_page_renders_editable_credentials_for_superuser(client):
    from django.utils import timezone

    from apps.accounts.models import User

    admin_user = User.objects.create_superuser(
        email="su@example.com", password="x", name="Super", tos_accepted_at=timezone.now()
    )
    client.force_login(admin_user)
    resp = client.get(ADD_URL)
    assert resp.status_code == 200
    # An editable form field (not the old read-only display) is rendered.
    assert b'name="credentials"' in resp.content


@pytest.mark.django_db
def test_admin_blocked_for_non_superuser_staff(client):
    from django.utils import timezone

    from apps.accounts.models import User

    staff = User.objects.create_user(
        email="staff@example.com", password="x", name="Staff", tos_accepted_at=timezone.now(), is_staff=True
    )
    client.force_login(staff)
    resp = client.get(ADD_URL)
    assert resp.status_code in (302, 403)


# ---------------------------------------------------------------------------
# Hardening: incomplete .env must not shadow a complete admin row
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_id": "ENV_ID"}})  # no secret -> incomplete
def test_resolve_incomplete_env_does_not_shadow_db(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "DB_ID", "client_secret": "DB_SECRET"},
    )
    # Partial env (missing secret) must fall back to the complete DB row.
    result = resolve_platform_credentials("facebook", organization.id)
    assert result == {"client_id": "DB_ID", "client_secret": "DB_SECRET"}


# ---------------------------------------------------------------------------
# resolve_app_secret — single per-org secret (.env dominant)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
def test_resolve_app_secret_returns_org_secret(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "x", "client_secret": "ORG_SEC"},
    )
    assert resolve_app_secret("facebook", organization.id) == "ORG_SEC"


@pytest.mark.django_db
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV={"facebook": {"app_id": "i", "app_secret": "ENV_SEC"}})
def test_resolve_app_secret_env_dominant(organization):
    PlatformCredential.objects.create(
        organization=organization,
        platform="facebook",
        credentials={"client_id": "x", "client_secret": "ORG_SEC"},
    )
    assert resolve_app_secret("facebook", organization.id) == "ENV_SEC"


# ---------------------------------------------------------------------------
# save(update_fields=...) still persists the derived is_configured flag
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_save_update_fields_persists_derived_flag(organization):
    cred = PlatformCredential.objects.create(
        organization=organization,
        platform="youtube",
        credentials={"client_id": "cid"},  # incomplete -> inactive
    )
    cred.refresh_from_db()
    assert cred.is_configured is False

    cred.credentials = {"client_id": "cid", "client_secret": "csec"}
    cred.save(update_fields=["credentials"])  # omits is_configured on purpose
    cred.refresh_from_db()
    assert cred.is_configured is True


# ---------------------------------------------------------------------------
# Backwards compatibility: existing .env-configured deployments keep working.
# Mirrors the real key shapes built in config/settings/base.py
# (PLATFORM_CREDENTIALS_FROM_ENV) so every platform's env config still resolves.
# ---------------------------------------------------------------------------

REALISTIC_ENV = {
    "facebook": {"app_id": "fb-id", "app_secret": "fb-sec"},
    "instagram": {"app_id": "fb-id", "app_secret": "fb-sec"},
    "threads": {"app_id": "fb-id", "app_secret": "fb-sec"},
    "instagram_login": {"app_id": "ig-id", "app_secret": "ig-sec"},
    "linkedin_personal": {"client_id": "li-id", "client_secret": "li-sec", "_oauth_mode": "oidc"},
    "linkedin_company": {"client_id": "lic-id", "client_secret": "lic-sec"},
    "tiktok": {"client_key": "tt-key", "client_secret": "tt-sec"},
    "youtube": {"client_id": "g-id", "client_secret": "g-sec"},
    "google_business": {"client_id": "g-id", "client_secret": "g-sec"},
    "pinterest": {"app_id": "pin-id", "app_secret": "pin-sec"},
}


@pytest.mark.django_db
@pytest.mark.parametrize("platform", list(REALISTIC_ENV))
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV=REALISTIC_ENV)
def test_existing_env_only_deployment_resolves_every_platform(platform, organization):
    # The existing-deployment reality: env set, no DB rows. Env creds resolve as-is.
    assert resolve_platform_credentials(platform, organization.id) == REALISTIC_ENV[platform]


@pytest.mark.django_db
@pytest.mark.parametrize("platform", list(REALISTIC_ENV))
@override_settings(PLATFORM_CREDENTIALS_FROM_ENV=REALISTIC_ENV)
def test_env_dominates_db_for_every_platform(platform, organization):
    # Even with a complete admin row present, a complete env config wins.
    PlatformCredential.objects.create(
        organization=organization,
        platform=platform,
        credentials={"client_id": "DB", "client_secret": "DB", "client_key": "DB"},
    )
    assert resolve_platform_credentials(platform, organization.id) == REALISTIC_ENV[platform]
