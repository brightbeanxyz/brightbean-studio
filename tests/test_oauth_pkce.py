"""Tests for client-side PKCE helpers (apps/social_accounts/oauth_pkce.py)."""

from types import SimpleNamespace

from apps.social_accounts.oauth_pkce import issue_pkce_verifier, pkce_kwargs


class TestIssuePkceVerifier:
    def test_returns_verifier_for_pkce_provider(self):
        verifier = issue_pkce_verifier(SimpleNamespace(uses_pkce=True))
        assert isinstance(verifier, str)
        # RFC 7636 allows 43-128 chars; token_urlsafe(64) yields ~86.
        assert 43 <= len(verifier) <= 128

    def test_returns_none_for_non_pkce_provider(self):
        assert issue_pkce_verifier(SimpleNamespace(uses_pkce=False)) is None

    def test_fresh_verifier_each_call(self):
        provider = SimpleNamespace(uses_pkce=True)
        assert issue_pkce_verifier(provider) != issue_pkce_verifier(provider)


class TestPkceKwargs:
    def test_includes_verifier_when_present(self):
        assert pkce_kwargs("abc") == {"code_verifier": "abc"}

    def test_empty_when_none(self):
        # Non-PKCE providers are invoked with exactly their original arg list.
        assert pkce_kwargs(None) == {}

    def test_empty_when_empty_string(self):
        assert pkce_kwargs("") == {}
