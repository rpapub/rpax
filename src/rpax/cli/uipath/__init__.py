"""UiPath CLI sub-application."""
from rpax.cli.uipath._app import beta, command, experimental, plumbing, uipath_app

from rpax.cli.uipath import commands as _commands  # noqa: F401 — registers commands

__all__ = ["uipath_app", "command", "experimental", "plumbing", "beta"]
