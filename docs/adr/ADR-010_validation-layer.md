# ADR-010: Lightweight Validation Layer

**Status:** Proposed

## Context

Vendor IDE (UiPath Studio) enforces structural/semantic validity. Downstream layers require only verification that parser artifacts are present, coherent, and consumable. (See ADR-007/ADR-008/ADR-009.)

## Decision

Adopt a **lightweight** validation layer focused solely on **pipeline readiness** of parser outputs; no vendor semantics, no expression evaluation.

## Rationale

Vendor IDE already validates workflows; this layer **only** ensures next layers receive the **expected inputs**.

## Scope

Inputs: parser artifacts (`manifest.json`, `workflows.index.json`, `invocations.jsonl`, per-workflow activity data).
Outputs: status, counters, reasons; exit codes for CI.

## Checks (minimal)

* **Artifacts present**: required files exist.
* **Roots resolvable**: every `manifest.roots[]` exists on disk.
* **Referential integrity**: for `invocations.kind=invoke`, `from`/`to` workflows exist.
* **Kinds bounded**: `invoke|invoke-missing|invoke-dynamic` only.
* **Arguments presence**: invoked workflows have an `arguments` block (empty allowed).
* **Cycle annotation**: any detected cycles are tagged (no breaking required).
* **Provenance**: tool version and run metadata present.

## Non-Goals

No XAML schema checks; no dynamic path evaluation; no vendor rule enforcement.

## Outputs

* **Status**: `pass | warn | fail`.
* **Counters**: roots, workflows, invokes, missing, dynamic, cycles.
* **Reasons**: compact list (artifact/path + short message).

## Exit Codes

* `0` = pass (warnings allowed).
* `1` = fail (unresolvable roots, broken referential integrity, missing required artifacts).

## Config (tiny)

* `validation.failOnMissing` (bool)
* `validation.failOnCycles` (bool)
* `validation.warnOnDynamic` (bool)

## CI Usage

Run immediately after Parser; fail fast only on **pipeline blockers**; emit concise warnings otherwise.

## Consequences

Fast, deterministic guardrails; stable inputs for Access API/MCP; semantic depth deferred to vendor IDE.
