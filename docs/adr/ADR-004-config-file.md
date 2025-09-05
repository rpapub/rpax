# ADR: Configuration Schema (v1)

**Status:** Proposed

## Context

Stable, validated configuration is required for CLI behavior across parsing, validation, diffing, and integrations.

## Decision

* Define **JSON Schema** at **`src/rpax/schemas/config.v1.schema.json`**.
* Embed `$schema` in project config (`.rpax.json`) pointing to the schema’s `$id`.
* Version via filename suffix (`config.v1.schema.json`); **breaking changes ⇒ new file** (`config.v2.schema.json`).
* Publish read-only mirror under `docs/schemas/` (generated from source).
* Validate configs in CI; reject unknown fields (`additionalProperties:false`).
* Adopt the provided **draft** structure (enums, defaults, strict sections: `project`, `scan`, `output`, `validation`, `diff`, `mcp`, `logging`).
* Use `$id` with stable URL (e.g., `https://raw.githubusercontent.com/rpapub/rpax/main/src/rpax/schemas/config.v1.schema.json`) and `$schema` draft 2020-12.

### Example hierachiy

#### Core (must implement)

* `project.name` – project identifier
* `project.type` – **enum**: `process` | `library`
* `scan.exclude[]` – globs to skip (default: `.local/**`, `.settings/**`, …)
* `output.dir` – output directory for artifacts
* `output.formats[]` – **enum**: `json`, `mermaid`, …
* `validation.failOnMissing` – boolean
* `validation.failOnCycles` – boolean
* `validation.warnOnDynamic` – boolean

#### Optional (v0.0.1 feasible)

* `project.root` – project root path (default `"."`)
* `scan.maxDepth` – integer (default `10`)
* `scan.followDynamic` – boolean (default `false`)
* `output.summaries` – boolean (emit LLM-friendly outlines)
* `diff.baselineDir` – path for cached previous scan
* `diff.reportFormat` – **enum**: `json`, `markdown`, `html`
* `mcp.enabled` – boolean
* `mcp.uriPrefix` – string (default `uipath://proj`)
* `mcp.private[]` – globs for private URIs (default `runtime://**`)
* `logging.level` – **enum**: `error`, `warn`, `info`, `debug`, `trace`

#### Nice-to-have (future, ≥ v0.1)

* `validation.rules[]` – enable/disable individual validators
* `summaries.style` – **enum**: `short`, `full`, `javaDoc`
* `graph.theme` – output style (colors, layout hints)
* `diff.ignore[]` – ignore specific workflows/files in PR impact
* `mcp.audit` – enable access logging for MCP resource usage
* `plugins[]` – external analyzers or transformers to run on workflows
* `cache.dir` – path for incremental parse cache


## Options

* **A — JSON Schema (chosen):** machine-validated, editor tooling, CI-friendly.
* **B — Runtime-only validation (Pydantic):** simpler dev loop, weaker ecosystem interop.
* **C — Ad hoc config (YAML/none):** minimal overhead, no guarantees.

## Consequences

* Strong guarantees (strict keys, typed values, defaults).
* Clear evolution path via versioned files; deprecation notices in docs.
* Slight maintenance overhead (mirror generation, tests).

## Go / No-Go

* **Go:** Land `config.v1.schema.json` at the stated path; wire CI validation; add `$schema` to `.rpax.json`.
* **No-Go:** Do not mutate `v1`; any breaking change requires `v2` with migration notes.
