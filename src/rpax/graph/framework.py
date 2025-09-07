"""Graph generation framework implementing ADR-005 and ADR-013."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from ..config import RpaxConfig
from ..validation.framework import ArtifactSet
from .models import EdgeKind, EdgeSpec, GraphSpec, NodeRole, NodeSpec

logger = logging.getLogger(__name__)


class DiagramElement:
    """Enum-like class for diagram elements from ADR-013."""
    NODE = "node"
    EDGE = "edge"
    CLUSTER = "cluster"
    LEGEND = "legend"


class GraphRenderer(ABC):
    """Abstract base class for graph renderers."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Name of the output format."""
        pass

    @abstractmethod
    def render(self, spec: GraphSpec) -> str:
        """Render graph specification to string format."""
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Get file extension for this format."""
        pass


class GraphGenerator:
    """Main graph generation framework implementing ADR-005."""

    def __init__(self, config: RpaxConfig):
        self.config = config
        self.renderers: dict[str, GraphRenderer] = {}

    def add_renderer(self, renderer: GraphRenderer) -> None:
        """Add a graph renderer."""
        self.renderers[renderer.format_name] = renderer

    def generate_from_artifacts(self, artifacts_dir: Path, graph_type: str = "calls") -> GraphSpec:
        """Generate graph specification from parser artifacts.
        
        Args:
            artifacts_dir: Directory containing parser artifacts
            graph_type: Type of graph - 'calls', 'paths', 'project'
            
        Returns:
            GraphSpec ready for rendering
        """
        logger.info(f"Generating {graph_type} graph from artifacts in {artifacts_dir}")

        # Load artifacts
        artifacts = ArtifactSet.load(artifacts_dir)

        if not artifacts.manifest or not artifacts.workflows_index:
            raise ValueError("Required artifacts (manifest.json, workflows.index.json) not found")

        # Create graph spec based on type
        if graph_type == "calls":
            return self._generate_call_graph(artifacts)
        elif graph_type == "paths":
            return self._generate_path_graph(artifacts)
        elif graph_type == "project":
            return self._generate_project_overview(artifacts)
        else:
            raise ValueError(f"Unknown graph type: {graph_type}")

    def render_graph(self, spec: GraphSpec, format_name: str = "mermaid") -> str:
        """Render graph specification to string.
        
        Args:
            spec: Graph specification to render
            format_name: Output format ('mermaid', 'graphviz')
            
        Returns:
            Rendered graph as string
        """
        if format_name not in self.renderers:
            available = list(self.renderers.keys())
            raise ValueError(f"Unknown format '{format_name}'. Available: {available}")

        renderer = self.renderers[format_name]
        logger.info(f"Rendering graph with {renderer.format_name} renderer")
        return renderer.render(spec)

    def _generate_call_graph(self, artifacts: ArtifactSet) -> GraphSpec:
        """Generate call graph from invocations."""
        spec = GraphSpec(title="Workflow Call Graph")

        # Add all workflows as nodes
        workflows = artifacts.workflows_index.get("workflows", [])
        for workflow in workflows:
            node = self._create_node_from_workflow(workflow, artifacts)
            spec.add_node(node)

        # Add entry points from manifest
        entry_points = artifacts.manifest.get("entryPoints", [])
        main_workflow = artifacts.manifest.get("mainWorkflow")

        if main_workflow:
            spec.entry_points.add(main_workflow)

        for entry in entry_points:
            if isinstance(entry, dict) and "filePath" in entry:
                # Find workflow by file path
                for workflow in workflows:
                    if workflow.get("relativePath") == entry["filePath"]:
                        spec.entry_points.add(workflow["id"])
                        break

        # Add edges from invocations
        for invocation in artifacts.invocations:
            edge = self._create_edge_from_invocation(invocation)
            if edge:
                spec.add_edge(edge)

        # Mark orphaned nodes
        orphaned = spec.get_orphaned_nodes()
        for node_id in orphaned:
            if node_id in spec.nodes:
                spec.nodes[node_id].role = NodeRole.ORPHAN

        # Mark cycles
        spec.mark_cycles()

        logger.info(f"Generated call graph with {len(spec.nodes)} nodes and {len(spec.edges)} edges")
        return spec

    def _generate_path_graph(self, artifacts: ArtifactSet) -> GraphSpec:
        """Generate path-based graph from entry points."""
        # For now, this is the same as call graph but could be filtered
        return self._generate_call_graph(artifacts)

    def _generate_project_overview(self, artifacts: ArtifactSet) -> GraphSpec:
        """Generate high-level project overview."""
        spec = self._generate_call_graph(artifacts)
        spec.title = "Project Overview"

        # Could add summary statistics, key metrics, etc.
        return spec

    def _create_node_from_workflow(self, workflow: dict, artifacts: ArtifactSet) -> NodeSpec:
        """Create node specification from workflow data."""
        workflow_id = workflow.get("id", "")
        relative_path = workflow.get("relativePath", "")
        display_name = workflow.get("displayName", workflow.get("fileName", ""))

        # Determine cluster from path
        cluster = None
        if "/" in relative_path:
            cluster = str(Path(relative_path).parent)

        # Determine role (will be updated for entry points and orphans)
        role = NodeRole.WORKFLOW

        return NodeSpec(
            id=workflow_id,
            label=display_name,
            role=role,
            path=relative_path,
            cluster=cluster
        )

    def _create_edge_from_invocation(self, invocation: dict) -> EdgeSpec | None:
        """Create edge specification from invocation data."""
        kind_str = invocation.get("kind", "")
        from_node = invocation.get("from", "")
        to_node = invocation.get("to", "")

        if not from_node or not to_node:
            return None

        # Map kind string to enum
        kind_map = {
            "invoke": EdgeKind.INVOKE,
            "invoke-missing": EdgeKind.INVOKE_MISSING,
            "invoke-dynamic": EdgeKind.INVOKE_DYNAMIC
        }

        kind = kind_map.get(kind_str, EdgeKind.INVOKE)

        return EdgeSpec(
            from_node=from_node,
            to_node=to_node,
            kind=kind
        )
