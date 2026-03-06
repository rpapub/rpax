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
        bay_id: URL-safe record identifier
        timestamp: Timestamp of parsing
    """
    project: UiPathProject
    workflow_index: WorkflowIndex
    project_root: Path
    bay_id: str
    timestamp: datetime

    @property
    def project_slug(self) -> str:
        """Backward-compat alias for bay_id."""
        return self.bay_id


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

    def create_bay_directory(self, bay_id: str) -> Path:
        """Create and return record-specific directory within archive.

        Args:
            bay_id: URL-safe record identifier

        Returns:
            Path to record directory
        """
        record_dir = self.output_dir / bay_id
        record_dir.mkdir(parents=True, exist_ok=True)
        return record_dir

    def create_project_directory(self, bay_id: str) -> Path:
        """Backward-compat alias for create_bay_directory."""
        return self.create_bay_directory(bay_id)
