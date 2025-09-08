# ADR-008: Parser v0 — Lenient, Append-Only Telemetry

**Status:** Implemented (Updated 2025-09-08)  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Context

Early exploration across many UiPath/WF projects requires flexible capture of observations and errors before locking schemas (see ADR7 for eventual strict artifacts).

## Decision

Adopt **lenient, append-only JSONL** as v0 output. Filesystem is source of truth; strict schemas deferred until patterns stabilize. Maintain forward-compatible readers.

## Principles

* Append-only; never rewrite.
* Per-project “data lake” layout.
* Loose envelopes: `type` + minimal required fields; extras under `extras`.
* Capture raw snippets alongside normalized guesses.
* Errors as data (`parse_error`), not exceptions.
* Versioned records via `ver`; tolerant readers.

## Minimal Record Shapes (v0)

* `project_meta`: `{type, ver:0, projectRoot, projectJsonPath, name?, outputType?, language?, deps?, extras?}`
* `workflow`: `{type, ver:0, wfId, relPath, hash?, args?:{in?:[], out?:[], inOut?:[]}, extras?}`
* `invocation`: `{type, ver:0, from, to?, kind:"invoke|invoke-missing|invoke-dynamic|unknown", raw?, callerRel?, calleeRel?, extras?}`
* `path`: `{type, ver:0, root, sequence:[...], cycle?:bool, extras?}`
* `parse_error`: `{type, ver:0, scope:"project|workflow", file?, message, raw?, extras?}`
  Required: `type`. All other fields optional/tolerated.

## Storage Layout

```
.rpax-lake/
  {project_slug}/
    meta.jsonl           # project_meta, parse_error (project scope)
    workflows.jsonl      # workflow
    invocations.jsonl    # invocation
    paths.jsonl          # path
    logs/parse.log       # optional human log
```

Multiple runs append; each record carries `timestamp` and `runId` in `extras`.

## Identification & Hashing

* `wfId` = repo-relative POSIX path (best-effort).
* `hash` = SHA-256 of content (optional but recommended).
* `project_slug` = safe name + short hash of `project.json`.

## Tolerance Rules

* Unknown keys preserved.
* Missing files/roots captured as records (`invoke-missing`).
* Dynamic expressions stored in `raw`; `to` may be absent.
* Mixed VB/C# allowed; store observed values.

## Run Metadata (once per run, in `meta.jsonl`)

`{type:"project_meta", ver:0, runId, toolVersion, host:{os,arch}, config?:{...}, projectJsonHash}`

## Reader Contract (v0)

* Treat JSONL as **event streams**; process line-by-line.
* Require `type`; ignore unknown fields; prefer presence checks over schemas.
* Use `ver` for dispatch; accept `ver` ≥0 when fields are backward-compatible.
* Prefer `wfId` for joins; fall back to `relPath`.
* Do not infer failures from absence; rely on `parse_error` and `invocation.kind`.
* Expect duplicates across runs; group by `runId` or latest `timestamp` as needed.

## Field Naming Conventions

* snake\_case for keys; concise nouns (`wfId`, `relPath`, `runId` remain camelCase for legacy clarity).
* Booleans prefixed only when clarifying (`isAttended` stays as observed).
* Enumerations lower-case with hyphen-free tokens (`invoke`, `invoke-missing`).
* Time fields ISO-8601 strings in UTC (`timestamp`).
* `extras` reserved for experimental fields; nested keys allowed.

## Acceptance Criteria

* Emits records for every project with `project.json`.
* All errors represented as `parse_error` records; no hard validation.
* Re-runs append with new `runId` without altering prior data.

## Evolution Path

* Aggregate many projects; analyze JSONLs to derive **stable schemas**.
* Introduce schema-backed canonical artifacts and validation (per ADR7).
* Provide compactor to normalize/merge when schemas mature.

## Roadmap Phase

* **v0.0.1:** Primary implementation strategy for initial parser
* **v0.2:** Deprecated in favor of strict schemas (ADR-009)

## Open Questions

* Minimal guaranteed fields per record type beyond `type` (e.g., always include `timestamp`, `runId`?).
* Partitioning by date vs project\_slug for large corpora.
* Retention policy and compaction triggers.

## Related ADRs

* ADR-001: Lenient approach aligns with pattern-matching XAML parsing
* ADR-007: Phase 0 implementation strategy  
* ADR-009: Evolution path to strict canonical artifacts
* ADR-014: Lake storage model and identity scheme

## Amendment Notes

**2025-09-08 Status Update:** Lenient parsing strategy has been implemented in rpax v0.0.2. The codebase demonstrates lenient XAML parsing with error capture, JSONL outputs, and append-only telemetry patterns as specified. Error handling follows "errors as data" principle with parse_error records rather than exceptions. Amendment follows ADR-000 governance process.
