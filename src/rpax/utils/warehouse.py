"""Utilities for multi-record archive operations."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


class BayNotFoundError(Exception):
    """Raised when a record cannot be found in the archive."""
    pass


class MultipleBaysFoundError(Exception):
    """Raised when multiple records match the search criteria."""
    pass


def find_warehouse_directory(path: Path) -> Optional[Path]:
    """Find the archive directory starting from the given path.

    Args:
        path: Starting path to search from

    Returns:
        Path to archive directory if found, None otherwise
    """
    path = path.resolve()

    # Check if path itself is an archive directory
    if is_warehouse_directory(path):
        return path

    # Check common archive locations
    candidates = [
        path / ".rpax-warehouse",
        path / ".rpax-lake",  # legacy fallback
        path / ".rpax-out",
        path / "output",
        # Also check parent directories
        path.parent / ".rpax-warehouse",
        path.parent / ".rpax-lake",  # legacy fallback
        path.parent / ".rpax-out",
    ]

    for candidate in candidates:
        if is_warehouse_directory(candidate):
            return candidate

    return None


def is_warehouse_directory(path: Path) -> bool:
    """Check if a directory is a valid rpax archive.

    Args:
        path: Directory to check

    Returns:
        True if directory contains archive structure
    """
    if not path.exists() or not path.is_dir():
        return False

    # Check for bays.json (multi-record archive)
    if (path / "bays.json").exists():
        return True

    # Legacy: check for projects.json (old multi-project lake)
    if (path / "projects.json").exists():
        return True

    # Check for direct manifest.json (single-record archive)
    if (path / "manifest.json").exists() and (path / "workflows.index.json").exists():
        return True

    return False


def is_multi_bay_warehouse(warehouse_dir: Path) -> bool:
    """Check if archive contains multiple records.

    Args:
        warehouse_dir: Archive directory path

    Returns:
        True if multi-record archive, False if single-record
    """
    return (warehouse_dir / "bays.json").exists() or (warehouse_dir / "projects.json").exists()


def load_bays_index(warehouse_dir: Path) -> Dict[str, any]:
    """Load bays.json index from archive directory.

    Args:
        warehouse_dir: Archive directory path

    Returns:
        Records index data

    Raises:
        FileNotFoundError: If bays.json doesn't exist
    """
    records_file = warehouse_dir / "bays.json"
    if records_file.exists():
        with open(records_file, encoding="utf-8") as f:
            return json.load(f)

    # Legacy fallback: projects.json
    projects_file = warehouse_dir / "projects.json"
    if projects_file.exists():
        with open(projects_file, encoding="utf-8") as f:
            data = json.load(f)
        # Normalize legacy format: projects[] → bays[]
        if "projects" in data and "bays" not in data:
            data["bays"] = [
                {**p, "bayId": p.get("bayId", p.get("projectSlug", p.get("slug", "")))}
                for p in data["projects"]
            ]
        return data

    raise FileNotFoundError(f"No bays.json found in {warehouse_dir}")


def list_bay_ids(warehouse_dir: Path) -> List[str]:
    """List all record IDs in the archive.

    Args:
        warehouse_dir: Archive directory path

    Returns:
        List of record IDs
    """
    if not is_multi_bay_warehouse(warehouse_dir):
        # Single record archive - infer record ID from directory structure
        for item in warehouse_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                return [item.name]
        return []

    records = load_bays_index(warehouse_dir)
    # Support bays[], records[] (old archive/record rename), and legacy projects[] keys
    entries = records.get("bays", records.get("records", records.get("projects", [])))
    return [
        r.get("bayId", r.get("recordId", r.get("projectSlug", r.get("slug", ""))))
        for r in entries
    ]


def resolve_bay_id(warehouse_dir: Path, record_hint: Optional[str] = None) -> str:
    """Resolve record ID from hint or auto-discover.

    Args:
        warehouse_dir: Archive directory path
        record_hint: Optional record name/ID hint

    Returns:
        Resolved record ID

    Raises:
        BayNotFoundError: If record not found
        MultipleBaysFoundError: If multiple matches and no disambiguation
    """
    bay_ids = list_bay_ids(warehouse_dir)

    if not bay_ids:
        raise BayNotFoundError("No bays found in warehouse")

    # If no hint provided, auto-discover
    if not record_hint:
        if len(bay_ids) == 1:
            return bay_ids[0]
        else:
            # Multiple bays, need disambiguation
            console.print("[yellow]Multiple bays found in warehouse:[/yellow]")
            for rid in bay_ids:
                console.print(f"  - {rid}")
            console.print("\n[dim]Specify bay with --bay parameter[/dim]")
            raise MultipleBaysFoundError(f"Found {len(bay_ids)} bays, specify --bay")

    # Exact match
    if record_hint in bay_ids:
        return record_hint

    # Partial match
    matches = [rid for rid in bay_ids if record_hint.lower() in rid.lower()]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        console.print(f"[yellow]Multiple bays match '{record_hint}':[/yellow]")
        for rid in matches:
            console.print(f"  - {rid}")
        raise MultipleBaysFoundError(f"Multiple matches for '{record_hint}'")
    else:
        console.print(f"[red]No bay found matching '{record_hint}'[/red]")
        console.print("[yellow]Available bays:[/yellow]")
        for rid in bay_ids:
            console.print(f"  - {rid}")
        raise BayNotFoundError(f"No bay found matching '{record_hint}'")


def get_bay_artifacts_dir(warehouse_dir: Path, bay_id: str) -> Path:
    """Get artifacts directory for a specific record.

    Args:
        warehouse_dir: Archive directory path
        bay_id: Record identifier

    Returns:
        Path to record artifacts directory

    Raises:
        BayNotFoundError: If record directory doesn't exist
    """
    if is_multi_bay_warehouse(warehouse_dir):
        record_dir = warehouse_dir / bay_id
    else:
        # Single record archive - artifacts are in archive root
        record_dir = warehouse_dir

    if not record_dir.exists():
        raise BayNotFoundError(f"Bay directory not found: {record_dir}")

    if not (record_dir / "manifest.json").exists():
        raise BayNotFoundError(f"No manifest.json found in {record_dir}")

    return record_dir


def load_workflow_index(artifacts_dir: Path) -> Dict[str, any]:
    """Load workflows.index.json from record artifacts directory.

    Args:
        artifacts_dir: Record artifacts directory

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


def find_workflow_in_record(artifacts_dir: Path, workflow_hint: str) -> Optional[Dict[str, any]]:
    """Find a workflow in a record by ID, filename, or partial path.

    Args:
        artifacts_dir: Record artifacts directory
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


def show_bay_summary(warehouse_dir: Path, bay_id: str) -> None:
    """Display summary information for a record.

    Args:
        warehouse_dir: Archive directory path
        bay_id: Record identifier
    """
    try:
        artifacts_dir = get_bay_artifacts_dir(warehouse_dir, bay_id)

        # Load manifest
        manifest_file = artifacts_dir / "manifest.json"
        with open(manifest_file, encoding="utf-8") as f:
            manifest = json.load(f)

        # Load workflow index
        index = load_workflow_index(artifacts_dir)

        console.print(f"\n[bold blue]Project: {manifest.get('projectName', 'Unknown')}[/bold blue]")
        console.print(f"Record ID: {bay_id}")
        console.print(f"Type: {manifest.get('projectType', 'Unknown')}")
        console.print(f"Workflows: {index.get('totalWorkflows', 0)}")
        console.print(f"Entry Points: {len(manifest.get('entryPoints', []))}")

    except Exception as e:
        console.print(f"[red]Error loading record summary: {e}[/red]")


# ---------------------------------------------------------------------------
# Backward-compatibility shims — import aliases for old names
# These allow a gradual migration of callers.
# ---------------------------------------------------------------------------

ProjectNotFoundError = BayNotFoundError
MultipleProjectsFoundError = MultipleBaysFoundError
find_lake_directory = find_warehouse_directory
is_lake_directory = is_warehouse_directory
is_multi_project_lake = is_multi_bay_warehouse
load_projects_index = load_bays_index
list_project_slugs = list_bay_ids
resolve_project_slug = resolve_bay_id
get_project_artifacts_dir = get_bay_artifacts_dir
find_workflow_in_project = find_workflow_in_record
show_project_summary = show_bay_summary
