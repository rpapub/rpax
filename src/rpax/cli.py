"""CLI interface for rpax using Typer framework."""

import csv
import fnmatch
import json as jsonlib
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from rpax import __description__, __version__
from rpax.artifacts import ArtifactGenerator
from rpax.config import OutputFormat, load_config
from rpax.explain import ExplanationFormatter, WorkflowAnalyzer
from rpax.graph import GraphGenerator, MermaidRenderer
from rpax.parser.project import ProjectParser
from rpax.parser.xaml import XamlDiscovery
from rpax.schemas import ArtifactValidator, SchemaGenerator
from rpax.validation import ValidationFramework


def api_expose(
    path: Optional[str] = None,
    methods: Optional[List[str]] = None,
    summary: Optional[str] = None,
    tags: Optional[List[str]] = None,
    enabled: bool = True,
    mcp_resource_type: Optional[str] = None,
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
            "summary": summary or (func.__doc__.split('\n')[0] if func.__doc__ else f"{func.__name__} operation"),
            "tags": tags or [],
            "mcp_hints": {"resource_type": mcp_resource_type} if mcp_resource_type else {}
        }
        return func
    return decorator


app = typer.Typer(
    name="rpax",
    help=__description__,
    add_completion=False,
    rich_markup_mode="rich"
)

console = Console()

# Global flag to track graceful shutdown
_shutdown_requested = False

def _signal_handler(signum: int, frame) -> None:
    """Handle interrupt signals gracefully."""
    global _shutdown_requested
    
    signal_names = {
        signal.SIGINT: "SIGINT (Ctrl+C)",
        signal.SIGTERM: "SIGTERM"
    }
    
    signal_name = signal_names.get(signum, f"signal {signum}")
    
    if not _shutdown_requested:
        _shutdown_requested = True
        console.print(f"\n[yellow]⚠ Received {signal_name} - shutting down gracefully...[/yellow]")
        console.print("[dim]Press Ctrl+C again to force quit[/dim]")
        
        # Exit gracefully
        raise typer.Exit(1)
    else:
        # Second interrupt - force quit
        console.print("[red]⚠ Force quit requested[/red]")
        sys.exit(130)  # Standard exit code for Ctrl+C

def _setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        if hasattr(signal, 'SIGTERM'):  # SIGTERM not available on Windows
            signal.signal(signal.SIGTERM, _signal_handler)
    except (OSError, ValueError):
        # Signal handling might not be available in all environments
        pass


def version_callback(value: bool) -> None:
    """Show version information and exit."""
    if value:
        console.print(f"rpax version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=version_callback, help="Show version and exit")
    ] = False,
) -> None:
    """rpax - Code-first CLI tool for UiPath project analysis."""
    # Setup signal handlers for graceful shutdown
    _setup_signal_handlers()


def _resolve_multiple_project_artifacts_paths(lake_path: Path, project_slugs: list[str], command_context: str = "workflows") -> list[tuple[str, Path]]:
    """Resolve artifacts paths for multiple projects in a multi-project lake.
    
    Args:
        lake_path: Path to the lake directory
        project_slugs: List of project slugs to resolve
        command_context: Context for error messages
        
    Returns:
        List of (project_slug, artifacts_path) tuples
        
    Raises:
        typer.Exit: If project selection fails or projects not found
    """
    projects_file = lake_path / "projects.json"
    if not projects_file.exists():
        console.print(f"[red]Error:[/red] No projects.json found in {lake_path}")
        raise typer.Exit(1)

    try:
        with open(projects_file, encoding="utf-8") as f:
            index_data = jsonlib.load(f)

        projects = index_data.get("projects", [])
        if not projects:
            console.print("[red]Error:[/red] No projects found in lake")
            raise typer.Exit(1)

        # Build slug to project mapping
        project_map = {p.get("slug"): p for p in projects}
        available_slugs = list(project_map.keys())
        
        # Resolve each requested project
        resolved_projects = []
        missing_projects = []
        
        for slug in project_slugs:
            if slug in project_map:
                artifacts_path = lake_path / slug
                if artifacts_path.exists():
                    resolved_projects.append((slug, artifacts_path))
                else:
                    console.print(f"[yellow]Warning:[/yellow] Project artifacts not found for '{slug}': {artifacts_path}")
            else:
                missing_projects.append(slug)
        
        # Report missing projects
        if missing_projects:
            console.print(f"[red]Error:[/red] Project(s) not found: {', '.join(missing_projects)}")
            console.print(f"Available projects: {', '.join(available_slugs)}")
            raise typer.Exit(1)
        
        return resolved_projects
        
    except jsonlib.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON in projects.json: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read projects index: {e}")
        raise typer.Exit(1)


def _resolve_project_artifacts_path(lake_path: Path, project_slug: str | None = None, command_context: str = "workflows") -> Path:
    """Resolve the artifacts path for a specific project in a multi-project lake.
    
    Args:
        lake_path: Path to the lake directory
        project_slug: Optional project slug to select specific project
        
    Returns:
        Path to the project's artifacts directory
        
    Raises:
        typer.Exit: If project selection fails or no projects found
    """

    projects_file = lake_path / "projects.json"
    if not projects_file.exists():
        console.print(f"[red]Error:[/red] No projects.json found in {lake_path}")
        raise typer.Exit(1)

    try:
        with open(projects_file, encoding="utf-8") as f:
            index_data = jsonlib.load(f)

        projects = index_data.get("projects", [])
        if not projects:
            console.print("[red]Error:[/red] No projects found in lake")
            raise typer.Exit(1)

        if project_slug:
            # Find specific project
            for project in projects:
                if project.get("slug") == project_slug:
                    artifacts_path = lake_path / project_slug
                    if not artifacts_path.exists():
                        console.print(f"[red]Error:[/red] Project artifacts not found: {artifacts_path}")
                        raise typer.Exit(1)
                    return artifacts_path

            # Project not found
            available = [p.get("slug") for p in projects]
            console.print(f"[red]Error:[/red] Project '{project_slug}' not found.")
            console.print(f"Available projects: {', '.join(available)}")
            raise typer.Exit(1)

        elif len(projects) == 1:
            # Use single project as default
            project = projects[0]
            project_slug = project.get("slug")
            console.print(f"[dim]Using project: {project.get('name')} ({project_slug})[/dim]")
            return lake_path / project_slug

        else:
            # Multiple projects, user must specify
            console.print("[yellow]Multiple projects found. Please specify --project option:[/yellow]")
            console.print("")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Slug")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Last Parsed")

            for project in projects:
                table.add_row(
                    project.get("slug", ""),
                    project.get("name", ""),
                    project.get("projectType", ""),
                    project.get("lastParsed", "")[:19] if project.get("lastParsed") else ""  # Trim timestamp
                )

            console.print(table)
            console.print("")
            # Show dynamic example based on the command context
            sample_project = projects[0].get("slug", "f4aa3834") if projects else "f4aa3834"
            console.print(f"Example: [cyan]rpax list {command_context} --project {sample_project}[/cyan]")
            raise typer.Exit(1)

    except (OSError, jsonlib.JSONDecodeError) as e:
        console.print(f"[red]Error:[/red] Failed to read projects.json: {e}")
        raise typer.Exit(1)


def _resolve_project_path(path: Path) -> Path:
    """Resolve project path with smart detection of project.json vs directory.
    
    Args:
        path: Input path (directory or project.json file)
        
    Returns:
        Path to project directory containing project.json
        
    Raises:
        FileNotFoundError: If project.json cannot be found
    """
    resolved_path = path.resolve()

    # Check if path ends with project.json
    if resolved_path.name.lower() == "project.json":
        # Path is project.json file - use parent directory
        project_dir = resolved_path.parent
        project_file = resolved_path

        if not project_file.exists():
            raise FileNotFoundError(f"Project file not found: {project_file}")

        console.print(f"[dim]Detected project.json file: {project_file}[/dim]")

    else:
        # Path is directory - look for project.json inside
        project_dir = resolved_path
        project_file = ProjectParser.find_project_file(project_dir)

        if project_file is None:
            raise FileNotFoundError(f"No project.json found in directory: {project_dir}")

        console.print(f"[dim]Found project.json: {project_file}[/dim]")

    return project_dir


@api_expose(enabled=False)  # CLI-only: writes files, parses projects
@app.command()
def parse(
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
    additional_paths: Annotated[
        list[Path],
        typer.Option("--path", help="Additional project paths for batch parsing (can be used multiple times)")
    ] = None,
) -> None:
    """Parse UiPath project(s) and generate artifacts.
    
    Parse a single project via PATH argument, or multiple projects via additional --path options.
    All paths should point to UiPath project directories or project.json files.
    All projects are parsed into the same multi-project lake.
    """
    try:
        # Collect all project paths to parse
        project_paths = []
        
        # Add main project path
        if path != Path(".") or not additional_paths:
            # Only add main path if explicitly specified or no --path options
            project_paths.append(_resolve_project_path(path))
        
        # Add additional project paths
        if additional_paths:
            for project_path in additional_paths:
                project_paths.append(_resolve_project_path(project_path))
        
        if not project_paths:
            console.print("[red]Error:[/red] No projects specified")
            raise typer.Exit(1)
        
        # Load base configuration from first project
        base_config = load_config(config or project_paths[0] / ".rpax.json")
        
        # Override output directory if specified  
        if out:
            base_config.output.dir = str(out)
        
        console.print(f"[blue]Output lake:[/blue] {base_config.output.dir}")
        console.print(f"[green]Parsing {len(project_paths)} project(s):[/green]")
        
        total_workflows = 0
        total_errors = 0
        all_artifacts = {}
        
        # Parse each project
        for i, project_path in enumerate(project_paths, 1):
            console.print(f"\n[cyan]Project {i}/{len(project_paths)}:[/cyan] {project_path}")
            
            # Load project-specific config if available
            project_config_path = project_path / ".rpax.json"
            if project_config_path.exists():
                project_config = load_config(project_config_path)
                # Keep same output directory for multi-project lake
                project_config.output.dir = base_config.output.dir
            else:
                project_config = base_config
            
            try:
                # Parse project.json
                console.print("[dim]  Parsing project.json...[/dim]")
                project = ProjectParser.parse_project_from_dir(project_path)
                console.print(f"[green]  OK[/green] Project: {project.name} ({project.project_type})")
                
                # Update config with project info
                if not project_config.project.name:
                    project_config.project.name = project.name
                
                # Discover workflows
                console.print("[dim]  Discovering XAML workflows...[/dim]")
                discovery = XamlDiscovery(project_path, exclude_patterns=project_config.scan.exclude)
                workflow_index = discovery.discover_workflows()
                
                console.print(f"[green]  OK[/green] Found {workflow_index.total_workflows} workflows")
                if workflow_index.failed_parses > 0:
                    console.print(f"[yellow]  WARN[/yellow] {workflow_index.failed_parses} workflows had parse errors")
                
                total_workflows += workflow_index.total_workflows
                total_errors += workflow_index.failed_parses
                
                # Generate artifacts
                console.print("[dim]  Generating artifacts...[/dim]")
                generator = ArtifactGenerator(project_config, out)
                artifacts = generator.generate_all_artifacts(project, workflow_index, project_path)
                
                console.print(f"[green]  OK[/green] Generated {len(artifacts)} artifact files")
                all_artifacts.update(artifacts)
                
            except Exception as e:
                console.print(f"[red]  Error parsing project {project_path}:[/red] {e}")
                total_errors += 1
                continue
        
        # Summary
        console.print(f"\n[green]OK Batch parsing complete:[/green]")
        console.print(f"  - Projects processed: {len(project_paths)}")
        console.print(f"  - Total workflows: {total_workflows}")
        console.print(f"  - Total artifacts: {len(all_artifacts)}")
        if total_errors > 0:
            console.print(f"  - [yellow]Errors/warnings: {total_errors}[/yellow]")
        
        console.print(f"\n[blue]Multi-project lake:[/blue] {base_config.output.dir}")
        console.print(f"[dim]Use 'rpax projects' to list all projects in the lake[/dim]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Make sure you're in a UiPath project directory with project.json[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _filter_workflows(workflows: list[Any], search: str | None = None,
                     filter_pattern: str | None = None) -> list[Any]:
    """Filter workflows based on search term and pattern."""
    filtered = workflows

    # Apply search filter
    if search:
        search_lower = search.lower()
        filtered = [
            w for w in filtered
            if (search_lower in w.file_name.lower() or
                search_lower in (w.display_name or "").lower() or
                search_lower in w.relative_path.lower())
        ]

    # Apply pattern filter (case-insensitive)
    if filter_pattern:
        filter_pattern_lower = filter_pattern.lower()
        filtered = [
            w for w in filtered
            if (fnmatch.fnmatch(w.file_name.lower(), filter_pattern_lower) or
                fnmatch.fnmatch(w.relative_path.lower(), filter_pattern_lower))
        ]

    return filtered


def _sort_workflows(workflows: list[Any], sort_by: str, reverse: bool = False) -> list[Any]:
    """Sort workflows by specified field."""
    sort_key_map = {
        "name": lambda w: w.file_name.lower(),
        "size": lambda w: w.file_size,
        "modified": lambda w: w.last_modified,
        "path": lambda w: w.relative_path.lower()
    }

    if sort_by not in sort_key_map:
        return workflows

    return sorted(workflows, key=sort_key_map[sort_by], reverse=reverse)


def _output_workflows_table(workflows: list[Any], verbose: bool = False) -> None:
    """Output workflows in table format."""
    if not workflows:
        console.print("[dim]No workflows found[/dim]")
        return

    # Check if this is a multi-project listing (workflows have project_slug)
    is_multi_project = workflows and hasattr(workflows[0], 'project_slug')

    # Create table
    table = Table(title=f"Workflows ({len(workflows)} found)")
    
    if is_multi_project:
        table.add_column("Project", style="magenta", no_wrap=True)
    
    table.add_column("Path", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Size", style="dim", justify="right")

    if verbose:
        table.add_column("Modified", style="dim")
        table.add_column("Hash", style="magenta", max_width=12)

    table.add_column("Status", style="green")

    for workflow in workflows:
        status = "OK" if workflow.parse_successful else "WARN"
        size_kb = f"{workflow.file_size // 1024}KB" if workflow.file_size > 1024 else f"{workflow.file_size}B"

        row = []
        
        if is_multi_project:
            # Add project slug (shortened for display)
            project_display = getattr(workflow, 'project_slug', 'unknown')
            if len(project_display) > 12:
                project_display = project_display[:9] + "..."
            row.append(project_display)
        
        row.extend([
            workflow.relative_path,
            workflow.display_name or workflow.file_name,
            size_kb
        ])

        if verbose:
            # Format last modified date
            try:
                mod_date = datetime.fromisoformat(workflow.last_modified.replace("Z", "+00:00"))
                formatted_date = mod_date.strftime("%Y-%m-%d %H:%M")
            except:
                formatted_date = workflow.last_modified[:16]

            row.extend([
                formatted_date,
                workflow.content_hash[:8] + "..."
            ])

        row.append(status)
        table.add_row(*row)

    console.print(table)


def _output_workflows_json(workflows: list[Any], verbose: bool = False) -> None:
    """Output workflows in JSON format."""
    data = []
    for workflow in workflows:
        item = {
            "path": workflow.relative_path,
            "name": workflow.display_name or workflow.file_name,
            "fileName": workflow.file_name,
            "size": workflow.file_size,
            "status": "OK" if workflow.parse_successful else "WARN"
        }

        if verbose:
            item.update({
                "id": workflow.id,
                "contentHash": workflow.content_hash,
                "lastModified": workflow.last_modified,
                "filePath": workflow.file_path,
                "projectSlug": workflow.project_slug,
                "discoveredAt": workflow.discovered_at
            })

        data.append(item)

    print(jsonlib.dumps({"workflows": data, "total": len(data)}, indent=2))


def _output_workflows_csv(workflows: list[Any], verbose: bool = False) -> None:
    """Output workflows in CSV format."""
    import sys

    fieldnames = ["path", "name", "fileName", "size", "status"]
    if verbose:
        fieldnames.extend(["id", "contentHash", "lastModified", "filePath", "projectSlug"])

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for workflow in workflows:
        row = {
            "path": workflow.relative_path,
            "name": workflow.display_name or workflow.file_name,
            "fileName": workflow.file_name,
            "size": workflow.file_size,
            "status": "OK" if workflow.parse_successful else "WARN"
        }

        if verbose:
            row.update({
                "id": workflow.id,
                "contentHash": workflow.content_hash,
                "lastModified": workflow.last_modified,
                "filePath": workflow.file_path,
                "projectSlug": workflow.project_slug
            })

        writer.writerow(row)


@api_expose(
    path="/projects/{project}/workflows",
    methods=["GET"],
    tags=["workflows"],
    summary="List workflows, roots, orphans, or activities in a project",
    mcp_resource_type="workflow_list"
)
@app.command("list")
def list_items(
    item_type: Annotated[
        str,
        typer.Argument(help="Type of items to list: workflows, roots, orphans, activities")
    ] = "workflows",
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project path or lake directory to analyze (default: .rpax-lake)")
    ] = Path(".rpax-lake"),
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table, json, csv (default: table)")
    ] = "table",
    project: Annotated[
        str,
        typer.Option("--project", help="Project slug for single-project listing")
    ] = None,
    projects: Annotated[
        list[str],
        typer.Option("--projects", help="Multiple project slugs for cross-project listing (comma-separated or multiple uses)")
    ] = None,
    search: Annotated[
        str,
        typer.Option("--search", "-s", help="Search term to filter results by name/path (optional)")
    ] = None,
    sort: Annotated[
        str,
        typer.Option("--sort", help="Sort by: name, size, modified, path (default: name)")
    ] = "name",
    reverse: Annotated[
        bool,
        typer.Option("--reverse", "-r", help="Reverse sort order (default: False)")
    ] = False,
    filter_pattern: Annotated[
        str,
        typer.Option("--filter", help="Filter by glob pattern: '*.xaml', '*Test*', etc. (optional)")
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Limit number of results shown (default: no limit)")
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed information and metadata (default: False)")
    ] = False,
) -> None:
    """List project elements with enhanced filtering, sorting, and output formats."""
    valid_types = ["workflows", "roots", "orphans", "activities"]
    valid_formats = ["table", "json", "csv"]
    valid_sorts = ["name", "size", "modified", "path"]

    # Validate arguments
    if item_type not in valid_types:
        console.print(f"[red]Error:[/red] Invalid type '{item_type}'. Must be one of: {', '.join(valid_types)}")
        raise typer.Exit(1)

    if format not in valid_formats:
        console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}")
        raise typer.Exit(1)

    if sort not in valid_sorts:
        console.print(f"[red]Error:[/red] Invalid sort field '{sort}'. Must be one of: {', '.join(valid_sorts)}")
        raise typer.Exit(1)

    # Validate project parameter usage
    if project and projects:
        console.print("[red]Error:[/red] Cannot use both --project and --projects. Use one or the other.")
        console.print("[dim]  --project SLUG     : Single project listing")
        console.print("[dim]  --projects SLUG1,SLUG2 : Multi-project listing")
        raise typer.Exit(1)

    # Convert single project to list for unified handling
    target_projects = None
    if project:
        target_projects = [project]
    elif projects:
        # Handle both comma-separated and multiple option formats
        target_projects = []
        for project_spec in projects:
            if "," in project_spec:
                # Comma-separated: "proj1,proj2,proj3"
                target_projects.extend([p.strip() for p in project_spec.split(",") if p.strip()])
            else:
                # Single project per option: --projects proj1 --projects proj2
                target_projects.append(project_spec.strip())
        
        # Remove duplicates while preserving order
        target_projects = list(dict.fromkeys(target_projects))

    try:
        project_path = path.resolve()

        # Show header for table output
        if format == "table":
            console.print(f"[green]Listing {item_type}:[/green] {project_path}")

        if item_type == "workflows":
            # Check if this is a multi-project lake directory
            if (project_path / "projects.json").exists():
                # Multi-project lake structure
                from rpax.models.workflow import Workflow, WorkflowIndex

                if target_projects and len(target_projects) > 1:
                    # Multi-project query using --projects
                    resolved_projects = _resolve_multiple_project_artifacts_paths(project_path, target_projects, "workflows")
                    all_workflows = []
                    
                    for project_slug, artifacts_path in resolved_projects:
                        with open(artifacts_path / "workflows.index.json") as f:
                            index_data = jsonlib.load(f)
                        
                        # Add project context to each workflow
                        project_workflows = []
                        for w_data in index_data.get("workflows", []):
                            workflow = Workflow(**w_data)
                            # Add project context for multi-project display
                            workflow.project_slug = project_slug
                            project_workflows.append(workflow)
                        
                        all_workflows.extend(project_workflows)
                    
                    workflow_index = WorkflowIndex(
                        project_name=f"Multi-project ({len(resolved_projects)} projects)",
                        project_root="<multiple>",
                        scan_timestamp="",
                        total_workflows=len(all_workflows),
                        successful_parses=len(all_workflows),
                        failed_parses=0,
                        workflows=all_workflows
                    )
                else:
                    # Single project query (existing logic)
                    single_project = target_projects[0] if target_projects else None
                    artifacts_path = _resolve_project_artifacts_path(project_path, single_project, "workflows")

                    with open(artifacts_path / "workflows.index.json") as f:
                        index_data = jsonlib.load(f)

                    # Convert to WorkflowIndex object
                    workflow_index = WorkflowIndex(
                        project_name=index_data.get("projectName", ""),
                        project_root=index_data.get("projectRoot", ""),
                        scan_timestamp=index_data.get("scanTimestamp", ""),
                        total_workflows=index_data.get("totalWorkflows", 0),
                        successful_parses=index_data.get("successfulParses", 0),
                        failed_parses=index_data.get("failedParses", 0),
                        workflows=[Workflow(**w) for w in index_data.get("workflows", [])]
                    )
            else:
                # Path is project directory, scan for workflows
                rpax_config = load_config(project_path / ".rpax.json")
                discovery = XamlDiscovery(project_path, exclude_patterns=rpax_config.scan.exclude)
                workflow_index = discovery.discover_workflows()

            if workflow_index.total_workflows == 0:
                if format == "table":
                    console.print("[dim]No workflows found[/dim]")
                elif format == "json":
                    print(jsonlib.dumps({"workflows": [], "total": 0}))
                elif format == "csv":
                    import sys
                    writer = csv.DictWriter(sys.stdout, fieldnames=["path", "name", "fileName", "size", "status"])
                    writer.writeheader()
                return

            # Apply filtering
            workflows = _filter_workflows(
                workflow_index.workflows,
                search=search,
                filter_pattern=filter_pattern
            )

            # Apply sorting
            workflows = _sort_workflows(workflows, sort, reverse)

            # Apply limit
            if limit:
                workflows = workflows[:limit]

            # Output in requested format
            if format == "table":
                _output_workflows_table(workflows, verbose)

                if workflow_index.failed_parses > 0:
                    console.print(f"\n[yellow]WARN[/yellow] {workflow_index.failed_parses} workflows had parse errors")

            elif format == "json":
                _output_workflows_json(workflows, verbose)

            elif format == "csv":
                _output_workflows_csv(workflows, verbose)

        elif item_type == "roots":
            # Check if this is a multi-project lake directory
            if (project_path / "projects.json").exists():
                # Multi-project lake structure
                artifacts_path = _resolve_project_artifacts_path(project_path, project, "roots")

                if not (artifacts_path / "manifest.json").exists():
                    if format == "table":
                        console.print("[red]Error:[/red] No manifest.json found for project")
                    elif format == "json":
                        print(jsonlib.dumps({"entry_points": [], "total": 0, "error": "No manifest found"}))
                    return

                with open(artifacts_path / "manifest.json") as f:
                    manifest_data = jsonlib.load(f)

                entry_points = manifest_data.get("entryPoints", [])


            elif (project_path / "manifest.json").exists() and (project_path / "workflows.index.json").exists():
                # Path is artifacts directory
                with open(project_path / "manifest.json") as f:
                    manifest_data = jsonlib.load(f)
                entry_points = manifest_data.get("entryPoints", [])
            else:
                # Path is project directory, scan for project.json
                rpax_config = load_config(project_path / ".rpax.json")
                # Parse project to get entry points
                project_parser = ProjectParser.parse_project_from_dir(project_path)

                if not project_parser.entry_points:
                    if format == "table":
                        console.print("[dim]No entry points defined[/dim]")
                    elif format == "json":
                        print(jsonlib.dumps({"entry_points": [], "total": 0}))
                    elif format == "csv":
                        import sys
                        writer = csv.DictWriter(sys.stdout, fieldnames=["workflow", "inputs", "outputs"])
                        writer.writeheader()
                    return

                entry_points = project_parser.entry_points

            # Check if no entry points found
            if not entry_points:
                if format == "table":
                    console.print("[dim]No entry points defined[/dim]")
                elif format == "json":
                    print(jsonlib.dumps({"entry_points": [], "total": 0}))
                elif format == "csv":
                    import sys
                    writer = csv.DictWriter(sys.stdout, fieldnames=["workflow", "inputs", "outputs"])
                    writer.writeheader()
                return

            # Filter entry points if search term provided
            if search:
                search_lower = search.lower()
                if (project_path / "manifest.json").exists():
                    # Entry points are dictionaries from manifest
                    entry_points = [
                        ep for ep in entry_points
                        if search_lower in ep.get("filePath", "").lower()
                    ]
                else:
                    # Entry points are objects from project parsing
                    entry_points = [
                        ep for ep in entry_points
                        if search_lower in ep.file_path.lower()
                    ]

            # Apply limit
            if limit:
                entry_points = entry_points[:limit]

            # Helper function to extract entry point data uniformly
            def get_ep_data(ep):
                if isinstance(ep, dict):
                    # From manifest.json
                    return {
                        "file_path": ep.get("filePath", ""),
                        "unique_id": ep.get("uniqueId", ""),
                        "input_count": len(ep.get("input", [])),
                        "output_count": len(ep.get("output", [])),
                        "inputs": ep.get("input", []),
                        "outputs": ep.get("output", [])
                    }
                else:
                    # From project object
                    return {
                        "file_path": ep.file_path,
                        "unique_id": ep.unique_id,
                        "input_count": len(ep.input),
                        "output_count": len(ep.output),
                        "inputs": ep.input,
                        "outputs": ep.output
                    }

            # Output entry points
            if format == "table":
                table = Table(title=f"Entry Points ({len(entry_points)} found)")
                if verbose:
                    table.add_column("Workflow", style="cyan")
                    table.add_column("Unique ID", style="dim", max_width=20)
                    table.add_column("Inputs", style="blue", justify="right")
                    table.add_column("Outputs", style="green", justify="right")
                else:
                    table.add_column("Workflow", style="cyan")
                    table.add_column("Inputs", style="blue", justify="right")
                    table.add_column("Outputs", style="green", justify="right")

                for entry_point in entry_points:
                    ep_data = get_ep_data(entry_point)
                    if verbose:
                        unique_id = ep_data["unique_id"]
                        display_id = unique_id[:20] + "..." if len(unique_id) > 20 else unique_id
                        table.add_row(
                            ep_data["file_path"],
                            display_id,
                            str(ep_data["input_count"]),
                            str(ep_data["output_count"])
                        )
                    else:
                        table.add_row(
                            ep_data["file_path"],
                            str(ep_data["input_count"]),
                            str(ep_data["output_count"])
                        )

                console.print(table)

            elif format == "json":
                data = []
                for ep in entry_points:
                    ep_data = get_ep_data(ep)
                    item = {
                        "workflow": ep_data["file_path"],
                        "inputs": ep_data["input_count"],
                        "outputs": ep_data["output_count"]
                    }
                    if verbose:
                        item.update({
                            "uniqueId": ep_data["unique_id"],
                            "inputDetails": ep_data["inputs"],
                            "outputDetails": ep_data["outputs"]
                        })
                    data.append(item)
                print(jsonlib.dumps({"entry_points": data, "total": len(data)}, indent=2))

            elif format == "csv":
                import sys
                fieldnames = ["workflow", "inputs", "outputs"]
                if verbose:
                    fieldnames.extend(["uniqueId"])

                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                writer.writeheader()

                for entry_point in entry_points:
                    ep_data = get_ep_data(entry_point)
                    row = {
                        "workflow": ep_data["file_path"],
                        "inputs": ep_data["input_count"],
                        "outputs": ep_data["output_count"]
                    }
                    if verbose:
                        row["uniqueId"] = ep_data["unique_id"]
                    writer.writerow(row)

        elif item_type == "orphans":
            if format == "table":
                console.print("[yellow]WARN[/yellow] Orphan detection now available with validation framework!")
                console.print("[dim]Use 'rpax validate orphans' to identify workflows not reachable from entry points[/dim]")
            elif format == "json":
                print(jsonlib.dumps({"orphans": [], "total": 0, "message": "Use 'rpax validate orphans' for orphan detection"}))
            elif format == "csv":
                import sys
                writer = csv.DictWriter(sys.stdout, fieldnames=["message"])
                writer.writeheader()
                writer.writerow({"message": "Use 'rpax validate orphans' for orphan detection"})

        elif item_type == "activities":
            # List available activities from parsed workflows
            try:
                artifacts_path = _resolve_project_artifacts_path(project_path, project, "activities")
                activities_dir = artifacts_path / "activities.tree"

                if not activities_dir.exists():
                    if format == "table":
                        console.print("[yellow]No activities found[/yellow] - run 'rpax parse' first")
                    elif format == "json":
                        print(jsonlib.dumps({"activities": [], "total": 0}))
                    elif format == "csv":
                        import sys
                        writer = csv.DictWriter(sys.stdout, fieldnames=["workflow", "activity_count"])
                        writer.writeheader()
                    return

                # Scan activity files and extract all activities
                activity_files = list(activities_dir.glob("*.json"))
                all_activities = []

                for activity_file in activity_files:
                    try:
                        with open(activity_file, encoding="utf-8") as f:
                            activity_tree = jsonlib.load(f)

                        workflow_id = activity_tree.get("workflowId", activity_file.stem)
                        root_node = activity_tree.get("rootNode", {})

                        # Extract all activities from this workflow
                        workflow_activities = _extract_all_activities(root_node, workflow_id)
                        all_activities.extend(workflow_activities)

                    except Exception as e:
                        console.print(f"[yellow]Warning:[/yellow] Failed to parse {activity_file}: {e}")

                # Apply search and filters
                if search:
                    search_lower = search.lower()
                    all_activities = [a for a in all_activities if
                                    search_lower in a["workflow"].lower() or
                                    search_lower in a["activity_type"].lower() or
                                    search_lower in a["display_name"].lower()]

                if filter_pattern:
                    import fnmatch
                    all_activities = [a for a in all_activities if
                                    fnmatch.fnmatch(a["workflow"], filter_pattern) or
                                    fnmatch.fnmatch(a["activity_type"], filter_pattern)]

                # Sort activities
                sort_key_map = {
                    "name": "display_name",
                    "size": "display_name",  # fallback to display_name
                    "modified": "display_name",  # fallback to display_name
                    "path": "workflow"
                }
                sort_key = sort_key_map.get(sort, "display_name")
                all_activities.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

                # Apply limit
                if limit:
                    all_activities = all_activities[:limit]

                # Output
                if format == "table":
                    table = Table(title=f"Activities ({len(all_activities)} total)")
                    table.add_column("Workflow", style="cyan")
                    table.add_column("Activity Type", style="green")
                    table.add_column("Display Name", style="white")
                    table.add_column("Node ID", style="dim")

                    if verbose:
                        table.add_column("Target/Expression", style="yellow")

                    for activity in all_activities:
                        row = [
                            activity["workflow"],
                            activity["activity_type"],
                            activity["display_name"],
                            activity["node_id"]
                        ]

                        if verbose:
                            extra_info = activity.get("target_workflow") or activity.get("expression", "")
                            if extra_info and len(extra_info) > 50:
                                extra_info = extra_info[:47] + "..."
                            row.append(extra_info)

                        table.add_row(*row)
                    console.print(table)

                elif format == "json":
                    print(jsonlib.dumps({"activities": all_activities, "total": len(all_activities)}, indent=2))

                elif format == "csv":
                    import sys
                    fieldnames = ["workflow", "activity_type", "display_name", "node_id", "target_workflow", "expression"]
                    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                    writer.writeheader()
                    for activity in all_activities:
                        # Flatten for CSV output
                        csv_row = {
                            "workflow": activity["workflow"],
                            "activity_type": activity["activity_type"],
                            "display_name": activity["display_name"],
                            "node_id": activity["node_id"],
                            "target_workflow": activity.get("target_workflow", ""),
                            "expression": activity.get("expression", "")
                        }
                        writer.writerow(csv_row)

            except Exception as e:
                console.print(f"[red]Error:[/red] Failed to list activities: {e}")
                raise typer.Exit(1)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("[dim]Make sure you're in a UiPath project directory with project.json[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _count_activity_nodes(node: dict) -> int:
    """Count total activity nodes in an activity tree."""
    if not node:
        return 0

    count = 1  # Count this node
    children = node.get("children", [])
    for child in children:
        count += _count_activity_nodes(child)
    return count


def _calculate_activity_depth(node: dict) -> int:
    """Calculate maximum depth of an activity tree."""
    if not node:
        return 0

    children = node.get("children", [])
    if not children:
        return 1

    return 1 + max(_calculate_activity_depth(child) for child in children)


def _extract_all_activities(node: dict, workflow_id: str, parent_path: str = "") -> list[dict[str, Any]]:
    """Recursively extract all activities from an activity tree node."""
    if not node:
        return []

    activities = []

    # Extract current activity
    node_id = node.get("nodeId", "")
    activity_type = node.get("activityType", "Unknown")
    display_name = node.get("displayName", activity_type)
    properties = node.get("properties", {})

    # Build hierarchical path
    current_path = f"{parent_path}.{display_name}" if parent_path else display_name

    activity = {
        "workflow": workflow_id,
        "node_id": node_id,
        "activity_type": activity_type,
        "display_name": display_name,
        "path": current_path,
        "parent_id": node.get("parentId"),
        "properties": properties
    }

    # Add special properties for common activity types
    if activity_type == "InvokeWorkflowFile":
        activity["target_workflow"] = properties.get("WorkflowFileName", "")
    elif activity_type in ["Assign", "WriteLine", "LogMessage"]:
        activity["expression"] = properties.get("Text") or properties.get("Message", "")

    activities.append(activity)

    # Recursively extract children
    children = node.get("children", [])
    for child in children:
        child_activities = _extract_all_activities(child, workflow_id, current_path)
        activities.extend(child_activities)

    return activities


@api_expose(
    path="/projects/{project}/validation",
    methods=["GET"],
    tags=["validation"],
    summary="Run validation rules on parser artifacts",
    mcp_resource_type="validation_report"
)
@app.command()
def validate(
    path: Annotated[
        Path,
        typer.Argument(help="Path to artifacts directory or project directory")
    ] = Path("."),
    rule: Annotated[
        str,
        typer.Option("--rule", "-r", help="Specific rule to run: all, missing, cycles, config (default: all)")
    ] = "all",
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table, json, markdown (default: table)")
    ] = "table",
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Configuration file path (default: search for .rpax.json)")
    ] = None,
) -> None:
    """Run validation rules on parser artifacts."""
    valid_rules = ["all", "missing", "cycles", "config"]
    valid_formats = ["table", "json", "markdown"]

    if rule not in valid_rules:
        console.print(f"[red]Error:[/red] Invalid rule '{rule}'. Must be one of: {', '.join(valid_rules)}")
        raise typer.Exit(1)

    if format not in valid_formats:
        console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}")
        raise typer.Exit(1)

    try:
        path = path.resolve()

        # Determine if path is artifacts directory or project directory
        artifacts_dir = None
        if (path / "manifest.json").exists() and (path / "workflows.index.json").exists():
            # Path is artifacts directory
            artifacts_dir = path
            console.print(f"[green]Validating artifacts:[/green] {artifacts_dir}")
        else:
            # Path is project directory, look for default output
            # Try common output locations
            candidates = [
                path / "rpax-output",
                path / ".rpax" / "output",
                path / "output"
            ]

            for candidate in candidates:
                if (candidate / "manifest.json").exists():
                    artifacts_dir = candidate
                    break

            if not artifacts_dir:
                console.print(f"[red]Error:[/red] No artifacts found in {path}")
                console.print("[dim]Run 'rpax parse' first or specify artifacts directory[/dim]")
                raise typer.Exit(1)

            console.print(f"[green]Validating artifacts:[/green] {artifacts_dir}")

        # Load configuration
        rpax_config = load_config(config or path / ".rpax.json")

        # Create validation framework
        framework = ValidationFramework(rpax_config)
        framework.create_default_rules()

        # Run validation
        result = framework.validate(artifacts_dir)

        # Output results
        if format == "json":
            console.print(jsonlib.dumps(result.to_dict(), indent=2))
        elif format == "markdown":
            console.print("# Validation Report")
            console.print(f"**Status:** {result.status.value}")
            console.print(f"**Exit Code:** {result.exit_code}")
            console.print()

            if result.counters:
                console.print("## Counters")
                for key, value in result.counters.items():
                    console.print(f"- {key}: {value}")
                console.print()

            if result.issues:
                console.print("## Issues")
                for issue in result.issues:
                    console.print(f"- **{issue.severity.value.upper()}** {issue.rule}: {issue.message}")
        else:  # table format
            # Status summary
            status_color = "green" if result.status.value == "pass" else "yellow" if result.status.value == "warn" else "red"
            console.print(f"[{status_color}]Validation Status: {result.status.value.upper()}[/{status_color}]")
            console.print(f"Exit Code: {result.exit_code}")

            # Counters table
            if result.counters:
                console.print("\n[blue]Counters:[/blue]")
                counter_table = Table()
                counter_table.add_column("Metric", style="cyan")
                counter_table.add_column("Count", style="white", justify="right")

                for key, value in sorted(result.counters.items()):
                    counter_table.add_row(key.replace("_", " ").title(), str(value))

                console.print(counter_table)

            # Issues table
            if result.issues:
                console.print("\n[blue]Issues Found:[/blue]")
                issues_table = Table()
                issues_table.add_column("Rule", style="cyan")
                issues_table.add_column("Severity", style="white")
                issues_table.add_column("Message", style="white")
                issues_table.add_column("Location", style="dim")

                for issue in result.issues:
                    severity_color = "red" if issue.severity.value == "fail" else "yellow" if issue.severity.value == "warn" else "green"
                    location = ""
                    if issue.artifact:
                        location += issue.artifact
                    if issue.path:
                        location += f" {issue.path}"

                    issues_table.add_row(
                        issue.rule,
                        f"[{severity_color}]{issue.severity.value.upper()}[/{severity_color}]",
                        issue.message,
                        location
                    )

                console.print(issues_table)
            else:
                console.print("\n[green]No issues found![/green]")

        # Exit with appropriate code
        raise typer.Exit(result.exit_code)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_expose(
    path="/projects/{project}/graphs/{graph_type}",
    methods=["GET"],
    tags=["graphs"],
    summary="Generate workflow call graphs and diagrams",
    mcp_resource_type="graph_diagram"
)
@app.command()
def graph(
    graph_type: Annotated[
        str,
        typer.Argument(help="Type of graph: calls, paths, project")
    ] = "calls",
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to artifacts directory or project directory (default: current)")
    ] = Path("."),
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output file path (default: stdout)")
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: mermaid, graphviz (default: mermaid)")
    ] = "mermaid",
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Configuration file path (default: search for .rpax.json)")
    ] = None,
) -> None:
    """Generate workflow call graphs and diagrams."""
    valid_types = ["calls", "paths", "project"]
    valid_formats = ["mermaid", "graphviz"]

    if graph_type not in valid_types:
        console.print(f"[red]Error:[/red] Invalid graph type '{graph_type}'. Must be one of: {', '.join(valid_types)}")
        raise typer.Exit(1)

    if format not in valid_formats:
        console.print(f"[red]Error:[/red] Invalid format '{format}'. Must be one of: {', '.join(valid_formats)}")
        raise typer.Exit(1)

    if format == "graphviz":
        console.print("[yellow]Warning:[/yellow] Graphviz format not yet implemented (planned for v0.2)")
        console.print("[dim]Using Mermaid format instead[/dim]")
        format = "mermaid"

    try:
        path = path.resolve()

        # Determine if path is artifacts directory or project directory
        artifacts_dir = None
        if (path / "manifest.json").exists() and (path / "workflows.index.json").exists():
            # Path is artifacts directory
            artifacts_dir = path
            console.print(f"[green]Generating graph from artifacts:[/green] {artifacts_dir}")
        else:
            # Path is project directory, look for artifacts
            candidates = [
                path / ".rpax-lake",
                path / ".rpax-out",
                path / "output"
            ]

            for candidate in candidates:
                if (candidate / "manifest.json").exists():
                    artifacts_dir = candidate
                    break

            if not artifacts_dir:
                console.print(f"[red]Error:[/red] No artifacts found in {path}")
                console.print("[dim]Run 'rpax parse' first or specify artifacts directory[/dim]")
                raise typer.Exit(1)

            console.print(f"[green]Generating graph from artifacts:[/green] {artifacts_dir}")

        # Load configuration
        rpax_config = load_config(config or path / ".rpax.json")

        # Create graph generator
        generator = GraphGenerator(rpax_config)
        generator.add_renderer(MermaidRenderer())

        # Generate graph specification
        console.print(f"[dim]Generating {graph_type} graph...[/dim]")
        spec = generator.generate_from_artifacts(artifacts_dir, graph_type)
        console.print(f"[green]OK[/green] Graph with {len(spec.nodes)} nodes and {len(spec.edges)} edges")

        # Render graph
        console.print(f"[dim]Rendering with {format} format...[/dim]")
        rendered = generator.render_graph(spec, format)

        # Determine output file
        if out:
            output_file = out.resolve()
        else:
            # Default output based on type and format
            renderer = generator.renderers[format]
            extension = renderer.get_file_extension()
            output_file = artifacts_dir / f"{graph_type}-graph{extension}"

        # Write output
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(rendered)

        console.print(f"[green]Graph generated:[/green] {output_file}")

        # Show some statistics
        if spec.entry_points:
            console.print(f"[blue]Entry points:[/blue] {len(spec.entry_points)}")

        orphaned = spec.get_orphaned_nodes()
        if orphaned:
            console.print(f"[yellow]Orphaned workflows:[/yellow] {len(orphaned)}")

        cycles = spec.detect_cycles()
        if cycles:
            console.print(f"[red]Cycles detected:[/red] {len(cycles)}")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_expose(
    path="/projects/{project}/workflows/{workflow}",
    methods=["GET"],
    tags=["workflows"],
    summary="Show detailed information about a specific workflow",
    mcp_resource_type="workflow_detail"
)
@app.command()
def explain(
    workflow: Annotated[
        str,
        typer.Argument(help="Workflow identifier (ID, filename, or partial path)")
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to lake directory or project directory (default: current)")
    ] = Path("."),
    project: Annotated[
        str,
        typer.Option("--project", help="Project slug (required for multi-project lakes)")
    ] = None,
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Configuration file path (default: search for .rpax.json)")
    ] = None,
    pseudocode: Annotated[
        bool,
        typer.Option("--pseudocode", help="Show pseudocode representation of workflow activities")
    ] = False,
) -> None:
    """Show detailed information about a specific workflow."""
    from rpax.utils.lake import (
        find_lake_directory,
        resolve_project_slug,
        get_project_artifacts_dir,
        MultipleProjectsFoundError,
        ProjectNotFoundError
    )
    
    try:
        path = path.resolve()

        # Find lake directory
        lake_dir = find_lake_directory(path)
        if not lake_dir:
            console.print(f"[red]Error:[/red] No rpax lake found in {path}")
            console.print("[dim]Run 'rpax parse' first or specify lake directory with --path[/dim]")
            raise typer.Exit(1)

        # Resolve project slug
        try:
            project_slug = resolve_project_slug(lake_dir, project)
        except (MultipleProjectsFoundError, ProjectNotFoundError):
            raise typer.Exit(1)

        # Get project artifacts directory
        artifacts_dir = get_project_artifacts_dir(lake_dir, project_slug)
        
        console.print(f"[dim]Using project: {project_slug}[/dim]")

        # Load configuration
        rpax_config = load_config(config or path / ".rpax.json")

        # Create analyzer and formatter
        analyzer = WorkflowAnalyzer(rpax_config)
        formatter = ExplanationFormatter(console)

        # Analyze workflow
        console.print(f"[dim]Analyzing workflow: {workflow}[/dim]")
        try:
            explanation = analyzer.explain_workflow(artifacts_dir, workflow)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")

            # Show available workflows as suggestions
            console.print("\n[dim]Available workflows:[/dim]")
            available = analyzer.list_all_workflows(artifacts_dir)

            if available:
                # Show first 10 matches or similar workflows
                suggestions = []
                workflow_lower = workflow.lower()

                # Find partial matches
                for avail in available:
                    if workflow_lower in avail.lower():
                        suggestions.append(avail)

                if not suggestions:
                    suggestions = available[:10]  # Show first 10 if no matches

                for suggestion in suggestions[:10]:
                    console.print(f"  • {suggestion}")

                if len(available) > 10:
                    console.print(f"  ... and {len(available) - 10} more")
            else:
                console.print("  [dim]No workflows found in artifacts[/dim]")

            raise typer.Exit(1)

        # Format and display explanation
        formatter.format_explanation(explanation)
        
        # Show pseudocode if requested
        if pseudocode:
            console.print("\n[bold]Pseudocode[/bold]")
            try:
                from rpax.pseudocode import PseudocodeGenerator
                from rpax.pseudocode.models import PseudocodeArtifact
                
                # Look for pseudocode artifact
                pseudocode_dir = artifacts_dir / "pseudocode"
                if pseudocode_dir.exists():
                    # Find matching pseudocode file
                    matching_files = list(pseudocode_dir.glob(f"*{workflow}*.json"))
                    
                    if matching_files:
                        pseudocode_file = matching_files[0]
                        
                        # Load and render pseudocode
                        with open(pseudocode_file, encoding="utf-8") as f:
                            artifact_data = jsonlib.load(f)
                        
                        generator = PseudocodeGenerator()
                        artifact = PseudocodeArtifact(**artifact_data)
                        text_output = generator.render_as_text(artifact)
                        
                        console.print(f"[dim]Activities: {artifact.total_activities} | Lines: {artifact.total_lines}[/dim]\n")
                        console.print(text_output)
                    else:
                        console.print("[dim]No pseudocode artifact found for this workflow[/dim]")
                else:
                    console.print("[dim]No pseudocode artifacts found. Run 'rpax parse' to regenerate.[/dim]")
                    
            except Exception as e:
                console.print(f"[red]Error loading pseudocode:[/red] {e}")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_expose(
    path="/schemas/{action}",
    methods=["GET", "POST"],
    tags=["schemas"],
    summary="Generate JSON schemas or validate artifacts against schemas",
    mcp_resource_type="schema_definition"
)
@app.command()
def schema(
    action: Annotated[
        str,
        typer.Argument(help="Action to perform: generate, validate")
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to artifacts directory or output directory (default: current)")
    ] = Path("."),
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output directory for generated schemas (default: current)")
    ] = None,
) -> None:
    """Generate JSON schemas or validate artifacts against schemas."""
    valid_actions = ["generate", "validate"]

    if action not in valid_actions:
        console.print(f"[red]Error:[/red] Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
        raise typer.Exit(1)

    try:
        path = path.resolve()

        if action == "generate":
            # Generate JSON schemas
            console.print("[dim]Generating JSON schemas from Pydantic models...[/dim]")

            generator = SchemaGenerator()
            schemas = generator.generate_all_schemas()

            # Determine output directory
            if out:
                output_dir = out.resolve()
            else:
                output_dir = path / "schemas"

            # Save schemas
            schema_files = generator.save_schemas(output_dir)

            console.print(f"[green]Generated {len(schema_files)} JSON schemas:[/green]")
            for schema_name, schema_file in schema_files.items():
                console.print(f"  • {schema_name}: {schema_file}")

            # Validate schema compliance
            console.print("\n[dim]Validating schema compliance...[/dim]")
            errors = generator.validate_schema_compliance()

            if errors:
                console.print("[yellow]Schema validation warnings:[/yellow]")
                for error in errors:
                    console.print(f"  • {error}")
            else:
                console.print("[green]All schemas are valid![/green]")

        elif action == "validate":
            # Validate artifacts against schemas
            console.print("[dim]Loading schemas and validating artifacts...[/dim]")

            # First generate schemas
            generator = SchemaGenerator()
            schemas = generator.generate_all_schemas()

            # Create validator
            validator = ArtifactValidator(schemas)

            # Determine artifacts directory
            artifacts_dir = None
            if (path / "manifest.json").exists():
                artifacts_dir = path
            else:
                # Look for artifacts in common locations
                candidates = [
                    path / ".rpax-lake",
                    path / ".rpax-out",
                    path / "output"
                ]

                for candidate in candidates:
                    if (candidate / "manifest.json").exists():
                        artifacts_dir = candidate
                        break

            if not artifacts_dir:
                console.print(f"[red]Error:[/red] No artifacts found in {path}")
                console.print("[dim]Run 'rpax parse' first or specify artifacts directory[/dim]")
                raise typer.Exit(1)

            console.print(f"[green]Validating artifacts:[/green] {artifacts_dir}")

            # Validate all artifacts
            results = validator.validate_all_artifacts(artifacts_dir)

            # Display results
            total_errors = sum(len(errors) for errors in results.values())

            if total_errors == 0:
                console.print("[green]All artifacts are valid![/green]")
            else:
                console.print(f"[yellow]Found {total_errors} validation issues:[/yellow]")

                for artifact_type, errors in results.items():
                    if errors:
                        console.print(f"\n[red]{artifact_type}:[/red]")
                        for error in errors[:10]:  # Show first 10 errors
                            console.print(f"  • {error}")

                        if len(errors) > 10:
                            console.print(f"  ... and {len(errors) - 10} more errors")

            # Exit with error code if validation failed
            if validator.has_validation_errors(results):
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_expose(enabled=False)  # CLI-only: help documentation
@app.command()
def help() -> None:
    """Show detailed help information."""
    console.print(f"[bold]{__description__}[/bold]")
    console.print(f"Version: {__version__}")
    console.print()

    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("parse", "Parse UiPath project -> JSON artifacts")
    table.add_row("list", "Enumerate project elements (workflows, roots, orphans)")
    table.add_row("validate", "Run validation rules on parser artifacts")
    table.add_row("graph", "Generate workflow call graphs and diagrams")
    table.add_row("explain", "Show detailed information about a specific workflow")
    table.add_row("pseudocode", "Show pseudocode representation of workflow activities")
    table.add_row("schema", "Generate JSON schemas or validate artifacts against schemas")
    table.add_row("activities", "Access workflow activity trees, control flow, and resources")
    table.add_row("clear", "Clear lake data with safety guardrails (CLI-only)")
    table.add_row("help", "Show this help information")

    console.print(table)
    console.print()
    console.print("[dim]More commands available in future versions:[/dim]")
    console.print("[dim]  - diff      - Compare scans for PR impact analysis[/dim]")
    console.print("[dim]  - summarize - Generate LLM-friendly project outlines[/dim]")


@api_expose(
    path="/projects/{project}/workflows/{workflow}/activities/{action}",
    methods=["GET"],
    tags=["activities"],
    summary="Access workflow activity trees, control flow, and resource references",
    mcp_resource_type="activity_data"
)
@app.command()
def activities(
    action: Annotated[
        str,
        typer.Argument(help="Action to perform: tree, flow, resources, metrics, instances")
    ],
    workflow: Annotated[
        str | None,
        typer.Argument(help="Workflow name (without .xaml)")
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to artifacts directory or lake directory (default: .rpax-lake)")
    ] = Path(".rpax-lake"),
    project: Annotated[
        str | None,
        typer.Option("--project", help="Project slug for multi-project lakes (optional)")
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json, table (default: json)")
    ] = "json",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed information and metadata (default: False)")
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Limit number of results shown (default: no limit)")
    ] = None,
) -> None:
    """Access workflow activity trees, control flow, and resource references.
    
    Actions:
    - tree: Show activity tree for a workflow
    - flow: Show control flow edges for a workflow  
    - resources: Show resource references for a workflow
    - metrics: Show calculated metrics for a workflow or all workflows
    - instances: Show activity instances with business logic for a workflow
    """
    try:
        project_path = path.resolve()

        # Check for multi-project or single-project structure
        if (project_path / "projects.json").exists():
            # Multi-project lake - use project resolution logic
            artifacts_path = _resolve_project_artifacts_path(project_path, project, "activities")
        elif (project_path / "manifest.json").exists():
            # Single-project directory - use directory directly
            artifacts_path = project_path
        else:
            console.print(f"[red]Error:[/red] No manifest.json or projects.json found in {project_path}")
            console.print("[dim]Run 'rpax parse' first or specify correct artifacts directory[/dim]")
            raise typer.Exit(1)

        valid_actions = ["tree", "flow", "refs", "metrics", "instances"]
        if action not in valid_actions:
            console.print(f"[red]Error:[/red] Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
            raise typer.Exit(1)

        if action in ["tree", "flow", "refs", "instances"] and not workflow:
            console.print(f"[red]Error:[/red] Workflow name required for '{action}' action")
            console.print("[dim]Example: rpax activities tree PathKeeper --path .rpax-lake[/dim]")
            raise typer.Exit(1)

        if action == "tree":
            _show_activity_tree(artifacts_path, workflow, format, verbose)
        elif action == "flow":
            _show_control_flow(artifacts_path, workflow, format, verbose)
        elif action == "refs":
            _show_refs(artifacts_path, workflow, format, verbose)
        elif action == "metrics":
            _show_metrics(artifacts_path, workflow, format, verbose, limit)
        elif action == "instances":
            _show_activity_instances(artifacts_path, workflow, format, verbose, limit)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _show_activity_tree(artifacts_path: Path, workflow: str, format: str, verbose: bool) -> None:
    """Show activity tree for a workflow."""
    tree_file = artifacts_path / "activities.tree" / f"{workflow}.json"

    if not tree_file.exists():
        console.print(f"[red]Error:[/red] Activity tree not found for {workflow}")
        console.print(f"[dim]Expected: {tree_file}[/dim]")
        raise typer.Exit(1)

    with open(tree_file, encoding="utf-8") as f:
        tree_data = jsonlib.load(f)

    if format == "json":
        print(jsonlib.dumps(tree_data, indent=2))
    elif format == "table":
        _display_activity_tree_table(tree_data, verbose)
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for activity tree")
        raise typer.Exit(1)


def _show_control_flow(artifacts_path: Path, workflow: str, format: str, verbose: bool) -> None:
    """Show control flow for a workflow."""
    flow_file = artifacts_path / "activities.cfg" / f"{workflow}.jsonl"

    if not flow_file.exists():
        console.print(f"[red]Error:[/red] Control flow not found for {workflow}")
        console.print(f"[dim]Expected: {flow_file}[/dim]")
        raise typer.Exit(1)

    edges = []
    with open(flow_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                edges.append(jsonlib.loads(line))

    if format == "json":
        print(jsonlib.dumps({"workflow": workflow, "edges": edges}, indent=2))
    elif format == "table":
        _display_control_flow_table(workflow, edges, verbose)
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for control flow")
        raise typer.Exit(1)


def _show_refs(artifacts_path: Path, workflow: str, format: str, verbose: bool) -> None:
    """Show references for a workflow."""
    refs_file = artifacts_path / "activities.refs" / f"{workflow}.json"

    if not refs_file.exists():
        console.print(f"[red]Error:[/red] References not found for {workflow}")
        console.print(f"[dim]Expected: {refs_file}[/dim]")
        raise typer.Exit(1)

    with open(refs_file, encoding="utf-8") as f:
        refs_data = jsonlib.load(f)

    if format == "json":
        print(jsonlib.dumps(refs_data, indent=2))
    elif format == "table":
        _display_resources_table(refs_data, verbose)
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for resources")
        raise typer.Exit(1)


def _show_metrics(artifacts_path: Path, workflow: str | None, format: str, verbose: bool, limit: int | None) -> None:
    """Show metrics for a workflow or all workflows."""
    if workflow:
        # Show metrics for specific workflow
        metrics_file = artifacts_path / "metrics" / f"{workflow}.json"

        if not metrics_file.exists():
            console.print(f"[red]Error:[/red] Metrics not found for {workflow}")
            console.print(f"[dim]Expected: {metrics_file}[/dim]")
            raise typer.Exit(1)

        with open(metrics_file, encoding="utf-8") as f:
            metrics_data = jsonlib.load(f)

        if format == "json":
            print(jsonlib.dumps(metrics_data, indent=2))
        elif format == "table":
            _display_single_metrics_table(metrics_data, verbose)
    else:
        # Show metrics for all workflows
        metrics_dir = artifacts_path / "metrics"
        if not metrics_dir.exists():
            console.print("[red]Error:[/red] No metrics directory found")
            raise typer.Exit(1)

        all_metrics = []
        for metrics_file in metrics_dir.glob("*.json"):
            try:
                with open(metrics_file, encoding="utf-8") as f:
                    metrics_data = jsonlib.load(f)
                all_metrics.append(metrics_data)
            except Exception as e:
                console.print(f"[yellow]WARN[/yellow] Failed to read {metrics_file}: {e}")

        if limit:
            all_metrics = all_metrics[:limit]

        if format == "json":
            print(jsonlib.dumps({"metrics": all_metrics, "total": len(all_metrics)}, indent=2))
        elif format == "table":
            _display_all_metrics_table(all_metrics, verbose)


def _show_activity_instances(artifacts_path: Path, workflow: str, format: str, verbose: bool, limit: int | None) -> None:
    """Show activity instances for a workflow."""
    instances_file = artifacts_path / "activities.instances" / f"{workflow}.json"

    if not instances_file.exists():
        console.print(f"[red]Error:[/red] Activity instances not found for {workflow}")
        console.print(f"[dim]Expected: {instances_file}[/dim]")
        raise typer.Exit(1)

    with open(instances_file, encoding="utf-8") as f:
        instances_data = jsonlib.load(f)

    if limit and isinstance(instances_data, list):
        instances_data = instances_data[:limit]

    if format == "json":
        print(jsonlib.dumps(instances_data, indent=2))
    elif format == "table":
        _display_activity_instances_table(instances_data, verbose)
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for activity instances")
        raise typer.Exit(1)


def _display_activity_instances_table(instances_data: dict[str, Any] | list[dict[str, Any]], verbose: bool) -> None:
    """Display activity instances in table format."""
    if isinstance(instances_data, dict):
        # Single workflow instances
        workflow_id = instances_data.get("workflow_id", "Unknown")
        instances = instances_data.get("instances", [])
        console.print(f"[green]Activity Instances:[/green] {workflow_id}")
        console.print(f"[dim]Total Activities:[/dim] {len(instances)}")
        console.print()
    else:
        # List of instances
        instances = instances_data
        console.print(f"[green]Activity Instances[/green]")
        console.print(f"[dim]Total Activities:[/dim] {len(instances)}")
        console.print()

    # Create table
    table = Table(title="Activity Instances")
    table.add_column("Activity ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="yellow")
    table.add_column("Arguments", style="green")
    table.add_column("Expressions", style="magenta")
    
    if verbose:
        table.add_column("Variables", style="blue")
        table.add_column("Config", style="dim")

    for instance in instances:
        activity_id = instance.get("activity_id", "")
        # Show short form of activity ID
        if "#" in activity_id:
            short_id = activity_id.split("#")[-1][:12] + "..."
        else:
            short_id = activity_id[:15] + "..."

        activity_type = instance.get("activity_type", "Unknown")
        arguments = instance.get("arguments", {})
        expressions = instance.get("expressions", [])
        variables = instance.get("variables_referenced", [])
        config = instance.get("configuration", {})

        args_summary = f"{len(arguments)} args" if arguments else "no args"
        expr_summary = f"{len(expressions)} exprs" if expressions else "no exprs"

        row = [short_id, activity_type, args_summary, expr_summary]
        
        if verbose:
            vars_summary = f"{len(variables)} vars" if variables else "no vars"
            config_summary = f"{len(config)} configs" if config else "no config"
            row.extend([vars_summary, config_summary])

        table.add_row(*row)

    console.print(table)


def _display_activity_tree_table(tree_data: dict[str, Any], verbose: bool) -> None:
    """Display activity tree in table format."""
    console.print(f"[green]Activity Tree:[/green] {tree_data['workflowId']}")
    console.print(f"[dim]Content Hash:[/dim] {tree_data['contentHash'][:16]}...")
    console.print(f"[dim]Variables:[/dim] {len(tree_data.get('variables', []))}")
    console.print(f"[dim]Arguments:[/dim] {len(tree_data.get('arguments', []))}")
    console.print()

    # Display tree structure
    def display_node(node, indent=0):
        indent_str = "  " * indent
        activity_type = node.get("activityType", "Unknown")
        display_name = node.get("displayName", activity_type)

        if verbose:
            console.print(f"{indent_str}+- {display_name} [{activity_type}]")
            if node.get("properties"):
                console.print(f"{indent_str}   Properties: {len(node['properties'])}")
            if node.get("arguments"):
                console.print(f"{indent_str}   Arguments: {len(node['arguments'])}")
        else:
            console.print(f"{indent_str}+- {display_name}")

        for child in node.get("children", []):
            display_node(child, indent + 1)

    root_node = tree_data.get("rootNode", {})
    display_node(root_node)


def _display_control_flow_table(workflow: str, edges: list[dict[str, Any]], verbose: bool) -> None:
    """Display control flow in table format."""
    table = Table(title=f"Control Flow: {workflow} ({len(edges)} edges)")
    table.add_column("From", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("To", style="cyan")

    if verbose:
        table.add_column("Condition", style="dim")

    for edge in edges:
        row = [
            edge.get("from", ""),
            edge.get("type", ""),
            edge.get("to", "")
        ]

        if verbose:
            row.append(edge.get("condition", "") or "")

        table.add_row(*row)

    console.print(table)


def _display_resources_table(refs_data: dict[str, Any], verbose: bool) -> None:
    """Display resource references in table format."""
    references = refs_data.get("references", [])
    table = Table(title=f"Resource References: {refs_data['workflowId']} ({len(references)} references)")
    table.add_column("Type", style="yellow")
    table.add_column("Name", style="cyan")
    table.add_column("Value", style="white")

    if verbose:
        table.add_column("Node ID", style="dim")
        table.add_column("Dynamic", style="red")

    for ref in references:
        row = [
            ref.get("type", ""),
            ref.get("name", ""),
            ref.get("value", "")[:50] + ("..." if len(ref.get("value", "")) > 50 else "")
        ]

        if verbose:
            row.extend([
                ref.get("nodeId", ""),
                "Yes" if ref.get("isDynamic") else "No"
            ])

        table.add_row(*row)

    console.print(table)


def _display_single_metrics_table(metrics_data: dict[str, Any], verbose: bool) -> None:
    """Display metrics for a single workflow in table format."""
    console.print(f"[green]Metrics:[/green] {metrics_data['workflowId']}")
    console.print(f"Total Nodes: {metrics_data.get('totalNodes', 0)}")
    console.print(f"Max Depth: {metrics_data.get('maxDepth', 0)}")
    console.print(f"Loops: {metrics_data.get('loopCount', 0)}")
    console.print(f"Invokes: {metrics_data.get('invokeCount', 0)}")
    console.print(f"Logs: {metrics_data.get('logCount', 0)}")
    console.print(f"Try/Catch: {metrics_data.get('tryCatchCount', 0)}")
    console.print(f"Selectors: {metrics_data.get('selectorCount', 0)}")

    if verbose:
        activity_types = metrics_data.get("activityTypes", {})
        if activity_types:
            console.print("\n[dim]Activity Types:[/dim]")
            for activity_type, count in sorted(activity_types.items()):
                console.print(f"  {activity_type}: {count}")


def _display_all_metrics_table(all_metrics: list[dict[str, Any]], verbose: bool) -> None:
    """Display metrics for all workflows in table format."""
    table = Table(title=f"Workflow Metrics ({len(all_metrics)} workflows)")
    table.add_column("Workflow", style="cyan")
    table.add_column("Nodes", style="white", justify="right")
    table.add_column("Depth", style="white", justify="right")
    table.add_column("Loops", style="yellow", justify="right")
    table.add_column("Invokes", style="green", justify="right")

    if verbose:
        table.add_column("Logs", style="blue", justify="right")
        table.add_column("Try/Catch", style="red", justify="right")
        table.add_column("Selectors", style="magenta", justify="right")

    for metrics in all_metrics:
        row = [
            metrics.get("workflowId", "Unknown"),
            str(metrics.get("totalNodes", 0)),
            str(metrics.get("maxDepth", 0)),
            str(metrics.get("loopCount", 0)),
            str(metrics.get("invokeCount", 0))
        ]

        if verbose:
            row.extend([
                str(metrics.get("logCount", 0)),
                str(metrics.get("tryCatchCount", 0)),
                str(metrics.get("selectorCount", 0))
            ])

        table.add_row(*row)

    console.print(table)


@api_expose(
    path="/projects",
    methods=["GET"],
    tags=["projects"],
    summary="List all projects in the rpax lake",
    mcp_resource_type="project_list"
)
@app.command()
def projects(
    path: Annotated[Path, typer.Argument(help="Path to rpax lake directory")] = Path(".rpax-lake"),
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, csv (default: table)")] = "table",
    search: Annotated[str | None, typer.Option("--search", "-s", help="Search projects by name or slug")] = None,
    limit: Annotated[int | None, typer.Option("--limit", "-l", help="Limit number of results")] = None,
) -> None:
    """List all projects in the rpax lake."""
    try:
        project_path = path.resolve()
        
        # Check for projects.json
        projects_file = project_path / "projects.json"
        if not projects_file.exists():
            console.print(f"[red]Error:[/red] No projects.json found in {project_path}")
            console.print("[dim]This doesn't appear to be a multi-project lake[/dim]")
            raise typer.Exit(1)
        
        # Load projects index
        with open(projects_file, encoding="utf-8") as f:
            index_data = jsonlib.load(f)
        
        projects = index_data.get("projects", [])
        if not projects:
            if format == "table":
                console.print("[dim]No projects found in lake[/dim]")
            elif format == "json":
                print(jsonlib.dumps({"projects": [], "total": 0}))
            return
        
        # Filter by search term
        if search:
            search_lower = search.lower()
            projects = [
                p for p in projects 
                if search_lower in p.get("name", "").lower() 
                or search_lower in p.get("slug", "").lower()
            ]
        
        # Apply limit
        if limit:
            projects = projects[:limit]
        
        # Output results
        if format == "table":
            from rich.table import Table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan")
            table.add_column("Slug", style="green") 
            table.add_column("Type", style="blue")
            table.add_column("Workflows", justify="right", style="yellow")
            table.add_column("Last Updated", style="dim")
            
            for project in projects:
                table.add_row(
                    project.get("name", ""),
                    project.get("slug", ""),
                    project.get("type", ""),
                    str(project.get("totalWorkflows", 0)),
                    project.get("lastUpdated", "")
                )
            
            console.print(table)
            console.print(f"\n[dim]Total: {len(projects)} project(s)[/dim]")
            
        elif format == "json":
            print(jsonlib.dumps({
                "projects": projects,
                "total": len(projects)
            }, indent=2))
            
        elif format == "csv":
            import sys
            writer = csv.DictWriter(
                sys.stdout, 
                fieldnames=["name", "slug", "type", "totalWorkflows", "lastUpdated"]
            )
            writer.writeheader()
            for project in projects:
                writer.writerow({
                    "name": project.get("name", ""),
                    "slug": project.get("slug", ""),
                    "type": project.get("type", ""),
                    "totalWorkflows": project.get("totalWorkflows", 0),
                    "lastUpdated": project.get("lastUpdated", "")
                })
        
    except Exception as e:
        console.print(f"[red]Error listing projects:[/red] {e}")
        raise typer.Exit(1)


@api_expose(enabled=False)  # CLI-only: destructive operations
@app.command()
def clear(
    scope: Annotated[
        str,
        typer.Argument(help="Clear scope: lake, project, artifacts")
    ] = "artifacts",
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Lake directory path")
    ] = Path(".rpax-lake"),
    project: Annotated[
        str | None,
        typer.Option("--project", help="Specific project slug to clear (required for 'project' scope)")
    ] = None,
    confirm: Annotated[
        bool,
        typer.Option("--confirm", help="Actually perform deletion (default: dry-run mode)")
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip interactive confirmation prompts")
    ] = False,
) -> None:
    """Clear rpax lake data with strong safety guardrails.
    
    SCOPES:
      artifacts - Clear generated artifacts, preserve original files (SAFEST)
      project   - Clear all data for specific project (requires --project)
      lake      - Clear entire lake directory (DESTRUCTIVE)
    
    SAFETY FEATURES:
      - Dry-run by default (use --confirm to execute)
      - Multiple confirmation prompts 
      - Size warnings for large deletions
      - Project validation and existence checks
    
    WARNING: This command is CLI-only and never exposed via API or MCP.
    """
    # Validate scope
    valid_scopes = ["artifacts", "project", "lake"]
    if scope not in valid_scopes:
        console.print(f"[red]Error:[/red] Invalid scope '{scope}'. Valid options: {', '.join(valid_scopes)}")
        raise typer.Exit(1)

    # Validate lake directory exists
    if not path.exists():
        console.print(f"[red]Error:[/red] Lake directory does not exist: {path}")
        raise typer.Exit(1)

    if not path.is_dir():
        console.print(f"[red]Error:[/red] Path is not a directory: {path}")
        raise typer.Exit(1)

    # Scope-specific validation
    if scope == "project":
        if not project:
            console.print("[red]Error:[/red] --project is required when scope is 'project'")
            raise typer.Exit(1)

        project_dir = path / project
        if not project_dir.exists():
            console.print(f"[red]Error:[/red] Project '{project}' not found in lake")
            console.print(f"[dim]Expected: {project_dir}[/dim]")
            raise typer.Exit(1)

    # Calculate deletion scope and size
    targets_to_delete = []
    total_size = 0

    if scope == "artifacts":
        # Clear artifacts but preserve project structure and projects.json
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # This is a project directory - clear its contents
                for artifact in item.iterdir():
                    if artifact.name != "project.json":  # Preserve original project.json if copied
                        targets_to_delete.append(artifact)
                        if artifact.is_file():
                            total_size += artifact.stat().st_size
                        elif artifact.is_dir():
                            total_size += sum(f.stat().st_size for f in artifact.rglob("*") if f.is_file())
            elif item.is_file() and item.name != "projects.json":
                # This is a root-level artifact file - clear it but preserve projects.json
                targets_to_delete.append(item)
                total_size += item.stat().st_size

    elif scope == "project":
        # Clear entire project directory
        project_dir = path / project
        targets_to_delete.append(project_dir)
        if project_dir.exists():
            total_size = sum(f.stat().st_size for f in project_dir.rglob("*") if f.is_file())

    elif scope == "lake":
        # Clear entire lake directory contents
        for item in path.iterdir():
            targets_to_delete.append(item)
            if item.is_file():
                total_size += item.stat().st_size
            elif item.is_dir():
                total_size += sum(f.stat().st_size for f in item.rglob("*") if f.is_file())

    # Display scope summary
    console.print("\n[bold]Clear Operation Summary[/bold]")
    console.print(f"Scope: [cyan]{scope}[/cyan]")
    console.print(f"Lake Path: [dim]{path}[/dim]")
    if scope == "project":
        console.print(f"Project: [yellow]{project}[/yellow]")
    console.print(f"Items to delete: [red]{len(targets_to_delete)}[/red]")
    console.print(f"Total size: [red]{_format_size(total_size)}[/red]")

    if not targets_to_delete:
        console.print(f"\n[green]Nothing to delete in scope '{scope}'[/green]")
        return

    # Show what would be deleted (first 10 items)
    console.print("\n[bold]Items to be deleted:[/bold]")
    for i, target in enumerate(targets_to_delete[:10]):
        item_type = "DIR " if target.is_dir() else "FILE"
        console.print(f"  [dim]{item_type}[/dim] {target.relative_to(path)}")

    if len(targets_to_delete) > 10:
        console.print(f"  [dim]... and {len(targets_to_delete) - 10} more items[/dim]")

    # Dry-run mode (default)
    if not confirm:
        console.print("\n[yellow]DRY RUN MODE[/yellow] - No files will be deleted")
        console.print("Use --confirm to actually perform deletion")
        return

    # Size warning for large deletions
    if total_size > 100 * 1024 * 1024:  # 100MB
        console.print(f"\n[bold red]WARNING:[/bold red] Large deletion detected ({_format_size(total_size)})")
        console.print("This operation will delete significant data.")

    # Interactive confirmations (unless --force)
    if not force:
        # First confirmation
        confirm_scope = typer.confirm(f"Are you sure you want to clear scope '{scope}'?")
        if not confirm_scope:
            console.print("[green]Operation cancelled[/green]")
            return

        # Second confirmation for destructive operations
        if scope in ["project", "lake"]:
            confirm_destructive = typer.confirm(f"This will permanently delete {len(targets_to_delete)} items. Continue?")
            if not confirm_destructive:
                console.print("[green]Operation cancelled[/green]")
                return

        # Final confirmation with exact scope name
        final_confirm = typer.confirm(f"Type 'yes' to confirm deletion of scope '{scope}'", default=False)
        if not final_confirm:
            console.print("[green]Operation cancelled[/green]")
            return

    # Perform deletion
    console.print("\n[bold]Executing deletion...[/bold]")
    import shutil
    deleted_count = 0
    failed_count = 0

    for target in targets_to_delete:
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            deleted_count += 1
            console.print(f"[green]OK[/green] Deleted {target.relative_to(path)}")
        except Exception as e:
            failed_count += 1
            console.print(f"[red]FAIL[/red] Failed to delete {target.relative_to(path)}: {e}")

    # Summary
    console.print("\n[bold]Deletion Complete[/bold]")
    console.print(f"Deleted: [green]{deleted_count}[/green] items")
    if failed_count > 0:
        console.print(f"Failed: [red]{failed_count}[/red] items")
        raise typer.Exit(1)
    else:
        console.print("[green]All items successfully deleted[/green]")


@api_expose(
    path="/projects/{project}/workflows/{workflow}/pseudocode",
    methods=["GET"],
    tags=["analysis"],
    summary="Show pseudocode representation of workflow activities",
    mcp_resource_type="pseudocode_text"
)
@app.command()
def pseudocode(
    workflow: Annotated[
        str,
        typer.Argument(help="Workflow identifier (ID, filename, or partial path). Use --all to show all workflows.")
    ] = None,
    path: Annotated[
        str,
        typer.Option(
            "-p", "--path",
            help="Path to lake directory (default: .rpax-lake)"
        )
    ] = ".rpax-lake",
    project: Annotated[
        str,
        typer.Option(help="Project slug for multi-project lakes (optional)")
    ] = None,
    format_type: Annotated[
        str,
        typer.Option(
            "-f", "--format",
            help="Output format: text, json (default: text)"
        )
    ] = "text",
    all_workflows: Annotated[
        bool,
        typer.Option(
            "--all", 
            help="Show pseudocode for all workflows in the project"
        )
    ] = False,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive", "-r",
            help="Recursively expand InvokeWorkflowFile activities to show complete call tree"
        )
    ] = False,
) -> None:
    """Show pseudocode representation of workflow activities.
    
    Generate human-readable pseudocode showing the logical flow of activities
    in a UiPath workflow using the gist format:
    
    - [DisplayName] Tag (Path: Activity/Sequence/...)
    
    Examples:
        rpax pseudocode Main.xaml
        rpax pseudocode Calculator --project my-calc-abcd1234  
        rpax pseudocode VerifyConnection --format json
        rpax pseudocode --all                 # Show all workflows
        rpax pseudocode Main.xaml --recursive # Show complete call tree
    """
    try:
        # Import here to avoid circular imports
        from rpax.pseudocode import PseudocodeGenerator
        
        # Validate arguments
        if not all_workflows and not workflow:
            console.print("[red]Error:[/red] Must specify either a workflow name or use --all flag")
            raise typer.Exit(1)
        
        if all_workflows and workflow:
            console.print("[red]Error:[/red] Cannot specify both workflow name and --all flag")
            raise typer.Exit(1)
        
        # Resolve project artifacts path
        artifacts_path = _resolve_project_artifacts_path(
            Path(path), project, command_context="pseudocode"
        )
        
        # Find workflow artifact file
        pseudocode_dir = artifacts_path / "pseudocode"
        if not pseudocode_dir.exists():
            console.print(f"[red]Error:[/red] No pseudocode artifacts found in {pseudocode_dir}")
            console.print("[dim]Run 'rpax parse' to generate pseudocode artifacts[/dim]")
            raise typer.Exit(1)
        
        if all_workflows:
            # Show pseudocode for all workflows (including nested directories)
            all_pseudocode_files = list(pseudocode_dir.rglob("*.json"))
            # Exclude index file
            pseudocode_files = [f for f in all_pseudocode_files if f.name != "index.json"]
            
            if not pseudocode_files:
                console.print("[red]Error:[/red] No pseudocode files found")
                raise typer.Exit(1)
            
            # Sort files for consistent output
            pseudocode_files.sort(key=lambda f: f.stem)
            
            generator = PseudocodeGenerator()
            from rpax.pseudocode.models import PseudocodeArtifact
            
            if format_type == "json":
                # Output all artifacts as JSON array
                all_artifacts = []
                for pfile in pseudocode_files:
                    with open(pfile, encoding="utf-8") as f:
                        artifact_data = jsonlib.load(f)
                    all_artifacts.append(artifact_data)
                console.print(jsonlib.dumps(all_artifacts, indent=2))
            elif format_type == "text":
                console.print(f"[bold]Pseudocode for All Workflows ({len(pseudocode_files)} total)[/bold]\n")
                
                for i, pfile in enumerate(pseudocode_files):
                    with open(pfile, encoding="utf-8") as f:
                        artifact_data = jsonlib.load(f)
                    
                    artifact = PseudocodeArtifact(**artifact_data)
                    
                    if recursive:
                        text_output = _render_recursive_pseudocode(artifact, pseudocode_dir, generator)
                    else:
                        text_output = generator.render_as_text(artifact)
                    
                    if i > 0:
                        console.print("\n" + "="*50 + "\n")
                    
                    console.print(f"[bold cyan]{artifact.workflow_id}[/bold cyan]")
                    console.print(f"[dim]Activities: {artifact.total_activities} | Lines: {artifact.total_lines}[/dim]\n")
                    console.print(text_output)
            else:
                console.print(f"[red]Error:[/red] Unknown format '{format_type}'. Use 'text' or 'json'.")
                raise typer.Exit(1)
                
        else:
            # Show pseudocode for specific workflow
            matching_files = list(pseudocode_dir.glob(f"*{workflow}*.json"))
            
            if not matching_files:
                console.print(f"[red]Error:[/red] No pseudocode found for workflow '{workflow}'")
                console.print(f"[dim]Available workflows:[/dim]")
                for file in pseudocode_dir.glob("*.json"):
                    if file.name != "index.json":
                        console.print(f"  - {file.stem}")
                raise typer.Exit(1)
            
            if len(matching_files) > 1:
                console.print(f"[red]Error:[/red] Ambiguous workflow '{workflow}' matches multiple files:")
                for file in matching_files:
                    console.print(f"  - {file.stem}")
                raise typer.Exit(1)
            
            pseudocode_file = matching_files[0]
            
            # Load pseudocode artifact
            with open(pseudocode_file, encoding="utf-8") as f:
                artifact_data = jsonlib.load(f)
            
            if format_type == "json":
                # Output raw JSON
                console.print(jsonlib.dumps(artifact_data, indent=2))
            elif format_type == "text":
                # Generate formatted text output
                generator = PseudocodeGenerator()
                from rpax.pseudocode.models import PseudocodeArtifact
                
                artifact = PseudocodeArtifact(**artifact_data)
                
                if recursive:
                    text_output = _render_recursive_pseudocode(artifact, pseudocode_dir, generator)
                else:
                    text_output = generator.render_as_text(artifact)
                
                console.print(f"\n[bold]Pseudocode for {artifact.workflow_id}[/bold]")
                console.print(f"[dim]Activities: {artifact.total_activities} | Lines: {artifact.total_lines}[/dim]\n")
                console.print(text_output)
            else:
                console.print(f"[red]Error:[/red] Unknown format '{format_type}'. Use 'text' or 'json'.")
                raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _render_recursive_pseudocode(artifact, pseudocode_dir, generator, visited=None, max_depth=3):
    """Render pseudocode with recursive expansion of InvokeWorkflowFile activities.
    
    This function processes the basic pseudocode text and expands InvokeWorkflowFile 
    activities by inserting the content of invoked workflows inline.
    """
    if visited is None:
        visited = set()
    
    if max_depth <= 0:
        return generator.render_as_text(artifact)
    
    # Prevent infinite recursion
    if artifact.workflow_id in visited:
        return f"[RECURSIVE: {artifact.workflow_id}] (already expanded above)"
    
    visited.add(artifact.workflow_id)
    
    try:
        # Get the basic text output (without nested children processing)
        text_output = generator.render_as_text(artifact)
        lines = text_output.split('\n')
        result_lines = []
        
        import re
        
        for line in lines:
            if not line.strip():
                continue
                
            result_lines.append(line)
            
            # Check if this line contains an InvokeWorkflowFile
            if ("InvokeWorkflowFile" in line and ".xaml" in line and 
                "Invoke Workflow File" in line):
                
                # Extract workflow path from parentheses in format: (Framework\InitAllSettings.xaml)
                workflow_match = None
                pattern = r'\(([^)]+)\.xaml\)'
                match = re.search(pattern, line)
                
                if match:
                    workflow_path = match.group(1)
                    # Convert backslashes to forward slashes for file system compatibility
                    workflow_match = workflow_path.replace('\\', '/')
                
                if workflow_match:
                    # Try to find the invoked workflow
                    invoked_artifact = _load_invoked_workflow_pseudocode(workflow_match, pseudocode_dir)
                    
                    if invoked_artifact and invoked_artifact.workflow_id not in visited:
                        # Get current line indentation
                        current_indent = len(line) - len(line.lstrip())
                        extra_indent_spaces = current_indent + 4
                        extra_indent = " " * extra_indent_spaces
                        
                        # Recursively expand the invoked workflow (with depth limit)
                        nested_text = _render_recursive_pseudocode(
                            invoked_artifact,
                            pseudocode_dir, 
                            generator,
                            visited.copy(),  # Use copy to allow same workflow in different branches
                            max_depth - 1
                        )
                        
                        if nested_text.strip():
                            # Add each line with proper indentation
                            for nested_line in nested_text.split('\n'):
                                if nested_line.strip():
                                    clean_line = nested_line.lstrip()
                                    indented_line = extra_indent + clean_line
                                    result_lines.append(indented_line)
        
        return "\n".join(result_lines)
    
    finally:
        visited.discard(artifact.workflow_id)  # Remove from visited set

def _extract_workflow_from_display_name(display_name: str) -> str:
    """Extract workflow filename from InvokeWorkflowFile display name.
    
    Examples:
        'Process\\Initialization.xaml - Invoke Workflow File' -> 'Process/Initialization'
        'AdditionOf2Terms.xaml - Invoke Workflow File' -> 'AdditionOf2Terms'  
    """
    if not display_name or '.xaml' not in display_name:
        return None
        
    # Extract the .xaml filename part
    xaml_part = display_name.split(' - ')[0].strip()
    
    # Remove .xaml extension and normalize path separators
    workflow_name = xaml_part.replace('.xaml', '').replace('\\', '/')
    
    return workflow_name

def _load_invoked_workflow_pseudocode(workflow_name: str, pseudocode_dir):
    """Load pseudocode artifact for an invoked workflow.
    
    Args:
        workflow_name: Workflow name like 'Process/Initialization' or 'AdditionOf2Terms'
        pseudocode_dir: Directory containing pseudocode artifacts
        
    Returns:
        PseudocodeArtifact or None if not found
    """
    from rpax.pseudocode.models import PseudocodeArtifact
    
    # Try various possible file patterns
    possible_patterns = [
        f"{workflow_name}.xaml.json",           # Direct match
        f"*{workflow_name.split('/')[-1]}*.json",  # Match just the filename part  
    ]
    
    for pattern in possible_patterns:
        matching_files = list(pseudocode_dir.rglob(pattern))
        
        if matching_files:
            # Take the first match
            pseudocode_file = matching_files[0]
            
            try:
                with open(pseudocode_file, encoding="utf-8") as f:
                    artifact_data = jsonlib.load(f)
                return PseudocodeArtifact(**artifact_data)
            except Exception:
                continue  # Try next pattern
    
    return None


@api_expose(enabled=False)  # CLI-only: dev/admin server management 
@app.command()
def api(
    config: Annotated[Path | None, typer.Option("-c", "--config", help="Configuration file path (default: search for .rpax.json)")] = None,
    enable: Annotated[bool, typer.Option("--enable/--disable", help="Override API enabled setting from config")] = None,
    enable_temp: Annotated[bool, typer.Option("--enable-temp", help="Temporarily enable API (ignores config.api.enabled)")] = False,
    port: Annotated[int | None, typer.Option("--port", help="Override port from config")] = None,
    bind: Annotated[str | None, typer.Option("--bind", help="Override bind address from config")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable access logging (shows HTTP requests with status codes)")] = False,
):
    """Start the rpax Access API server per ADR-022.
    
    Provides minimal HTTP API with health and status endpoints for external tool integration.
    Server runs on localhost-only by default with automatic port discovery.
    
    Service discovery file written to %LOCALAPPDATA%/rpax/api-info.json for PowerShell integration.
    """
    from rpax.api import start_api_server, ApiError
    import time
    
    try:
        # Load configuration
        rpax_config = load_config(config)
        
        # Apply CLI overrides
        if enable is not None:
            rpax_config.api.enabled = enable
        elif enable_temp:
            # Temporary enable overrides config completely
            rpax_config.api.enabled = True
        if port is not None:
            rpax_config.api.port = port
        if bind is not None:
            rpax_config.api.bind = bind
        
        # Validate lake directory exists
        lake_path = Path(rpax_config.output.dir)
        if not lake_path.exists():
            console.print(f"[red]Error:[/red] Lake directory not found: {lake_path}")
            console.print("[dim]Run 'rpax parse' first to create artifacts[/dim]")
            raise typer.Exit(1)
        
        # Start server
        server = start_api_server(rpax_config, verbose=verbose)
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down API server...[/yellow]")
            server.stop()
    
    except ApiError as e:
        console.print(f"[red]API Error:[/red] {e.detail}")
        raise typer.Exit(e.status_code // 100)  # Convert HTTP status to exit code
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@api_expose(
    path="/health",
    methods=["GET"],
    tags=["system"],
    summary="Check API server health status",
    mcp_resource_type="health_check"
)
@app.command()
def health() -> None:
    """Check API server health status.
    
    This command provides health information about the rpax system,
    useful for monitoring and integration purposes.
    """
    from datetime import datetime, timezone
    
    try:
        console.print("[green]rpax Health Check[/green]")
        console.print(f"Status: [green]OK[/green]")
        console.print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        console.print(f"Version: {__version__}")
        
        # Check if lake directory exists
        lake_path = Path(".rpax-lake")
        if lake_path.exists():
            console.print(f"Lake: [green]Available[/green] ({lake_path.resolve()})")
            
            # Count projects if possible
            try:
                projects_file = lake_path / "projects.json"
                if projects_file.exists():
                    import json
                    with open(projects_file) as f:
                        projects_data = json.load(f)
                    project_count = len(projects_data.get("projects", []))
                    console.print(f"Projects: {project_count}")
                else:
                    console.print("Projects: [dim]Not indexed[/dim]")
            except Exception:
                console.print("Projects: [dim]Unable to count[/dim]")
        else:
            console.print(f"Lake: [yellow]Not found[/yellow] ({lake_path.resolve()})")
            
    except Exception as e:
        console.print(f"[red]Health check failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("object-repository")
def object_repository(
    action: Annotated[
        str,
        typer.Argument(help="Action to perform: summary, apps, targets, mcp-resources")
    ],
    app_name: Annotated[
        str | None,
        typer.Argument(help="App name for app-specific actions (optional)")
    ] = None,
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to artifacts directory or lake directory (default: .rpax-lake)")
    ] = Path(".rpax-lake"),
    project: Annotated[
        str | None,
        typer.Option("--project", help="Project slug for multi-project lakes (optional)")
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json, table (default: json)")
    ] = "json",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed information and metadata (default: False)")
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Limit number of results shown (default: no limit)")
    ] = None,
) -> None:
    """Access Object Repository artifacts for Library projects.
    
    Actions:
    - summary: Show Object Repository library overview
    - apps: List applications in the Object Repository
    - targets: Show UI targets for an app (requires app name)
    - mcp-resources: Show MCP resources for external integration
    """
    try:
        project_path = path.resolve()

        # Check for multi-project or single-project structure
        if (project_path / "projects.json").exists():
            # Multi-project lake - use project resolution logic
            artifacts_path = _resolve_project_artifacts_path(project_path, project, "object-repository")
        elif (project_path / "manifest.json").exists():
            # Single-project directory - use directory directly
            artifacts_path = project_path
        else:
            console.print(f"[red]Error:[/red] No manifest.json or projects.json found in {project_path}")
            console.print("[dim]Run 'rpax parse' first or specify correct artifacts directory[/dim]")
            raise typer.Exit(1)

        # Check if Object Repository artifacts exist
        object_repo_dir = artifacts_path / "object-repository"
        if not object_repo_dir.exists():
            console.print(f"[red]Error:[/red] No Object Repository artifacts found in {artifacts_path}")
            console.print("[dim]Object Repository is only available for UiPath Library projects[/dim]")
            raise typer.Exit(1)

        valid_actions = ["summary", "apps", "targets", "mcp-resources"]
        if action not in valid_actions:
            console.print(f"[red]Error:[/red] Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}")
            raise typer.Exit(1)

        if action == "targets" and not app_name:
            console.print(f"[red]Error:[/red] App name required for '{action}' action")
            console.print("[dim]Example: rpax object-repository targets Calculator --path .rpax-lake[/dim]")
            raise typer.Exit(1)

        if action == "summary":
            _show_object_repository_summary(object_repo_dir, format, verbose)
        elif action == "apps":
            _show_object_repository_apps(object_repo_dir, format, verbose, limit)
        elif action == "targets":
            _show_object_repository_targets(object_repo_dir, app_name, format, verbose, limit)
        elif action == "mcp-resources":
            _show_object_repository_mcp_resources(object_repo_dir, format, verbose)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _show_object_repository_summary(object_repo_dir: Path, format: str, verbose: bool) -> None:
    """Show Object Repository summary."""
    summary_file = object_repo_dir / "repository-summary.json"
    
    if not summary_file.exists():
        console.print(f"[red]Error:[/red] Object Repository summary not found")
        console.print(f"[dim]Expected: {summary_file}[/dim]")
        raise typer.Exit(1)

    with open(summary_file, encoding="utf-8") as f:
        summary_data = jsonlib.load(f)

    if format == "json":
        print(jsonlib.dumps(summary_data, indent=2))
    elif format == "table":
        console.print(f"[green]Object Repository Library[/green]")
        console.print(f"Library ID: {summary_data.get('libraryId', 'Unknown')}")
        console.print(f"Library Type: {summary_data.get('libraryType', 'Unknown')}")
        console.print(f"Total Apps: {summary_data.get('totalApps', 0)}")
        console.print(f"Total Targets: {summary_data.get('totalTargets', 0)}")
        console.print(f"Generated: {summary_data.get('generatedAt', 'Unknown')}")
        
        if verbose and summary_data.get("apps"):
            console.print(f"\nApplications:")
            for app in summary_data["apps"]:
                console.print(f"  - {app.get('name', 'Unknown')} ({app.get('targetsCount', 0)} targets)")
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for Object Repository summary")
        raise typer.Exit(1)


def _show_object_repository_apps(object_repo_dir: Path, format: str, verbose: bool, limit: int | None) -> None:
    """Show Object Repository applications."""
    apps_dir = object_repo_dir / "apps"
    
    if not apps_dir.exists():
        console.print(f"[red]Error:[/red] No Object Repository apps found")
        raise typer.Exit(1)

    app_files = list(apps_dir.glob("*.json"))
    if limit:
        app_files = app_files[:limit]

    if format == "json":
        apps_data = []
        for app_file in app_files:
            with open(app_file, encoding="utf-8") as f:
                app_data = jsonlib.load(f)
                apps_data.append(app_data)
        print(jsonlib.dumps({"apps": apps_data, "total": len(apps_data)}, indent=2))
    elif format == "table":
        table = Table(title="Object Repository Applications")
        table.add_column("Name", style="cyan")
        table.add_column("App ID", style="yellow", no_wrap=True)
        table.add_column("Targets", style="green")
        table.add_column("Description", style="dim")
        
        for app_file in app_files:
            with open(app_file, encoding="utf-8") as f:
                app_data = jsonlib.load(f)
                
            name = app_data.get("name", "Unknown")
            app_id = app_data.get("appId", "Unknown")[:12] + "..."
            targets_count = str(app_data.get("totalTargets", 0))
            description = app_data.get("description", "")
            
            if not verbose and len(description) > 50:
                description = description[:47] + "..."
                
            table.add_row(name, app_id, targets_count, description)
        
        console.print(table)
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for Object Repository apps")
        raise typer.Exit(1)


def _show_object_repository_targets(object_repo_dir: Path, app_name: str, format: str, verbose: bool, limit: int | None) -> None:
    """Show Object Repository targets for an app."""
    apps_dir = object_repo_dir / "apps"
    app_file = apps_dir / f"{app_name}.json"
    
    if not app_file.exists():
        console.print(f"[red]Error:[/red] App '{app_name}' not found in Object Repository")
        console.print(f"[dim]Available apps: {', '.join([f.stem for f in apps_dir.glob('*.json')])}")
        raise typer.Exit(1)

    with open(app_file, encoding="utf-8") as f:
        app_data = jsonlib.load(f)

    targets = app_data.get("targets", [])
    if limit:
        targets = targets[:limit]

    if format == "json":
        print(jsonlib.dumps({"app": app_data["name"], "targets": targets, "total": len(targets)}, indent=2))
    elif format == "table":
        table = Table(title=f"UI Targets: {app_data['name']} ({len(targets)} targets)")
        table.add_column("Friendly Name", style="cyan")
        table.add_column("Element Type", style="yellow")
        table.add_column("Target ID", style="green", no_wrap=True)
        table.add_column("Selectors", style="magenta")
        
        if verbose:
            table.add_column("Design Props", style="dim")
        
        for target in targets:
            friendly_name = target.get("friendlyName", "Unknown")
            element_type = target.get("elementType", "Unknown")
            target_id = target.get("targetId", "Unknown")[:12] + "..."
            selectors = target.get("selectors", [])
            selectors_summary = f"{len(selectors)} selectors"
            
            row = [friendly_name, element_type, target_id, selectors_summary]
            
            if verbose:
                design_props = target.get("designProperties", {})
                props_summary = f"{len(design_props)} props" if design_props else "no props"
                row.append(props_summary)
            
            table.add_row(*row)
        
        console.print(table)
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for Object Repository targets")
        raise typer.Exit(1)


def _show_object_repository_mcp_resources(object_repo_dir: Path, format: str, verbose: bool) -> None:
    """Show Object Repository MCP resources."""
    mcp_file = object_repo_dir / "mcp-resources.json"
    
    if not mcp_file.exists():
        console.print(f"[red]Error:[/red] MCP resources not found")
        console.print(f"[dim]Expected: {mcp_file}[/dim]")
        raise typer.Exit(1)

    with open(mcp_file, encoding="utf-8") as f:
        mcp_data = jsonlib.load(f)

    if format == "json":
        print(jsonlib.dumps(mcp_data, indent=2))
    elif format == "table":
        resources = mcp_data.get("resources", [])
        table = Table(title=f"MCP Resources ({len(resources)} resources)")
        table.add_column("URI", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Type", style="green")
        table.add_column("Description", style="dim")
        
        for resource in resources:
            uri = resource.get("uri", "Unknown")
            name = resource.get("name", "Unknown")
            content_type = resource.get("content", {}).get("type", "Unknown")
            description = resource.get("description", "")
            
            if not verbose and len(description) > 60:
                description = description[:57] + "..."
                
            table.add_row(uri, name, content_type, description)
        
        console.print(table)
        console.print(f"\n[dim]Generated at: {mcp_data.get('generatedAt', 'Unknown')}[/dim]")
    else:
        console.print(f"[red]Error:[/red] Unsupported format '{format}' for MCP resources")
        raise typer.Exit(1)


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


if __name__ == "__main__":
    app()
