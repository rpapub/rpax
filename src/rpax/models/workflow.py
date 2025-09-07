"""Models for XAML workflow representation and indices."""

import hashlib
from pathlib import Path

from pydantic import BaseModel, Field


class Workflow(BaseModel):
    """Individual XAML workflow model."""
    id: str  # Composite ID: projectSlug + wfId + contentHash
    project_slug: str = Field(alias="projectSlug")
    workflow_id: str = Field(alias="workflowId")  # Normalized file path
    content_hash: str = Field(alias="contentHash")

    # File metadata
    file_path: str = Field(alias="filePath")  # Original file path
    file_name: str = Field(alias="fileName")
    relative_path: str = Field(alias="relativePath")  # POSIX normalized (wfId)
    original_path: str | None = Field(alias="originalPath", default=None)  # Original casing for provenance (ADR-014)

    # Workflow metadata
    display_name: str | None = Field(alias="displayName", default=None)
    description: str | None = None

    # Discovery metadata
    discovered_at: str = Field(alias="discoveredAt")  # ISO timestamp
    file_size: int = Field(alias="fileSize")
    last_modified: str = Field(alias="lastModified")  # ISO timestamp

    # XAML content metadata (ISSUE-060)
    root_annotation: str | None = Field(alias="rootAnnotation", default=None)
    arguments: list[dict] = Field(default_factory=list)  # WorkflowArgument data
    variables: list[dict] = Field(default_factory=list)  # WorkflowVariable data
    activities: list[dict] = Field(default_factory=list)  # ActivityContent data
    expression_language: str = Field(alias="expressionLanguage", default="VisualBasic")
    total_activities: int = Field(alias="totalActivities", default=0)
    total_arguments: int = Field(alias="totalArguments", default=0)
    total_variables: int = Field(alias="totalVariables", default=0)

    # Package usage from XAML namespaces
    namespaces: dict[str, str] = Field(default_factory=dict)  # xmlns declarations (prefix -> namespace URI)
    packages_used: list[str] = Field(alias="packagesUsed", default_factory=list)  # UiPath package names extracted from namespaces

    # Parsing status
    parse_successful: bool = Field(alias="parseSuccessful", default=True)
    parse_errors: list[str] = Field(alias="parseErrors", default_factory=list)

    @classmethod
    def generate_content_hash(cls, content: bytes) -> str:
        """Generate content hash for workflow file (full SHA-256 per ADR-014)."""
        return hashlib.sha256(content).hexdigest()  # Full SHA-256 hash

    @classmethod
    def generate_composite_id(cls, project_slug: str, workflow_id: str, content_hash: str) -> str:
        """Generate composite ID following ADR-014 identity system.
        
        Format: projectSlug#wfId#contentHash
        Where projectSlug = kebab(name) + "-" + shortHash(project.json)
        """
        return f"{project_slug}#{workflow_id}#{content_hash[:16]}"  # Use short hash in composite ID

    @classmethod
    def normalize_path(cls, file_path: Path, project_root: Path) -> str:
        """Normalize path to POSIX format relative to project root."""
        try:
            relative = file_path.resolve().relative_to(project_root.resolve())
            return str(relative).replace("\\", "/")  # Convert to POSIX
        except ValueError:
            # File is outside project root, use absolute path
            return str(file_path.resolve()).replace("\\", "/")

    model_config = {"populate_by_name": True}


class WorkflowIndex(BaseModel):
    """Index of all discovered workflows in a project."""
    project_name: str = Field(alias="projectName")
    project_root: str = Field(alias="projectRoot")
    scan_timestamp: str = Field(alias="scanTimestamp")  # ISO timestamp

    # Statistics
    total_workflows: int = Field(alias="totalWorkflows")
    successful_parses: int = Field(alias="successfulParses")
    failed_parses: int = Field(alias="failedParses")

    # Workflow entries
    workflows: list[Workflow] = Field(default_factory=list)

    # Excluded files
    excluded_patterns: list[str] = Field(alias="excludedPatterns", default_factory=list)
    excluded_files: list[str] = Field(alias="excludedFiles", default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate parsing success rate."""
        if self.total_workflows == 0:
            return 1.0
        return self.successful_parses / self.total_workflows

    def get_workflow_by_id(self, workflow_id: str) -> Workflow | None:
        """Find workflow by composite ID."""
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                return workflow
        return None

    def get_workflows_by_path_pattern(self, pattern: str) -> list[Workflow]:
        """Find workflows matching path pattern."""
        import fnmatch
        matching = []
        for workflow in self.workflows:
            if fnmatch.fnmatch(workflow.relative_path, pattern):
                matching.append(workflow)
        return matching

    model_config = {"populate_by_name": True}
