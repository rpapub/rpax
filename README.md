# rpax

CLI tool for parsing UiPath projects into call graphs, dependency maps,
and structured JSON artifacts for documentation, validation, and CI impact analysis.

> **Alpha** — distributed via [test PyPI](https://test.pypi.org/project/rpax/).
> Expect breaking changes between versions.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uvx --from rpax \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    rpax --help
```

## Quick start

```bash
# Parse a project — artifacts land in .rpax-warehouse/ relative to CWD
uvx rpax parse /path/to/uipath/project

# Validate the parsed output (referential integrity, cycles, etc.)
uvx rpax validate

# Run code quality checks (naming, size, annotations, error handling)
uvx rpax review

# Show call graph as Mermaid diagram
uvx rpax graph calls
```

## Commands

| Command | Description |
|---------|-------------|
| `parse [PATH]` | Parse UiPath project(s); generate artifacts into `.rpax-warehouse/` |
| `validate` | Check for missing references, cycles, orphans |
| `review` | Code quality checks: naming, size, annotations, error handling |
| `list workflows` | Enumerate discovered XAML workflows |
| `list orphans` | Workflows never called by anything |
| `list roots` | Entry-point workflows |
| `graph calls` | Mermaid or Graphviz call graph |
| `explain <workflow>` | Arguments, callees, callers for one workflow |
| `pseudocode <workflow>` | Activity tree as readable pseudocode |
| `list-bays` | List all projects (bays) in the warehouse |
| `activities` | Inspect activity trees and resource references |
| `view` | Compact portrait summary of a bay |

Run `rpax <command> --help` for full options.

## `rpax review` — code quality checks

Surfaces static issues from parsed artifacts without re-running Studio:

| Rule | Checks |
|------|--------|
| `argument_naming` | `in_` / `out_` / `io_` prefix convention violations |
| `workflow_size` | Workflows exceeding activity count threshold (default: 50) |
| `annotation_coverage` | Non-trivial workflows with no activity annotations |
| `error_handling` | Non-trivial workflows with no TryCatch blocks |
| `orphan_workflows` | Workflows unreachable from any declared entry point |

```bash
rpax review                        # table output, defaults
rpax review --format summary       # rule → issue count overview
rpax review --max-activities 30    # stricter size threshold
rpax review --bay my-project       # target a specific bay in a multi-bay warehouse
```

## Output artifacts

`parse` writes per-project artifacts under `.rpax-warehouse/<bay-id>/`:

| File | Contents |
|------|----------|
| `manifest.json` | Project metadata and entry points |
| `workflows.index.json` | All discovered XAML workflows |
| `invocations.jsonl` | Call graph edges (caller → callee) |
| `call-graph.json` | Resolved dependency graph with metrics |
| `metrics/` | Per-workflow activity metrics |
| `activities.tree/` | Per-workflow activity trees |
| `pseudocode/` | Human-readable activity summaries |

## License

[CC-BY 4.0](LICENSE)
