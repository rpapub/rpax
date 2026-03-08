"""Shared CLI decorators: api_expose and maturity command factories."""
from __future__ import annotations


def api_expose(
    path: str | None = None,
    methods: list[str] | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
    enabled: bool = True,
    mcp_resource_type: str | None = None,
):
    """Blueprint decorator for Layer 3/4 generation.

    Stores metadata for OpenAPI/MCP generation - never called at runtime.

    Args:
        path: API endpoint path (default: auto-generate from command name)
        methods: HTTP methods (default: ["GET"])
        summary: OpenAPI summary (default: use docstring)
        tags: OpenAPI tags for grouping
        enabled: Whether to expose this command (default: True)
        mcp_resource_type: Optional hint for MCP resource generation
    """

    def decorator(func):
        # Auto-generate path from function name if not provided
        default_path = f"/{func.__name__.replace('_command', '').replace('_', '-')}"

        func._rpax_api = {
            "enabled": enabled,
            "path": path or default_path,
            "methods": methods or ["GET"],
            "summary": summary
            or (
                func.__doc__.split("\n")[0]
                if func.__doc__
                else f"{func.__name__} operation"
            ),
            "tags": tags or [],
            "mcp_hints": (
                {"resource_type": mcp_resource_type} if mcp_resource_type else {}
            ),
        }
        return func

    return decorator


def make_command_factories(app):
    """Create maturity-tagged command decorator factories bound to a Typer app.

    Returns a tuple: (command, experimental, plumbing, beta)
    Each is a decorator factory that wraps app.command() and tags the function
    with _rpax_maturity.

    Usage:
        command, experimental, plumbing, beta = make_command_factories(uipath_app)

        @command("bump")
        def bump_cmd(...): ...

        @experimental()
        def parse(...): ...
    """

    def _factory(level: str, panel: str | None = None, hidden: bool = False):
        def factory(*args, **kwargs):
            if panel:
                kwargs.setdefault("rich_help_panel", panel)
            if hidden:
                kwargs.setdefault("hidden", True)
            typer_deco = app.command(*args, **kwargs)

            def wrapper(func):
                func._rpax_maturity = level
                return typer_deco(func)

            return wrapper

        return factory

    return (
        _factory("prod"),
        _factory("experimental", panel="Experimental"),
        _factory("plumbing", hidden=True),
        _factory("beta", hidden=True),
    )
