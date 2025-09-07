# ADR-013: Diagram Elements (Standardization)

**Status:** Proposed

## Context

Graphs appear in docs/CI. Consistent elements and styling needed across renderers. (Related: ADR5.)

## Decision

Define renderer-agnostic diagram semantics now; support both Mermaid and Graphviz; keep styling minimal and mappable.

## Scope

* Nodes (workflows), Edges (invocations), Clusters (folders/modules), Legends.
* Optional: intra-workflow control-flow (CFG) views.

## Elements

* **Node = workflow** identified by `wfId` (repo-relative).
* **Roles:** entry point, test root, orphan.
* **Edge kinds:** invoke, invoke-missing, invoke-dynamic.
* **Clusters:** group by top-level folder (`Framework/`, `Tests/`, `Activities/`).
* **CFG (optional):** sequence-next, branch-then/else, case, loop-back, catch/finally.

## Styling (semantic → visual)

* Entry point: emphasized node.
* Test root: de-emphasized or variant border.
* Orphan: muted.
* Edges: solid = invoke; dashed = missing; dotted = dynamic.
* Cycles: annotate on edge.
* Roots: highlight fan-out view.

## Legend

* Include a standard legend in every diagram (nodes, edge styles, cycle note).

## Outputs

* Diagram specs derived from artifacts (no re-parse).
* Per-root call graph, whole-project graph, optional per-workflow CFG.
* Renderer selection via config; defaults to Mermaid; Graphviz optional for large graphs.

## Non-Goals

* Custom per-project themes.
* Arbitrary node shapes per activity type.

## Consequences

* Consistent visuals across tools.
* Easy renderer swaps.
* Minimal styling reduces maintenance.

## Acceptance

* Same graph renders equivalently in both renderers (semantics preserved).
* Legend present and accurate.
* Edge styles match kinds; roles consistently marked.
* Clusters reflect folder structure deterministically.

## Roadmap Phase

* **v0.1:** Mermaid diagram element standards
* **v0.2:** Extended support for Graphviz elements

## Open Points

* Thresholds for switching to Graphviz on large graphs.
* Exact visual for "entry point" and "test root" within Mermaid constraints.

## Related ADRs

* ADR-003: Diagram generation via `graph` command
* ADR-005: Implements standardized elements across Mermaid/Graphviz renderers
* ADR-009: Uses activity data from parser artifacts for CFG views
