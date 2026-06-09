"""OAuth discovery metadata for the BrightBean Studio MCP Authorization Server.

An MCP client (e.g. Claude Desktop) discovers the OAuth endpoints by fetching:
  - RFC 8414 authorization-server metadata -> /.well-known/oauth-authorization-server
  - RFC 9728 protected-resource metadata   -> /.well-known/oauth-protected-resource

Studio serves the app, the API (where /api/v1/mcp lives), and the OAuth
Authorization Server (where users log in) on ONE host, so MCP_PUBLIC_BASE_URL
and MCP_OAUTH_ISSUER_URL are normally the same origin — but they are kept
separate so a split deployment can override either independently.
"""

from __future__ import annotations

from django.conf import settings


def authorization_server_metadata() -> dict:
    """RFC 8414 authorization-server metadata document."""
    issuer = settings.MCP_OAUTH_ISSUER_URL
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize/",
        "token_endpoint": f"{issuer}/oauth/token/",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke_token/",
        "scopes_supported": ["mcp"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "service_documentation": f"{settings.MCP_PUBLIC_BASE_URL}/api/v1/docs",
    }


def protected_resource_metadata() -> dict:
    """RFC 9728 protected-resource metadata for the /api/v1/mcp endpoint."""
    return {
        "resource": f"{settings.MCP_PUBLIC_BASE_URL}/api/v1/mcp",
        "authorization_servers": [settings.MCP_OAUTH_ISSUER_URL],
        "scopes_supported": ["mcp"],
        "resource_name": "BrightBean Studio MCP",
        "resource_documentation": f"{settings.MCP_PUBLIC_BASE_URL}/api/v1/docs",
    }
