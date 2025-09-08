"""Demonstration of integrated CLI with activity resources and error collection.

Shows how to update the existing parse command to use:
- ActivityResourceManager for activity-centric resources
- ErrorCollector for run-scoped lake-level error handling
- Both legacy and V0 schema support
"""

from datetime import datetime  
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from slugify import slugify

from rpax.config import load_config
from rpax.parser.project import ProjectParser
from rpax.parser.workflow_discovery import create_workflow_discovery
from rpax.output.base import ParsedProjectData
from rpax.cli_integration import create_integrated_pipeline

console = Console()


def integrated_parse_command(
    path: Annotated[
        Path,
        typer.Argument(help="Path to UiPath project directory or project.json file")
    ] = Path("."),
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output directory for artifacts (default: .rpax-lake)")
    ] = None,
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Configuration file path (default: search for .rpax.json)")
    ] = None,
    schema: Annotated[
        str,
        typer.Option("--schema", help="Output schema version (legacy, v0)")
    ] = "legacy",
    additional_paths: Annotated[
        List[Path],
        typer.Option("--path", help="Additional project paths for batch parsing (can be used multiple times)")
    ] = None,
) -> None:
    """Parse UiPath project(s) and generate artifacts with integrated error collection.
    
    Enhanced version of parse command that includes:
    - Activity resource generation with package relationships
    - Run-scoped error collection at lake level
    - Progressive disclosure for V0 schema
    """
    
    # Initialize error collection early
    project_paths = _collect_project_paths(path, additional_paths)
    base_config = load_config(config or project_paths[0] / ".rpax.json")
    
    if out:
        base_config.output.dir = str(out)
    
    # Initialize integrated pipeline
    lake_root = Path(base_config.output.dir)
    pipeline = create_integrated_pipeline(base_config, lake_root, "parse")
    
    console.print(f"[blue]Output lake:[/blue] {base_config.output.dir}")
    console.print(f"[blue]Schema version:[/blue] {schema}")  
    console.print(f"[green]Parsing {len(project_paths)} project(s) with integrated pipeline:[/green]")
    
    total_workflows = 0
    total_errors = 0
    all_artifacts = {}
    
    try:
        # Parse each project with error collection
        for i, project_path in enumerate(project_paths, 1):
            console.print(f"\n[cyan]Project {i}/{len(project_paths)}:[/cyan] {project_path}")
            
            try:
                # Parse project with integrated pipeline  
                project_artifacts = _parse_single_project_integrated(
                    project_path, base_config, schema, pipeline
                )
                
                all_artifacts.update(project_artifacts["artifacts"])
                total_workflows += project_artifacts["workflow_count"]
                
                console.print(f"[green]  OK[/green] Generated {len(project_artifacts['artifacts'])} artifacts")
                
                # Show activity resource summary if generated
                if any(name.startswith("activity_resources") for name in project_artifacts["artifacts"]):
                    activity_count = project_artifacts.get("activity_count", 0)
                    console.print(f"[green]  OK[/green] Activity resources: {activity_count} activities processed")
                
            except Exception as e:
                console.print(f"[red]  Error parsing project {project_path}:[/red] {e}")
                total_errors += 1
                continue
        
        # Show summary with error information
        console.print(f"\n[green]Batch parsing complete:[/green]")
        console.print(f"  - Projects processed: {len(project_paths)}")
        console.print(f"  - Total workflows: {total_workflows}")
        console.print(f"  - Total artifacts: {len(all_artifacts)}")
        
        # Show error summary if errors occurred
        if pipeline.has_errors():
            error_summary = pipeline.get_error_summary()
            console.print(f"\n[yellow]Warnings/Errors collected:[/yellow]")
            for severity, count in error_summary.items():
                if count > 0:
                    console.print(f"  - {severity}: {count}")
        
        # Generate lake index
        if len(project_paths) > 1:
            _generate_lake_index(lake_root, all_artifacts)
            console.print("[green]  OK[/green] Generated multi-project lake index")
    
    except Exception as e:
        console.print(f"[red]Critical error during parsing:[/red] {e}")
        raise typer.Exit(1)
    
    finally:
        # Always flush errors to filesystem
        error_file = pipeline.finalize_run()
        if error_file and pipeline.has_errors():
            console.print(f"\n[blue]Error diagnostics saved to:[/blue] {error_file}")
            console.print("[dim]Use `rpax errors show` to view detailed error information[/dim]")
        
        # Exit with error code if critical errors occurred
        if pipeline.has_critical_errors():
            console.print("[red]Critical errors occurred - see error diagnostics for details[/red]")
            raise typer.Exit(1)


def _collect_project_paths(path: Path, additional_paths: Optional[List[Path]]) -> List[Path]:
    """Collect all project paths to parse."""
    project_paths = []
    
    # Add main project path
    if path != Path(".") or not additional_paths:
        project_paths.append(_resolve_project_path(path))
    
    # Add additional project paths
    if additional_paths:
        for project_path in additional_paths:
            project_paths.append(_resolve_project_path(project_path))
    
    if not project_paths:
        console.print("[red]Error:[/red] No projects specified")
        raise typer.Exit(1)
    
    return project_paths


def _resolve_project_path(path: Path) -> Path:
    """Resolve project path to directory containing project.json."""
    if path.is_file() and path.name == "project.json":
        return path.parent
    elif path.is_dir():
        if (path / "project.json").exists():
            return path
        else:
            console.print(f"[red]Error:[/red] No project.json found in {path}")
            raise typer.Exit(1)
    else:
        console.print(f"[red]Error:[/red] Invalid project path: {path}")
        raise typer.Exit(1)


def _parse_single_project_integrated(
    project_path: Path,
    base_config,
    schema: str,
    pipeline
) -> dict:
    """Parse single project with integrated pipeline."""
    
    # Load project-specific config if available
    project_config_path = project_path / ".rpax.json"
    if project_config_path.exists():
        project_config = load_config(project_config_path)
        # Keep same output directory for multi-project lake
        project_config.output.dir = base_config.output.dir
    else:
        project_config = base_config
    
    # Parse project.json
    console.print("[dim]  Parsing project.json...[/dim]")
    project = ProjectParser.parse_project_from_dir(project_path)
    console.print(f"[green]  OK[/green] Project: {project.name} ({project.project_type})")
    
    # Update config with project info
    if not project_config.project.name:
        project_config.project.name = project.name
    
    # Discover workflows (respecting configuration)
    include_coded = project_config.parser.include_coded_workflows
    if schema == "v0" and include_coded:
        console.print("[dim]  Discovering workflows (XAML + coded)...[/dim]")
        discovery = create_workflow_discovery(
            project_path,
            exclude_patterns=project_config.scan.exclude,
            include_coded_workflows=True
        )
    else:
        console.print("[dim]  Discovering XAML workflows...[/dim]")
        discovery = create_workflow_discovery(
            project_path,
            exclude_patterns=project_config.scan.exclude,
            include_coded_workflows=False
        )
    
    workflow_index = discovery.discover_workflows()
    
    console.print(f"[green]  OK[/green] Found {workflow_index.total_workflows} workflows")
    if workflow_index.failed_parses > 0:
        console.print(f"[yellow]  WARN[/yellow] {workflow_index.failed_parses} workflows had parse errors")
    
    # Create parsed data structure
    project_slug = slugify(project.name)
    parsed_data = ParsedProjectData(
        project=project,
        workflow_index=workflow_index,
        project_root=project_path,
        project_slug=project_slug,
        timestamp=datetime.now()
    )
    
    # Generate artifacts with integrated pipeline
    console.print("[dim]  Generating artifacts with integrated pipeline...[/dim]")
    artifacts = pipeline.generate_project_artifacts(parsed_data, schema)
    
    # Count activity resources for summary
    activity_count = 0
    for artifact_name in artifacts:
        if "activity_resources" in artifact_name and not artifact_name.endswith("_index"):
            # This is an individual workflow activity resource file
            activity_count += 1
    
    return {
        "artifacts": artifacts,
        "workflow_count": workflow_index.total_workflows,
        "activity_count": activity_count
    }


def _generate_lake_index(lake_root: Path, all_artifacts: dict):
    """Generate lake-level index for multi-project parsing."""
    from rpax.output.lake_index import LakeIndexGenerator
    
    lake_generator = LakeIndexGenerator(lake_root)
    lake_generator.generate_lake_index()


# Demonstration of new CLI commands for error diagnostics
def errors_show_command(
    run_id: Annotated[
        Optional[str],
        typer.Option("--run-id", help="Specific run ID to show (default: latest)")
    ] = None,
) -> None:
    """Show error diagnostics for rpax runs."""
    
    lake_root = Path(".rpax-lake")  # or from config
    errors_dir = lake_root / "_errors"
    
    if not errors_dir.exists():
        console.print("[yellow]No error diagnostics found[/yellow]")
        return
    
    # Load errors index
    index_file = errors_dir / "index.json"
    if not index_file.exists():
        console.print("[yellow]No error index found[/yellow]")
        return
    
    with open(index_file, 'r') as f:
        import json
        index_data = json.load(f)
    
    if not index_data.get("runs"):
        console.print("[green]No errors recorded[/green]")
        return
    
    # Show specific run or latest
    if run_id:
        target_run = next((run for run in index_data["runs"] if run["run_id"] == run_id), None)
        if not target_run:
            console.print(f"[red]Run ID not found:[/red] {run_id}")
            return
        runs_to_show = [target_run]
    else:
        # Show latest run
        runs_to_show = index_data["runs"][:1]
    
    # Display error information
    for run in runs_to_show:
        console.print(f"\n[cyan]Run {run['run_id']}:[/cyan]")
        console.print(f"  Command: {run['command']}")
        console.print(f"  Started: {run['started_at']}")
        console.print(f"  Duration: {run['duration_seconds']:.2f}s")
        console.print(f"  Total errors: {run['total_errors']}")
        
        if run['errors_by_severity']:
            console.print("  Errors by severity:")
            for severity, count in run['errors_by_severity'].items():
                if count > 0:
                    console.print(f"    {severity}: {count}")
        
        # Load detailed errors
        error_file = errors_dir / run["error_file"]
        if error_file.exists():
            with open(error_file, 'r') as f:
                error_data = json.load(f)
            
            console.print(f"\n[yellow]Detailed errors from {error_file}:[/yellow]")
            for error in error_data["errors"][:5]:  # Show first 5 errors
                console.print(f"  [{error['severity'].upper()}] {error['error_type']}: {error['message']}")
                if error.get('context', {}).get('project_slug'):
                    console.print(f"    Project: {error['context']['project_slug']}")
                if error.get('context', {}).get('component'):
                    console.print(f"    Component: {error['context']['component']}")
            
            if len(error_data["errors"]) > 5:
                console.print(f"  ... and {len(error_data['errors']) - 5} more errors")


if __name__ == "__main__":
    # Demo usage
    console.print("Demo of integrated CLI with activity resources and error collection")
    console.print("This shows how the parse command would work with the new pipeline")