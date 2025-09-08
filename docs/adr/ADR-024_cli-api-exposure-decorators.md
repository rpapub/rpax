# ADR-024: CLI Blueprint Decorators for Layer 3/4 Generation

**Status:** Accepted  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  
**Consulted:** CLI Design, Access API Layer, MCP Integration Layer

## Context

The `rpax` CLI implements Layer 1+2 (Parser + Validation) and serves as the **blueprint source** for generating Layer 3 (API) and Layer 4 (MCP) services.

**Architecture Pattern:**
```
CLI Commands (decorated) → OpenAPI.yaml → FastAPI Service → MCP Resources
```

**Key Requirements:**
- CLI decorators provide **metadata only** for generation
- API/MCP services are **independent implementations** that never call CLI
- Single source of truth for service specifications
- Support for multiple API versions and evolution

## Decision

Implement `@api_expose()` decorators as **blueprint metadata** for generating independent Layer 3/4 services:  

```python
def api_expose(
    path: str = None,               # API endpoint path
    methods: List[str] = None,      # HTTP methods ["GET", "POST"] 
    summary: str = None,            # OpenAPI summary
    tags: List[str] = None,         # OpenAPI tags
    enabled: bool = True,           # Whether to expose (default: True)
    
    # Optional hints for MCP generation
    mcp_resource_type: str = None,  # "workflow_list", "project_detail"
):
    """Blueprint decorator for Layer 3/4 generation.
    
    Stores metadata for OpenAPI/MCP generation - never called at runtime.
    """
    def decorator(func):
        func._rpax_api = {
            "enabled": enabled,
            "path": path or f"/{func.__name__.replace('_command', '')}",
            "methods": methods or ["GET"],
            "summary": summary or func.__doc__,
            "tags": tags or [],
            "mcp_hints": {"resource_type": mcp_resource_type}
        }
        return func
    return decorator

# Usage examples:
@api_expose()  # All defaults
@app.command()
def projects(path: Path = ".rpax-lake"):
    """List all projects in the lake."""
    pass

@api_expose(
    path="/projects/{project}/workflows",
    tags=["workflows"],
    mcp_resource_type="workflow_list"
)
@app.command() 
def list_command(project: str = None):
    """List workflows in a project."""
    pass

@api_expose(enabled=False)  # Explicit CLI-only
@app.command()
def parse(path: Path):
    """Parse UiPath project (CLI-only - writes files)."""
    pass
```

**Generation Pipeline:**
1. **OpenAPI Generation**: Extract `f._rpax_api` metadata + CLI parameter info → `docs/openapi.yaml`
2. **FastAPI Generation**: Generate independent service code from OpenAPI spec  
3. **MCP Generation**: Generate MCP resources from API endpoints + MCP hints

## Rationale

**Blueprint Pattern Advantages:**
- **Single Source of Truth**: All service specifications derive from CLI metadata
- **Independent Services**: API/MCP never call CLI - optimized implementations
- **Evolution Support**: Multiple API versions from same CLI blueprint
- **Clear Separation**: CLI = Layer 1+2 + blueprint; API/MCP = Layer 3/4 services
- **Testability**: Each layer tested independently with shared ArtifactsManager

**Command Classification:**
- **API-Exposed**: `list`, `projects`, `graph`, `explain`, `validate`, `schema`, `activities`
- **CLI-Only**: `parse`, `clear`, `help` (writes files, destructive, or dev-only)
- **TBD**: `pseudocode` (may expose read-only subsets in future)

## Alternatives Considered

1. **Separate API Command Registry**
   - Rejected: Duplicate maintenance, drift risk
   - Commands could be added to CLI but forgotten in API registry

2. **Configuration-Based Mapping**  
   - Rejected: External config files add complexity
   - Harder to keep CLI and API changes synchronized

3. **Naming Convention** (`api_list`, `cli_parse`)
   - Rejected: Function name pollution, unclear boundaries
   - Would require duplicate implementations

4. **Separate API Module**
   - Rejected: Would duplicate parameter validation and business logic
   - Harder to ensure CLI and API behavior consistency

## Implementation Plan

### Phase 1: Blueprint Infrastructure
- **ISSUE-048**: Implement `@api_expose()` decorator in `src/rpax/cli.py`
- **ISSUE-049**: Decorate existing CLI commands with appropriate metadata
- **ISSUE-050**: Create OpenAPI generator (`tools/generate_openapi.py`)

### Phase 2: Independent Services (Future)
- Generate FastAPI service code from OpenAPI specification
- Generate MCP server code from API specification + MCP hints
- Implement shared `ArtifactsManager` for direct lake access

### Phase 3: Service Deployment
- Deploy FastAPI service independently (no CLI dependency)
- Deploy MCP server independently (no API dependency)
- Monitor and optimize each service separately

## Consequences

**Positive:**
- Clear separation between CLI and API surfaces
- Metadata lives with implementation (no drift)
- Enables automatic API generation from CLI introspection
- Future-proof for command additions/changes

**Negative:**  
- Additional decorator complexity in CLI code
- Requires discipline to use decorators consistently
- API changes require CLI code modifications

**Neutral:**
- Fits existing Typer/FastAPI ecosystem patterns
- Leverages existing CLI introspection infrastructure
- Compatible with current CLI documentation generation

## Compliance and Monitoring

- **ADR-003**: CLI command surface remains stable, decorators are additive
- **ADR-011**: Access API gets clear command boundaries from decorators  
- **ADR-012**: MCP resources generated only from API-exposed commands
- **Monitoring**: CLI docs generation should validate decorator consistency

## Related ADRs

- **ADR-003**: CLI Commands and Parameters - defines CLI surface area
- **ADR-011**: Access API Layer - **DEPENDS ON THIS ADR** for API endpoint generation from CLI decorators
- **ADR-012**: MCP Integration Layer - defines external resource contracts
- **ADR-021**: CLI Command Specification - provides parameter metadata foundation

## Dependencies

**This ADR is a prerequisite for ADR-011 (Access API Layer).**

The Access API implementation should generate HTTP endpoints by parsing Typer CLI commands decorated with `@api_expose()`, rather than manually implementing separate API endpoints. This ensures single source of truth and prevents drift between CLI and API behavior.