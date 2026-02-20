"""Base classes for output generators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

from rpax.models.project import UiPathProject
from rpax.models.workflow import WorkflowIndex


@dataclass
class ParsedProjectData:
    """Parsed project data for generators.

    Attributes:
        project: Parsed UiPath project
        workflow_index: Index of discovered workflows
        project_root: Root directory of the project
        project_slug: URL-safe project identifier
        timestamp: Timestamp of parsing
    """
    project: UiPathProject
    workflow_index: WorkflowIndex
    project_root: Path
    project_slug: str
    timestamp: datetime


class OutputGenerator(ABC):
    """Base class for output generators."""

    def __init__(self, output_dir: Path):
        """Initialize output generator.

        Args:
            output_dir: Base output directory (lake root)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def schema_version(self) -> str:
        """Schema version identifier (e.g., 'legacy', 'v0')."""
        pass

    @abstractmethod
    def generate(self, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate artifacts from parsed data.

        Args:
            data: Parsed project data

        Returns:
            Dictionary mapping artifact names to generated file paths
        """
        pass

    def create_project_directory(self, project_slug: str) -> Path:
        """Create and return project-specific directory within lake.

        Args:
            project_slug: URL-safe project identifier

        Returns:
            Path to project directory
        """
        project_dir = self.output_dir / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
