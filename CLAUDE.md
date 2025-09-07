# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**rpax** is a code-first CLI tool that parses UiPath Process and Library projects into JSON call graphs, arguments, and diagrams for documentation, validation, and CI impact analysis. The project follows a layered architecture with clear separation between parsing, validation, access API, and MCP/integration layers.

## Architecture

The codebase is structured around a **4-layer architecture** (ADR-002):

1. **Parser Layer** - Discovers `.xaml` files, normalizes IDs, emits canonical artifacts (graphs/manifests/indices)
2. **Validation & CI Layer** - Applies configurable gates (missing/dynamic invokes, cycles, orphans) for pipelines  
3. **Access API Layer** - Lightweight, read-only HTTP interface over artifacts for tools/CI
4. **MCP/Integration Layer** - Stable external resource contracts (URIs/schemas) for broader ecosystem consumption

### Key Technical Decisions

- **XAML Parsing**: Uses pattern-matching approach (namespace-agnostic) rather than strict schema validation for resilience (ADR-001)
- **Configuration**: JSON Schema-based configuration at `.rpax.json` with versioned schemas (ADR-004)
- **Graph Visualization**: Supports both Mermaid (default, markdown-friendly) and Graphviz (CI/large projects) (ADR-005)

## Directory Structure

```
src/rpax/                 # Main Python package
├── schemas/              # JSON schemas for configuration
│   └── config.v1.schema.json
└── pyproject.toml       # Python package configuration

docs/
├── adr/                 # Architecture Decision Records
├── llm/context/         # LLM context and style guides  
├── risks/               # Risk register and edge cases
└── roadmap/             # Project roadmap and backlog

.github/workflows/       # CI configuration
```

## Commands & Development Workflow

### CLI Surface (ADR-003)

The rpax CLI provides these core commands:

```bash
rpax parse [path] [--out dir]        # Parse project → JSON artifacts
rpax graph calls [--out file]        # Generate call graphs  
rpax list {roots,workflows,orphans}  # Enumerate project elements
rpax explain <workflow>              # Show workflow details
rpax validate {all,missing,cycles}   # Run validation rules
rpax diff <scanA> <scanB>            # Compare scans for PR impact
rpax config {show,init,set}          # Manage configuration
rpax summarize {workflow,project}    # Generate LLM-friendly summaries
rpax mcp-export [--out dir]          # Export MCP resources
```

### Python Development

- **Language**: Python 3.11+ with type hints everywhere
- **Package Manager**: Use `uv` for dependency management
- **Code Style**: Follow Black (88 chars), isort, Ruff linting, mypy type checking (docs/llm/context/styleguide.md)
- **Testing**: pytest with coverage enforcement
- **Package Layout**: Standard `src/` layout with PEP 621 metadata in `pyproject.toml`

### Configuration Schema

Projects use `.rpax.json` configuration files validated against JSON Schema (ADR-004). Core required fields:
- `project.name` - project identifier  
- `project.type` - enum: `process` | `library`
- `scan.exclude[]` - glob patterns to skip scanning
- `output.dir` - output directory for artifacts
- `validation.failOnMissing/failOnCycles` - validation rules

## Artifacts & Output Formats  

The parser generates canonical artifacts:
- `manifest.json` - project metadata and entry points
- `workflows.index.json` - discovered XAML workflows
- `invocations.jsonl` - call graph relationships
- `activities.*/` - activity details and references  
- `paths/` - call tree paths from entry points

Output formats support both **Mermaid** (GitHub/docs friendly) and **Graphviz** (scalable CI diagrams) (ADR-005).

## Risk Areas & Edge Cases

Key challenges documented in `docs/risks/register.md`:
- Dynamic invocations with variables/Path.Combine (RISK-002)
- Cross-project workflow references (RISK-003)
- Large projects (1k+ workflows) performance (RISK-008)
- Case sensitivity and path normalization (RISK-014)
- Multiple entry points with same filenames (RISK-001)
- Library vs Process project differences (RISK-004)

## Important Development Notes

- **XML Parsing**: Use `defusedxml` for security when parsing XAML (docs/llm/context/styleguide.md)
- **Path Handling**: Always normalize to POSIX-style paths for cross-platform compatibility
- **Error Handling**: Record `parse_error` events instead of crashing on malformed inputs (RISK-009)
- **Performance**: Consider streaming parsers and parallelism for large projects (RISK-008)
- **Configuration Versioning**: Breaking config changes require new schema versions (v2, v3, etc.) (ADR-004)

## Development Methodology

Follow this structured approach for implementing rpax features:

### 1. **TODO Validation**
- Verify `TODO.md` exists and is synchronized with current phase from `docs/roadmap/implementation-phases.md`
- Ensure next items align with roadmap priorities and acceptance criteria
- Update TODO.md if roadmap has evolved or priorities have changed

### 2. **Planning & Analysis**  
- Select next TODO item and analyze requirements thoroughly
- Reference relevant ADRs for architectural guidance and constraints
- Break down complex features into testable, incremental steps
- Consider edge cases documented in `docs/risks/register.md`
- Plan test strategy before writing any implementation code

### 3. **Test-Driven Implementation**
- Generate comprehensive tests covering happy path, edge cases, and error conditions
- Write failing tests first to validate test logic
- Implement feature incrementally to make tests pass
- Ensure tests follow patterns in `docs/llm/context/styleguide.md`

### 4. **Validation Cycle**
- Run full test suite after implementation
- If tests fail: analyze whether code or tests need fixes, iterate until green
- If tests pass: run linting (ruff), type checking (mypy), formatting (black)
- Validate against acceptance criteria from roadmap phase

### 5. **Integration & Milestone Validation**
- Update TODO.md to reflect completed work and next priorities
- Update roadmap if implementation revealed new insights or scope changes
- Make focused git commit with clear description following repository conventions
- When adequate milestone reached: validate against real UiPath test projects

### 6. **Architectural Consistency**
- When in doubt, consult ADR documents for guidance on technical decisions
- Prefer existing patterns over introducing new approaches
- Document any deviations from ADRs or propose new ADRs for significant changes

### Integration Testing Strategy

Run comprehensive validation against provided test projects at these milestones:
- **v0.0.1 completion**: All 3 test projects parse without crashes
- **v0.1 features**: Validation rules and Mermaid graphs work on test projects  
- **Major refactors**: Ensure no regressions in parsing or artifact generation

## Test Corpuses

Local UiPath Studio projects for development and testing:

- `D:\github.com\rpapub\rpax-corpuses\c25v001_CORE_00000001\project.json`
- `D:\github.com\rpapub\rpax-corpuses\c25v001_CORE_00000010\project.json`
- `D:\github.com\rpapub\FrozenChlorine\project.json`
- `D:\github.com\rpapub\PropulsiveForce\CPRIMA-USG-001_ShouldStopPresence\Violation\project.json`  
- `D:\github.com\rpapub\PropulsiveForce\CPRIMA-USG-001_ShouldStopPresence\NoViolation\project.json`

These test corpuses provide real-world UiPath workflows for testing parser implementation, validating artifact generation, and ensuring the tool handles various project structures and patterns. They are intended as pytest fixtures for comprehensive integration testing.

## References

- Architecture decisions: `docs/adr/ADR-*.md`
- Python style guide: `docs/llm/context/styleguide.md`
- Risk register: `docs/risks/register.md`
- Project roadmap: `docs/roadmap/backlog/compose-artifacts.md`