"""Utilities for multi-project lake operations."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


class ProjectNotFoundError(Exception):
    """Raised when a project cannot be found in the lake."""
    pass


class MultipleProjectsFoundError(Exception):
    """Raised when multiple projects match the search criteria."""
    pass


def find_lake_directory(path: Path) -> Optional[Path]:
    """Find the lake directory starting from the given path.
    
    Args:
        path: Starting path to search from
        
    Returns:
        Path to lake directory if found, None otherwise
    """
    path = path.resolve()
    
    # Check if path itself is a lake directory
    if is_lake_directory(path):
        return path
    
    # Check common lake locations
    candidates = [
        path / ".rpax-lake",
        path / ".rpax-out", 
        path / "output",
        # Also check parent directories
        path.parent / ".rpax-lake",
        path.parent / ".rpax-out",
    ]
    
    for candidate in candidates:
        if is_lake_directory(candidate):
            return candidate
    
    return None


def is_lake_directory(path: Path) -> bool:
    """Check if a directory is a valid rpax lake.
    
    Args:
        path: Directory to check
        
    Returns:
        True if directory contains lake structure
    """
    if not path.exists() or not path.is_dir():
        return False
    
    # Check for projects.json (multi-project lake)
    if (path / "projects.json").exists():
        return True
    
    # Check for direct manifest.json (single-project lake)
    if (path / "manifest.json").exists() and (path / "workflows.index.json").exists():
        return True
    
    return False


def is_multi_project_lake(lake_dir: Path) -> bool:
    """Check if lake contains multiple projects.
    
    Args:
        lake_dir: Lake directory path
        
    Returns:
        True if multi-project lake, False if single-project
    """
    return (lake_dir / "projects.json").exists()


def load_projects_index(lake_dir: Path) -> Dict[str, any]:
    """Load projects.json index from lake directory.
    
    Args:
        lake_dir: Lake directory path
        
    Returns:
        Projects index data
        
    Raises:
        FileNotFoundError: If projects.json doesn't exist
    """
    projects_file = lake_dir / "projects.json"
    if not projects_file.exists():
        raise FileNotFoundError(f"No projects.json found in {lake_dir}")
    
    with open(projects_file, encoding="utf-8") as f:
        return json.load(f)


def list_project_slugs(lake_dir: Path) -> List[str]:
    """List all project slugs in the lake.
    
    Args:
        lake_dir: Lake directory path
        
    Returns:
        List of project slugs
    """
    if not is_multi_project_lake(lake_dir):
        # Single project lake - infer slug from directory structure
        for item in lake_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                return [item.name]
        return []
    
    projects = load_projects_index(lake_dir)
    return [project["slug"] for project in projects.get("projects", [])]


def resolve_project_slug(lake_dir: Path, project_hint: Optional[str] = None) -> str:
    """Resolve project slug from hint or auto-discover.
    
    Args:
        lake_dir: Lake directory path
        project_hint: Optional project name/slug hint
        
    Returns:
        Resolved project slug
        
    Raises:
        ProjectNotFoundError: If project not found
        MultipleProjectsFoundError: If multiple matches and no disambiguation
    """
    project_slugs = list_project_slugs(lake_dir)
    
    if not project_slugs:
        raise ProjectNotFoundError("No projects found in lake")
    
    # If no hint provided, auto-discover
    if not project_hint:
        if len(project_slugs) == 1:
            return project_slugs[0]
        else:
            # Multiple projects, need disambiguation
            console.print("[yellow]Multiple projects found in lake:[/yellow]")
            for slug in project_slugs:
                console.print(f"  - {slug}")
            console.print("\n[dim]Specify project with --project parameter[/dim]")
            raise MultipleProjectsFoundError(f"Found {len(project_slugs)} projects, specify --project")
    
    # Exact match
    if project_hint in project_slugs:
        return project_hint
    
    # Partial match
    matches = [slug for slug in project_slugs if project_hint.lower() in slug.lower()]
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        console.print(f"[yellow]Multiple projects match '{project_hint}':[/yellow]")
        for slug in matches:
            console.print(f"  - {slug}")
        raise MultipleProjectsFoundError(f"Multiple matches for '{project_hint}'")
    else:
        console.print(f"[red]No project found matching '{project_hint}'[/red]")
        console.print("[yellow]Available projects:[/yellow]")
        for slug in project_slugs:
            console.print(f"  - {slug}")
        raise ProjectNotFoundError(f"No project found matching '{project_hint}'")


def get_project_artifacts_dir(lake_dir: Path, project_slug: str) -> Path:
    """Get artifacts directory for a specific project.
    
    Args:
        lake_dir: Lake directory path
        project_slug: Project slug identifier
        
    Returns:
        Path to project artifacts directory
        
    Raises:
        ProjectNotFoundError: If project directory doesn't exist
    """
    if is_multi_project_lake(lake_dir):
        project_dir = lake_dir / project_slug
    else:
        # Single project lake - artifacts are in lake root
        project_dir = lake_dir
    
    if not project_dir.exists():
        raise ProjectNotFoundError(f"Project directory not found: {project_dir}")
    
    if not (project_dir / "manifest.json").exists():
        raise ProjectNotFoundError(f"No manifest.json found in {project_dir}")
    
    return project_dir


def load_workflow_index(artifacts_dir: Path) -> Dict[str, any]:
    """Load workflows.index.json from project artifacts directory.
    
    Args:
        artifacts_dir: Project artifacts directory
        
    Returns:
        Workflow index data
        
    Raises:
        FileNotFoundError: If workflows.index.json doesn't exist
    """
    index_file = artifacts_dir / "workflows.index.json"
    if not index_file.exists():
        raise FileNotFoundError(f"No workflows.index.json found in {artifacts_dir}")
    
    with open(index_file, encoding="utf-8") as f:
        return json.load(f)


def find_workflow_in_project(artifacts_dir: Path, workflow_hint: str) -> Optional[Dict[str, any]]:
    """Find a workflow in project by ID, filename, or partial path.
    
    Args:
        artifacts_dir: Project artifacts directory
        workflow_hint: Workflow identifier hint
        
    Returns:
        Workflow data if found, None otherwise
    """
    try:
        index = load_workflow_index(artifacts_dir)
        workflows = index.get("workflows", [])
        
        # Exact ID match
        for workflow in workflows:
            if workflow.get("id") == workflow_hint:
                return workflow
        
        # Filename match
        for workflow in workflows:
            if workflow.get("fileName") == workflow_hint:
                return workflow
        
        # Partial path match
        for workflow in workflows:
            relative_path = workflow.get("relativePath", "")
            if workflow_hint.lower() in relative_path.lower():
                return workflow
        
        # Display name match
        for workflow in workflows:
            display_name = workflow.get("displayName", "")
            if workflow_hint.lower() in display_name.lower():
                return workflow
        
        return None
        
    except FileNotFoundError:
        return None


def show_project_summary(lake_dir: Path, project_slug: str) -> None:
    """Display summary information for a project.
    
    Args:
        lake_dir: Lake directory path
        project_slug: Project slug
    """
    try:
        artifacts_dir = get_project_artifacts_dir(lake_dir, project_slug)
        
        # Load manifest
        manifest_file = artifacts_dir / "manifest.json"
        with open(manifest_file, encoding="utf-8") as f:
            manifest = json.load(f)
        
        # Load workflow index
        index = load_workflow_index(artifacts_dir)
        
        console.print(f"\n[bold blue]Project: {manifest.get('projectName', 'Unknown')}[/bold blue]")
        console.print(f"Slug: {project_slug}")
        console.print(f"Type: {manifest.get('projectType', 'Unknown')}")
        console.print(f"Workflows: {index.get('totalWorkflows', 0)}")
        console.print(f"Entry Points: {len(manifest.get('entryPoints', []))}")
        
    except Exception as e:
        console.print(f"[red]Error loading project summary: {e}[/red]")