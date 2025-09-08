# ADR-030: Path Separator Normalization Strategy

**Status:** Approved  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  
**Consulted:** Parser Layer, Access API Layer

## Context

The rpax project operates across multiple contexts with different path separator expectations:

1. **UiPath Context (Windows)**: Native XAML files use backslashes (`Framework\InitAllSettings.xaml`)
2. **Lake Storage**: Mixed usage creating resolution failures  
3. **API/MCP Context**: URIs require forward slashes for resource addressing
4. **Cross-platform**: Must work on Windows, Linux, macOS

**Current Problem**: Inconsistent path separators cause "missing" workflow resolution failures, as demonstrated in corpus testing where `Framework\InitAllSettings.xaml` couldn't be resolved despite being parsed.

**Evidence**: 
- `invocations.jsonl` uses backslashes: `"targetPath": "Framework\\InitAllSettings.xaml"`
- `workflows.index.json` uses forward slashes: `"relativePath": "Framework/InitAllSettings.xaml"`
- Resolution logic fails due to separator mismatch

## Decision

**Adopt forward slashes (POSIX format) as the canonical internal representation throughout rpax.**

### Core Principle
All internal paths, workflow IDs, and resource references use forward slashes (`/`) regardless of the host operating system.

### Conversion Points
- **Input Boundary**: Normalize backslashes to forward slashes immediately upon parsing XAML
- **Storage**: All lake artifacts use forward slash paths
- **Output Boundary**: Convert to platform-specific paths only when performing OS operations

## Implementation

### 1. Parser Layer (Layer 1)
```python
def normalize_path(path: str) -> str:
    """Convert any path to canonical forward slash format."""
    return path.replace("\\", "/")
```

Apply normalization at:
- XAML workflow discovery (`parser/xaml.py`)
- InvokeWorkflowFile target extraction (`parser/xaml_analyzer.py`) 
- Workflow ID generation (`models/workflow.py`)

### 2. Lake Artifacts
- `invocations.jsonl`: `targetPath` uses forward slashes
- `workflows.index.json`: All path fields use forward slashes
- `manifest.json`: Entry points use forward slashes
- Resource URIs: Natural forward slash format for MCP/API

### 3. Resolution Logic
- Normalize both source and target paths before comparison
- Support mixed format during transition period
- Fail gracefully with clear error messages

### 4. OS Operations
- Convert to platform-specific paths only when accessing files
- Use `pathlib.Path()` for cross-platform file operations
- Maintain Windows absolute paths in `filePath` for debugging

## Rationale

### Benefits
- **MCP Compatibility**: URIs naturally expect forward slashes
- **Cross-platform**: Eliminates Windows-specific path handling
- **LLM Context**: Consistent, clean paths for AI understanding
- **Debugging**: Single format reduces separator-related bugs
- **Resolution**: Eliminates "missing" workflow issues from separator mismatch

### Alternatives Considered

1. **Keep Native Separators**: Rejected - breaks MCP URI scheme
2. **Convert at Output**: Rejected - internal inconsistency causes bugs
3. **Support Both Formats**: Rejected - complexity without benefit
4. **Platform Detection**: Rejected - unnecessary complexity

## Consequences

**Positive:**
- Resolves corpus testing "missing" workflow bugs
- Enables clean MCP resource URIs (`rpax://project/workflow/path`)
- Simplifies cross-platform development and testing
- Reduces path-related debugging complexity

**Negative:**
- Requires updating existing lake artifacts (migration)
- Potential confusion for Windows developers expecting backslashes
- One-time effort to audit all path handling code

**Migration:**
- Support both formats during transition
- Update artifacts progressively during parsing
- Document path format in lake schema

## Compliance

- **ADR-012**: Enables clean MCP URI scheme (`rpax://projects/{p}/workflows/{wf}`)
- **ADR-009**: Standardizes artifact path representation
- **ADR-002**: Maintains layer separation with consistent interfaces

## Implementation Tracking

- **ISSUE-058**: Complete path separator normalization to forward slashes
- **Testing**: Verify corpus projects resolve correctly
- **Migration**: Update existing lake artifacts to forward slash format

## Related ADRs

- **ADR-012**: MCP Integration Layer - requires forward slash URIs
- **ADR-009**: Parser Artifacts - path field normalization
- **ADR-002**: Layered Architecture - clean interface contracts