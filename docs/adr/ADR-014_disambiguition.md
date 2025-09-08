# ADR-014: Identity & Disambiguation (Multi-Project “Lake”)

**Status:** Proposed  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Context

A single “lake” directory stores artifacts for multiple UiPath/WF projects and multiple runs. MCP exposure requires unambiguous, stable addressing across projects, files, and runs.

## Options

* **A — Path-only ID:** repo-relative path as sole key.
* **B — Content-only ID:** content hash as sole key.
* **C — Composite ID (project + path + content hash).**

## Decision

Adopt **Composite ID** (Option C).

## Rationale

* Path alone breaks on renames/moves.
* Content alone obscures human navigation and collides for identical files across projects.
* Composite preserves human-readable addressing and enables rename tolerance.

## Identity Model

* **projectSlug**: unique per project in lake. Recommendation: `kebab(name) + "-" + shortHash(project.json)`.
* **wfId (canonical path ID)**: POSIX, repo-relative, case-sensitive; normalize `.`/`..`, collapse separators; forbid trailing slash.
* **contentHash**: `sha256(full file bytes)`; encode as lowercase hex.
* **activity nodeId**: stable, path-like locator within a workflow (sibling indexes), independent of GUIDs.

## Rules

* Persist **both** `wfId` and `contentHash` on all workflow/activity artifacts; include `projectSlug` at artifact roots.
* Prefer `contentHash` for equality across scans; prefer `wfId` for display and hyperlinks.
* MCP URIs include `projectSlug` + `wfId`; hashes surfaced as metadata (e.g., ETag).
* Apply Unicode path normalization (NFC) before computing `wfId`; resolve symlinks; reject paths escaping project root.
* Treat comparisons as **case-sensitive**; store original path casing as `wfPathOriginal` for provenance.

## Consequences

* Unique, human-navigable addressing across projects.
* Robust rename/move detection via `contentHash`.
* Deterministic URIs suitable for MCP and docs.
* Small overhead for hash computation and slug generation.

## Open Questions

* projectSlug collision policy (e.g., numeric disambiguator vs longer hash).
* Hash algorithm policy (stay with SHA-256 or allow BLAKE3 under a `hashAlgo` field).
* Retention of historical `wfId` aliases after moves (optional alias map).

## Roadmap Phase

* **v0.0.1:** Core identity model for multi-project artifact storage

## Go / No-Go

* **Go:** Composite ID with SHA-256, POSIX `wfId`, normalized paths, explicit `projectSlug`.
* **No-Go:** Path-only or content-only identifiers as the sole key in the lake.

## Related ADRs

* ADR-006: projectSlug generated from project.json metadata
* ADR-007: wfId requirements and normalization rules  
* ADR-008: Lake storage model for multi-project artifacts
* ADR-009: Identity scheme used throughout canonical artifacts
* ADR-011: projectSlug used in Access API URL structure
* ADR-012: Identity model drives MCP URI scheme
