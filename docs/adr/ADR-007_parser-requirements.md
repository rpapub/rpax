# ADR7: Parser Requirements

**Status:** Proposed

## Context

Parser layer extracts and normalizes UiPath Process/Library data into canonical artifacts for downstream layers.

> **ADR-008 link:** Use **lenient, append-only JSONL** *temporarily*, then **switch to strict, schema-backed canonical artifacts**.

## Scope

Data extraction, normalization, canonical artifact emission. No validation, rendering, summarization, or MCP export.

## Inputs

* `project.json` (mandatory).
* All `*.xaml` under root, excluding: `.local/**`, `.settings/**`, `.screenshots/**`, `TestResults/**`.
* Config: project root path (default `.`).

## Responsibilities

1. **Project metadata**  
   Parse `project.json`; extract name, type, version, language, targetFramework, dependencies, entryPoints; normalize POSIX paths.

2. **Workflow discovery**  
   Enumerate `*.xaml`; assign `wfId` = repo-relative path; compute stable hash; extract declared arguments (In/Out/InOut, type, name).

3. **Invocation resolution**  
   Detect `InvokeWorkflowFile`; resolve literal targets relative to caller; record edges as `invoke`, `invoke-missing`, or `invoke-dynamic`; preserve raw string/expression.

4. **Graph construction**  
   Build directed graph; identify roots from `project.json` (`.main` + `.entryPoints[*]`); expand paths per root; detect and annotate cycles (no resolution).

5. **Activity extraction**  
   Parse each workflow’s XAML activity tree; capture node type, displayName, stable `nodeId`, and properties; preserve parent–child order.  
   - Record control-flow constructs (Sequence, If, While, Switch, Flowchart, Try/Catch).  
   - Extract workflow-scope variables, arguments, and imports.  
   - Capture intra-workflow control-flow edges (seq-next, branch, loop-back).  
   - Collect references to external resources (selectors, assets, queues, files, URLs).  
   - Store unknown or complex properties in a lenient `properties` bag for later interpretation.

## Outputs (phased)

**Phase 0 (ADR-008):**  
Lenient JSONL event streams (append-only, deterministic order, tolerant of missing/unknown fields).

**Phase 1 (target):**  
Strict JSON/JSONL **canonical artifacts** with **JSON Schemas**; deterministic, validated, and versioned.

* `manifest.json` — project metadata, roots, dependencies.
* `workflows.index.json` — workflows with `wfId`, hash, arguments, variables, imports.
* `invocations.jsonl` — cross-workflow edges with `kind` (`invoke`, `invoke-missing`, `invoke-dynamic`).
* `paths/<root>.paths.jsonl` — flattened call sequences per entry point.
* `activities.tree/<wfId>.json` — full activity tree for each workflow (nodes, properties, parent→child order).
* `activities.cfg/<wfId>.jsonl` — intra-workflow control-flow edges (seq-next, branch, loop-back, catch/finally).
* `activities.refs/<wfId>.json` — extracted external references (selectors, assets, queues, files, URLs).
* `metrics/<wfId>.json` — counts and summary metrics (node count, depth, invokes, loops, logs, selectors).

## Constraints

* Success/failure based only on parseability.
* Deterministic results across environments.
* No dependency on UiPath Studio/runtime.

## Non-Functional

* Performance: ≥1000 workflows in ≤5s (commodity hardware).
* Determinism: stable ordering and hashes.
* Extensibility: artifacts include `schemaVersion`.

## Out of Scope

Validation, diagram/rendering, summaries, MCP export, heuristic/dynamic path resolution beyond literal handling, parsing `.cs` (only acknowledge presence).

## Prioritization (MoSCoW)

* **Must:** mandatory `project.json`; metadata extraction; POSIX path normalization; workflow discovery; hashing; literal invoke resolution; edge emission; graph + path expansion; cycle annotation; deterministic artifacts.
* **Should:** argument direction/type capture; test roots listing; large-repo performance optimizations.
* **Could:** heuristic hints for common dynamic patterns (flagged, not resolved); optional test roots as secondary roots.
* **Won’t (v1):** dynamic expression evaluation; coded workflow parsing; vendor runtime integration.

## Decision

* **Go:** Start with **Phase 0** (lenient JSONL per ADR-008).
* **Go:** Commit to **Phase 1**: introduce schemas and strict canonical artifacts.
* **Gate to switch:**

  * Corpus coverage ≥ **50 projects** across **process/library**.
  * Literal invoke resolution ≥ **95%** on corpus.
  * Field stability report shows ≥ **90%** unchanged across two runs per project.
* **Transition plan:**

  * Publish **both** formats for one release cycle.
  * Mark lenient streams **deprecated** upon schema v1 publish.
  * Enforce strict validation in next minor release.

## Consequences

* Clear contracts for downstream layers; simplified CI wiring.
* Projects with stale or malformed `project.json` require correction.
* Dynamic invokes remain flagged, not resolved.

## Acceptance Criteria

* Phase 0: zero crashes; append-only JSONL emitted for corpus; deterministic ordering.
* Switch readiness: gates met; draft **schema v1** ready; migration notes prepared.
* Phase 1: strict artifacts validate cleanly on corpus; CI uses schemas.

## Roadmap Phase

* **v0.0.1:** Phase 0 lenient JSONL implementation
* **v0.1:** Phase 1 transition to strict canonical artifacts with schemas

## Open Questions

* Treat test entries as roots by default or behind a flag.
* Required vs optional capture of `.entryPoints[*].input/output`.
* Enumerations for `expressionLanguage` and `targetFramework` scope and values.

## Related ADRs

* ADR-001: Implements pattern-matching approach for XAML parsing
* ADR-006: Uses project.json as mandatory input
* ADR-008: Phase 0 lenient capture strategy  
* ADR-009: Target artifact specification
* ADR-014: Identity model for wfId and content hashing
* ADR-015: Python stack implementing these requirements
