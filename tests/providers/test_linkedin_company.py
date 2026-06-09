"""Tests for LinkedInCompanyProvider.get_user_pages."""

from unittest.mock import MagicMock, patch

from providers.linkedin_company import LinkedInCompanyProvider


def _make_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


class TestGetUserPages:
    @patch.object(LinkedInCompanyProvider, "_request")
    def test_resolves_logo_url_from_projection(self, mock_request):
        # `organizationalEntityAcls` with the projection used in the provider
        # returns the org URN under `organizationalTarget`, the expanded org
        # under `organizationalTarget~`, and logo media URLs under
        # `logoV2.original~.elements[0].identifiers[0].identifier`.
        mock_request.return_value = _make_response(
            {
                "elements": [
                    {
                        "organizationalTarget": "urn:li:organization:98765",
                        "organizationalTarget~": {
                            "id": 98765,
                            "localizedName": "Acme Robotics",
                            "vanityName": "acme-robotics",
                            "logoV2": {
                                "original~": {
                                    "elements": [
                                        {
                                            "identifiers": [
                                                {
                                                    "identifier": "https://media.licdn.com/dms/image/C4E03AQFM2Cu_RPHz4A/company-logo_200_200/0/example.png",
                                                }
                                            ],
                                        }
                                    ],
                                }
                            },
                        },
                    }
                ]
            }
        )

        provider = LinkedInCompanyProvider()
        pages = provider.get_user_pages("token-xyz")

        assert pages == [
            {
                "id": "98765",
                "name": "Acme Robotics",
                "handle": "acme-robotics",
                "access_token": "token-xyz",
                "picture": "https://media.licdn.com/dms/image/C4E03AQFM2Cu_RPHz4A/company-logo_200_200/0/example.png",
            }
        ]
        # Verify the projection-bearing URL is what we requested.
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert "/v2/organizationalEntityAcls" in args[1]
        assert "role=ADMINISTRATOR" in args[1]
        assert "logoV2(original~:playableStreams)" in args[1]

    @patch.object(LinkedInCompanyProvider, "_request")
    def test_picture_is_none_when_logo_missing(self, mock_request):
        # Org with no logoV2 set at all (newly created page without a logo).
        mock_request.return_value = _make_response(
            {
                "elements": [
                    {
                        "organizationalTarget": "urn:li:organization:11111",
                        "organizationalTarget~": {
                            "id": 11111,
                            "localizedName": "No Logo Co",
                            "vanityName": "no-logo",
                        },
                    }
                ]
            }
        )

        provider = LinkedInCompanyProvider()
        pages = provider.get_user_pages("token")

        assert len(pages) == 1
        assert pages[0]["picture"] is None
        assert pages[0]["id"] == "11111"
        assert pages[0]["name"] == "No Logo Co"

    @patch.object(LinkedInCompanyProvider, "_request")
    def test_picture_is_none_when_logo_elements_empty(self, mock_request):
        # logoV2 present but elements list is empty.
        mock_request.return_value = _make_response(
            {
                "elements": [
                    {
                        "organizationalTarget": "urn:li:organization:22222",
                        "organizationalTarget~": {
                            "id": 22222,
                            "localizedName": "Empty Elements Co",
                            "vanityName": "empty-elements",
                            "logoV2": {"original~": {"elements": []}},
                        },
                    }
                ]
            }
        )

        provider = LinkedInCompanyProvider()
        pages = provider.get_user_pages("token")

        assert pages[0]["picture"] is None

    @patch.object(LinkedInCompanyProvider, "_request")
    def test_returns_empty_list_when_no_orgs(self, mock_request):
        # User administers no organizations.
        mock_request.return_value = _make_response({"elements": []})

        provider = LinkedInCompanyProvider()
        pages = provider.get_user_pages("token")

        assert pages == []

    @patch.object(LinkedInCompanyProvider, "_request")
    def test_id_falls_back_to_expanded_when_urn_missing(self, mock_request):
        # Defensive: if `organizationalTarget` URN is missing but the expanded
        # block carries an `id`, fall back to that.
        mock_request.return_value = _make_response(
            {
                "elements": [
                    {
                        "organizationalTarget~": {
                            "id": 33333,
                            "localizedName": "Fallback Co",
                            "vanityName": "fallback",
                        },
                    }
                ]
            }
        )

        provider = LinkedInCompanyProvider()
        pages = provider.get_user_pages("token")

        assert pages[0]["id"] == "33333"
