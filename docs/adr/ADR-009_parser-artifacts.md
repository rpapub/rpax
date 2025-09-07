# ADR-009: Parser Artifacts (Activities, CFG, Invokes)

**Status:** Accepted  
**Date:** 2025-09-07  
**Updated:** Layer 1 Stabilization findings - Activity entity as first-class artifact

## Context

Downstream layers require rich, deterministic data beyond call paths: full activity trees, control-flow edges, resource references, and cross-workflow invokes.

**Layer 1 Stabilization Finding (2025-09-07):** During corpus testing with FrozenChlorine project, we discovered that **individual Activity instances are the missing core entity**. Current data model has structural trees but lacks complete activity configurations with business logic - the true atoms of interest for MCP/LLM consumption.

> Relation: ADR-007 (parser scope, later strict schemas) and ADR-008 (lenient v0 event capture). ADR-009 defines the **target artifact set**; initial population may derive from lenient streams until schemas stabilize.

## Scope

UiPath **Process** and **Library** projects. Input: `project.json` + all `*.xaml`. No validation, rendering, MCP.

## Decision

Adopt the following **data-only** artifacts as the canonical target set; emit deterministically; preserve ordering; include provenance. Initial phase may back these files with lenient records (ADR-008), then harden to strict schemas (ADR-007 transition gates).

## Artifact Inventory

* `manifest.json` — project meta: name, type, language, targetFramework, roots (main + entryPoints), dependencies.
* `workflows.index.json` — catalog of workflows (`wfId`, `relPath`, `hash`, summary of variables/arguments/imports).
* `invocations.jsonl` — cross-workflow edges with kind: `invoke|invoke-missing|invoke-dynamic`, plus raw expression.
* **`activities.instances/<wfId>.json`** — **NEW: Complete activity configurations with all arguments, properties, and business logic** (first-class Activity entities).
* `activities.tree/<wfId>.json` — full activity tree; node order preserved (structural hierarchy).
* `activities.cfg/<wfId>.jsonl` — intra-workflow control-flow edges (e.g., `seq-next`, `branch-then/else`, `case`, `loop-back`, `catch`, `finally`).
* `activities.refs/<wfId>.json` — resource references (selectors, assets, queues, files, URLs).
* `metrics/<wfId>.json` — counts and simple measures (nodes, depth, loops, invokes, logs, try/catch, selectors).
* `paths/<root>.paths.jsonl` — flattened call paths per declared root.

## Extraction (per workflow)

### Activity Instances (NEW - Core Business Logic Entities)
* **Complete configuration:** All XAML attributes and properties captured per activity
* **Arguments extraction:** All activity arguments with names, types, values, and expressions  
* **Nested configuration:** Complex objects (Target, AssignOperations, ViewState) fully extracted
* **Business logic expressions:** UiPath Studio-valid VB.NET/C# expressions preserved as-is
* **Selector extraction:** FullSelector, FuzzySelector, TargetAnchorable configurations
* **Activity identity:** Stable `activityId` with workflow context and content hash
* **Parent-child relationships:** Complete hierarchy links for each activity instance

**Real-world example coverage:**
- `<uix:NClick ActivateBefore="True" ClickType="Single">` → Complete argument capture
- `<ui:GetIMAPMailMessages Server="[in_Config(...)]">` → Expression preservation  
- `<ui:ForEach Values="[CharacterList]">` → Collection binding extraction
- `<If Condition="[currentItem IsNot Nothing...]">` → Complex condition preservation

### Structural Artifacts (Existing)
* **Activity tree:** full structure; parent→children order (structural hierarchy only).
* **Nodes:** `type` (fully-qualified), `displayName`, stable `nodeId` (path-like), basic properties.
* **Flow constructs:** Sequence, Flowchart, StateMachine, Try/Catch, If, Switch, While/Do/ForEach/Parallel, Invoke Code/Method, Invoke Workflow.
* **Messaging/logging:** Log Message, Write Line, Comment.
* **UiPath specifics:** selectors, target apps, timeouts, ContinueOnError, RetryScope params.
* **Workflow scope:** variables (name, type, default, scope), arguments (direction/type/default), imports.
* **Invokes:** `InvokeWorkflowFile` literal targets; mark `invoke-missing` or `invoke-dynamic` with captured `raw`.

## Identification & Provenance

* `wfId` = repo-relative POSIX path `path/to/File.xaml`.
* `nodeId` = stable path-like locator (sibling indices).
* **`activityId`** = unique activity identifier: `{projectId}#{wfId}#{nodeId}#{activityHash}`
* Include content `hash` per workflow and per activity.
* Preserve `sap2010:WorkflowViewState.IdRef` under provenance when present.
* Record tool version, run timestamp, and config fingerprint at artifact root.

**Activity Identity Examples:**
```
f4aa3834#Process/Calculator/ClickListOfCharacters#Activity/Sequence/ForEach/Sequence/NApplicationCard/Sequence/If/Sequence/NClick#abc123ef
frozenchlorine-1082950b#StandardCalculator#Activity/Sequence/InvokeWorkflowFile_5#def456ab
```

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

## Implementation Roadmap

### Phase 1: Activity Instances Foundation (v0.1.0)
* **Extend XamlParser** (src/xaml_parser/) to extract complete activity configurations
* **Add ActivityInstance model** with arguments, configuration, business logic extraction
* **Generate activities.instances/*.json** artifacts during workflow parsing
* **Implement activity identity** with stable activityId generation
* **Schema validation** for Activity artifacts

### Phase 2: Integration & Testing (v0.1.1) 
* **Integrate with existing rpax parser** pipeline for artifact generation
* **Corpus validation** against FrozenChlorine, PurposefulPromethium projects
* **Performance optimization** for large workflows (1k+ activities)
* **Schema versioning** and backward compatibility

### Phase 3: MCP Integration (v0.1.2)
* **MCP resource exposure** of Activity instances for LLM consumption  
* **Cross-reference support** between activities, workflows, and invocations
* **Activity search and filtering** via Access API layer

## Consequences

### Benefits
* **Complete business logic capture**: Individual activities with all configuration for LLM analysis
* **Enables rich downstream tooling**: Documentation, CI rules, and MCP without re-parsing  
* **True MCP readiness**: First-class Activity entities provide atomic business logic units
* **Clear path**: From lenient capture (ADR-008) to strict, schema-backed artifacts (ADR-007)

### Implementation Costs
* **Additional parsing complexity**: Complete XAML extraction vs basic structural analysis
* **Increased storage requirements**: Full activity configurations vs summary data
* **Schema evolution**: Activity artifacts require comprehensive schema versioning
* **Performance considerations**: Activity-level parsing for large workflows (1k+ activities)

## Related ADRs

* **ADR-007**: Parser requirements driving these artifact definitions
* **ADR-008**: Phase 0 lenient capture feeds into these artifacts
* **ADR-010**: Validation layer consumes these artifacts
* **ADR-011**: Access API serves these artifacts over HTTP
* **ADR-012**: MCP layer exposes these as resources (now includes Activity entities)
* **ADR-014**: Identity scheme used throughout artifacts (extended for Activity identity)
* **ADR-031**: XAML parsing strategy provides foundation for complete Activity extraction

## Layer 1 Stabilization Evidence

**Corpus Testing Results (2025-09-07):**
- **FrozenChlorine project**: Identified 22 false positive invocations eliminated through visibility filtering
- **Real activity examples**: `<uix:NClick>`, `<ui:GetIMAPMailMessages>`, `<ui:ForEach>` with complete configurations
- **Business logic capture**: Complex expressions, selectors, nested configurations not represented in current model
- **MCP server need**: Individual activities are the atomic business logic units required for LLM understanding

**Architectural Gap Confirmed:**
- Current `activities.tree` captures hierarchy but not complete business logic
- Missing Activity entity prevents rich downstream analysis and MCP consumption
- Individual activities contain the true business value for automation understanding
