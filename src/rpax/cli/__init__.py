"""rpax CLI package — entry point for pyproject.toml."""
from rpax.cli.main import app
from rpax.cli.uipath.commands import _resolve_project_path, parse  # re-exported for tests

__all__ = ["app", "_resolve_project_path", "parse"]
