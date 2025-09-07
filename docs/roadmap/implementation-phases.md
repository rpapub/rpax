# rpax Implementation Roadmap

This document outlines the phased implementation plan for rpax, mapping architectural decisions (ADRs) to deliverable milestones.

## Overview

The implementation follows the 4-layer architecture (ADR-002) with incremental delivery across versions:

- **v0.0.1 (MVP):** Core parser + CLI foundation
- **v0.1:** Validation + visualization 
- **v0.2:** HTTP API + advanced analysis
- **v0.3+:** MCP integration + ecosystem

## Version 0.0.1 - Foundation (MVP)

**Goal:** Establish core parsing capability and basic CLI

### Core Features
- **Parser Layer** (ADR-007, ADR-008, ADR-009)
  - Pattern-matching XAML parsing (ADR-001) 
  - project.json metadata extraction (ADR-006)
  - Lenient JSONL artifact generation (ADR-008)
  - Basic workflow discovery and invocation detection
  
- **CLI Basics** (ADR-003, ADR-015)
  - `rpax parse` command for artifact generation
  - `rpax list workflows` for project enumeration
  - `rpax help` with command documentation
  - Configuration via `.rpax.json` (ADR-004)

- **Identity System** (ADR-014)
  - Composite ID scheme (projectSlug + wfId + contentHash)
  - POSIX path normalization
  - Multi-project "lake" storage

### Technology Stack (ADR-015)
- Python 3.11+ with Typer CLI framework
- always use `uv` and a venv
- lxml + defusedxml for XAML parsing
- Pydantic v2 for data modeling
- Synchronous architecture (no async/parallel yet)
- uv for package management

### Acceptance Criteria
- Parse 3 test projects without crashes
- Generate deterministic JSONL artifacts
- Handle missing/dynamic invocations gracefully
- Zero-config operation with sensible defaults

---

## Version 0.1 - Analysis & Visualization

**Goal:** Add validation and diagram generation capabilities

### New Features
- **Validation Layer** (ADR-010)
  - `rpax validate` command with configurable rules
  - Pipeline readiness checks (missing invokes, cycles, orphans)
  - CI-friendly exit codes and reporting
  
- **Graph Visualization** (ADR-005, ADR-013)
  - `rpax graph` command with Mermaid output
  - Standardized diagram elements (nodes, edges, clusters)
  - Per-root call graphs and project overviews
  
- **Enhanced CLI** (ADR-003)
  - `rpax explain <workflow>` for detailed workflow info
  - Enhanced `rpax list` with filtering options
  - Better error messages and help text

- **Strict Artifacts** (ADR-007, ADR-009)
  - Transition from lenient JSONL to schema-backed JSON
  - JSON Schema validation for all artifacts
  - Versioned artifact formats with migration notes

### Technology Evolution
- Add JSON Schema generation via Pydantic
- Introduce pytest test suite with coverage
- Add pre-commit hooks (Black, Ruff, mypy)

### Acceptance Criteria
- Validate 50+ UiPath projects with <5% false positives
- Generate readable Mermaid diagrams for complex projects
- Schema validation passes on all generated artifacts
- Test coverage >80% on core parser logic

---

## Version 0.2 - API & Advanced Analysis

**Goal:** HTTP API access and sophisticated analysis features

### New Features
- **Access API Layer** (ADR-011)
  - Read-only HTTP API over parser artifacts
  - Multi-project discovery and querying
  - ETag caching and content negotiation
  - Stable URLs for CI integration

- **Advanced CLI** (ADR-003)
  - `rpax diff` for PR impact analysis
  - `rpax summarize` for LLM-friendly project outlines
  - Graphviz support for large diagram rendering
  
- **Performance Optimization**
  - Optional multiprocessing for large projects
  - Incremental parsing with content-based caching
  - Streaming JSONL readers for memory efficiency

### Technology Evolution (ADR-015)
- FastAPI for HTTP API implementation
- Async/await patterns for I/O operations
- Optional Graphviz integration
- Performance profiling and optimization

### Acceptance Criteria
- Handle projects with 1000+ workflows in <30 seconds
- API serves 10+ concurrent requests efficiently
- Diff analysis shows meaningful PR impacts
- Memory usage remains bounded for large projects

---

## Version 0.3+ - Ecosystem Integration

**Goal:** MCP integration and extensibility

### New Features
- **MCP Layer** (ADR-012)
  - Read-only MCP server exposing artifacts as resources
  - Stable URI scheme for ecosystem consumption
  - Compatible migration from Access API
  
- **Extensibility**
  - `rpax mcp-export` for resource template generation
  - Plugin architecture for custom analyzers
  - Webhook support for CI integrations

- **Advanced Analysis** (from backlog)
  - Workflow factsheets and design documents
  - Dependency mapping and impact analysis
  - Resource usage reports (selectors, assets, queues)
  - Metrics dashboards for governance

### Technology Evolution
- MCP protocol implementation
- Plugin discovery and lifecycle management
- Advanced caching strategies
- Deployment automation (Docker, k8s)

### Acceptance Criteria
- MCP resources accessible from Claude/IDEs
- Plugin system supports 3rd party extensions
- Enterprise deployment guides available
- Performance scales to 10k+ workflow projects

---

## Risk Mitigation

### Phase Gates
Each version requires meeting specific criteria before proceeding:

- **v0.0.1 → v0.1:** 95% literal invoke resolution on test corpus
- **v0.1 → v0.2:** Field stability >90% across schema versions
- **v0.2 → v0.3:** API performance benchmarks met

### Rollback Plans
- Maintain backward compatibility for CLI commands
- Version artifacts to enable downgrades
- Feature flags for experimental capabilities

### Dependencies
- **External:** UiPath Studio project availability for testing
- **Internal:** Completion of ADR documentation and risk analysis
- **Technical:** Python 3.11+ adoption, uv tooling setup

---

## Success Metrics

### Adoption
- GitHub stars and community contributions
- Integration into CI pipelines
- Usage in documentation workflows

### Quality
- Test coverage >90% maintained across versions
- Zero critical security vulnerabilities
- Performance regressions caught in CI

### Ecosystem
- MCP resource consumption by AI tools
- Plugin ecosystem development
- Enterprise deployment success stories

---

## References

- ADR-002: Layered architecture driving this phasing
- ADR-015: Technology stack evolution across versions
- docs/risks/register.md: Risk mitigation strategies
- docs/roadmap/backlog/compose-artifacts.md: Feature backlog details