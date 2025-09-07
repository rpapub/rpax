# ADR-005: Graph Visualization Options

**Status:** Proposed

## Context

Visualization needed for workflow invocation graphs in docs and CI.

## Options

### Option A — Mermaid

**Pros:** markdown-friendly; native support in GitHub/GitLab/MkDocs; easy to tweak.
**Cons:** limited layouts; slow on very large graphs; best for HTML/MD.
**Best for:** READMEs, docs, quick inspection.

### Option B — Graphviz

**Pros:** mature layouts (`dot`, `neato`, etc.); handles dense graphs; exports SVG/PNG/PDF.
**Cons:** external dependency; `.dot` less human-friendly; extra export step.
**Best for:** CI artifacts, large projects, publication-quality diagrams.

## Decision

* **Go:** Implement **both** options.
* **Go:** Default = **Mermaid**; optional **Graphviz** export for large/CI diagrams.
* **No-Go:** Additional graph libs (D3/Cytoscape/Vis.js) for this phase.

## Roadmap Phase

* **v0.1:** Mermaid support for GitHub/docs integration
* **v0.2:** Optional Graphviz support for large/CI diagrams

## Consequences

* Wider coverage: docs-friendly + scalable CI output.
* Adds Graphviz runtime dependency (documented, optional).
* Configuration surface: `output.formats` accepts `"mermaid"` and `"graphviz"`.
* Styling conventions required (root highlighting, edge annotations, folder clustering).

## Related ADRs

* ADR-003: Graph rendering accessed via `graph` command
* ADR-013: Diagram element standardization across both renderers
* ADR-015: Implementation defers Graphviz to v0.2+ (emit .dot files only initially)
