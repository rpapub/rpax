"""Root Typer app, version callback, signal handlers, and root command aliases."""
from __future__ import annotations

import signal
import sys
from typing import Annotated

import typer
from rich.console import Console

from rpax import __description__, __version__
from rpax.cli.uipath import uipath_app
from rpax.cli.uipath.commands import bump_cmd, explain, parse

app = typer.Typer(
    name="rpa-cli", help=__description__, add_completion=False, rich_markup_mode="rich"
)
console = Console()

# Global flag to track graceful shutdown
_shutdown_requested = False


def _signal_handler(signum: int, frame) -> None:
    """Handle interrupt signals gracefully."""
    global _shutdown_requested

    signal_names = {signal.SIGINT: "SIGINT (Ctrl+C)", signal.SIGTERM: "SIGTERM"}
    signal_name = signal_names.get(signum, f"signal {signum}")

    if not _shutdown_requested:
        _shutdown_requested = True
        console.print(
            f"\n[yellow]⚠ Received {signal_name} - shutting down gracefully...[/yellow]"
        )
        console.print("[dim]Press Ctrl+C again to force quit[/dim]")
        raise typer.Exit(1)
    else:
        console.print("[red]⚠ Force quit requested[/red]")
        sys.exit(130)  # Standard exit code for Ctrl+C


def _setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        if hasattr(signal, "SIGTERM"):  # SIGTERM not available on Windows
            signal.signal(signal.SIGTERM, _signal_handler)
    except (OSError, ValueError):
        pass


def version_callback(value: bool) -> None:
    """Show version information and exit."""
    if value:
        console.print(f"rpa-cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v", callback=version_callback, help="Show version and exit"
        ),
    ] = False,
) -> None:
    """rpa-cli - Code-first CLI tool for UiPath project analysis."""
    _setup_signal_handlers()
    from rpax.utils.motd import show_motd  # local import to keep startup lean

    show_motd(console)


# Attach uipath sub-app
app.add_typer(uipath_app, name="uipath")

# Root-level aliases — classified commands only
app.command("bump")(bump_cmd)
# parse/explain: experimental but aliased at root to avoid breaking existing scripts
app.command("parse")(parse)
app.command("explain")(explain)
