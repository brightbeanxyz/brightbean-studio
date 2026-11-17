from urllib.parse import parse_qs, urlparse

import pytest

from providers.google_business import GoogleBusinessProvider
from providers.youtube import YouTubeProvider


@pytest.mark.parametrize("provider_cls", [YouTubeProvider, GoogleBusinessProvider])
def test_auth_url_shows_account_chooser_and_consent(provider_cls):
    """Without select_account Google reuses the signed-in identity, so a Brand Account can never be chosen."""
    url = provider_cls({"client_id": "cid", "client_secret": "s"}).get_auth_url("https://x/cb/", "st")
    prompts = parse_qs(urlparse(url).query)["prompt"][0].split(" ")
    assert set(prompts) == {"consent", "select_account"}
