# ADR-002: Layered Architecture for UiPath Workflow Analysis

**Status:** Accepted

## Context

Need modular analysis of UiPath/WF projects with clear evolution path toward integrations.

## Architecture Overview

The system follows a **4-layer architecture** with a **blueprint-driven generation pattern**:

```
Layer 1+2: CLI App (rpax) - Blueprint + Implementation
    ↓ (blueprint/spec generation)
OpenAPI.yaml
    ↓ (implementation generation)  
Layer 3: FastAPI Service (independent code)
    ↓ (resource spec generation)
Layer 4: MCP Resources (independent code)
```

**Key Principle**: CLI is the **specification source**, never the **runtime implementation** for API/MCP.

## Layers Implementation

### **Layer 1+2: CLI Application (rpax)**
**Implementation**: Python CLI with Typer
**Role**: Blueprint source + dev/admin tooling

**Layer 1 (Parser) Operations:**
- `rpax parse` — discover `.xaml`, normalize IDs, emit canonical artifacts
- `rpax schema` — generate JSON schemas for artifacts  
- `rpax pseudocode` — generate pseudocode artifacts with recursive expansion

**Layer 2 (Validation/CI) Operations:**
- `rpax validate` — apply configurable gates (missing/dynamic invokes, cycles, orphans)

**Dev/Admin Operations (CLI-only):**
- `rpax list`, `rpax explain`, `rpax graph`, `rpax activities` — read artifacts for testing
- `rpax clear`, `rpax projects` — lake management operations

### **Layer 3: Access API (Independent Service)**
**Implementation**: FastAPI service generated from OpenAPI spec
**Role**: HTTP interface over artifacts for tools/CI

**Key Characteristics:**
- Generated from CLI blueprint, never calls CLI
- Independent artifact access via shared `ArtifactsManager`
- JSON responses, HTTP status codes, async operations
- ETag caching and content negotiation

### **Layer 4: MCP/Integration (Independent Service)**  
**Implementation**: MCP server generated from API spec
**Role**: Stable external resource contracts for ecosystem consumption

**Key Characteristics:**
- Generated from API specification, never calls API
- Independent artifact access via shared `ArtifactsManager`  
- MCP resource protocol, streaming operations
- URI scheme: `rpax://projects/{slug}/workflows/{id}`

## Decision

* **Go:** Implement blueprint-driven generation for all layers
* **Go:** CLI serves as Layer 1+2 implementation + blueprint source
* **Go:** Generate independent Layer 3/4 services from CLI metadata
* **No-Go:** Layer 3/4 services never call CLI at runtime

## Shared Components

### **ArtifactsManager (Cross-Layer)**
**Role**: Shared artifact access for all layers
**Implementation**: Direct lake file system access
**Usage**: CLI operations, API responses, MCP resources

```python
class ArtifactsManager:
    def get_workflows(self, project_slug: str) -> List[Workflow]
    def get_projects(self) -> List[Project] 
    def load_manifest(self, project_slug: str) -> Manifest
```

## Roadmap Phases

* **v0.0.1:** Layer 1+2 CLI implementation (ADR-007, ADR-008, ADR-009, ADR-010)
* **v0.1:** CLI decorator system for blueprint generation (ADR-024)  
* **v0.2:** Layer 3 FastAPI service generated from OpenAPI spec (ADR-011)
* **v0.3+:** Layer 4 MCP resources generated from API spec (ADR-012)

## Consequences

* **Positive**: Independent layer evolution, optimized implementations, clear separation
* **Positive**: Blueprint-driven consistency, single source of truth for API contracts
* **Negative**: Code generation complexity, multiple deployment artifacts
* **Neutral**: Shared ArtifactsManager provides common foundation

## Related ADRs

* ADR-007/008/009: Parser layer artifacts and formats (Layer 1)
* ADR-010: Validation layer rules and gates (Layer 2)  
* ADR-011: Access API HTTP interface (Layer 3) - **DEPENDS ON ADR-024**
* ADR-012: MCP resource contracts (Layer 4)
* ADR-015: Python CLI stack foundation
* ADR-024: CLI decorator blueprint system - **ENABLES Layer 3/4 generation**
