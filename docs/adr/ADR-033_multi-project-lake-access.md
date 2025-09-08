# ADR-033: Multi-Project Lake Access Patterns

**Status:** Approved  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  

## Context

As rpax lake usage grows, users need to manage multiple projects within a single lake for organizational efficiency and cross-project analysis. The original design focused on single-project parsing, but practical usage reveals needs for:

### Current Limitations
1. **No Lake-Level Discovery**: Users can't easily find projects within a lake
2. **Manual Project Navigation**: No programmatic way to list or search projects
3. **MCP Integration Gap**: MCP clients need lake-level resource discovery
4. **Poor Multi-Project UX**: Users must remember exact project slugs

### Use Cases Requiring Lake Access
- **Development Teams**: Managing multiple related UiPath projects in one lake
- **MCP Clients**: Progressive disclosure starting from "what projects exist?"
- **Governance Tools**: Generating project inventories for compliance
- **CI/CD Pipelines**: Discovering and validating multiple projects

## Decision

Implement **multi-project lake access patterns** centered around a `rpax list-projects` command and supporting infrastructure for lake-level project discovery and navigation.

## Architecture

### Lake Index Structure
```
.rpax-lake/
├── projects.json                   # Lake-level project registry
├── {project_slug_1}/
│   ├── project.json               # Project metadata
│   ├── manifest.json              # Parsing results
│   └── ...
├── {project_slug_2}/
└── ...
```

### projects.json Schema
```json
{
  "metadata": {
    "rpax_version": "0.0.3",
    "lake_created": "2025-01-09T10:00:00Z",
    "last_updated": "2025-01-09T12:00:00Z",
    "total_projects": 3
  },
  "projects": [
    {
      "name": "Calculator Process",
      "slug": "calculator-process-f4aa3834",
      "type": "process",
      "source_path": "D:/Projects/Calculator/project.json",
      "project_json_hash": "abc123...",
      "total_workflows": 8,
      "last_parsed": "2025-01-09T11:30:00Z",
      "last_updated": "2025-01-08T15:20:00Z",
      "entry_points": ["Main.xaml", "Setup.xaml"],
      "dependencies": ["UiPath.System.Activities", "Calculator.Library"],
      "parsing_status": "success"
    }
  ]
}
```

### Command Interface

#### `rpax list-projects` Command
```bash
# Basic usage
rpax list-projects                                    # List all projects in default lake
rpax list-projects --path /custom/lake                # List projects in specific lake

# Filtering and search
rpax list-projects --search "calc"                    # Case-insensitive name search
rpax list-projects --type process                     # Filter by project type

# Output formatting  
rpax list-projects --format table                     # Human-readable table (default)
rpax list-projects --format json                      # JSON for tooling/MCP
rpax list-projects --format csv --out projects.csv    # CSV export
```

#### Integration with Existing Commands
```bash
# Enhanced parse command for multi-project scenarios
rpax parse --path project1/ --path project2/ --out shared-lake/

# Cross-project validation
rpax validate shared-lake/ --cross-project-missing     # Find missing cross-project refs
```

## Implementation Details

### 1. Lake Index Management

**Automatic Maintenance**:
- `projects.json` updated during `rpax parse` operations
- Incremental updates when individual projects are re-parsed
- Hash-based change detection to avoid unnecessary updates

**Index Generation**:
```python
class LakeIndexManager:
    def update_project_entry(self, project_path: Path, parse_results: ParseResults):
        """Update project entry in lake index after successful parse."""
        
    def discover_projects_in_lake(self, lake_path: Path) -> List[ProjectEntry]:
        """Scan lake directory and build index from discovered projects."""
        
    def search_projects(self, query: str, lake_path: Path) -> List[ProjectEntry]:
        """Search projects by name with fuzzy matching."""
```

### 2. Multi-Project Parsing Workflow

**Batch Processing**:
```bash
rpax parse --path project1/ --path project2/ --path project3/ --out unified-lake/
```

**Incremental Updates**:
- Only re-parse projects with changed `project.json` files
- Update `projects.json` index after each project
- Maintain parsing timestamps and status

### 3. MCP Integration Points

**Progressive Disclosure Pattern**:
1. **Discovery**: `GET /lakes/{lake}/projects` → project list
2. **Selection**: `GET /lakes/{lake}/projects/{slug}` → project details  
3. **Navigation**: `GET /lakes/{lake}/projects/{slug}/workflows` → workflow list
4. **Details**: `GET /lakes/{lake}/projects/{slug}/workflows/{workflow}` → full details

**Resource Identification**:
```
rpax://{lake_name}/projects                    # Project list resource
rpax://{lake_name}/projects/{slug}             # Specific project resource
rpax://{lake_name}/projects/{slug}/manifest    # Project parsing results
```

### 4. Cross-Project Analysis Features

**Missing Workflow Detection Across Projects**:
- Detect `InvokeWorkflowFile` calls that reference workflows in other lake projects
- Generate cross-project dependency graphs
- Validate cross-project references during CI/CD

**Shared Dependency Analysis**:
- Identify common dependencies across projects
- Detect version conflicts in shared libraries
- Generate dependency compatibility reports

## Command Specification

### `rpax list-projects`

**Purpose**: Discover and list projects within a lake with search and filtering capabilities.

**Parameters**:
- `--path <lake_path>`: Lake directory path (default: `.rpax-lake`)
- `--search <pattern>`: Filter projects by name (case-insensitive substring match)
- `--type <process|library>`: Filter by project type
- `--format <table|json|csv>`: Output format (default: `table`)
- `--out <file>`: Output file (stdout if not specified)
- `--verbose`: Include additional project details

**Output Formats**:

**Table Format** (default, human-readable):
```
PROJECT NAME         TYPE      WORKFLOWS  LAST UPDATED           STATUS
Calculator Process   process   8          2025-01-08 15:20:00    ✓
Invoice Library      library   12         2025-01-07 09:30:00    ✓ 
Data Processor       process   15         2025-01-09 11:45:00    ⚠ (3 missing)
```

**JSON Format** (tooling/MCP consumption):
```json
{
  "projects": [...],
  "total": 3,
  "lake_path": "/path/to/.rpax-lake",
  "last_scan": "2025-01-09T12:00:00Z"
}
```

**Error Handling**:
- Missing lake directory: Create empty `projects.json` and show "No projects found"
- Corrupted `projects.json`: Regenerate from directory scan
- Permission errors: Clear error message with resolution steps

## Consequences

### Positive Outcomes
- **Improved UX**: Users can easily discover projects in their lakes
- **MCP Ready**: Lake-level resources enable progressive disclosure patterns  
- **Better Organization**: Multi-project lakes become practical for teams
- **Cross-Project Analysis**: Foundation for dependency analysis across projects
- **Tooling Integration**: JSON output enables third-party tool integration
- **CI/CD Enhancement**: Batch processing supports automated workflows

### Trade-offs Accepted
- **Additional Complexity**: Lake index maintenance adds operational overhead
- **Storage Overhead**: `projects.json` duplicates some project metadata
- **Consistency Challenges**: Index must stay synchronized with actual projects
- **Breaking Change Risk**: Future schema changes may require migration

### Implementation Requirements
- Update `rpax parse` to maintain `projects.json` index
- Add `LakeIndexManager` class for index operations
- Implement fuzzy search for project name matching
- Add comprehensive error handling for corrupted/missing indices
- Update MCP server to expose lake-level resources
- Document multi-project workflows in user guides

## Architectural Alignment

### ADR Consistency
- **ADR-002** (4-Layer Architecture): Lake access extends Layer 1 (Parser) with multi-project capabilities
- **ADR-012** (MCP Layer): Lake-level resources align with MCP progressive disclosure patterns
- **ADR-032** (v0 Schema): Lake index complements project-level v0/ experimental schema
- **ADR-003** (Command Surface): Follows established CLI patterns for consistency

### Future Enhancements
- **Lake Templates**: Standard lake structures for common scenarios (team, CI/CD, governance)
- **Cross-Project Call Graphs**: Visualize dependencies across multiple projects
- **Lake Validation Rules**: Check cross-project consistency and completeness
- **Lake Migration Tools**: Utilities for reorganizing and upgrading lake structures

## Success Metrics

### v0.0.3 Targets
- `rpax list-projects` command functional with table and JSON output
- `projects.json` index generated and maintained during parse operations
- Search filtering works with substring matching
- Multi-project parsing workflow (`--path` multiple times) operational

### v0.1.0 Validation
- MCP clients successfully consume lake-level project resources
- Cross-project analysis features demonstrate value for multi-project scenarios
- Performance remains acceptable for lakes with 10+ projects
- User feedback validates improved multi-project experience

This architecture establishes rpax as a platform for managing collections of UiPath projects rather than just individual project analysis, enabling team collaboration and organizational-scale RPA governance.