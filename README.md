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
# Parse a project — artifacts land in .rpax-lake/ relative to CWD
uvx rpax parse /path/to/uipath/project

# Validate the parsed output
uvx rpax validate .rpax-lake

# Show call graph as Mermaid diagram
uvx rpax graph calls --path .rpax-lake
```

## Commands

| Command | Description |
|---------|-------------|
| `parse [PATH]` | Parse UiPath project(s); generate artifacts into `.rpax-lake/` |
| `validate` | Check for missing references, cycles, orphans |
| `list workflows` | Enumerate discovered XAML workflows |
| `list orphans` | Workflows never called by anything |
| `list roots` | Entry-point workflows |
| `graph calls` | Mermaid or Graphviz call graph |
| `explain <workflow>` | Arguments, callees, callers for one workflow |
| `pseudocode <workflow>` | Activity tree as readable pseudocode |
| `projects` | List all projects in the lake |
| `activities` | Inspect activity trees and resource references |

Run `rpax <command> --help` for full options.

## Output artifacts

`parse` writes per-project artifacts under `.rpax-lake/<project-slug>/`:

| File | Contents |
|------|----------|
| `manifest.json` | Project metadata and entry points |
| `workflows.index.json` | All discovered XAML workflows |
| `invocations.jsonl` | Call graph edges (caller → callee) |
| `call-graph.json` | Resolved dependency graph with metrics |
| `activities/` | Per-workflow activity trees |
| `pseudocode/` | Human-readable activity summaries |

## License

[CC-BY 4.0](LICENSE)
