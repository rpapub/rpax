# ADR-005: Graph Visualization Options

**Status:** Implemented (Updated 2025-09-08)  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

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

## Amendment Notes (2025-09-08)

**What Changed**: Status updated from Proposed to Implemented, added implementation status
**Why Amended**: Graph visualization system has been implemented with Mermaid support
**Impact**: Confirms graph generation is operational for documentation and analysis

## Implementation Status (Updated 2025-09-08)

* **v0.0.2:** ✅ Mermaid support implemented and operational
* **v0.0.3:** ✅ Graph generation via `rpax graph` command working
* **Future:** Graphviz support for large/CI diagrams (architecture ready)

## Consequences

* Wider coverage: docs-friendly + scalable CI output.
* Adds Graphviz runtime dependency (documented, optional).
* Configuration surface: `output.formats` accepts `"mermaid"` and `"graphviz"`.
* Styling conventions required (root highlighting, edge annotations, folder clustering).

## Related ADRs

* ADR-003: Graph rendering accessed via `graph` command
* ADR-013: Diagram element standardization across both renderers
* ADR-015: Implementation defers Graphviz to v0.2+ (emit .dot files only initially)
