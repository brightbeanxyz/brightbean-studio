"""ACCOUNT_ALLOW_SIGNUP closes public registration on single-operator deployments."""

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.django_db
@override_settings(ACCOUNT_ALLOW_SIGNUP=False)
def test_signup_closed_rejects_new_accounts(client):
    response = client.post(reverse("account_signup"), {"email": "stranger@example.com", "password1": "a-Long-pass-123!"})
    assert not User.objects.filter(email="stranger@example.com").exists()
    assert response.status_code in (200, 302)


@pytest.mark.django_db
@override_settings(ACCOUNT_ALLOW_SIGNUP=False)
def test_existing_user_can_still_log_in(client):
    User.objects.create_user(email="owner@example.com", password="a-Long-pass-123!")
    client.post(reverse("account_login"), {"login": "owner@example.com", "password": "a-Long-pass-123!"})
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_signup_open_by_default(client):
    client.post(reverse("account_signup"), {"email": "new@example.com", "password1": "a-Long-pass-123!"})
    assert User.objects.filter(email="new@example.com").exists()
