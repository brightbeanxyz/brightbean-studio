"""Run the BrightBean MCP server.

  python manage.py mcp_serve --stdio                  # for local AI clients
  python manage.py mcp_serve --http --port 8765       # for network clients (phase 2)

The API token is read from $BRIGHTBEAN_API_TOKEN.
"""

import os
import sys

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run the BrightBean MCP server (stdio or HTTP)."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=False)
        mode.add_argument("--stdio", action="store_true", help="Speak MCP over stdio (default).")
        mode.add_argument("--http", action="store_true", help="Speak MCP over HTTP/SSE.")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=8765)
        parser.add_argument(
            "--token-env",
            default="BRIGHTBEAN_API_TOKEN",
            help="Name of the env var holding the API token (stdio mode only).",
        )

    def handle(self, *args, **options):
        try:
            from apps.mcp_server.context import AuthContext, MCPAuthError
            from apps.mcp_server.server import build_server
        except ImportError as exc:
            raise CommandError(f"Failed to import MCP server: {exc}") from exc

        if options["http"]:
            raise CommandError("HTTP transport is not implemented yet (Phase 2). Use --stdio for now.")

        # Default to stdio.
        raw_token = os.environ.get(options["token_env"], "").strip()
        if not raw_token:
            raise CommandError(f"${options['token_env']} is not set. Mint a token at /accounts/api-tokens/.")

        try:
            ctx = AuthContext.from_token(raw_token)
        except MCPAuthError as exc:
            raise CommandError(str(exc)) from exc

        self.stderr.write(
            f"BrightBean MCP server starting for {ctx.user.email}"
            + (
                f" (scoped to workspace {ctx.api_token.scoped_workspace.name})"
                if ctx.is_workspace_scoped and ctx.api_token.scoped_workspace
                else ""
            )
        )

        try:
            server = build_server(ctx)
        except ImportError as exc:
            raise CommandError(
                "The `mcp` package is not installed. Install with: pip install 'mcp>=1.2,<2.0'\n"
                f"Underlying error: {exc}"
            ) from exc

        # FastMCP.run() handles the stdio loop and blocks until EOF.
        try:
            server.run()
        except KeyboardInterrupt:
            sys.exit(0)
