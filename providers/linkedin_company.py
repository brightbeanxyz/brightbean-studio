"""LinkedIn provider variant for Company Page posting.

Lists organizations the authenticated member administers, lets the user
pick one, and publishes to that Company Page via the organization URN.
"""

from __future__ import annotations

import logging

from .exceptions import APIError
from .linkedin import API_BASE, LINKEDIN_HEADERS, LinkedInProvider, _encode_urn

logger = logging.getLogger(__name__)


class LinkedInCompanyProvider(LinkedInProvider):
    """LinkedIn provider scoped to Company Page posting."""

    @property
    def platform_name(self) -> str:
        return "LinkedIn (Company Page)"

    @property
    def required_scopes(self) -> list[str]:
        return [
            "r_basicprofile",
            "w_member_social",
            "w_organization_social",
            "r_organization_social",
            "rw_organization_admin",
        ]

    def _inbox_author_urn(self, access_token: str) -> str | None:
        # A Company Page's posts are authored by the organization. Asking for
        # the member's posts with a Page token fails with HTTP 400.
        org_id = self.credentials.get("organization_id")
        return f"urn:li:organization:{org_id}" if org_id else None

    # Set once the versioned comments endpoint answered 403 for this app.
    _legacy_comments = False

    def _inbox_comments_page(self, access_token: str, post_urn: str, start: int):
        # The versioned /rest comments endpoint answers 403 for apps that lack the
        # partner social-actions product. The /v2 endpoint returns the same data,
        # so fall back to it and stay on it for the rest of this poll.
        if not self._legacy_comments:
            try:
                return super()._inbox_comments_page(access_token, post_urn, start)
            except APIError as exc:
                if exc.status_code != 403:
                    raise
                self._legacy_comments = True
        return self._request(
            "GET",
            f"{API_BASE}/v2/socialActions/{_encode_urn(post_urn)}/comments",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
            params={"start": start, "count": 100},
        )

    def _inbox_own_actors(self, access_token: str, author: str) -> set[str]:
        # The Page itself and the admin who posts first comments through us.
        actors = {author}
        profile = self.get_profile(access_token)
        if profile.platform_id:
            actors.add(f"urn:li:person:{profile.platform_id}")
        return actors

    def get_user_pages(self, access_token: str) -> list[dict]:
        resp = self._request(
            "GET",
            f"{API_BASE}/v2/organizationalEntityAcls"
            "?q=roleAssignee&role=ADMINISTRATOR"
            "&projection=(elements*(organizationalTarget~(id,localizedName,vanityName,logoV2(original~:playableStreams))))",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
        )
        data = resp.json()
        pages: list[dict] = []
        for element in data.get("elements", []):
            org = element.get("organizationalTarget~", {})
            org_urn = element.get("organizationalTarget", "")
            org_id = org_urn.split(":")[-1] if org_urn else org.get("id", "")
            logo_url = None
            logo = org.get("logoV2", {}).get("original~", {})
            elements = logo.get("elements", [])
            if elements:
                identifiers = elements[0].get("identifiers", [])
                if identifiers:
                    logo_url = identifiers[0].get("identifier")
            pages.append(
                {
                    "id": str(org_id),
                    "name": org.get("localizedName", ""),
                    "handle": org.get("vanityName", ""),
                    "access_token": access_token,
                    "picture": logo_url,
                }
            )
        return pages
