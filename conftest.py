import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.media_library.storage import reset_cached_client
from apps.members.models import OrgMembership
from apps.organizations.models import Organization


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com", password="testpass123", name="Test User", tos_accepted_at=timezone.now()
    )


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Test Organization")


@pytest.fixture
def org_owner(db, user, organization):
    OrgMembership.objects.create(user=user, organization=organization, org_role=OrgMembership.OrgRole.OWNER)
    return user


@pytest.fixture(autouse=True)
def _fresh_storage_client():
    """Keep the memoized boto3 client from leaking across tests.

    ``apps.media_library.storage`` caches one client for the life of the
    process — the point is to stop django-storages rebuilding a boto3 Session
    per thread. Without this, the first test to touch S3 would pin its client
    and every later ``override_settings`` on a bucket or endpoint would be
    silently ignored.
    """
    reset_cached_client()
    yield
    reset_cached_client()
