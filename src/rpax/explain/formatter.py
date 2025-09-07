"""Rich console formatting for workflow explanations."""


from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import ArgumentInfo, CallerInfo, InvocationInfo, WorkflowExplanation


class ExplanationFormatter:
    """Formats workflow explanations for rich console display."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def format_explanation(self, explanation: WorkflowExplanation) -> None:
        """Format and display complete workflow explanation."""

        # Header with workflow identity
        self._format_header(explanation)

        # Basic information panel
        self._format_basic_info(explanation)

        # Arguments section (if any)
        if explanation.arguments:
            self._format_arguments(explanation.arguments)

        # Dependencies section (what this workflow calls)
        if explanation.invokes:
            self._format_invocations(explanation.invokes)

        # Callers section (what calls this workflow)
        if explanation.called_by:
            self._format_callers(explanation.called_by)

        # Classification and insights
        self._format_classification(explanation)

        # Statistics summary
        self._format_statistics(explanation)

    def _format_header(self, explanation: WorkflowExplanation) -> None:
        """Format workflow header with name and key indicators."""

        # Create header text with indicators
        header_text = f"[WORKFLOW] {explanation.display_name}"

        # Add role indicators
        indicators = []
        if explanation.is_entry_point:
            indicators.append("[bold blue]ENTRY POINT[/bold blue]")
        if explanation.is_test:
            indicators.append("[bold green]TEST[/bold green]")
        if explanation.is_orphan:
            indicators.append("[bold yellow]ORPHAN[/bold yellow]")
        if explanation.is_reusable:
            indicators.append("[bold cyan]REUSABLE[/bold cyan]")

        if indicators:
            header_text += f" {' '.join(indicators)}"

        # Show complexity
        complexity_colors = {
            "Simple": "green",
            "Moderate": "yellow",
            "Complex": "orange",
            "Very Complex": "red"
        }
        complexity_color = complexity_colors.get(explanation.complexity_score, "white")
        header_text += f" [{complexity_color}]{explanation.complexity_score}[/{complexity_color}]"

        self.console.print(Panel(header_text, title="Workflow Analysis", expand=False))
        self.console.print()

    def _format_basic_info(self, explanation: WorkflowExplanation) -> None:
        """Format basic workflow information."""

        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        table.add_row("ID", explanation.workflow_id)
        table.add_row("Path", explanation.relative_path)
        table.add_row("Project", explanation.project_name)

        if explanation.folder_category:
            table.add_row("Category", explanation.folder_category)

        # File info
        size_kb = explanation.file_size // 1024 if explanation.file_size > 1024 else explanation.file_size
        size_unit = "KB" if explanation.file_size > 1024 else "B"
        table.add_row("Size", f"{size_kb} {size_unit}")

        if explanation.last_modified:
            table.add_row("Modified", explanation.last_modified)

        # Parse status
        status_color = "green" if explanation.parse_successful else "red"
        status_text = "OK Parsed successfully" if explanation.parse_successful else "ERROR Parse errors"
        table.add_row("Status", f"[{status_color}]{status_text}[/{status_color}]")

        self.console.print(table)

        # Show parse errors if any
        if explanation.parse_errors:
            self.console.print("\n[red]Parse Errors:[/red]")
            for error in explanation.parse_errors:
                self.console.print(f"  • {error}")

        self.console.print()

    def _format_arguments(self, arguments: list[ArgumentInfo]) -> None:
        """Format workflow arguments."""

        table = Table(title="Arguments", box=box.ROUNDED)
        table.add_column("Name", style="bold cyan")
        table.add_column("Direction", style="blue")
        table.add_column("Type", style="green")
        table.add_column("Default", style="dim")
        table.add_column("Description", style="white")

        for arg in arguments:
            direction_colors = {"In": "blue", "Out": "green", "InOut": "yellow"}
            direction_color = direction_colors.get(arg.direction, "white")

            table.add_row(
                arg.name,
                f"[{direction_color}]{arg.direction}[/{direction_color}]",
                arg.type_name or "Object",
                arg.default_value or "",
                arg.description or ""
            )

        self.console.print(table)
        self.console.print()

    def _format_invocations(self, invocations: list[InvocationInfo]) -> None:
        """Format workflow invocations (dependencies)."""

        table = Table(title=f"Dependencies ({len(invocations)} invocations)", box=box.ROUNDED)
        table.add_column("Target Workflow", style="cyan", no_wrap=True, max_width=40)
        table.add_column("Type", style="white")
        table.add_column("Args", style="dim", max_width=30)

        for inv in invocations:
            # Get just the workflow name for display
            target_display = self._get_workflow_display_name(inv.target_workflow)

            # Color code by invocation type
            type_colors = {
                "invoke": "green",
                "invoke-missing": "red",
                "invoke-dynamic": "yellow"
            }
            type_color = type_colors.get(inv.kind, "white")
            type_display = inv.kind.replace("invoke-", "").replace("invoke", "direct")

            # Format arguments
            args_display = ""
            if inv.arguments:
                args_list = [f"{k}={v}" for k, v in list(inv.arguments.items())[:2]]
                args_display = ", ".join(args_list)
                if len(inv.arguments) > 2:
                    args_display += f" (+{len(inv.arguments)-2} more)"

            table.add_row(
                target_display,
                f"[{type_color}]{type_display}[/{type_color}]",
                args_display
            )

        self.console.print(table)
        self.console.print()

    def _format_callers(self, callers: list[CallerInfo]) -> None:
        """Format workflow callers."""

        table = Table(title=f"Called By ({len(callers)} callers)", box=box.ROUNDED)
        table.add_column("Caller Workflow", style="cyan", no_wrap=True, max_width=40)
        table.add_column("Type", style="white")
        table.add_column("Args Passed", style="dim", max_width=30)

        for caller in callers:
            # Get just the workflow name for display
            caller_display = self._get_workflow_display_name(caller.caller_workflow)

            # Color code by invocation type
            type_colors = {
                "invoke": "green",
                "invoke-missing": "red",
                "invoke-dynamic": "yellow"
            }
            type_color = type_colors.get(caller.kind, "white")
            type_display = caller.kind.replace("invoke-", "").replace("invoke", "direct")

            # Format arguments
            args_display = ""
            if caller.arguments_passed:
                args_list = [f"{k}={v}" for k, v in list(caller.arguments_passed.items())[:2]]
                args_display = ", ".join(args_list)
                if len(caller.arguments_passed) > 2:
                    args_display += f" (+{len(caller.arguments_passed)-2} more)"

            table.add_row(
                caller_display,
                f"[{type_color}]{type_display}[/{type_color}]",
                args_display
            )

        self.console.print(table)
        self.console.print()

    def _format_classification(self, explanation: WorkflowExplanation) -> None:
        """Format workflow classification and role."""

        classifications = []

        if explanation.is_entry_point:
            classifications.append(">> **Entry Point** - Can be executed directly from UiPath")

        if explanation.is_test:
            classifications.append("** **Test Workflow** - Used for testing other components")

        if explanation.is_orphan:
            classifications.append("?? **Orphan** - Not called by any other workflow")

        if explanation.is_reusable:
            classifications.append("<> **Reusable** - Called by multiple workflows")

        if not explanation.has_dependencies:
            classifications.append("[] **Self-Contained** - Doesn't depend on other workflows")

        if classifications:
            self.console.print("[bold]Classification:[/bold]")
            for classification in classifications:
                self.console.print(f"  {classification}")
            self.console.print()

    def _format_statistics(self, explanation: WorkflowExplanation) -> None:
        """Format workflow statistics."""

        table = Table(title="Statistics", box=box.SIMPLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")

        table.add_row("Total Invocations", str(explanation.total_invocations))
        table.add_row("Unique Dependencies", str(explanation.unique_dependencies))
        table.add_row("Times Called", str(len(explanation.called_by)))
        table.add_row("Complexity", explanation.complexity_score)

        self.console.print(table)
        self.console.print()

    def _get_workflow_display_name(self, workflow_id: str) -> str:
        """Extract display name from workflow ID."""
        # Try to get just the workflow name from the composite ID
        if "#" in workflow_id:
            parts = workflow_id.split("#")
            if len(parts) >= 2:
                workflow_path = parts[1]  # Get the wfId part
                if "/" in workflow_path:
                    return workflow_path.split("/")[-1]  # Get just filename
                return workflow_path

        # Fallback to full ID if parsing fails
        return workflow_id[:40] + "..." if len(workflow_id) > 40 else workflow_id
