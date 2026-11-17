"""LinkedIn provider variant for Company Page posting.

Lists organizations the authenticated member administers, lets the user
pick one, and publishes to that Company Page via the organization URN.
"""

from __future__ import annotations

import logging

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
            # Commenting as the page: without it LinkedIn answers
            # 403 partnerApiSocialActions.CREATE on the first comment.
            "w_organization_social_feed",
        ]

    def _comment_actor(self, access_token: str, post_id: str) -> str:
        """Comment as the page that authored the post, not as the admin who connected it.

        ``publish_comment`` gets no account, so the post's own author is the
        reliable source for the organization URN (one GET, covered by
        r_organization_social).
        """
        resp = self._request(
            "GET",
            f"{API_BASE}/rest/posts/{_encode_urn(post_id)}",
            access_token=access_token,
            headers=LINKEDIN_HEADERS,
        )
        author = resp.json().get("author", "")
        if author.startswith("urn:li:organization:"):
            return author
        return super()._comment_actor(access_token, post_id)

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
