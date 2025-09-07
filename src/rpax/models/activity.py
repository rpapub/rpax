"""Data models for UiPath workflow activities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ActivityNode:
    """Represents a single activity node in a workflow."""
    node_id: str  # Stable path-like locator (sibling indices)
    activity_type: str  # Fully-qualified type name
    display_name: str  # DisplayName property
    properties: dict[str, Any] = field(default_factory=dict)  # All activity properties
    arguments: dict[str, Any] = field(default_factory=dict)  # Activity arguments
    children: list["ActivityNode"] = field(default_factory=list)  # Child activities
    parent_id: str | None = None  # Parent node ID for navigation

    # UiPath-specific fields
    continue_on_error: bool | None = None
    timeout: str | None = None
    retry_scope_params: dict[str, Any] | None = None

    # Provenance
    view_state_id: str | None = None  # sap2010:WorkflowViewState.IdRef

    def add_child(self, child: "ActivityNode") -> None:
        """Add a child activity node."""
        child.parent_id = self.node_id
        self.children.append(child)

    def get_depth(self) -> int:
        """Calculate depth in activity tree."""
        if not self.children:
            return 1
        return 1 + max(child.get_depth() for child in self.children)

    def get_all_descendants(self) -> list["ActivityNode"]:
        """Get all descendant nodes recursively."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants


@dataclass
class ControlFlowEdge:
    """Represents a control flow edge between activities."""
    from_node_id: str  # Source node ID
    to_node_id: str  # Target node ID
    edge_type: str  # seq-next, branch-then, branch-else, case, loop-back, catch, finally
    condition: str | None = None  # For conditional edges

    def __str__(self) -> str:
        """String representation of the edge."""
        condition_str = f" ({self.condition})" if self.condition else ""
        return f"{self.from_node_id} --{self.edge_type}{condition_str}--> {self.to_node_id}"


@dataclass
class ResourceReference:
    """Represents a reference to an external resource."""
    resource_type: str  # selector, asset, queue, file, url, etc.
    resource_name: str  # Name or identifier
    resource_value: str  # Actual value (path, URL, selector string)
    node_id: str  # Activity node that references this resource
    property_name: str  # Property that contains the reference

    # Additional metadata
    is_dynamic: bool = False  # True if contains variables/expressions
    raw_value: str | None = None  # Original raw value before processing


@dataclass
class WorkflowMetrics:
    """Simple metrics for a workflow."""
    total_nodes: int = 0
    max_depth: int = 0
    loop_count: int = 0
    invoke_count: int = 0
    log_count: int = 0
    try_catch_count: int = 0
    selector_count: int = 0

    # Activity type counts
    activity_types: dict[str, int] = field(default_factory=dict)

    def increment_activity_type(self, activity_type: str) -> None:
        """Increment count for an activity type."""
        if activity_type in self.activity_types:
            self.activity_types[activity_type] += 1
        else:
            self.activity_types[activity_type] = 1


@dataclass
class ActivityTree:
    """Complete activity tree for a workflow."""
    workflow_id: str  # Workflow identifier (relative path)
    root_node: ActivityNode  # Root activity node
    variables: list[dict[str, Any]] = field(default_factory=list)  # Workflow variables
    arguments: list[dict[str, Any]] = field(default_factory=list)  # Workflow arguments
    imports: list[str] = field(default_factory=list)  # Namespace imports
    content_hash: str = ""  # Content hash for change detection

    # Metadata
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    extractor_version: str = "0.1.0"

    def get_all_nodes(self) -> list[ActivityNode]:
        """Get all nodes in the tree."""
        nodes = [self.root_node]
        nodes.extend(self.root_node.get_all_descendants())
        return nodes

    def find_node_by_id(self, node_id: str) -> ActivityNode | None:
        """Find a node by its ID."""
        for node in self.get_all_nodes():
            if node.node_id == node_id:
                return node
        return None

    def get_nodes_by_type(self, activity_type: str) -> list[ActivityNode]:
        """Get all nodes of a specific activity type."""
        return [node for node in self.get_all_nodes()
                if node.activity_type == activity_type]


@dataclass
class WorkflowControlFlow:
    """Control flow graph for a workflow."""
    workflow_id: str
    edges: list[ControlFlowEdge] = field(default_factory=list)

    def add_edge(self, from_id: str, to_id: str, edge_type: str, condition: str = None) -> None:
        """Add a control flow edge."""
        edge = ControlFlowEdge(from_id, to_id, edge_type, condition)
        self.edges.append(edge)

    def get_successors(self, node_id: str) -> list[str]:
        """Get all successor nodes for a given node."""
        return [edge.to_node_id for edge in self.edges if edge.from_node_id == node_id]

    def get_predecessors(self, node_id: str) -> list[str]:
        """Get all predecessor nodes for a given node."""
        return [edge.from_node_id for edge in self.edges if edge.to_node_id == node_id]


@dataclass
class WorkflowResources:
    """Resource references for a workflow."""
    workflow_id: str
    references: list[ResourceReference] = field(default_factory=list)

    def add_reference(self, resource_type: str, name: str, value: str,
                     node_id: str, property_name: str, is_dynamic: bool = False) -> None:
        """Add a resource reference."""
        ref = ResourceReference(
            resource_type=resource_type,
            resource_name=name,
            resource_value=value,
            node_id=node_id,
            property_name=property_name,
            is_dynamic=is_dynamic
        )
        self.references.append(ref)

    def get_by_type(self, resource_type: str) -> list[ResourceReference]:
        """Get all references of a specific type."""
        return [ref for ref in self.references if ref.resource_type == resource_type]
