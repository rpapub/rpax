"""Mermaid diagram renderer implementing ADR-005 and ADR-013."""

import logging

from .framework import GraphRenderer
from .models import EdgeKind, GraphSpec, NodeRole

logger = logging.getLogger(__name__)


class MermaidRenderer(GraphRenderer):
    """Mermaid diagram renderer for workflow graphs."""

    @property
    def format_name(self) -> str:
        return "mermaid"

    def get_file_extension(self) -> str:
        return ".mmd"

    def render(self, spec: GraphSpec) -> str:
        """Render graph specification as Mermaid flowchart."""
        lines = []

        # Header
        lines.append("flowchart TD")
        lines.append(f"    %% {spec.title}")
        lines.append("")

        # Nodes
        lines.append("    %% Nodes")
        for node in spec.nodes.values():
            node_line = self._render_node(node, spec.entry_points)
            lines.append(f"    {node_line}")

        lines.append("")

        # Edges
        if spec.edges:
            lines.append("    %% Edges")
            for edge in spec.edges:
                edge_line = self._render_edge(edge)
                lines.append(f"    {edge_line}")
            lines.append("")

        # Clusters/Subgraphs (if any)
        for cluster in spec.clusters.values():
            if len(cluster.nodes) > 1:  # Only create subgraphs for multiple nodes
                lines.append(f'    subgraph {cluster.id}["{cluster.label}"]')
                for node_id in sorted(cluster.nodes):
                    if node_id in spec.nodes:
                        node = spec.nodes[node_id]
                        lines.append(f"        {node.safe_id}")
                lines.append("    end")
                lines.append("")

        # Styling based on node roles
        lines.extend(self._render_styling(spec))

        # Legend
        lines.extend(self._render_legend(spec))

        return "\n".join(lines)

    def _render_node(self, node, entry_points: set[str]) -> str:
        """Render a single node."""
        safe_id = node.safe_id
        label = self._escape_label(node.label)

        # Choose node shape based on role
        if node.role == NodeRole.ENTRY_POINT or node.id in entry_points:
            # Entry points: hexagon
            return f"{safe_id}{{{{{label}}}}}"
        elif node.role == NodeRole.TEST_ROOT:
            # Test roots: stadium
            return f"{safe_id}[{label}]"
        elif node.role == NodeRole.ORPHAN:
            # Orphans: plain rectangle with dashed border (styled separately)
            return f"{safe_id}[{label}]"
        else:
            # Regular workflows: rounded rectangle
            return f"{safe_id}({label})"

    def _render_edge(self, edge) -> str:
        """Render a single edge."""
        from_safe = self._get_safe_id(edge.from_node)
        to_safe = self._get_safe_id(edge.to_node)

        # Choose arrow style based on edge kind
        if edge.kind == EdgeKind.INVOKE:
            arrow = "-->" if not edge.has_cycle else "-.->|cycle|"
        elif edge.kind == EdgeKind.INVOKE_MISSING:
            arrow = "-.->|missing|"
        elif edge.kind == EdgeKind.INVOKE_DYNAMIC:
            arrow = "-.->|dynamic|"
        else:
            arrow = "-->"

        if edge.label and not edge.has_cycle:
            return f"{from_safe} {arrow}|{self._escape_label(edge.label)}| {to_safe}"
        else:
            return f"{from_safe} {arrow} {to_safe}"

    def _render_styling(self, spec: GraphSpec) -> list:
        """Render node styling based on roles."""
        lines = []

        if any(node.role == NodeRole.ENTRY_POINT or node.id in spec.entry_points for node in spec.nodes.values()):
            lines.append("    %% Entry point styling")
            for node in spec.nodes.values():
                if node.role == NodeRole.ENTRY_POINT or node.id in spec.entry_points:
                    lines.append("    classDef entryPoint fill:#e1f5fe,stroke:#01579b,stroke-width:2px")
                    lines.append(f"    class {node.safe_id} entryPoint")
                    break

        if any(node.role == NodeRole.ORPHAN for node in spec.nodes.values()):
            lines.append("    %% Orphan styling")
            lines.append("    classDef orphan fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray: 3 3")
            for node in spec.nodes.values():
                if node.role == NodeRole.ORPHAN:
                    lines.append(f"    class {node.safe_id} orphan")

        if any(node.role == NodeRole.TEST_ROOT for node in spec.nodes.values()):
            lines.append("    %% Test root styling")
            lines.append("    classDef testRoot fill:#fff3e0,stroke:#ef6c00,stroke-width:1px")
            for node in spec.nodes.values():
                if node.role == NodeRole.TEST_ROOT:
                    lines.append(f"    class {node.safe_id} testRoot")

        return lines

    def _render_legend(self, spec: GraphSpec) -> list:
        """Render legend as comments (Mermaid doesn't have native legend support)."""
        lines = []
        lines.append("    %% Legend:")

        # Node types present
        node_types = set(node.role for node in spec.nodes.values())
        if spec.entry_points:
            node_types.add("entry_point")

        for role in sorted(node_types):
            if role == NodeRole.ENTRY_POINT or "entry_point" in str(role):
                lines.append("    %% ◊ Entry Point - Main workflow(s)")
            elif role == NodeRole.ORPHAN:
                lines.append("    %% ◇ Orphan - Not reachable from entry points")
            elif role == NodeRole.TEST_ROOT:
                lines.append("    %% ⬜ Test Root - Test workflow")
            elif role == NodeRole.WORKFLOW:
                lines.append("    %% ⬭ Workflow - Standard workflow")

        # Edge types present
        edge_types = set(edge.kind for edge in spec.edges)
        if edge_types:
            lines.append("    %% ")
            lines.append("    %% Edge types:")
            for kind in sorted(edge_types):
                if kind == EdgeKind.INVOKE:
                    lines.append("    %% ──→ Invoke - Direct workflow call")
                elif kind == EdgeKind.INVOKE_MISSING:
                    lines.append("    %% ·─→ Missing - Referenced workflow not found")
                elif kind == EdgeKind.INVOKE_DYNAMIC:
                    lines.append("    %% ·─→ Dynamic - Workflow path determined at runtime")

        # Cycles
        if any(edge.has_cycle for edge in spec.edges):
            lines.append("    %% ·─→ Cycle - Circular workflow dependency")

        return lines

    def _escape_label(self, label: str) -> str:
        """Escape label for Mermaid rendering."""
        if not label:
            return ""

        # Replace characters that can break Mermaid syntax
        label = label.replace('"', "'")  # Replace quotes
        label = label.replace("[", "(")    # Replace brackets
        label = label.replace("]", ")")
        label = label.replace("{", "(")    # Replace braces
        label = label.replace("}", ")")
        label = label.replace("|", ":")    # Replace pipes

        # Truncate very long labels
        if len(label) > 30:
            label = label[:27] + "..."

        return label

    def _get_safe_id(self, node_id: str) -> str:
        """Get safe ID for node reference."""
        import re
        return re.sub(r"[^a-zA-Z0-9_]", "_", node_id)
