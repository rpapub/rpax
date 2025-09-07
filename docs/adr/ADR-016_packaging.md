# ADR-0016: Packaging

**Status:** Proposed
**Date:** 2025-09-05

## Context

Need distribution-ready Python packaging per standards (PEP 621), with wheels/sdists, CLI entry points, typed package, tooling, CI/CD, SemVer via VCS tags, optional extras.

## Options

### A. setuptools + setuptools-scm

* ✅ Standards-first, simple, widely supported; VCS-tag versions; reproducible builds
* ⚠️ Requires tags discipline

### B. Poetry

* ✅ All-in-one UX
* ⚠️ Extra lock/installer layer; CI/publish differences

### C. Hatch (Chosen)

* ✅ Modern build backend; environment isolation; versioning hooks
* ✅ PEP 621 native support
* ✅ Flexible matrix testing without external tox/nox
* ⚠️ Requires team adoption and learning curve

## Decision

Adopt **Option C (Hatch)** as packaging/build system.

### Scope

* Single package `rpax`
* Standards-based config in `pyproject.toml`

### Out of Scope

* Vendor-specific pipelines
* Private package indexes
* Monorepo setups

## Implementation

### Layout

```
rpax/
  pyproject.toml
  src/rpax/
    __init__.py
    cli.py
    config.py
    artifacts.py
    explain/
      __init__.py
      analyzer.py
      formatter.py
    graph/
      __init__.py
      framework.py
      mermaid.py
      models.py
    models/
      __init__.py
      manifest.py
      project.py
      workflow.py
    parser/
      __init__.py
      project.py
      xaml.py
      xaml_analyzer.py
    schemas/
      __init__.py
      generator.py
      validator.py
    validation/
      __init__.py
      framework.py
      rules.py
  tests/
  schemas/
  docs/
    adr/
  .github/
    workflows/
  README.md
  LICENSE
  AUTHORS.md
  CLAUDE.md
  .pre-commit-config.yaml
  .gitignore
  uv.lock
```

### pyproject.toml (actual implementation)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "rpax"
version = "0.0.1"
description = "Code-first CLI tool that parses UiPath Process and Library projects into JSON call graphs, arguments, and diagrams for documentation, validation, and CI impact analysis"
readme = "README.md"
license = {file = "LICENSE"}
authors = [
    {name = "rpapub", email = "contact@rpapub.dev"}
]
keywords = ["uipath", "rpa", "automation", "cli", "parsing", "documentation", "ci", "analysis"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console", 
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Systems Administration",
    "Topic :: Utilities"
]
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.9.0,<1.0.0",
    "pydantic[email]>=2.0.0,<3.0.0", 
    "lxml>=4.9.0,<6.0.0",
    "defusedxml>=0.7.1,<1.0.0",
    "rich>=13.0.0,<14.0.0",
    "pathlib>=1.0.1",
    "jsonschema>=4.17.0,<5.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-xdist>=3.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "pre-commit>=3.0.0",
    "types-lxml>=2023.0.0.0"
]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0", 
    "pytest-xdist>=3.0.0"
]

[project.scripts]
rpax = "rpax.cli:app"

[project.urls]
Homepage = "https://github.com/rpapub/rpax"
Repository = "https://github.com/rpapub/rpax"
Issues = "https://github.com/rpapub/rpax/issues"
Documentation = "https://rpapub.dev/rpax"

[tool.hatch.build.targets.sdist]
include = [
    "/src/rpax",
    "/README.md",
    "/LICENSE",
    "/AUTHORS.md"
]

[tool.hatch.build.targets.wheel]
packages = ["src/rpax"]

# Additional tooling configuration (Black, Ruff, mypy, pytest, coverage)
# See full pyproject.toml for complete configuration details
```

### `__init__.py` (actual implementation)

```python
"""rpax - Code-first CLI tool for UiPath project analysis.

rpax parses UiPath Process and Library projects into JSON call graphs, arguments, 
and diagrams for documentation, validation, and CI impact analysis.
"""

__version__ = "0.0.1"
__author__ = "rpapub"
__email__ = "contact@rpapub.dev"
__description__ = "Code-first CLI tool for UiPath project analysis"

from rpax.config import RpaxConfig

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "__description__",
    "RpaxConfig",
]
```

### Build & Verify

* Build: `hatch build` → sdist + wheel
* Verify: `pipx install dist/rpax-*.whl`

### Typing & Style

* `py.typed` included
* mypy, Ruff, Black
* pre-commit hooks

### Tests

* pytest + coverage
* Hatch envs for matrix testing

### Docs & Files

* README, CHANGELOG, LICENSE, CONTRIBUTING

### CI/CD

* PR: lint, type-check, test, build
* Tag: build + publish to PyPI, attach hashes, optional SBOM

### Provenance

* sha256 hashes for artifacts
* optional SBOM (CycloneDX)

### Versioning

* SemVer via tags
* hatch version bump + VCS tag

### Extras

* `rpax[mcp]` stdio server deps
* `rpax[api]` FastAPI/uvicorn

## Consequences

* Modern packaging with Hatch simplifies config
* Requires adoption of new workflows by contributors

## Rollout

* v0.0.1: baseline Hatch packaging, CI, lint/type/tests
* v0.1.0+: extras, SBOM, extended matrix

## Resolved Questions

* **License**: Creative Commons Attribution 4.0 International License (CC-BY) in LICENSE file, but pyproject.toml specifies MIT License classifier - needs alignment
* **Minimum supported Python version**: Python >=3.11 - chosen for modern language features and type hints support
