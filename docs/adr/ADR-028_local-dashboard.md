# ADR-028: Local Dashboard for rpax (Read-Only, API-Backed)

**Status:** Implemented 
**Date:** 2025-09-06  
**Implementation:** Dashboard mockup created with real API integration

## Context

RPA developers (Windows-focused) benefit from a minimal, **visual view** over the rpax-lake.
The CLI and Access API are functional but text-centric; a **local dashboard** would lower the barrier for inspection, debugging, and preparing IssueSaniBundle reports.

Constraints:

* Must work **offline**, **no telemetry**.
* Must ship **inside rpax/MCP server package**.
* No external libs/CDNs.
* Minimal risk: redaction-first.

## Decision

Introduce a **read-only dashboard**, served via `rpax dash`, as an **opt-in** feature.
It will embed static UI assets in the package and surface them under `/ui` when Access API is running.

## Defaults

### Enablement

* Disabled by default (`dash.enabled = false`).
* Start manually: `uv run rpax dash` or `rpax api --dash`.

### Bind & Port

* Default bind: `127.0.0.1`.
* Default port: `8624`.
* If port is busy, probe next available in range 8624–8630.

### Assets

* Ship static assets (HTML, JS, CSS) with the Python wheel.
* No CDN, no runtime fetches.

### API

* Default API target: `http://127.0.0.1:8623`.
* Configurable with `--api`.

### Browser

* Default: auto-open browser on Windows.
* Config flag: `dash.open_browser = true`.

### Views

* **Status** (`/v0/status`) → runtime and lake info.
* **Projects** (list/search).
* **Workflows** (inventory).
* **Errors** (counts and redacted details).
* **Pseudocode** (per-workflow).
* **IssueSaniBundle** (button: invokes `rpax diag package`, shows file path).

## Consequences

* Users get an offline-friendly viewer over artifacts.
* Minimal scope: **read-only**, API-backed only.
* MCP server remains single source of truth; dashboard is an optional thin layer.
* Redaction is guaranteed: only MCP-safe fields are shown.

## Risks

* Scope creep: must enforce **read-only**.
* Port clashes: mitigate by probing.
* User trust: must clearly label “Local only. No telemetry.”

## Alternatives

* Keep CLI/API only: higher barrier for non-technical RPA devs.
* Build heavy SPA: overkill, higher maintenance, more risk.

## Future Work

* Pagination/streaming for large lakes.
* Mermaid/Graphviz rendering of graphs.
* Service discovery (`api-info.json`).
* Bookmarkable deep links and MCP URI copy.

