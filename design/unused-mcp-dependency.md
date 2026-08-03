# The `mcp` SDK dependency is unused

`requirements.txt` pins `mcp>=1.0,<2.0` and describes it as backing the `/api/v1/mcp` transport. `apps/mcp/transport.py` states the opposite in its module docstring: the JSON-RPC core was hand-rolled *because* the SDK assumes an ASGI/Starlette stack while this project is WSGI Django.

A tree-wide scan during migration found zero imports of `mcp`. It pulls roughly fifteen transitive packages (starlette, uvicorn, sse-starlette, pydantic-settings, jsonschema, python-multipart, ...).

Decision: left in place. Removing it is correct but belongs to a dependency-hygiene change, not a framework migration - keeping the two separate keeps this migration's blast radius reviewable.
