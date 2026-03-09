# rpax

CLI tool for parsing UiPath projects into call graphs, dependency maps,
and structured JSON artifacts for documentation, validation, and CI impact analysis.

> **Alpha** — distributed via [test PyPI](https://test.pypi.org/project/rpa-cli/).
> Expect breaking changes between versions.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uvx --from rpa-cli \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    rpa-cli --help
```

## Quick start

```bash
# Parse a project — artifacts land in .rpax-warehouse/ relative to CWD
rpa-cli parse /path/to/uipath/project

# Inspect a specific workflow
rpa-cli explain MyWorkflow.xaml

# Bump the project version
rpa-cli bump patch
```

## Commands

| Command | Status | Description |
|---------|--------|-------------|
| `parse [PATH]` | experimental | Parse UiPath project(s); generate artifacts into `.rpax-warehouse/` |
| `explain <workflow>` | experimental | Arguments, callees, callers for one workflow |
| `bump {major\|minor\|patch}` | stable | Bump `projectVersion` in `project.json` |

Run `rpa-cli <command> --help` for full options.

### Bump without installing

Run `bump` directly from the project directory without a permanent install:

```bash
uvx --from rpa-cli \
    --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    rpa-cli bump patch
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
