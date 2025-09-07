"""Graph visualization module for rpax.

Implements diagram generation according to ADR-005 and ADR-013 with support
for Mermaid (primary) and Graphviz (future) output formats.
"""

from .framework import DiagramElement, EdgeKind, GraphGenerator, NodeRole
from .mermaid import MermaidRenderer
from .models import ClusterSpec, EdgeSpec, GraphSpec, NodeSpec

__all__ = [
    "GraphGenerator",
    "DiagramElement",
    "NodeRole",
    "EdgeKind",
    "MermaidRenderer",
    "GraphSpec",
    "NodeSpec",
    "EdgeSpec",
    "ClusterSpec"
]
