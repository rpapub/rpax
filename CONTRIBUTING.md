# Contributing to rpax

Thank you for your interest in contributing to rpax! This guide will help you get started with development.

## Introduction

<!-- Brief overview of the project and how contributions help -->

## Code of Conduct

<!-- Link to or include code of conduct expectations -->

## Prerequisites

### Required Tools

All contributors must have these tools installed:

1. **Python 3.11+** - Core language requirement
2. **uv** - Package manager (see [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/))
3. **Make** - Build automation tool
   - **Unix/Linux/macOS**: Usually pre-installed
   - **Windows**: Install via package manager:
     ```powershell
     # Chocolatey (recommended)
     choco install make
     
     # Or winget
     winget install GnuWin32.Make
     ```
4. **PowerShell Core (pwsh)** - Cross-platform shell
   - **Windows**: Install from [Microsoft Store](https://aka.ms/powershell) or `winget install Microsoft.PowerShell`
   - **Unix/Linux**: Follow [PowerShell installation guide](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell)
   - **GitHub Actions**: Pre-installed on all runners

### Verification

Verify your setup works:

```powershell
# Check tool versions
make --version          # Should show GNU Make
pwsh --version         # Should show PowerShell 7.x
uv --version           # Should show uv package manager
python --version       # Should show Python 3.11+
```

## Development Setup

### Getting rpax Working in an Already Cloned Repo

If you already have the rpax repository cloned, follow these steps to get it working:

```powershell
# Navigate to your cloned rpax directory
cd path\to\your\rpax

# Install rpax with ALL dependencies (dev, test, api, mcp extras)
uv sync --all-extras

# Verify installation works
uv run rpax --version
uv run rpax --help

# Test that all tools are available
uv run pytest --version
uv run ruff --version  
uv run mypy --version
uv run black --version
```

**Important**: Always use `uv sync --all-extras` to ensure all optional dependencies are installed. This includes:
- **dev**: Development tools (black, ruff, mypy, pre-commit)
- **test**: Testing framework (pytest, pytest-cov, pytest-xdist)
- **api**: FastAPI server dependencies (fastapi, uvicorn)
- **mcp**: Model Context Protocol integration dependencies

### Running Tests

To run the test suite:

```powershell
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=rpax --cov-report=term-missing

# Run specific test categories
uv run pytest tests/unit/           # Unit tests only
uv run pytest tests/integration/    # Integration tests only
uv run pytest -m "not slow"        # Skip slow tests

# Run tests in parallel (faster)
uv run pytest -n auto

# Run linting and type checking
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/  # Check formatting
uv run mypy src/
uv run black --check src/ tests/

# Fix formatting automatically
uv run ruff format src/ tests/
uv run black src/ tests/
```

**Testing Prerequisites**: Make sure you've run `uv sync --all-extras` to install all test dependencies including pytest, pytest-cov, and pytest-xdist.

## Branching Model

<!-- Git flow, branch naming conventions, etc. -->

## Commit Messages

<!-- Commit message format, conventional commits, etc. -->

## Pull Request Process

<!-- Steps for creating and reviewing PRs -->

## Development Task Automation

### Using Makefile for Development Tasks

rpax uses a **Makefile with PowerShell Core (pwsh)** for cross-platform development task automation. This approach provides the standardization benefits of Make while ensuring compatibility across Windows development and Ubuntu CI environments.

#### Prerequisites

All tools listed in the [Prerequisites](#prerequisites) section above must be installed.

#### Available Tasks

```powershell
# See all available tasks
make help

# Parse all test corpus projects (Windows development only)
make parse-all-corpuses

# Parse individual corpus projects
make parse-frozenchlorine
make parse-corpus-core1  
make parse-corpus-core10

# Development and CI tasks (cross-platform)
make test           # Run pytest test suite
make lint           # Run ruff and mypy checks
make format         # Auto-format code with black and ruff
make clean          # Clean rpax artifacts + build artifacts
make clean-lake     # Clean entire rpax lake (destructive)  
make clean-build    # Clean only build artifacts (safe)
make install        # Install package in development mode
make ci-test        # Run tests with coverage for CI
make build          # Build package distributions
```

#### Cross-Platform Design

The Makefile is designed for two distinct use cases:

1. **Windows Development**: Corpus parsing tasks using absolute paths to local test projects
   - `make parse-all-corpuses` - Process all test corpus projects
   - Uses Windows-specific paths like `D:/github.com/rpapub/FrozenChlorine/project.json`

2. **Cross-Platform CI/CD**: Standard development tasks using PowerShell Core cmdlets
   - `make clean` - Uses `Remove-Item` and `Get-ChildItem` for file operations
   - `make test`, `make lint` - Platform-independent Python tool execution
   - Works identically on Windows development and Ubuntu GitHub runners

#### Architecture Decision

See [ADR-031: Use Makefile with PowerShell Core](docs/adr/ADR-031.md) for the complete rationale behind this tooling choice. Key benefits:

- **Cross-platform compatibility**: PowerShell Core works identically on Windows and Linux
- **Path handling**: Automatic path separator normalization across platforms  
- **Industry standard**: Makefile provides expected development workflow
- **uv integration**: Seamless integration with `uv run` Python execution

#### Example Workflows

```powershell
# Standard development workflow
make clean          # Clean previous artifacts
make format         # Format code  
make lint           # Check code quality
make test           # Run test suite
make parse-all-corpuses  # Test against corpus projects

# Package build and testing workflow
make build          # Build wheel and sdist distributions
make check-package  # Validate built package contents and metadata
make test-install   # Test installation from built wheel

# CI/CD workflow (works on both Windows and Ubuntu)
make clean
make ci-test        # Run tests with coverage reporting
make build          # Build distributions

# Individual corpus testing
make parse-frozenchlorine  # Test specific corpus project
```

#### PowerShell Core Commands

The Makefile uses PowerShell cmdlets for cross-platform file operations:

```makefile
# Cross-platform clean operation  
clean:
    $(RPAX) clear artifacts --confirm    # Use rpax's built-in lake cleaning
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build/
```

These commands work identically on Windows PowerShell, Windows PowerShell Core, and Linux PowerShell Core, ensuring consistent behavior across all development environments.

## Coding Style / Linting

rpax enforces consistent code quality through automated tooling integrated with the Makefile workflow.

## OpenAPI Specification Generation

### Generating API Documentation from CLI Blueprint

rpax uses a unique **blueprint-driven approach** where the CLI commands serve as the source of truth for API specification generation. The `@api_expose()` decorators on CLI commands define which endpoints should be available in the HTTP API.

#### Generating OpenAPI Specs

```powershell
# Generate OpenAPI specification from CLI decorators
uv run python tools/generate_openapi.py

# Output: docs/api/v0/openapi.yaml (YAML format with all dependencies)
```

#### API Versioning Configuration

API version and generation settings are configured in `pyproject.toml`:

```toml
[tool.rpax.api_generation]
version = "v0"          # API version (v0 for initial development)
base_path = "/api"      # Base API path
title = "rpax API"      # OpenAPI title
description = "UiPath project analysis API - generated from CLI blueprint"
```

#### Architecture

The blueprint generation pattern ensures single source of truth:

```
CLI Commands (@api_expose decorated)
    ↓ (extract metadata)
OpenAPI Specification (docs/api/v0/openapi.yaml)
    ↓ (future: generate service)
FastAPI Service (independent implementation)
    ↓ (future: generate resources)
MCP Resources (independent implementation)
```

#### Output Structure

Generated specifications are versioned:
- `docs/api/v0/openapi.yaml` - Current API specification
- `docs/api/v1/openapi.yaml` - Future version specifications
- Format: YAML preferred (falls back to JSON if PyYAML unavailable)

#### CLI Command Classification

Commands are classified using `@api_expose()` decorators:

**API-Exposed Commands:**
- `list` → `GET /projects/{project}/workflows`
- `projects` → `GET /projects`  
- `explain` → `GET /projects/{project}/workflows/{workflow}`
- `validate` → `GET /projects/{project}/validation`
- `graph` → `GET /projects/{project}/graphs/{graph_type}`
- `schema` → `GET /schemas/{action}`
- `activities` → `GET /projects/{project}/workflows/{workflow}/activities/{action}`
- `pseudocode` → `GET /projects/{project}/workflows/{workflow}/pseudocode`

**CLI-Only Commands:**
- `parse` → (writes files, not suitable for API)
- `clear` → (destructive operations, CLI-only)
- `help` → (CLI-specific help)
- `api` → (server management, CLI-only)

#### Blueprint Development Workflow

1. **Modify CLI command** with appropriate `@api_expose()` decorator
2. **Regenerate spec**: `uv run python tools/generate_openapi.py`
3. **Review changes**: Check `docs/api/v0/openapi.yaml`
4. **Test CLI**: `uv run rpax <command> --help` to verify decorator works
5. **Future**: Generate FastAPI service from updated spec

## Access API Development

### Working with the rpax API Server

rpax includes a minimal read-only HTTP API server for programmatic access to lake data. This is useful during development for testing integrations and debugging parsing results.

#### Starting the API Server

```powershell
# Start API server with default configuration (requires api.enabled=true in config)
uv run rpax api

# Force enable API regardless of config setting
uv run rpax api --enable

# Temporarily enable API for one session (ignores config)
uv run rpax api --enable-temp

# Start with custom configuration
uv run rpax api --config .rpax.json --enable

# Override port and bind address
uv run rpax api --port 8624 --bind 127.0.0.1

# Start in background for testing
uv run rpax api --enable-temp &
```

#### Temporary vs Permanent API Enabling

**`--enable`**: Overrides config setting permanently for this session
- Changes the effective config for this API session
- Useful when you want to enable API despite config having `"enabled": false`
- Can be combined with other overrides like `--port`

**`--enable-temp`**: Ignores config entirely, forces API to start
- Perfect for development when you want to quickly inspect lake data
- No need to modify config files
- Ideal for one-off debugging sessions

```powershell
# Development workflow examples:

# 1. Parse project, then quickly inspect via API
uv run rpax parse "D:\MyUiPathProject"
uv run rpax api --enable-temp

# 2. Enable API despite config saying disabled
uv run rpax api --enable --port 9000

# 3. Standard workflow with config
# (config.json has "api": {"enabled": true})
uv run rpax api
```

#### API Endpoints

The API provides two main endpoints for development and monitoring:

1. **Health Check**: `GET /health`
   ```json
   {
     "status": "ok",
     "timestamp": "2025-01-08T12:00:00Z"
   }
   ```

2. **Status Overview**: `GET /status`
   ```json
   {
     "rpaxVersion": "0.0.1",
     "uptime": "1h23m45s",
     "startedAt": "2025-01-08T10:36:15Z",
     "mountedLakes": [
       {
         "path": "/path/to/.rpax-lake",
         "projectCount": 3,
         "lastScanAt": "2025-01-08T12:00:00Z"
       }
     ],
     "totalProjectCount": 3,
     "latestActivityAt": "2025-01-08T11:30:00Z",
     "memoryUsage": {
       "heapUsed": "45.2MB",
       "heapTotal": "64.0MB"
     }
   }
   ```

#### Service Discovery

The API server creates a service discovery file for other tools to locate the running instance:

**Location**: `%LOCALAPPDATA%\rpax\api-info.json` (Windows) or `~/.local/share/rpax/api-info.json` (Unix)

**Contents**:
```json
{
  "url": "http://127.0.0.1:8623",
  "pid": 12345,
  "startedAt": "2025-01-08T10:36:15Z",
  "rpaxVersion": "0.0.1",
  "lakes": ["/path/to/.rpax-lake"],
  "projectCount": 3,
  "configPath": "/path/to/.rpax.json"
}
```

#### Configuration

Add API settings to your `.rpax.json`:

```json
{
  "project": {
    "name": "MyProject",
    "type": "process"
  },
  "api": {
    "enabled": true,
    "port": 8623,
    "bind": "127.0.0.1",
    "readOnly": true
  }
}
```

#### Testing the API

```powershell
# Test health endpoint
curl http://127.0.0.1:8623/health

# Test status endpoint
curl http://127.0.0.1:8623/status

# Test method not allowed (should return 405)
curl -X POST http://127.0.0.1:8623/health

# Test unknown endpoint (should return 404)
curl http://127.0.0.1:8623/unknown
```

#### Development Notes

- **Read-only**: API never modifies lake data - only provides read access
- **Localhost only**: Binds to 127.0.0.1 by default for security
- **Auto-increment ports**: If configured port is busy, automatically tries next available port
- **Graceful shutdown**: Service discovery file is cleaned up on shutdown
- **Memory monitoring**: Status endpoint includes memory usage for debugging

## Python Packaging & Distribution

### Building Packages for Distribution

rpax uses modern Python packaging with hatchling build backend and dynamic versioning for maintainable releases.

#### Package Configuration

**Version Management**: rpax uses **single source of truth versioning** where `src/rpax/__init__.py` contains the authoritative version:

```python
__version__ = "0.1.0"  # Single source of truth
```

The `pyproject.toml` is configured to read this dynamically:

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/rpax/__init__.py"
```

This ensures `rpax --version` always matches the package version.

#### Package Contents

The package includes **everything needed for standalone operation**:

- **Core package**: `src/rpax/` - Main CLI and parsing logic
- **XAML parser**: `src/xaml_parser/` - Standalone XAML parsing module
- **JSON schemas**: Embedded in package for artifact validation
- **All dependencies**: Specified with appropriate version ranges

#### Build Workflow

```powershell
# Prerequisites: Install with dev dependencies
uv sync --all-extras

# Build package distributions
make build          # Creates dist/rpax-*.whl and dist/rpax-*.tar.gz

# Validate package contents and metadata
make check-package  # Lists wheel contents + runs twine check

# Test installation in current environment
make test-install   # Installs wheel + tests CLI functionality
```

#### Package Validation

The build process includes comprehensive validation:

1. **Content verification**: Lists all files included in wheel
2. **Metadata validation**: Uses `twine check` to validate PyPI compatibility  
3. **Installation testing**: Installs built wheel and tests CLI commands
4. **Version consistency**: Ensures CLI `--version` matches package metadata

#### Manual Package Inspection

```powershell
# List wheel contents
uv run python -m zipfile -l dist/rpax-*.whl

# Validate PyPI compatibility
uv run python -m twine check dist/*

# Test in clean virtual environment
python -m venv test-env
test-env\Scripts\activate
pip install dist/rpax-*.whl
rpax --version
rpax --help
deactivate
```

#### Package Dependencies

**Runtime dependencies** (required for `pip install rpax`):
- `typer>=0.9.0,<1.0.0` - CLI framework
- `pydantic[email]>=2.0.0,<3.0.0` - Data validation
- `lxml>=4.9.0,<6.0.0` + `defusedxml>=0.7.1,<1.0.0` - Secure XML processing
- `rich>=13.0.0,<14.0.0` - Rich console output
- Additional dependencies as specified in `pyproject.toml`

**Development dependencies** (available via `uv sync --all-extras`):
- **dev**: Testing, linting, formatting tools (pytest, ruff, black, mypy)
- **api**: FastAPI server dependencies (fastapi, uvicorn) 
- **mcp**: Model Context Protocol integration
- **build**: Package building tools (build, twine)

#### Version Release Process

1. **Update version**: Edit `src/rpax/__init__.py` only
   ```python
   __version__ = "0.1.1"  # New version
   ```

2. **Test locally**: 
   ```powershell
   make build
   make check-package
   make test-install
   ```

3. **Commit changes**: Version update + any release changes

4. **Build release package**: `make build` creates distribution-ready files

#### Packaging Architecture

rpax packaging follows these principles:

- **Single source of truth**: Version defined once in `__init__.py`
- **Complete packages**: Everything needed bundled (no external file dependencies)
- **Reproducible builds**: Locked dependencies with appropriate version ranges
- **Professional validation**: Comprehensive testing before distribution
- **Clear documentation**: Complete packaging workflow documented for contributors

## Lake Management

### Clearing Lake Data

rpax provides a safe `clear` command for managing lake data during development. This is especially useful when testing different project configurations or cleaning up after failed parses.

#### Command Overview

```powershell
# Show what would be cleared (dry-run mode - default)
uv run rpax clear artifacts

# Actually clear artifacts (safest option)
uv run rpax clear artifacts --confirm

# Clear specific project data
uv run rpax clear project --project f4aa3834 --confirm

# Clear entire lake (DESTRUCTIVE - use with caution)
uv run rpax clear lake --confirm
```

#### Clear Scopes

1. **`artifacts`** (SAFEST) - Clear generated artifacts, preserve original files
   - Removes: manifest.json, workflows.index.json, invocations.jsonl, activities.*, metrics.*, paths.*
   - Preserves: project.json files, projects.json index structure
   - Use case: Clean up after parsing experiments

2. **`project`** - Clear all data for specific project
   - Requires: `--project <slug>` parameter
   - Removes: Entire project directory and contents
   - Use case: Remove specific project from lake

3. **`lake`** (DESTRUCTIVE) - Clear entire lake directory
   - Removes: Everything in the lake directory
   - Use case: Complete reset during development

#### Safety Features

- **Dry-run by default**: All commands show preview without `--confirm`
- **Multiple confirmations**: Destructive operations require multiple prompts
- **Size warnings**: Large deletions (>100MB) show warnings
- **Project validation**: Verifies projects exist before attempting deletion
- **CLI-only**: Never exposed via API or MCP for security

#### Examples

```powershell
# Preview what artifacts would be cleared
uv run rpax clear artifacts --path .rpax-lake

# Clear artifacts for development cleanup
uv run rpax clear artifacts --confirm

# Remove a specific project (get slug from rpax list first)
uv run rpax list workflows  # Shows available projects
uv run rpax clear project --project my-proj-1234 --confirm

# Complete lake reset (development only)
uv run rpax clear lake --confirm --force  # Skip interactive prompts
```

#### Best Practices

- Always run without `--confirm` first to preview changes
- Use `artifacts` scope for most development cleanup needs
- Only use `lake` scope when you need a complete reset
- Keep backups of important projects before clearing
- Use `--project` parameter to target specific projects

## Testing

<!-- Testing philosophy, test structure, coverage requirements -->

## Documentation

<!-- How to update docs, ADRs, etc. -->

## Issue Reporting

<!-- How to report bugs, request features -->

## Release Process

<!-- How releases are created and published -->

## License & Attribution

<!-- Licensing requirements, attribution guidelines -->