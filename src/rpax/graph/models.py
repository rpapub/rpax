"""Graph data models for visualization according to ADR-013."""

from dataclasses import dataclass, field
from enum import Enum


class NodeRole(str, Enum):
    """Node roles according to ADR-013."""
    ENTRY_POINT = "entry_point"
    TEST_ROOT = "test_root"
    ORPHAN = "orphan"
    WORKFLOW = "workflow"


class EdgeKind(str, Enum):
    """Edge kinds according to ADR-013."""
    INVOKE = "invoke"
    INVOKE_MISSING = "invoke-missing"
    INVOKE_DYNAMIC = "invoke-dynamic"


@dataclass
class NodeSpec:
    """Specification for a workflow node."""
    id: str  # Workflow identifier
    label: str  # Display label
    role: NodeRole
    path: str  # Repository-relative path
    cluster: str | None = None  # Cluster/folder grouping

    @property
    def safe_id(self) -> str:
        """Get ID safe for diagram rendering (alphanumeric + underscore)."""
        # Replace non-alphanumeric characters with underscores
        import re
        return re.sub(r"[^a-zA-Z0-9_]", "_", self.id)


@dataclass
class EdgeSpec:
    """Specification for a workflow invocation edge."""
    from_node: str  # Source workflow ID
    to_node: str    # Target workflow ID
    kind: EdgeKind
    label: str | None = None
    has_cycle: bool = False


@dataclass
class ClusterSpec:
    """Specification for a workflow cluster/folder."""
    id: str  # Cluster identifier
    label: str  # Display label
    nodes: set[str] = field(default_factory=set)  # Node IDs in cluster


@dataclass
class GraphSpec:
    """Complete graph specification for rendering."""
    title: str
    nodes: dict[str, NodeSpec] = field(default_factory=dict)
    edges: list[EdgeSpec] = field(default_factory=list)
    clusters: dict[str, ClusterSpec] = field(default_factory=dict)
    entry_points: set[str] = field(default_factory=set)  # Node IDs

    def add_node(self, node: NodeSpec) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

        # Add to cluster if specified
        if node.cluster:
            if node.cluster not in self.clusters:
                self.clusters[node.cluster] = ClusterSpec(
                    id=node.cluster,
                    label=node.cluster.replace("/", " / ")
                )
            self.clusters[node.cluster].nodes.add(node.id)

    def add_edge(self, edge: EdgeSpec) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_orphaned_nodes(self) -> set[str]:
        """Get nodes that are not reachable from entry points."""
        if not self.entry_points:
            return set()

        # Build adjacency list
        graph = {}
        for edge in self.edges:
            if edge.from_node not in graph:
                graph[edge.from_node] = set()
            graph[edge.from_node].add(edge.to_node)

        # DFS from entry points
        visited = set()

        def visit(node: str):
            if node in visited:
                return
            visited.add(node)
            for neighbor in graph.get(node, set()):
                visit(neighbor)

        for entry in self.entry_points:
            if entry in self.nodes:
                visit(entry)

        # Orphans are nodes not visited
        return set(self.nodes.keys()) - visited

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the graph."""
        # Build adjacency list
        graph = {}
        for edge in self.edges:
            if edge.kind == EdgeKind.INVOKE:  # Only consider actual invocations
                if edge.from_node not in graph:
                    graph[edge.from_node] = set()
                graph[edge.from_node].add(edge.to_node)

        visited = set()
        rec_stack = set()
        cycles = []

        def has_cycle_util(node: str, path: list[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    has_cycle_util(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                has_cycle_util(node, [])

        return cycles

    def mark_cycles(self) -> None:
        """Mark edges that participate in cycles."""
        cycles = self.detect_cycles()
        cycle_edges = set()

        for cycle in cycles:
            for i in range(len(cycle) - 1):
                cycle_edges.add((cycle[i], cycle[i + 1]))

        for edge in self.edges:
            if (edge.from_node, edge.to_node) in cycle_edges:
                edge.has_cycle = True
