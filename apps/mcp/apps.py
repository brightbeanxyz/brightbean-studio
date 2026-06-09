from django.apps import AppConfig


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mcp"
    # ``mcp`` is also the name of a popular PyPI package; pick a unique
    # label so Django's app registry can't collide with one in the future.
    label = "mcp_server"
    verbose_name = "Model Context Protocol Server"

    def ready(self):
        # Force registration of all tools at app boot so `tools/list`
        # returns a complete catalog regardless of which router is hit
        # first. Import-side-effects only.
        from apps.mcp import handlers  # noqa: F401
