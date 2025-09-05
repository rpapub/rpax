# ADR-009: Parser Artifacts (Activities, CFG, Invokes)

**Status:** Proposed

## Context

Downstream layers require rich, deterministic data beyond call paths: full activity trees, control-flow edges, resource references, and cross-workflow invokes.

> Relation: ADR-007 (parser scope, later strict schemas) and ADR-008 (lenient v0 event capture). ADR-009 defines the **target artifact set**; initial population may derive from lenient streams until schemas stabilize.

## Scope

UiPath **Process** and **Library** projects. Input: `project.json` + all `*.xaml`. No validation, rendering, MCP.

## Decision

Adopt the following **data-only** artifacts as the canonical target set; emit deterministically; preserve ordering; include provenance. Initial phase may back these files with lenient records (ADR-008), then harden to strict schemas (ADR-007 transition gates).

## Artifact Inventory

* `manifest.json` — project meta: name, type, language, targetFramework, roots (main + entryPoints), dependencies.
* `workflows.index.json` — catalog of workflows (`wfId`, `relPath`, `hash`, summary of variables/arguments/imports).
* `invocations.jsonl` — cross-workflow edges with kind: `invoke|invoke-missing|invoke-dynamic`, plus raw expression.
* `activities.tree/<wfId>.json` — full activity tree; node order preserved.
* `activities.cfg/<wfId>.jsonl` — intra-workflow control-flow edges (e.g., `seq-next`, `branch-then/else`, `case`, `loop-back`, `catch`, `finally`).
* `activities.refs/<wfId>.json` — resource references (selectors, assets, queues, files, URLs).
* `metrics/<wfId>.json` — counts and simple measures (nodes, depth, loops, invokes, logs, try/catch, selectors).
* `paths/<root>.paths.jsonl` — flattened call paths per declared root.

## Extraction (per workflow)

* **Activity tree:** full structure; parent→children order.
* **Nodes:** `type` (fully-qualified), `displayName`, stable `nodeId` (path-like), `properties` (lenient), activity arguments.
* **Flow constructs:** Sequence, Flowchart, StateMachine, Try/Catch, If, Switch, While/Do/ForEach/Parallel, Invoke Code/Method, Invoke Workflow.
* **Messaging/logging:** Log Message, Write Line, Comment.
* **UiPath specifics:** selectors, target apps, timeouts, ContinueOnError, RetryScope params.
* **Workflow scope:** variables (name, type, default, scope), arguments (direction/type/default), imports.
* **Invokes:** `InvokeWorkflowFile` literal targets; mark `invoke-missing` or `invoke-dynamic` with captured `raw`.

## Identification & Provenance

* `wfId` = repo-relative POSIX path `path/to/File.xaml`.
* `nodeId` = stable path-like locator (sibling indices).
* Include content `hash` per workflow.
* Preserve `sap2010:WorkflowViewState.IdRef` under provenance when present.
* Record tool version, run timestamp, and config fingerprint at artifact root.

## Ordering & Determinism

* Child order as in XAML.
* Deterministic traversal and sorted catalogs.
* Byte-stable outputs on identical inputs.

## Tolerance (parser-only)

* Unknown properties retained under `properties` or `extras`.
* Missing targets recorded as `invoke-missing`; dynamic expressions recorded as `invoke-dynamic` with `raw`.
* Cycles detected and annotated; no resolution.

## Performance Targets

* ≥1k workflows per project within practical limits; parallel parsing permitted.
* Artifacts written atomically to avoid partial reads by consumers.

## Consequences

* Enables documentation, CI rules, and MCP without re-parsing.
* Clear path from lenient capture (ADR-008) to strict, schema-backed artifacts (ADR-007).
* Additional effort required to define and version schemas for each artifact.
