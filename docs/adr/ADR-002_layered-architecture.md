# ADR-002: Layered Architecture for UiPath Workflow Analysis

**Status:** Proposed

## Context

Need modular analysis of UiPath/WF projects with clear evolution path toward integrations.

## Layers (correct order)

1. **Parser** — discover `.xaml`, normalize IDs, emit canonical artifacts (graphs/manifests/indices).
2. **Validation & CI** — apply configurable gates (missing/dynamic invokes, cycles, orphans) for pipelines.
3. **Access API (pre-MCP)** — lightweight, read-only HTTP interface over artifacts for tools/CI; files remain source of truth.
4. **MCP/Integration** — stable external resource contracts (URIs/schemas) for broader ecosystem consumption.

## Decision

* **Go:** Explore/prototype all four layers; define clear artifact contracts between layers.
* **No-Go:** Do not couple Access API to MCP yet; retain files as canonical source.

## Consequences

* Enables incremental delivery (1→2→3→4).
* Adds interface documentation overhead.
* Deep semantic analysis and rule DSL remain future work.
