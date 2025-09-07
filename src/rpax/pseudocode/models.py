"""Data models for pseudocode artifacts."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class PseudocodeEntry:
    """Single pseudocode line entry."""
    
    indent: int
    display_name: str
    tag: str
    path: str
    formatted_line: str
    node_id: str
    depth: int
    is_visual: bool
    children: list["PseudocodeEntry"] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class PseudocodeArtifact(BaseModel):
    """Complete pseudocode artifact for a workflow."""
    
    workflow_id: str = Field(description="Workflow identifier")
    project_id: str = Field(description="Project identifier")
    project_slug: str = Field(description="Project slug")
    schema_version: str = Field(default="1.0.0", description="Artifact schema version")
    generated_at: str = Field(description="Generation timestamp")
    rpax_version: str = Field(description="rpax version used for generation")
    
    # Core pseudocode data
    activities: list[dict[str, Any]] = Field(description="Activity pseudocode entries")
    activity_count: int = Field(description="Total number of activities")
    
    # Legacy fields for compatibility
    format_version: str = Field(default="gist-style", description="Pseudocode format version")
    total_lines: int = Field(default=0, description="Total number of pseudocode lines")
    total_activities: int = Field(default=0, description="Total number of activities represented")
    entries: list[dict[str, Any]] = Field(default_factory=list, description="Legacy pseudocode entries")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Recursive expansion fields (ISSUE-040)
    expanded_pseudocode: list[str] = Field(default_factory=list, description="Recursively expanded pseudocode lines")
    expansion_config: dict[str, Any] = Field(default_factory=dict, description="Configuration used for expansion")
    generation_config: dict[str, Any] = Field(default_factory=dict, description="Configuration used during generation")
    
    model_config = {"extra": "allow"}  # Allow extra fields for backward compatibility


class PseudocodeIndex(BaseModel):
    """Index of all pseudocode artifacts in project."""
    
    project_id: str = Field(description="Project identifier")  
    project_slug: str = Field(description="Project slug")
    total_workflows: int = Field(description="Total workflows with pseudocode")
    workflows: list[dict[str, Any]] = Field(description="Workflow pseudocode references")
    rpax_schema_version: str = Field(alias="rpaxSchemaVersion", default="1.0")
    generated_at: str = Field(description="Generation timestamp")
    
    model_config = {"extra": "forbid", "populate_by_name": True}