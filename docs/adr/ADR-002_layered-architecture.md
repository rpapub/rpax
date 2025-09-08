# ADR-002: Layered Architecture for UiPath Workflow Analysis

**Status:** Amended (Updated 2025-09-08)

## Context

Need modular analysis of UiPath/WF projects with clear evolution path toward integrations.

## Amendment Notes (2025-09-08)

**What Changed**: Implementation exceeded original architectural vision
- Layer 2 redefined as "Transformation/Enhancement" (was "Validation/CI")  
- Added comprehensive activity resource model with package relationships
- Added lake-level error collection with run-scoped diagnostics
- Added V0 schema with progressive disclosure (low/medium/high detail levels)
- Added integrated CLI pipeline architecture
- Updated shared components to reflect actual implementation
- Updated roadmap to reflect completed phases through v0.0.3

**Why Amended**: Original architecture was foundational but implementation evolved beyond the initial scope while maintaining the core 4-layer principle.

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

**Layer 2 (Transformation/Enhancement) Operations:**
- `rpax pseudocode` — generate pseudocode artifacts with recursive expansion
- Activity resource generation with package relationships and container hierarchies
- Enhanced XAML analysis with visual vs structural activity detection
- V0 schema generation with progressive disclosure (low/medium/high detail levels)
- Lake-level error collection with run-scoped diagnostics
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

### **Shared Components (Cross-Layer)**

**ArtifactsManager**: Direct lake file system access for all layers
**ActivityResourceManager**: Activity-centric resource generation with package relationships
**ErrorCollector**: Run-scoped error collection with lake-level diagnostics  
**URIResolver**: Resource navigation and cross-references
**IntegratedArtifactPipeline**: Unified pipeline combining all components

```python
class ArtifactsManager:
    def get_workflows(self, project_slug: str) -> List[Workflow]
    def get_projects(self) -> List[Project] 
    def load_manifest(self, project_slug: str) -> Manifest

class ActivityResourceManager:
    def generate_activity_resources(self, workflow_index, project_root, project_slug, output_dir)
    def generate_v0_activity_resources(self, workflow_index, project_root, project_slug, v0_dir)

class ErrorCollector:
    def collect_error(self, error, context, severity)
    def flush_to_filesystem(self) -> Path
```

## Implementation Status (Updated 2025-09-08)

* **v0.0.1:** ✅ Layer 1+2 CLI foundation (ADR-007, ADR-008, ADR-009, ADR-010)
* **v0.0.2:** ✅ Enhanced XAML parsing, validation framework, Python packaging  
* **v0.0.3:** ✅ V0 schema, activity resources, error collection, integrated pipeline
* **v0.0.4:** 🔄 Architecture documentation, Layer 3 API implementation
* **v0.0.5+:** 🔒 Layer 4 MCP resources with stable resource contracts

**Note**: Previous internal roadmap versions (v0.1, v0.2, v0.3) were never published and have been superseded by the actual release sequence above.

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
