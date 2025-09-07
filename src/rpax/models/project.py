"""Models for UiPath project.json parsing and representation."""

import hashlib
import json
import re
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ArgumentDirection(str, Enum):
    """Argument direction types."""
    INPUT = "input"
    OUTPUT = "output"


class Argument(BaseModel):
    """UiPath workflow argument model."""
    name: str
    type: str
    required: bool = False
    has_default: bool = Field(alias="hasDefault", default=False)
    default_value: Any | None = Field(alias="defaultValue", default=None)

    model_config = {"populate_by_name": True}


class EntryPoint(BaseModel):
    """UiPath project entry point model."""
    file_path: str = Field(alias="filePath")
    unique_id: str = Field(alias="uniqueId")
    input: list[Argument] = Field(default_factory=list)
    output: list[Argument] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class RuntimeOptions(BaseModel):
    """UiPath project runtime options."""
    auto_dispose: bool = Field(alias="autoDispose", default=False)
    net_framework_lazy_loading: bool = Field(alias="netFrameworkLazyLoading", default=False)
    is_pausable: bool = Field(alias="isPausable", default=True)
    is_attended: bool = Field(alias="isAttended", default=False)
    requires_user_interaction: bool = Field(alias="requiresUserInteraction", default=True)
    supports_persistence: bool = Field(alias="supportsPersistence", default=False)
    workflow_serialization: str = Field(alias="workflowSerialization", default="DataContract")
    excluded_logged_data: list[str] = Field(alias="excludedLoggedData", default_factory=list)
    execution_type: str = Field(alias="executionType", default="Workflow")
    ready_for_pip: bool = Field(alias="readyForPiP", default=False)
    starts_in_pip: bool = Field(alias="startsInPiP", default=False)
    must_restore_all_dependencies: bool = Field(alias="mustRestoreAllDependencies", default=True)
    pip_type: str = Field(alias="pipType", default="ChildSession")

    model_config = {"populate_by_name": True}


class LibraryOptions(BaseModel):
    """UiPath library-specific options."""
    include_original_xaml: bool = Field(alias="includeOriginalXaml", default=False)
    private_workflows: list[str] = Field(alias="privateWorkflows", default_factory=list)

    model_config = {"populate_by_name": True}


class ProcessOptions(BaseModel):
    """UiPath process-specific options."""
    ignored_files: list[str] = Field(alias="ignoredFiles", default_factory=list)

    model_config = {"populate_by_name": True}


class FileInfo(BaseModel):
    """UiPath file information model."""
    editing_status: str = Field(alias="editingStatus")
    test_case_id: str | None = Field(alias="testCaseId", default=None)
    test_case_type: str | None = Field(alias="testCaseType", default=None)
    data_variation_file_path: str | None = Field(alias="dataVariationFilePath", default=None)
    file_name: str = Field(alias="fileName")
    execution_template_invoke_isolated: bool | None = Field(
        alias="executionTemplateInvokeIsolated", default=None
    )

    model_config = {"populate_by_name": True}


class DesignOptions(BaseModel):
    """UiPath design options."""
    project_profile: str = Field(alias="projectProfile", default="Development")
    output_type: str = Field(alias="outputType")
    library_options: LibraryOptions | None = Field(alias="libraryOptions", default=None)
    process_options: ProcessOptions | None = Field(alias="processOptions", default=None)
    file_info_collection: list[FileInfo] = Field(alias="fileInfoCollection", default_factory=list)
    modern_behavior: bool = Field(alias="modernBehavior", default=False)
    save_to_cloud: bool = Field(alias="saveToCloud", default=False)

    model_config = {"populate_by_name": True}


class UiPathProject(BaseModel):
    """Complete UiPath project.json model."""
    name: str
    project_id: str | None = Field(alias="projectId", default=None)
    description: str | None = None
    main: str
    dependencies: dict[str, str] = Field(default_factory=dict)
    web_services: list[dict[str, Any]] = Field(alias="webServices", default_factory=list)
    entities_stores: list[dict[str, Any]] = Field(alias="entitiesStores", default_factory=list)
    uipath_schema_version: str = Field(alias="schemaVersion")  # UiPath's schema version
    studio_version: str | None = Field(alias="studioVersion", default=None)
    project_version: str | None = Field(alias="projectVersion", default=None)
    runtime_options: RuntimeOptions | None = Field(alias="runtimeOptions", default=None)
    design_options: DesignOptions | None = Field(alias="designOptions", default=None)
    arguments: dict[ArgumentDirection, list[Argument]] | None = None
    expression_language: str | None = Field(alias="expressionLanguage", default="VisualBasic")
    entry_points: list[EntryPoint] = Field(alias="entryPoints", default_factory=list)
    is_template: bool = Field(alias="isTemplate", default=False)
    template_project_data: dict[str, Any] = Field(alias="templateProjectData", default_factory=dict)
    publish_data: dict[str, Any] = Field(alias="publishData", default_factory=dict)
    target_framework: str = Field(alias="targetFramework", default="Windows")

    @property
    def project_type(self) -> str:
        """Infer project type from design options."""
        if self.design_options and self.design_options.output_type:
            return self.design_options.output_type.lower()
        return "process"  # Default assumption

    @property
    def is_library(self) -> bool:
        """Check if this is a library project."""
        return self.project_type == "library"

    @property
    def is_process(self) -> bool:
        """Check if this is a process project."""
        return self.project_type == "process"

    def generate_project_slug(self, project_json_path: Path | None = None) -> str:
        """Generate stable project slug for multi-project lake storage.
        
        Strategy: Always use rock-solid slugify(name) + "-" + shortSha256(project.json)[:10]
        This ensures:
        - Human-readable project names in slugs
        - No collisions (unique content hash)
        - Stable slugs (name changes don't break references)
        - Consistent format across all projects
        - CLI comma-separation safety (no commas in slugs)
        - MCP URI compatibility (URI-safe characters only)
        
        Args:
            project_json_path: Path to project.json for content hashing
            
        Returns:
            Project slug format: "{slugified-name}-{hash10}" (11-38 chars)
        """
        # Rock-solid slug sanitization for CLI and MCP URI safety
        name_part = self._sanitize_slug_name(self.name)[:20]
        name_part = name_part or "unnamed"  # Ensure we have a name part

        if project_json_path and project_json_path.exists():
            # Hash canonical project.json content for uniqueness
            content = project_json_path.read_text(encoding="utf-8")
            canonical = json.dumps(json.loads(content), sort_keys=True, separators=(",", ":"))
            hash_val = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]
        else:
            # Fallback hash from project metadata if no file path
            # Use projectId if available, otherwise name + basic properties
            fallback_content = {
                "name": self.name,
                "projectId": self.project_id,
                "main": self.main,
                "uipathSchemaVersion": self.uipath_schema_version
            }
            canonical = json.dumps(fallback_content, sort_keys=True, separators=(",", ":"))
            hash_val = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:10]

        return f"{name_part}-{hash_val}"
    
    def _sanitize_slug_name(self, name: str) -> str:
        """Rock-solid slug sanitization for CLI and MCP URI safety.
        
        Sanitization strategy:
        1. Convert to lowercase
        2. Replace all non-alphanumeric characters with hyphens
        3. Collapse multiple consecutive hyphens into single hyphens
        4. Strip leading/trailing hyphens
        5. Ensure result is not empty
        
        This guarantees:
        - No commas (safe for CLI comma-separated parameters)
        - URI-safe characters only (alphanumeric + hyphens)
        - No consecutive hyphens or edge-case formatting
        - Always produces valid identifier
        
        Args:
            name: Raw project name to sanitize
            
        Returns:
            Sanitized slug component (or empty string if unsanitizable)
        """
        if not name or not name.strip():
            return ""
            
        # Step 1: Convert to lowercase
        sanitized = name.lower().strip()
        
        # Step 2: Replace all non-alphanumeric with hyphens
        # This handles commas, spaces, special chars, unicode, etc.
        sanitized = re.sub(r"[^a-z0-9]", "-", sanitized)
        
        # Step 3: Collapse consecutive hyphens into single hyphens
        # Handles cases like "My--Project" -> "my-project"
        sanitized = re.sub(r"-+", "-", sanitized)
        
        # Step 4: Strip leading/trailing hyphens
        # Handles cases like "-project-" -> "project"
        sanitized = sanitized.strip("-")
        
        return sanitized

    model_config = {"populate_by_name": True, "extra": "allow"}  # Allow additional fields for forward compatibility
