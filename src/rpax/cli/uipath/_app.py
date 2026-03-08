"""UiPath Typer app instance and maturity factories — imported by both __init__ and commands."""
import typer

from rpax.cli.decorators import make_command_factories

uipath_app = typer.Typer(help="UiPath project analysis")
command, experimental, plumbing, beta = make_command_factories(uipath_app)
