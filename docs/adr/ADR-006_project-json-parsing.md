# ADR-006: `project.json` Parsing Strategy

**Status:** Implemented (Updated 2025-09-08)  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Context

UiPath `project.json` defines roots/metadata needed for analysis, docs, CI.

## Options

### Option A — Strict (single source of truth)

* Required file; parse canonical subset; normalize paths; enum-validate; ignore unknown keys.

### Option B — Heuristic fallback (no `project.json`)

* Infer roots from filesystem; best-effort parsing.

### Option C — Hybrid (strict + opt-in fallback)

* Strict by default; fallback via flag.

## Decision

* **Go:** Option A.
* **No-Go:** Options B/C for v1.

### Canonical keys (extracted/standardized)

* **Metadata:** `.name`, `.projectId`, `.description`, `.projectVersion`, `.schemaVersion`, `.studioVersion`.
* **Roots:** `.main`, `.entryPoints[*].filePath`, `.entryPoints[*].uniqueId`, `.entryPoints[*].input`, `.entryPoints[*].output`.
* **Design:** `.expressionLanguage`, `.targetFramework`, `.designOptions.outputType`, `.designOptions.projectProfile`, `.designOptions.modernBehavior`.
* **Dependencies:** `.dependencies` (package → version).
* **Runtime:** `.runtimeOptions.executionType`, `.runtimeOptions.isAttended`, `.runtimeOptions.requiresUserInteraction`, `.runtimeOptions.supportsPersistence`, `.runtimeOptions.excludedLoggedData[*]`.
* **Tests:** `.designOptions.fileInfoCollection[*].fileName`, `.testCaseId`, `.testCaseType`, `.dataVariationFilePath`.

### Validation rules

* Missing/invalid `project.json` ⇒ fail.
* Enums checked (e.g., `process|library`, `Windows|Windows-Legacy`).
* Unknown keys ignored.

### Normalization

* Resolve and canonicalize paths (repo-relative, POSIX).
* Treat all `.entryPoints[*].filePath` as roots; `.main` as primary root.

## Consequences

* Deterministic roots/metadata; simpler CI.
* Projects with stale `project.json` must be fixed.
* Future changes require schema/version updates.

## Implications

* **Graphing:** roots from `.entryPoints[*].filePath`; tests may become secondary roots.
* **Docs:** surface metadata/deps; link diagrams to declared roots.
* **Diff/CI:** stable identifiers enable change detection; show dependency drift.

## Amendment Notes (2025-09-08)

**What Changed**: Status updated from Proposed to Implemented, added implementation status
**Why Amended**: Project.json parsing strategy has been implemented and is operational
**Impact**: Confirms project metadata extraction is working in production

## Implementation Status (Updated 2025-09-08)

* **v0.0.1:** ✅ Core project.json parsing implemented with metadata extraction
* **v0.0.2:** ✅ Root discovery and path normalization operational
* **v0.0.3:** ✅ Complete project metadata fidelity with multi-project support

## Open Questions

1. Treat test entries as roots by default or behind a flag?
2. Required vs optional handling of `.entryPoints[*].input/output`?
3. Enum sets for `expressionLanguage` / `targetFramework` scope?

## Related ADRs

* ADR-007: Parser layer uses this as primary input source
* ADR-009: Generates manifest.json artifact from this data
* ADR-014: projectSlug generation from project.json metadata
