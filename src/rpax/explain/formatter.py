"""Rich console formatting for workflow explanations."""


from rich import box
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from .analyzer import ArgumentInfo, WorkflowExplanation


class ExplanationFormatter:
    """Formats workflow explanations for rich console display."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def format_explanation(
        self,
        explanation: WorkflowExplanation,
        pseudocode_text: str | None = None,
    ) -> None:
        """Format and display workflow explanation focused on developer/reviewer needs."""

        self._format_header(explanation)

        if explanation.arguments:
            self._format_arguments(explanation.arguments)

        if explanation.variables:
            self._format_variables(explanation.variables)

        if explanation.annotated_activities:
            self._format_annotations(explanation.annotated_activities)

        if pseudocode_text:
            self._format_pseudocode(pseudocode_text)

    def _format_header(self, explanation: WorkflowExplanation) -> None:
        """Compact header: role line, then path | project."""

        # Role indicators
        indicators = []
        if explanation.is_entry_point:
            indicators.append("[bold blue]ENTRY POINT[/bold blue]")
        if explanation.is_test:
            indicators.append("[bold green]TEST[/bold green]")
        if explanation.is_orphan:
            indicators.append("[bold yellow]ORPHAN[/bold yellow]")
        if explanation.is_reusable:
            indicators.append("[bold cyan]REUSABLE[/bold cyan]")

        role_str = "  ".join(indicators) if indicators else ""
        if role_str:
            self.console.print(f"{explanation.project_name}  {role_str}")
        else:
            self.console.print(explanation.project_name)

        self.console.print(
            f"[dim]{explanation.relative_path}[/dim]  [bold]{explanation.display_name}[/bold]"
        )
        self.console.print()

        if explanation.parse_errors:
            self.console.print("[red]Parse Errors:[/red]")
            for error in explanation.parse_errors:
                self.console.print(f"  • {error}")
            self.console.print()

    def _format_arguments(self, arguments: list[ArgumentInfo]) -> None:
        """Format workflow arguments."""

        self.console.print(Rule(f" Arguments ({len(arguments)}) ", align="left"))

        table = Table(show_header=True, box=box.SIMPLE, pad_edge=False)
        table.add_column("Name", style="bold cyan")
        table.add_column("Dir", style="blue", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Description", style="white")

        direction_colors = {"In": "blue", "Out": "green", "InOut": "yellow"}

        for arg in arguments:
            color = direction_colors.get(arg.direction, "white")
            table.add_row(
                arg.name,
                f"[{color}]{arg.direction}[/{color}]",
                arg.type_name or "Object",
                arg.description or "",
            )

        self.console.print(table)
        self.console.print()

    def _format_variables(self, variables: list[dict]) -> None:
        """Compact variable listing."""

        self.console.print(Rule(f" Variables ({len(variables)}) ", align="left"))

        for var in variables:
            name = var.get("name", "?")
            # Prefer 'default' (activities.tree) then 'default_value' (index)
            expr = var.get("default") or var.get("default_value") or ""
            type_name = var.get("type") or var.get("typeName") or ""

            if expr:
                self.console.print(f"  [cyan]{name}[/cyan] = [dim]{expr}[/dim]")
            elif type_name:
                self.console.print(f"  [cyan]{name}[/cyan]  [dim]({type_name})[/dim]")
            else:
                self.console.print(f"  [cyan]{name}[/cyan]")

        self.console.print()

    def _format_annotations(self, annotated_activities: list[tuple[str, str]]) -> None:
        """Format annotated activities table."""

        self.console.print(Rule(" Annotations ", align="left"))

        table = Table(show_header=True, box=box.SIMPLE, pad_edge=False)
        table.add_column("Activity", style="bold cyan")
        table.add_column("Note", style="white")

        for display_name, note in annotated_activities:
            table.add_row(display_name, note)

        self.console.print(table)
        self.console.print()

    def _format_pseudocode(self, pseudocode_text: str) -> None:
        """Format pseudocode section."""

        self.console.print(Rule(" Pseudocode ", align="left"))
        self.console.print(f"[dim]{pseudocode_text}[/dim]")
        self.console.print()
