Great—planning/brainstorming only. No code.

# Problem focus

* **Goal:** Code-first CLI to parse UiPath projects (Process/Library), build **workflow invocation graphs**, and emit **stable, machine-readable artifacts** for docs, CI, and MCP resources.
* **Pain points:** Multiple **entry points** in `project.json`, same-name XAMLs in different folders, dynamic `InvokeWorkflowFile` paths, scattered user folders.

# Scope & success criteria

* **Must:** Discover all entry points; build a **multi-root call graph**; disambiguate workflows by **canonical path**; flag dynamic/missing targets; run headless in CI.
* **Nice:** Incremental caching, REFramework awareness, Config.xlsx → JSON, Object Repository mapping.

# Inputs → Outputs

* **Inputs:** `project.json`, all `*.xaml`, (optional) `Data/Config.xlsx`, `Objects/**`, `.screenshots/` ignored.
* **Primary outputs (JSON):**

  * `project.manifest.json` – metadata + entry points.
  * `workflows.index.json` – all workflows with canonical IDs.
  * `invocations.jsonl` – edges `{from,to,kind,exists,dynamic,source}`.
  * `roots.paths.jsonl` – paths per entry point (flattened, cycles noted).
* **Secondary outputs:** Mermaid graphs, HTML site map (optional), MCP resource map.

# Identity & disambiguation

* **Canonical path ID:** POSIX-style, repo-relative, case-sensitive: `wfId = "<relpath>/File.xaml"`.
* **Stable logical ID:** `hash = sha1(canonicalPath + fileSize + firstNBytes)` for rename tolerance.
* **Entry points:** Treat **all** defined in `project.json` as **roots**; store `{displayName, wfId}`.

# Parsing strategy (XAML)

* **Discovery:** All `*.xaml` excluding `.local/.settings/.screenshots/TestResults`.
* **Detection:** `InvokeWorkflowFile` by `local-name()` (namespace-agnostic).
* **Target extraction precedence:**

  1. Literal attribute `WorkflowFileName="..."`.
  2. Child property nodes.
  3. Expression inside `[...]` → attempt to recover string literals; else mark **dynamic** with captured expression.
* **Resolution:** Resolve relative to **caller’s directory**; normalize `..\` etc.
* **Edge kinds:** `invoke` (file), `invoke-dynamic` (unresolved), `invoke-missing` (file not found).

# Graph model

* **Nodes:** Workflows (XAML files).
* **Edges:** Directed, with `exists|dynamic|missing`.
* **Roots:** All entry points (multi-root).
* **Cycles:** Detect; keep edge; annotate cycles on path enumerations.
* **Views:**

  * **Call tree** per root (depth-limited).
  * **Fan-in/out** for any node.
  * **Islands** (unreachable files).

# Config & UX

* **Config file:** `.uipath-scan.json`

  * `entryPointOverrides` (if `project.json` absent/ambiguous)
  * `excludeGlobs`, `maxDepth`, `followDynamic: false|true|pattern`
  * `outputDir`, `hashAlgorithm`, `pathStyle`
* **CLI subcommands:**

  * `scan` (build manifest, index, edges, cache)
  * `graph` (emit mermaid/paths per root)
  * `list` (workflows, roots, orphans)
  * `explain <wf>` (who calls it / what it calls)
  * `validate` (broken links, cycles, unknown root)
  * `diff <scanA> <scanB>` (PR change impact)
  * `mcp-export` (emit resource templates + URIs)
  * `summarize` (chunk XAML, produce LLM-friendly outlines; optional)

# Incremental & performance

* **Content hashing** of each XAML; reparse only changed.
* **Edges cache** keyed by `callerHash`; invalidate on caller OR callee path change.
* **Parallel parse** with bounded workers.

# Edge cases to handle

* **Multiple entry points** with same file name in different folders → handled by canonical path IDs.
* **Dynamic invocations** (`Path.Combine`, variables) → flagged; optionally **heuristic resolution** via known roots/dirs.
* **Cross-project invokes** (relative going outside root) → mark and optionally include.
* **Library projects**: treat public XAML in `Activities/` as potential **exports**; still parse invokes.
* **Coded workflows** (C#) → record presence; no deep parse in v1 (note as “external/coded”).
* **Object Repository invokes** (if helper XAML wrappers exist) → they’re just XAML; parse normally.
* **Windows-Legacy vs Windows**: path rules same; VB vs C# expressions only affect literal recovery (treat uniformly).

# Validation rules (CI-useful)

* No **missing** targets unless explicitly allowed.
* No **dynamic** targets unless whitelisted.
* No **cycle** crossing across different entry points (configurable).
* Every entry point must be **reachable** (trivial) and produce at least 1 path.
* Orphan workflows list must be acknowledged or excluded.

# Documentation generation (code-first, optional)

* **Per-root READMEs:** minimal call tree + table of invokes with notes.
* **Per-workflow fact sheet:** inbound callers, outbound calls, parameters (from arguments block), annotations.
* **Project map:** index of roots and modules.

# MCP tie-in (read-only resources)

* URIs:

  * `uipath://proj/{name}/manifest.json`
  * `uipath://proj/{name}/workflows/{relpath}.xaml` (raw or outline)
  * `uipath://proj/{name}/graphs/invocations.jsonl`
  * `uipath://proj/{name}/graphs/paths/{rootId}.txt`
* Keep provenance neutral; emit summaries client-side by content hash.

# Roadmap

* **v0 (prototype):** scan + invocations + multi-root paths + CI validation.
* **v1:** incremental cache, diff, MCP export, basic summaries.
* **v1.1:** argument parsing (in/out), detect common REFramework states, better dynamic heuristics.
* **v2:** optional light evaluation (run StudioXamlInspector-like AST), integrate with runtime dumps.

# Minimal data schemas (sketch)

* `manifest`: `{ projectName, roots:[{displayName,wfId}], discoveredAt, toolVersion }`
* `workflow`: `{ wfId, relPath, hash, arguments:{in:[],out:[]}, annotations:{} }`
* `edge`: `{ from, to, kind:"invoke|invoke-dynamic|invoke-missing", exists, dynamic, source:{file,line} }`

# Open questions (please confirm)

1. **Target types:** Process only, or Libraries too?
2. **Tolerance for dynamic invokes:** fail CI or warn?
3. **Desired output default:** JSON only, or also Mermaid/Markdown?
4. **Diff use cases:** PR impact report required?
5. **Argument extraction:** needed in v0, or defer to v1?
