from unittest.mock import MagicMock

from providers.instagram import InstagramProvider


def test_get_user_pages_returns_linked_instagram_business_accounts():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Facebook Page",
                            "access_token": "page-token",
                            "category": "Creator",
                            "picture": {"data": {"url": "https://example.com/page.jpg"}},
                            "instagram_business_account": {
                                "id": "17841400000000000",
                                "username": "brightbean",
                                "name": "Brightbean",
                                "profile_picture_url": "https://example.com/ig.jpg",
                                "followers_count": 42,
                            },
                        },
                        {
                            "id": "page-2",
                            "name": "No Instagram Here",
                            "access_token": "unused-token",
                        },
                    ]
                }
            )
        )
    )

    accounts = provider.get_user_pages("user-token")

    assert accounts == [
        {
            "id": "17841400000000000",
            "name": "Brightbean",
            "handle": "brightbean",
            "access_token": "page-token",
            "category": "Creator",
            "picture": "https://example.com/ig.jpg",
            "followers_count": 42,
            "page_id": "page-1",
            "page_name": "Facebook Page",
        }
    ]
    provider._request.assert_called_once_with(
        "GET",
        "https://graph.facebook.com/v21.0/me/accounts",
        access_token="user-token",
        params={
            "fields": (
                "id,name,access_token,category,picture,"
                "instagram_business_account{id,username,name,profile_picture_url,followers_count}"
            ),
        },
    )


def test_get_user_pages_omits_blank_page_access_token():
    provider = InstagramProvider({"client_id": "id", "client_secret": "secret"})
    provider._request = MagicMock(
        return_value=MagicMock(
            json=MagicMock(
                return_value={
                    "data": [
                        {
                            "id": "page-1",
                            "name": "Facebook Page",
                            "access_token": "",
                            "instagram_business_account": {
                                "id": "17841400000000000",
                                "username": "brightbean",
                                "name": "Brightbean",
                            },
                        },
                    ]
                }
            )
        )
    )

    accounts = provider.get_user_pages("user-token")

    assert len(accounts) == 1
    assert "access_token" not in accounts[0]
