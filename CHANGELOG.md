# Changelog

All notable changes to rpax will be documented in this file.

## [v0.0.2] - 2025-09-07

**Status**: 🧪 Proof-of-Concept - UiPath project parsing capabilities demonstrated

### ✅ What Works

**Core Parsing**
- Parse UiPath project.json and XAML workflow files
- Extract complete workflow metadata (arguments, variables, activities)
- Generate JSON artifacts: manifest.json, workflows.index.json, invocations.jsonl
- Support both Process and Library project types

**Validation & Analysis**  
- Detect missing workflow invocations before deployment
- Find orphan workflows (never called by anything)
- Detect circular dependencies in workflow calls
- Validate project structure and configuration

**Visualization**
- Generate Mermaid diagrams of workflow call graphs
- Project overview diagrams with entry points
- Visual workflow relationship mapping

**CLI Interface**
- `rpa-cli parse` - Parse projects into structured JSON
- `rpa-cli validate` - Run validation rules with CI-friendly exit codes
- `rpa-cli graph` - Generate visual diagrams
- `rpa-cli list` - Browse workflows, roots, orphans with filtering
- `rpa-cli explain` - Detailed workflow information
- Professional packaging: single-source versioning, complete dependencies

**Architecture & Design Decisions**
- **Multi-project "lake" architecture** (ADR-014) - Always-multi-project approach for ecosystem consistency
- **XAML parsing strategy** (ADR-001) - Namespace-agnostic pattern-matching for UiPath resilience
- **4-layer architecture** (ADR-002) - Parser → Validation → API → MCP integration layers
- **JSON Schema configuration** (ADR-004) - Versioned `.rpax.json` with zero-config defaults
- **Graph visualization formats** (ADR-005) - Mermaid (docs) + Graphviz (CI) dual support
- **CLI-first design** (ADR-003) - Professional command surface with API generation foundation

**Quality & Testing**
- 249 passing tests including integration with real UiPath projects
- Tested against 5 diverse UiPath corpus projects
- Cross-platform compatibility (Windows/Linux)
- Comprehensive error handling and graceful degradation

### ❌ What Does NOT Exist (vs README.md claims)

**Installation Limitations**
- ❌ **No pip installation yet** - README shows `pip install rpax` but this doesn't work
- ❌ **Git clone required** - Must use `git clone + uv sync` installation method
- ⚠️ **No Windows installer** - Python 3.11+ and uv setup required manually

**API & Integration**
- ❌ **No web interface** - CLI-only, no dashboard or web UI
- ❌ **No CI/CD integrations** - No GitHub Actions, Jenkins plugins, etc.
- ❌ **No MCP integration** - Not accessible from Claude/IDEs yet
- ❌ **Limited API** - Basic HTTP server exists but minimal endpoints

**Advanced Features**
- ❌ **No factsheets** - No automated workflow documentation generation
- ❌ **No advanced reporting** - Basic validation only, no governance dashboards
- ❌ **No plugin system** - No custom analyzer extensibility
- ❌ **No remote parsing** - Cannot parse projects from Git URLs

**Production Readiness**
- ⚠️ **Alpha quality** - Proof-of-concept status, not production-ready
- ⚠️ **No guaranteed API stability** - CLI commands may change
- ⚠️ **Performance untested** - Not validated on very large projects (1000+ workflows)

### 🎯 Current Capabilities

This release **proves the concept** that comprehensive UiPath project analysis is possible:

1. **Before Deployment**: Find missing workflows and validation issues
2. **Documentation**: Generate visual project structure diagrams  
3. **Code Quality**: Identify orphan workflows and circular dependencies
4. **CI Integration**: Validation rules with proper exit codes ready for pipelines

### 🔮 Coming Soon

- **v0.0.3**: PyPI distribution (`pip install rpax`)
- **v0.1.0**: Stable CLI interface and web dashboard
- **v0.2.0**: Advanced reporting and CI integrations
- **v1.0.0**: Production-ready with guaranteed API stability

---

**Installation**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup  
**Issues**: Report problems at [GitHub Issues](https://github.com/rpapub/rpax/issues)  
**License**: [Creative Commons Attribution (CC-BY 4.0)](LICENSE)