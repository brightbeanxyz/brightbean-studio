"""LinkedIn inbox polling reads Company Page posts and their comments."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from providers.exceptions import APIError
from providers.linkedin_company import LinkedInCompanyProvider
from providers.linkedin_personal import LinkedInPersonalProvider
from providers.types import AccountProfile

ORG = "urn:li:organization:123"
ADMIN = "urn:li:person:admin"
POST = "urn:li:share:555"


def _comment(actor, text, when=1_790_000_000_000):
    return {
        "$URN": f"urn:li:comment:({POST},{text})",
        "actor": actor,
        "message": {"text": text},
        "created": {"time": when},
    }


def _company(comments, rest_comments_forbidden=False):
    provider = LinkedInCompanyProvider({"client_id": "id", "client_secret": "secret", "organization_id": "123"})
    provider.get_profile = MagicMock(return_value=AccountProfile(platform_id="admin", name="Admin", avatar_url=None))
    calls = []

    def request(method, url, **kwargs):
        calls.append((url, kwargs.get("params")))
        if rest_comments_forbidden and "/rest/socialActions/" in url:
            raise APIError("forbidden", status_code=403)
        data = {"elements": [{"id": POST}]} if url.endswith("/rest/posts") else {"elements": comments}
        return SimpleNamespace(json=lambda: data)

    provider._request = MagicMock(side_effect=request)
    return provider, calls


def test_company_reads_posts_authored_by_the_organization():
    provider, calls = _company([])
    provider.get_messages("token")

    assert calls[0][1]["author"] == ORG


def test_company_reads_comments_from_the_versioned_endpoint_first():
    provider, calls = _company([])
    provider.get_messages("token")

    assert "/rest/socialActions/" in calls[1][0]


def test_company_falls_back_to_v2_when_the_versioned_endpoint_is_forbidden():
    """Apps without the partner social-actions product get 403 on /rest comments."""
    provider, calls = _company([_comment("urn:li:person:customer", "Great post")], rest_comments_forbidden=True)
    messages = provider.get_messages("token")

    assert [m.text for m in messages] == ["Great post"]
    assert "/rest/socialActions/" in calls[1][0]
    assert "/v2/socialActions/" in calls[2][0]


def test_company_skips_comments_written_by_the_page_or_its_admin():
    provider, _ = _company(
        [
            _comment(ORG, "our own reply"),
            _comment(ADMIN, "first comment we posted"),
            _comment("urn:li:person:customer", "Great post"),
        ]
    )
    messages = provider.get_messages("token")

    assert [m.text for m in messages] == ["Great post"]
    assert messages[0].message_type == "comment"


def test_company_without_an_organization_id_reads_nothing():
    provider = LinkedInCompanyProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock()

    assert provider.get_messages("token") == []
    provider._request.assert_not_called()


def test_personal_oidc_account_still_reads_nothing():
    provider = LinkedInPersonalProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock()

    assert provider.get_messages("token") == []
    provider._request.assert_not_called()
