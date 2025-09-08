# Code Navigation Guide - rpax

**Target Audience**: New developers onboarding to rpax codebase  
**Purpose**: Quick reference for finding functionality and understanding code organization  
**Last Updated**: 2025-09-08  

---

## Quick Reference: "Where do I find...?"

### **CLI Commands**
- **Location**: `src/rpax/cli/`
- **Entry Point**: `src/rpax/cli/main.py` - Main CLI application with Typer
- **Commands**: `src/rpax/cli/commands/` - Individual command implementations
  - `parse.py` - Project parsing and artifact generation
  - `validate.py` - Validation rules and gates
  - `list.py` - Workflow and project listing
  - `graph.py` - Diagram generation (Mermaid/Graphviz)
  - `explain.py` - Workflow details and analysis

### **XAML Parsing**
- **Location**: `src/rpax/parser/`
- **Core Parser**: `src/rpax/parser/xaml_parser.py` - Main XAML parsing logic
- **Enhanced Analysis**: `src/rpax/parser/enhanced_xaml_analyzer.py` - Activity detection and analysis
- **Coded Workflows**: `src/rpax/parser/coded_workflow.py` - C# workflow parsing (.cs files)
- **Project Metadata**: `src/rpax/parser/project_parser.py` - project.json parsing

### **Activity Resources**
- **Location**: `src/rpax/resources/`
- **Manager**: `src/rpax/resources/activity_resource_manager.py` - Central resource coordination
- **Generator**: `src/rpax/resources/activity_resource_generator.py` - Resource creation from activities
- **Package Resolver**: `src/rpax/resources/activity_package_resolver.py` - UiPath package mapping
- **Container Parser**: `src/rpax/resources/container_info_parser.py` - Then/Else/Catch hierarchy
- **URI Resolution**: `src/rpax/resources/uri_resolver.py` - Resource addressing (`rpax://` scheme)

### **Error Collection & Diagnostics**
- **Location**: `src/rpax/diagnostics/`
- **Error Collector**: `src/rpax/diagnostics/error_collector.py` - Run-scoped error aggregation
- **Error Models**: `src/rpax/diagnostics/models.py` - ErrorContext, RpaxError, ErrorSummary
- **Lake Storage**: Errors stored at `{lake}/_errors/` for analysability

### **V0 Schema & Output**
- **Location**: `src/rpax/output/v0/`
- **Generator**: `src/rpax/output/v0/generator.py` - V0 schema generation pipeline
- **Detail Levels**: `src/rpax/output/v0/detail_levels.py` - Progressive disclosure (low/medium/high)
- **Entry Points**: `src/rpax/output/v0/entry_point_builder.py` - First-class entry point resources

### **Validation System**
- **Location**: `src/rpax/validation/`
- **Rules**: `src/rpax/validation/rules/` - Individual validation implementations
- **Framework**: `src/rpax/validation/validator.py` - Validation orchestration
- **Gates**: Configuration-driven validation for CI pipelines

### **Configuration & Schemas**
- **Location**: `src/rpax/schemas/`
- **Config Schema**: `src/rpax/schemas/config.v1.schema.json` - JSON Schema for .rpax.json
- **Models**: `src/rpax/models/` - Pydantic models for all data structures
- **Config Loader**: `src/rpax/config/` - Configuration loading and validation

---

## Architecture Overview: Key Modules

### **Layer 1: Parser (`src/rpax/parser/`)**
**Purpose**: Discover, normalize, and extract canonical data from UiPath projects

```
src/rpax/parser/
├── xaml_parser.py           # Core XAML parsing (pattern-matching approach)
├── enhanced_xaml_analyzer.py # Activity detection, visual vs structural
├── project_parser.py        # project.json metadata extraction
├── coded_workflow.py        # C# workflow parsing (.cs files)
├── workflow_discovery.py    # Multi-format workflow discovery
└── path_resolver.py         # Cross-platform path normalization
```

**Key Classes**:
- `XamlParser` - Main XAML processing with defusedxml
- `EnhancedXamlAnalyzer` - Activity analysis and container hierarchy
- `ProjectParser` - project.json metadata and entry point extraction
- `CodedWorkflowParser` - C# workflow argument extraction

### **Layer 2: Transformation (`src/rpax/output/`, `src/rpax/resources/`)**
**Purpose**: Transform parsed data into optimized schemas and resources

```
src/rpax/output/
├── v0/                      # V0 experimental schema (MCP-optimized)
│   ├── generator.py         # Main V0 generation pipeline
│   ├── detail_levels.py     # Progressive disclosure optimization
│   └── entry_point_builder.py # Entry point resource generation
└── legacy/                  # Original artifact formats
    ├── manifest_generator.py
    ├── workflow_indexer.py
    └── invocation_tracer.py

src/rpax/resources/
├── activity_resource_manager.py    # Resource coordination
├── activity_resource_generator.py  # Activity → resource conversion
├── activity_package_resolver.py    # UiPath package mapping
└── uri_resolver.py                 # Resource addressing scheme
```

**Key Classes**:
- `V0Generator` - Experimental schema pipeline
- `ActivityResourceManager` - Activity-centric resource model
- `DetailLevelExtractor` - Progressive disclosure optimization
- `URIResolver` - Resource navigation (`rpax://projects/{slug}/workflows/{id}`)

### **Layer 3: Access API (`src/rpax/api/`) - Architecture Ready**
**Purpose**: HTTP interface over artifacts (future implementation)

```
src/rpax/api/                # Future FastAPI implementation
├── decorators.py            # CLI → API exposure decorators
├── openapi_generator.py     # OpenAPI spec generation
└── service_discovery.py     # API endpoint discovery
```

### **Layer 4: MCP Integration (`src/rpax/mcp/`) - Architecture Ready**
**Purpose**: MCP resource contracts for ecosystem consumption

```
src/rpax/mcp/                # Future MCP server implementation
└── resource_contracts.py   # MCP resource protocol definitions
```

### **Cross-Layer: Integration (`src/rpax/cli_integration.py`)**
**Purpose**: Unified pipeline combining all components

```python
class IntegratedArtifactPipeline:
    """Combines parser, transformation, activity resources, and error collection"""
    def generate_project_artifacts(self, data: ParsedProjectData, schema_version: str)
```

---

## Common Development Tasks

### **Adding a New CLI Command**

1. **Create command file**: `src/rpax/cli/commands/my_command.py`
2. **Follow existing patterns**: Look at `parse.py` or `list.py` for structure
3. **Add to main CLI**: Register in `src/rpax/cli/main.py`
4. **Update ADR-003**: Document new command surface

```python
# Example structure
import typer
from rpax.models import ProjectData

def my_command(
    path: str = typer.Argument(..., help="Project path"),
    output: Optional[str] = typer.Option(None, help="Output directory")
) -> None:
    """Command description for help text"""
    # Implementation here
```

### **Adding New Validation Rule**

1. **Create rule file**: `src/rpax/validation/rules/my_rule.py`
2. **Implement validation interface**: Follow pattern from existing rules
3. **Register rule**: Add to validation framework
4. **Add configuration**: Update config schema for enable/disable

```python
# Example validation rule
from rpax.validation.base import ValidationRule, ValidationResult

class MyValidationRule(ValidationRule):
    def validate(self, project_data: ProjectData) -> List[ValidationResult]:
        # Rule implementation
        return results
```

### **Extending XAML Parsing**

1. **Pattern identification**: Add pattern to `enhanced_xaml_analyzer.py`
2. **Activity mapping**: Update activity type detection
3. **Test coverage**: Add test cases for new patterns
4. **Documentation**: Update parsing documentation

### **Adding New Output Format**

1. **Generator implementation**: Create in `src/rpax/output/`
2. **Format registration**: Add to output format enum
3. **CLI integration**: Update graph/export commands
4. **Configuration**: Add format options to config schema

---

## Data Flow: Key Interfaces

### **Main Data Pipeline**
```
UiPath Project Files
    ↓ (XamlParser, ProjectParser)
ParsedProjectData
    ↓ (IntegratedArtifactPipeline)
Generated Artifacts + Activity Resources + Error Diagnostics
    ↓ (Output Generators)
Lake Artifacts (JSON files)
```

### **Key Data Models** (`src/rpax/models/`)

```python
# Core data structures
class ProjectData:          # Complete project representation
class WorkflowData:         # Individual workflow information  
class ActivityData:         # Activity analysis results
class InvocationData:       # Workflow call relationships
class ManifestData:         # Project metadata and entry points
```

### **Configuration Flow**
```
.rpax.json (user config)
    ↓ (Config loader + JSON Schema validation)
ConfigurationData
    ↓ (CLI commands)
Runtime behavior configuration
```

---

## Testing Architecture

### **Test Organization** (`tests/`)

```
tests/
├── unit/                    # Isolated component tests
│   ├── parser/             # XAML parsing tests
│   ├── resources/          # Activity resource tests
│   ├── validation/         # Validation rule tests
│   └── output/             # Output format tests
├── integration/            # Multi-component tests
│   ├── cli/               # CLI command integration
│   ├── pipeline/          # End-to-end pipeline tests
│   └── corpus/            # Real project testing
└── fixtures/              # Test data and mocks
    ├── projects/          # Sample UiPath projects
    ├── expected_outputs/  # Expected artifact outputs
    └── mock_data/         # Generated test data
```

### **Test Corpus Integration**
- **Real Projects**: 5 UiPath corpus projects for integration testing
- **Test Categories**: Unit → Integration → Corpus validation
- **Performance**: Benchmarks against large projects (1k+ workflows)

---

## Development Tools & Utilities

### **Makefile Targets** (see `Makefile`)
```bash
make test                    # Run full test suite
make parse-all              # Parse all corpus projects (legacy + V0)
make lint                   # Code quality checks (ruff, black, mypy)
make clean                  # Clean artifacts and cache
```

### **Debugging Workflows**
- **CLI Debugging**: Use `python -m rpax.cli.main` for development
- **Parser Debugging**: Direct module imports for component testing
- **Logging**: Rich console output with structured logging
- **Performance**: Built-in timing and memory analysis

### **Configuration for Development**
- **IDE Setup**: VS Code recommended with Python extensions
- **Pre-commit**: Automated formatting and linting
- **Type Checking**: mypy --strict for full type safety
- **Dependencies**: uv for fast, reproducible environments

---

## Extension Points

### **Parser Extensions**
- **Custom Activities**: Add to activity detection patterns
- **New File Types**: Extend discovery and parsing logic
- **Alternative Formats**: Add support for non-XAML workflows

### **Output Extensions**
- **New Schemas**: Follow V0 generator pattern for new formats
- **Export Formats**: Add diagram or data export capabilities
- **Resource Types**: Extend activity resource model

### **Integration Extensions**
- **API Endpoints**: Use decorator system for automatic exposure
- **MCP Resources**: Follow URI scheme for new resource types
- **Validation Rules**: Plugin architecture for custom rules

---

## Performance Considerations

### **Large Project Handling**
- **Streaming**: Parser uses iterative processing for memory efficiency
- **Parallelization**: Ready for multiprocessing on large corpuses
- **Caching**: Incremental parsing for unchanged projects
- **Memory**: Garbage collection optimization for long-running processes

### **Optimization Points**
- **XAML Parsing**: lxml for performance-critical operations
- **JSON Serialization**: Pydantic optimized models
- **File I/O**: Efficient batch operations for artifact generation
- **Resource Generation**: Lazy loading for activity resources

---

## Related Documentation

- **Architecture**: `docs/adr/ADR-002` - 4-layer architecture details
- **Development**: `CLAUDE.md` - Comprehensive development methodology  
- **Style Guide**: `docs/llm/context/styleguide.md` - Code standards
- **Risk Register**: `docs/risks/register.md` - Known edge cases and challenges
- **Testing**: Corpus projects documented in test fixtures

---

**Questions or Need Help?**
1. Check relevant ADRs in `docs/adr/` for architectural context
2. Look at existing implementations for patterns and conventions  
3. Review test cases for usage examples and edge cases
4. Consult `CLAUDE.md` for development methodology and workflows