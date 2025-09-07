"""Call graph models and data structures for rpax."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer


class WorkflowDependency(BaseModel):
    """Represents a dependency relationship between workflows."""
    
    source_workflow_id: str = Field(description="ID of the workflow making the call")
    target_workflow_id: str = Field(description="ID of the workflow being called")
    target_workflow_path: str = Field(description="Relative path to target workflow")
    invocation_type: str = Field(description="Type of invocation: static, dynamic, or missing")
    call_sites: List[str] = Field(default_factory=list, description="Activity IDs where this call occurs")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to target workflow")
    

class WorkflowNode(BaseModel):
    """Represents a workflow node in the call graph."""
    
    workflow_id: str = Field(description="Unique workflow identifier")
    workflow_path: str = Field(description="Relative path to workflow file")
    display_name: str = Field(description="Human-readable workflow name")
    is_entry_point: bool = Field(default=False, description="Whether this is a project entry point")
    call_depth: int = Field(default=0, description="Depth from nearest entry point")
    dependencies: List[WorkflowDependency] = Field(default_factory=list, description="Outbound dependencies")
    dependents: List[str] = Field(default_factory=list, description="Workflow IDs that call this workflow")


class CallGraphCycle(BaseModel):
    """Represents a detected cycle in the call graph."""
    
    cycle_id: str = Field(description="Unique identifier for this cycle")
    workflow_ids: List[str] = Field(description="Workflow IDs participating in the cycle")
    cycle_type: str = Field(description="Type of cycle: self, mutual, or complex")
    

class CallGraphMetrics(BaseModel):
    """Metrics and statistics about the call graph."""
    
    total_workflows: int = Field(description="Total number of workflows")
    total_dependencies: int = Field(description="Total number of dependency relationships")
    entry_points: int = Field(description="Number of entry point workflows")
    orphaned_workflows: int = Field(description="Number of workflows not reachable from entry points")
    max_call_depth: int = Field(description="Maximum call depth in the graph")
    cycles_detected: int = Field(description="Number of cycles detected")
    static_invocations: int = Field(description="Number of static (resolved) invocations")
    dynamic_invocations: int = Field(description="Number of dynamic (unresolved) invocations")
    missing_invocations: int = Field(description="Number of missing target workflows")


class CallGraphArtifact(BaseModel):
    """Complete call graph artifact for a project."""
    
    # Metadata
    project_id: str = Field(description="Project identifier")
    project_slug: str = Field(description="Project slug for file naming")
    schema_version: str = Field(default="1.0.0", description="Call graph schema version")
    generated_at: datetime = Field(description="Timestamp when call graph was generated")
    rpax_version: str = Field(description="Version of rpax that generated this artifact")
    
    # Graph data
    workflows: Dict[str, WorkflowNode] = Field(description="All workflows in the project indexed by workflow_id")
    entry_points: List[str] = Field(description="Workflow IDs that are project entry points")
    cycles: List[CallGraphCycle] = Field(default_factory=list, description="Detected cycles")
    metrics: CallGraphMetrics = Field(description="Graph metrics and statistics")
    
    # Additional metadata
    generation_config: Dict[str, Any] = Field(default_factory=dict, description="Configuration used during generation")
    
    @field_serializer('generated_at')
    def serialize_generated_at(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()