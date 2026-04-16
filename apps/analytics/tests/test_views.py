from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.analytics.models import PostSnapshot, RefreshLog


@pytest.mark.django_db
class TestBrandListView:
    def test_authenticated_user_sees_workspaces(self, client, org_member, workspace):
        client.force_login(org_member)
        response = client.get(reverse("analytics:brand_list"))
        assert response.status_code == 200
        assert workspace.name.encode() in response.content

    def test_unauthenticated_redirects(self, client):
        response = client.get(reverse("analytics:brand_list"))
        assert response.status_code == 302


@pytest.mark.django_db
class TestBrandDashboardView:
    def test_shows_dashboard(self, client, org_member, workspace):
        client.force_login(org_member)
        response = client.get(
            reverse("analytics:brand_dashboard", kwargs={"workspace_id": workspace.id})
        )
        assert response.status_code == 200

    def test_wrong_org_returns_404(self, client, org_member, other_workspace):
        """Users cannot see workspaces from other organizations."""
        client.force_login(org_member)
        response = client.get(
            reverse("analytics:brand_dashboard", kwargs={"workspace_id": other_workspace.id})
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestRefreshView:
    @patch("apps.analytics.views.refresh_metrics")
    def test_refresh_returns_htmx_partial(self, mock_refresh, client, org_member, workspace):
        mock_refresh.return_value = []
        client.force_login(org_member)
        response = client.post(
            reverse("analytics:refresh_metrics", kwargs={"workspace_id": workspace.id}),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        mock_refresh.assert_called_once()

    def test_refresh_rejects_get(self, client, org_member, workspace):
        client.force_login(org_member)
        response = client.get(
            reverse("analytics:refresh_metrics", kwargs={"workspace_id": workspace.id})
        )
        assert response.status_code == 405
