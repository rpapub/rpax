# ADR-012: MCP Server (Read-Only over Parser Artifacts)

**Status:** Proposed

## Context

Downstream consumers need stable, tool-agnostic access to parser artifacts. An MCP server can expose these as resources with minimal coupling. References: ADR-007/008/009 (parser), ADR-010 (validation), ADR-011 (Access API).

## Decision

Implement a **read-only MCP server** that surfaces parser artifacts as MCP resources. Align resource model with existing files; avoid server-side mutation or inference.

## Rationale

* Unify access for IDEs/agents without bespoke HTTP clients.
* Keep files as source of truth; MCP acts as a thin protocol façade.
* Preserve migration path from Access API to MCP without breaking URLs/workflows.

## Scope

* Resource namespaces for: `project`, `workflow`, `invocation`, `path`, `activity.tree`, `activity.cfg`, `activity.refs`, `metrics`.
* Read operations only (list/get/stream).
* Project discovery via configured artifact roots.
* Pass through schema/version metadata.

## Non-Goals

* No write/update/delete.
* No validation, rendering, or compaction.
* No dynamic recomputation of artifacts.

## Interfaces (high level, vague by design)

* Resource URIs mirror artifact layout (e.g., `rpax://projects/{p}/workflows/{wfId}`).
* Streaming for large sets (invocations/paths/cfg).
* Metadata via headers/properties (schema version, content hash).
* Authentication/tenancy delegated to MCP hosting environment.

## Versioning

* MCP API version `v0` initially; bump in lockstep with artifact epochs.
* Backward-compatible additions preferred; breaking changes via new namespaces.

## Migration Path

* Phase 1: run MCP side-by-side with Access API; identical data contract.
* Phase 2: mark Access API as optional; keep for non-MCP clients.
* Phase 3: deprecate Access API only if MCP adoption suffices.

## Operational Notes

* Stateless workers; artifacts mounted read-only.
* Caching allowed; validate by content hash.
* Health/readiness endpoints via MCP conventions.

## Risks

* Protocol constraints vs. existing consumers.
* Large resource sets require careful streaming/pagination.
* Artifact evolution may outpace MCP contract if not versioned tightly.

## Roadmap Phase

* **v0.3+:** MCP server for ecosystem integration

## Open Questions

1. Exact resource naming and namespace hierarchy.
2. Minimum metadata set on each resource (hash, timestamp, schema).
3. Pagination and filtering semantics for streams.
4. Multi-tenant isolation and authorization model.
5. Error mapping (file missing vs. resource not found).

## Related ADRs

* ADR-002: Layer 4 of the architectural stack
* ADR-009: Exposes parser artifacts as MCP resources
* ADR-011: Migration path from Access API with compatible contracts
* ADR-014: URI scheme using projectSlug and wfId
