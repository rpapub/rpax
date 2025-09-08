# ADR-015: Python Implementation Stack

**Status:** Implemented (Updated 2025-09-08)  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Amendment Notes (2025-09-08)

**What Changed**: Added git dependency to Python stack requirements
**Why Amended**: Current implementation requires git for repository operations and dependency analysis
**Impact**: Git is now a required system dependency alongside Python for rpax operations

## Context

Implementation of rpax v0.0.1 requires a concrete Python technology stack that balances simplicity, performance, and maintainability. The stack must support pattern-based XAML parsing (ADR-001), JSON Schema validation (ADR-004), and handle large projects efficiently (RISK-008). Initial focus is on CLI functionality and parser/validation layers (ADR-002), with preparation for future API and MCP layers.

## Options

### CLI Framework

**Option A — argparse (stdlib)**

**Pros:**
* Zero dependencies
* Part of standard library
* Simple for basic CLIs
* Stable API

**Cons:**
* Verbose for complex command trees
* Manual type conversion
* Limited help formatting
* No command aliases or plugins

**Option B — Click**

**Pros:**
* Mature, battle-tested (Flask, Black use it)
* Decorator-based, clean syntax
* Excellent subcommand support
* Plugin architecture available

**Cons:**
* External dependency
* Some type hint limitations
* Learning curve for advanced features

**Option C — Typer**

**Pros:**
* Built on Click, inherits stability
* Native type hints drive CLI behavior
* Automatic help from docstrings
* Modern Python-first design
* Excellent IDE support

**Cons:**
* Newer, smaller community
* Additional dependency layer over Click
* Less plugin ecosystem

### XML Parsing

**Option A — lxml + defusedxml**

**Pros:**
* C-based, fastest Python XML parser
* XPath support for pattern matching
* Handles large files efficiently
* defusedxml patches security vulnerabilities

**Cons:**
* Binary dependency (libxml2)
* Platform-specific builds needed
* Heavier than pure Python

**Option B — xml.etree + defusedxml**

**Pros:**
* Standard library base
* Sufficient for pattern matching
* defusedxml provides security
* Pure Python fallback available

**Cons:**
* Slower than lxml on large files
* Limited XPath (ElementPath only)
* Less convenient API

**Option C — BeautifulSoup4**

**Pros:**
* Forgiving parser, handles malformed XML
* Simple API
* Good for exploratory parsing

**Cons:**
* Not designed for large XML files
* Performance overhead
* Another dependency (plus lxml/html5lib)

### Data Modeling

**Option A — Pydantic v2**

**Pros:**
* Validation at parse time
* JSON serialization built-in
* JSON Schema generation
* Excellent type hint integration
* Fast (Rust-based core)

**Cons:**
* Significant dependency
* Migration complexity if v3 breaking changes
* Learning curve for advanced features

**Option B — dataclasses + jsonschema**

**Pros:**
* Standard library (dataclasses)
* Simple, Pythonic
* No framework lock-in
* jsonschema for validation

**Cons:**
* Manual JSON serialization logic
* No runtime validation without extra code
* More boilerplate for complex models

**Option C — attrs**

**Pros:**
* Mature, stable
* Good balance of features
* Supports older Python versions
* Validation via validators

**Cons:**
* External dependency
* Less momentum than Pydantic
* Manual JSON Schema integration

### Parallelization Strategy

**Option A — Synchronous (v0.0.1)**

**Pros:**
* Simplest to implement and debug
* No concurrency complexity
* Sufficient for most projects (<1000 workflows)
* Easy testing

**Cons:**
* Linear performance scaling
* May struggle with very large projects

**Option B — asyncio (defer to v0.2+)**

**Pros:**
* Good for I/O-bound operations (file reading)
* Modern Python async/await
* Single-threaded, predictable

**Cons:**
* Requires async rewrite of parser
* XML parsing still CPU-bound
* Complexity for marginal gains in this use case

**Option C — multiprocessing**

**Pros:**
* True parallelism for CPU-bound XML parsing
* Can process multiple XAML files simultaneously
* Good for large projects

**Cons:**
* Overhead for small projects
* Complex result aggregation
* Platform differences (spawn vs fork)

## Decision

### Go (v0.0.1)

#### Main rpax Package
* **CLI Framework:** Typer — Type-safe, modern, builds on Click's stability (ADR-003)
* **XML Parsing:** lxml + defusedxml — Performance critical for large XAML files (ADR-001)
* **Data Modeling:** Pydantic v2 — Validation and JSON Schema alignment with ADR-004)
* **Parallelization:** Synchronous first — Add multiprocessing in v0.1 if needed
* **Package Management:** uv — Fast, modern replacement for pip/pip-tools
* **Version Control:** git — Required for repository operations and dependency analysis
* **Testing:** pytest + pytest-cov — As specified in styleguide
* **Code Quality:** Black (88) + isort + Ruff + mypy --strict
* **Python Version:** 3.11+ — Modern type hints, performance improvements

#### Standalone Packages (e.g., xaml_parser)
* **XML Parsing:** xml.etree.ElementTree + defusedxml — Stdlib base with security
* **Data Modeling:** dataclasses — Zero dependencies for maximum portability  
* **Validation:** Custom validation — Minimal external dependencies
* **Testing:** pytest — Same testing framework as main package
* **Python Version:** 3.9+ — Broader compatibility for reusable packages

### Dependency Tree (v0.0.1)

```toml
[project]
dependencies = [
    "typer>=0.9",
    "rich>=13.0",  # Enhanced CLI output
    "pydantic>=2.5",
    "lxml>=5.0",
    "defusedxml>=0.7",
    "jsonschema>=4.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "black>=23.0",
    "isort>=5.12",
    "ruff>=0.1",
    "mypy>=1.7",
    "types-jsonschema",
]
```

### No-Go (v0.0.1)

* **No asyncio:** Defer async patterns until Access API layer (v0.2+, ADR-011)
* **No REST framework:** CLI only for v0.0.1
* **No database:** JSON files remain canonical storage per ADR-002
* **No Graphviz rendering:** Emit .dot files only; users run `dot` separately (ADR-005)
* **No custom plugin system:** Wait for usage patterns to emerge

## Roadmap Phases

* **v0.0.1 (MVP):** Core parser (ADR-007), CLI basics (ADR-003), lenient JSONL (ADR-008)
* **v0.1:** Add validation (ADR-010), strict schemas (ADR-009), Mermaid graphs (ADR-005)
* **v0.2+:** Access API with FastAPI/async (ADR-011), advanced CLI features
* **v0.3+:** MCP integration (ADR-012)

## Consequences

### Positive

* Type safety throughout via Typer + Pydantic + mypy
* Fast XML parsing for large enterprise projects (implements ADR-001)
* JSON Schema validation aligns with configuration (ADR-004)
* Modern tooling attractive to contributors
* Clear upgrade path (multiprocessing, async, API layers)

### Negative

* Binary dependency (lxml) complicates distribution
* Pydantic v2 lock-in for model definitions
* uv requirement may surprise pip users initially

### Mitigation

* Provide platform wheels via cibuildwheel in CI
* Document uv installation clearly in README
* Consider pure-Python fallback mode for constrained environments (future)

## Implementation Notes

1. Start with single-file XAML parsing, validate approach (ADR-001)
2. Implement manifest.json and workflows.index.json generation (ADR-006, ADR-009)
3. Add invocations.jsonl extraction via XPath patterns (ADR-007)
4. Layer in Pydantic models incrementally
5. JSON Schema validation last (after models stabilize)

## Related ADRs

* ADR-001: Pattern-matching XAML parsing approach implemented with lxml
* ADR-003: CLI surface implemented with Typer
* ADR-004: JSON Schema validation implemented with Pydantic
* ADR-007: Parser requirements this stack implements
* ADR-011: Future async/FastAPI evolution for Access API layer

## Amendment Notes

**2025-09-08 Status Update:** Python implementation stack has been fully implemented in rpax v0.0.2. The pyproject.toml demonstrates all specified technologies: Typer for CLI, Pydantic v2 for data modeling, lxml + defusedxml for XML parsing, and complete development toolchain with Black, Ruff, mypy, pytest. Python 3.11+ requirement and uv package management are enforced. Amendment follows ADR-000 governance process.