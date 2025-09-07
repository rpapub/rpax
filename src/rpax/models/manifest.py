"""Models for rpax project manifest and artifact summaries."""

from typing import Any

from pydantic import BaseModel, Field

from rpax.models.project import EntryPoint, RuntimeOptions, DesignOptions


class ProjectManifest(BaseModel):
    """Main project manifest containing metadata and entry points."""

    # Project identification
    project_name: str = Field(alias="projectName")
    project_id: str | None = Field(alias="projectId", default=None)
    project_type: str = Field(alias="projectType")  # process | library
    project_root: str = Field(alias="projectRoot")

    # Versioning
    rpax_version: str = Field(alias="rpaxVersion")
    rpax_schema_version: str = Field(alias="rpaxSchemaVersion", default="1.0")  # rpax artifact schema version
    generated_at: str = Field(alias="generatedAt")  # ISO timestamp

    # UiPath metadata
    main_workflow: str = Field(alias="mainWorkflow")
    description: str | None = None
    project_version: str | None = Field(alias="projectVersion", default=None)
    uipath_schema_version: str | None = Field(alias="uipathSchemaVersion", default=None)
    studio_version: str | None = Field(alias="studioVersion", default=None)
    target_framework: str = Field(alias="targetFramework", default="Windows")
    expression_language: str = Field(alias="expressionLanguage", default="VisualBasic")
    
    # UiPath configuration
    runtime_options: RuntimeOptions | None = Field(alias="runtimeOptions", default=None)
    design_options: DesignOptions | None = Field(alias="designOptions", default=None)

    # Entry points and dependencies
    entry_points: list[EntryPoint] = Field(alias="entryPoints", default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)

    # Discovery summary
    total_workflows: int = Field(alias="totalWorkflows")
    total_invocations: int = Field(alias="totalInvocations", default=0)
    parse_errors: int = Field(alias="parseErrors", default=0)

    # Configuration snapshot
    scan_config: dict[str, Any] = Field(alias="scanConfig", default_factory=dict)
    validation_config: dict[str, Any] = Field(alias="validationConfig", default_factory=dict)

    # Artifact references
    workflow_index_file: str = Field(alias="workflowIndexFile", default="workflows.index.json")
    invocations_file: str = Field(alias="invocationsFile", default="invocations.jsonl")
    activities_dir: str = Field(alias="activitiesDir", default="activities.json")
    paths_dir: str = Field(alias="pathsDir", default="paths/")
    pseudocode_file: str = Field(alias="pseudocodeFile", default="pseudocode.index.json")
    pseudocode_dir: str = Field(alias="pseudocodeDir", default="pseudocode/")

    @property
    def is_library(self) -> bool:
        """Check if this is a library project."""
        return self.project_type.lower() == "library"

    @property
    def is_process(self) -> bool:
        """Check if this is a process project."""
        return self.project_type.lower() == "process"

    @property
    def success_rate(self) -> float:
        """Calculate parsing success rate."""
        if self.total_workflows == 0:
            return 1.0
        successful = self.total_workflows - self.parse_errors
        return successful / self.total_workflows

    model_config = {"populate_by_name": True}
