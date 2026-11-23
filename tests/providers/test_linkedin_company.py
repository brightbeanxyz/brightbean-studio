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


class TestInbox:
    @patch.object(LinkedInCompanyProvider, "get_profile")
    @patch.object(LinkedInCompanyProvider, "_request")
    def test_get_messages_lists_the_organization_posts(self, mock_request, mock_profile):
        # An organization token asking for a person's posts gets a 400 from
        # LinkedIn, so the page must list its own posts.
        post_urn = "urn:li:share:111"
        mock_request.side_effect = [
            _make_response({"elements": [{"id": post_urn}]}),
            _make_response(
                {
                    "elements": [
                        {
                            "$URN": "urn:li:comment:(urn:li:activity:1,222)",
                            "actor": "urn:li:person:abc",
                            "created": {"time": 1_700_000_000_000},
                            "message": {"text": "Grazie!"},
                        }
                    ]
                }
            ),
        ]

        messages = LinkedInCompanyProvider().get_messages("token", organization_id="98765")

        assert mock_request.call_args_list[0].kwargs["params"]["author"] == "urn:li:organization:98765"
        mock_profile.assert_not_called()
        assert messages[0].extra["author_urn"] == "urn:li:organization:98765"

    @patch.object(LinkedInCompanyProvider, "get_profile")
    @patch.object(LinkedInCompanyProvider, "_request")
    def test_reply_is_sent_as_the_post_author(self, mock_request, mock_profile):
        resp = _make_response({})
        resp.headers = {"x-restli-id": "urn:li:comment:(urn:li:activity:1,333)"}
        mock_request.return_value = resp

        LinkedInCompanyProvider().reply_to_comment(
            "token",
            "urn:li:comment:(urn:li:activity:1,222)",
            "Grazie a te",
            extra={"post_urn": "urn:li:share:111", "author_urn": "urn:li:organization:98765"},
        )

        assert mock_request.call_args.kwargs["json"]["actor"] == "urn:li:organization:98765"
        mock_profile.assert_not_called()
