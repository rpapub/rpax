# ADR-003: rpax CLI Surface (Commands Only)

**Status:** Proposed

## Context

Public CLI contract required; internals out of scope.

## Options

* **A — Core only:** `parse`, `list`, `validate`, `help`.
* **B — Expanded surface (docs/CI/LLM/MCP):** adds `graph`, `explain`, `diff`, `config`, `summarize`, `mcp-export`.
* **C — Plugin model:** minimal core + discoverable extensions.

## Decision

Adopt **Option B**. Expose these subcommands:

* `parse` — scan project; emit JSON artifacts (manifest, workflows, invocations).
* `graph` — generate diagrams (Mermaid/HTML) from parsed data.
* `list` — enumerate workflows, entry points, orphans.
* `explain` — show details for one workflow (args, callers, callees).
* `validate` — run rules (missing invokes, cycles, config checks).
* `diff` — compare two scans for PR impact (added/removed/changed workflows or edges).
* `config` — view or edit local `.rpax.json` settings.
* `summarize` — produce LLM-friendly outlines of workflows/graphs.
* `mcp-export` — emit MCP resource templates for integration.
* `help` — usage info.

**No-Go (for this ADR):** server/API commands, database import, runtime execution.

### Sample flags and command tree

```bash
rpax [global flags] <command> [args]

Global flags
 ├─ -v, --version          # Show version
 ├─ -q, --quiet            # Suppress non-error output
 ├─ -j, --json             # Force JSON output to stdout
 ├─ -o, --out <dir/file>   # Set output directory or file
 ├─ -d, --depth <n>        # Limit traversal depth in graphs
 ├─ -c, --config <file>    # Use custom config file (.rpax.json by default)
 ├─ --no-color             # Disable ANSI colors
 ├─ --log-level <lvl>      # Set logging level (error,warn,info,debug,trace)
 └─ --cache <dir>          # Specify cache directory for incremental runs
```

```bash
rpax
 ├─ help [command]                 # Show usage
 ├─ parse [path] [--out dir]       # Parse project → JSON artifacts
 ├─ graph
 │   ├─ calls [--out file]         # Diagrams of invocation graph
 │   └─ paths [root] [--out file]  # Call trees from entry points
 ├─ list
 │   ├─ roots                      # Entry points from project.json
 │   ├─ workflows                  # All discovered XAMLs
 │   ├─ orphans                    # Not invoked by any other
 │   └─ invokes [wf]               # Direct invokes inside workflow
 ├─ explain <workflow>             # Show args, callers, callees
 ├─ validate
 │   ├─ all                        # Run all validation rules
 │   ├─ missing                    # Missing invoke targets
 │   ├─ cycles                     # Cyclic invokes
 │   └─ config                     # Config consistency
 ├─ diff <scanA> <scanB>           # Compare scans, PR impact
 ├─ config
 │   ├─ show                       # Print current config
 │   ├─ init                       # Create default .rpax.json
 │   └─ set <key> <value>          # Change config value
 ├─ summarize
 │   ├─ workflow <wf>              # Outline args, activities
 │   ├─ root <root>                # Summarize call tree
 │   └─ project                    # Summarize whole project
 └─ mcp-export [--out dir]         # Emit MCP resource templates
```

## Consequences

* Stable user-facing surface for docs/CI and integrations.
* Requires command-level versioning and deprecation policy.
* Leaves room for future plugin model without breaking surface.
