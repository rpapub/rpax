# ADR-021: CLI Commands and Parameters Specification

**Status:** Accepted  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  

## Context

The `rpax` CLI provides a comprehensive interface for UiPath project analysis. As the tool evolves, maintaining consistency in command design, parameter conventions, and user experience becomes critical. A formal specification ensures:

1. **API Consistency** - Uniform patterns across all commands
2. **Documentation Generation** - Automated help and reference materials  
3. **Integration Testing** - Systematic validation of CLI surface area
4. **Future Extensibility** - Clear patterns for new commands

## Command Taxonomy

### Core Analysis Commands
- `parse` - Convert UiPath projects to structured artifacts (supports batch parsing)
- `list` - Enumerate project elements with filtering and sorting
- `validate` - Run validation rules on parsed artifacts
- `graph` - Generate visual representations of workflows
- `explain` - Show detailed information about specific workflows

### Multi-Project Management Commands
- `projects` - List and discover projects in multi-project lakes
- `clear` - Clear lake data with safety guardrails (CLI-only)

### Utility Commands  
- `schema` - Generate/validate JSON schemas for artifacts
- `activities` - Access workflow activity trees and control flow
- `help` - Show comprehensive help information

## Parameter Conventions

### Standard Parameters

All commands follow consistent parameter patterns:

**Path Parameters:**
- `--path, -p` - Input directory or artifacts location
  - Default behavior: Current directory or `.rpax-lake`
  - Help format: "Path description (default: value)"
  - **Parse Context**: Multiple `--path` options for batch parsing of filesystem locations
  - **Query Context**: Single path to lake directory for consumption

**Output Parameters:**
- `--out, -o` - Output file/directory for generated content
  - Default behavior: Stdout or current directory
  - Help format: "Output description (default: behavior)"

**Format Parameters:**
- `--format, -f` - Output format selection
  - Common values: `table`, `json`, `csv`, `markdown`, `mermaid`
  - Default behavior: `table` for interactive, `json` for programmatic
  - Help format: "Output format: option1, option2 (default: value)"

**Configuration Parameters:**
- `--config, -c` - Configuration file override  
  - Default behavior: Search for `.rpax.json` in current/parent directories
  - Help format: "Configuration file path (default: search for .rpax.json)"

**Multi-Project Parameters:**
- `--project` - Project slug for single-project lake queries
  - **Usage**: Query commands only (list, explain, activities, etc.)
  - **Values**: Single project slug from lake (e.g., "my-project-abcd1234")
  - Default behavior: Auto-detect single project or prompt for selection
  - Help format: "Project slug for single-project listing"
- `--projects` - Project slugs for cross-project lake queries  
  - **Usage**: Query commands only (list, explain, activities, etc.)
  - **Values**: Multiple project slugs, supports both formats:
    - Comma-separated: `--projects "proj1,proj2,proj3"`
    - Multiple options: `--projects proj1 --projects proj2`
  - **Mutual Exclusion**: Cannot be used with `--project`
  - Help format: "Multiple project slugs for cross-project listing (comma-separated or multiple uses)"
- **Cross-Project Discovery**: Use `rpax projects` for overview and slug discovery
- **Note**: Parse operations use filesystem paths, not project slugs

### Filtering and Search Parameters

**Search and Filter:**
- `--search, -s` - Text-based search within results
  - Help format: "Search term to filter results by name/path (optional)"
- `--filter` - Pattern-based filtering (glob patterns)
  - Help format: "Filter by glob pattern: '*.xaml', '*Test*', etc. (optional)"

**Sorting and Limiting:**
- `--sort` - Sort field selection
  - Common values: `name`, `size`, `modified`, `path`
  - Help format: "Sort by: field1, field2, field3 (default: name)"
- `--reverse, -r` - Reverse sort order
  - Help format: "Reverse sort order (default: False)"
- `--limit, -l` - Result count limitation
  - Help format: "Limit number of results shown (default: no limit)"

**Detail Control:**
- `--verbose, -v` - Extended information display
  - Help format: "Show detailed information and metadata (default: False)"

## Command Specifications

### `rpax parse [PATH]`

**Purpose:** Parse UiPath project(s) into structured JSON artifacts (supports batch parsing)

**Arguments:**
- `PATH` - Path to project directory or project.json (default: current directory)

**Options:**
- `--out, -o PATH` - Output directory for artifacts (default: .rpax-lake)
- `--config, -c PATH` - Configuration file path (default: search for .rpax.json)
- `--path PATH` - Additional project paths for batch parsing (can be used multiple times)

**Batch Parsing:**
```bash
# Single project (traditional)
rpax parse /path/to/project

# Multiple projects (batch)
rpax parse /path/to/project1 --path /path/to/project2 --path /path/to/project3
```

**Output:** Creates artifacts in multi-project lake structure
**Exit Codes:** 0 (success), 1 (error)

### `rpax list [ITEM_TYPE]`

**Purpose:** Enumerate project elements with filtering and sorting

**Arguments:**
- `ITEM_TYPE` - Type of items: workflows, roots, orphans, activities (default: workflows)

**Options:**
- `--path, -p PATH` - Project path or lake directory (default: .rpax-lake)
- `--format, -f FORMAT` - Output format: table, json, csv (default: table)
- `--project PROJECT` - Project slug for single-project listing (optional)
- `--projects PROJECTS` - Multiple project slugs for cross-project listing (comma-separated or multiple uses)
- `--search, -s TERM` - Search term to filter results (optional)
- `--sort FIELD` - Sort by: name, size, modified, path (default: name)
- `--reverse, -r` - Reverse sort order (default: False)
- `--filter PATTERN` - Filter by glob pattern (optional)
- `--limit, -l COUNT` - Limit number of results (default: no limit)
- `--verbose, -v` - Show detailed information (default: False)

**Multi-Project Examples:**
```bash
# Single project
rpax list workflows --project my-calc-abcd1234

# Multiple projects (comma-separated)
rpax list workflows --projects "proj1,proj2,proj3"

# Multiple projects (multiple options)
rpax list workflows --projects proj1 --projects proj2
```

**Output:** Formatted list of project elements
**Exit Codes:** 0 (success), 1 (error)

### `rpax projects [PATH]`

**Purpose:** List and discover projects in multi-project lakes

**Arguments:**
- `PATH` - Path to rpax lake directory (default: .rpax-lake)

**Options:**
- `--format, -f FORMAT` - Output format: table, json, csv (default: table)
- `--search, -s TERM` - Search projects by name or slug (optional)
- `--limit, -l COUNT` - Limit number of results (default: no limit)

**Example Usage:**
```bash
# List all projects in table format
rpax projects

# List projects with JSON output
rpax projects --format json

# Search for specific projects
rpax projects --search calculator

# Discover projects in specific lake
rpax projects /path/to/shared-lake
```

**Output:** Formatted list of projects with metadata (name, slug, type, workflow count, last updated)
**Exit Codes:** 0 (success), 1 (error)

### `rpax validate [PATH]`

**Purpose:** Run validation rules on parsed artifacts

**Arguments:**
- `PATH` - Path to artifacts or project directory (default: current directory)

**Options:**
- `--rule, -r RULE` - Specific rule: all, missing, cycles, config (default: all)
- `--format, -f FORMAT` - Output format: table, json, markdown (default: table)
- `--config, -c PATH` - Configuration file path (default: search for .rpax.json)

**Output:** Validation results with issues and recommendations
**Exit Codes:** 0 (no issues), 1 (validation failures)

### `rpax graph [GRAPH_TYPE]`

**Purpose:** Generate workflow call graphs and diagrams

**Arguments:**
- `GRAPH_TYPE` - Graph type: calls, paths, project (default: calls)

**Options:**
- `--path, -p PATH` - Artifacts or project directory (default: current)
- `--out, -o PATH` - Output file path (default: stdout)
- `--format, -f FORMAT` - Output format: mermaid, graphviz (default: mermaid)
- `--config, -c PATH` - Configuration file path (default: search for .rpax.json)

**Output:** Graph definition in specified format
**Exit Codes:** 0 (success), 1 (error)

### `rpax explain WORKFLOW`

**Purpose:** Show detailed information about specific workflow

**Arguments:**
- `WORKFLOW` - Workflow identifier (ID, filename, or partial path)

**Options:**
- `--path, -p PATH` - Artifacts or project directory (default: current)
- `--config, -c PATH` - Configuration file path (default: search for .rpax.json)

**Output:** Comprehensive workflow analysis
**Exit Codes:** 0 (success), 1 (workflow not found)

### `rpax schema ACTION`

**Purpose:** Generate JSON schemas or validate artifacts

**Arguments:**
- `ACTION` - Action to perform: generate, validate

**Options:**
- `--path, -p PATH` - Artifacts directory or output directory (default: current)
- `--out, -o PATH` - Output directory for schemas (default: current)

**Output:** Schema files or validation results  
**Exit Codes:** 0 (success), 1 (error)

### `rpax activities ACTION [WORKFLOW]`

**Purpose:** Access workflow activity trees, control flow, and resources

**Arguments:**
- `ACTION` - Action: tree, flow, resources, metrics
- `WORKFLOW` - Workflow name (required for specific actions)

**Options:**
- `--path, -p PATH` - Artifacts or lake directory (default: .rpax-lake)
- `--project PROJECT` - Project slug for multi-project lakes (optional)
- `--format, -f FORMAT` - Output format: json, table (default: json)
- `--verbose, -v` - Show detailed information (default: False)
- `--limit, -l COUNT` - Limit number of results (default: no limit)

**Output:** Activity information in specified format
**Exit Codes:** 0 (success), 1 (error)

### `rpax clear [SCOPE]`

**Purpose:** Clear lake data with safety guardrails (CLI-only)

**Arguments:**
- `SCOPE` - Clear scope: artifacts, project, lake (default: artifacts)

**Options:**
- `--path, -p PATH` - Lake directory path (default: .rpax-lake)
- `--project PROJECT` - Specific project slug (required for project scope)
- `--confirm` - Actually perform deletion (default: dry-run mode)
- `--force` - Skip interactive confirmation prompts

**Safety Features:**
- Dry-run by default with explicit `--confirm` required
- Multiple confirmation prompts for destructive operations
- Size warnings for large deletions
- CLI-only restriction (never exposed via API or MCP)

**Output:** Deletion summary and confirmation prompts
**Exit Codes:** 0 (success), 1 (error or cancellation)

### `rpax help`

**Purpose:** Show comprehensive help information

**Arguments:** None

**Options:** None

**Output:** Command reference table with descriptions
**Exit Codes:** 0 (always)

## Error Handling Standards

### Exit Code Convention
- `0` - Success, no issues
- `1` - General error, validation failure, or user cancellation

### Error Message Format
- **Prefix:** `[red]Error:[/red]` for errors, `[yellow]Warning:[/yellow]` for warnings
- **Context:** Include relevant file paths, line numbers when available
- **Guidance:** Provide actionable next steps or suggestions

### Validation Behavior
- **Graceful Degradation** - Continue processing when possible
- **Clear Reporting** - Distinguish between errors and warnings
- **Contextual Help** - Reference relevant commands or documentation

## Multi-Project Support

### Always-Multi-Project Architecture
- **Unified Structure** - All lakes use multi-project layout, even for single projects
- **Projects Index** - `projects.json` always present at lake root
- **Project Subdirectories** - `{projectSlug}/` always contains artifacts
- **Simplified Codebase** - Single code path eliminates single vs. multi-project branching

### Lake Structure
```
.rpax-lake/
├── projects.json              # Always present
├── project-name-abcd1234/     # Project slug directory
│   ├── manifest.json
│   ├── workflows.index.json
│   ├── invocations.jsonl
│   └── activities.tree/*.json
└── another-proj-efgh5678/     # Additional projects
    └── ...
```

### Project Resolution

**Fundamental Separation of Concerns:**
- **Ingestion (Parse)** - Works with filesystem paths to UiPath projects
- **Consumption (Query)** - Works with project slugs within lakes

**Parse Operations (Ingestion):**
- Use filesystem paths to project directories/project.json files
- Examples: `rpax parse /path/to/project`, `rpax parse . --path ../other-project`
- Parameters: `PATH` argument and `--path` options for batch parsing

**Query Operations (Consumption):**
- Use single project slug from lake (`--project my-project-abcd1234`)
- Examples: `rpax list workflows --project my-project-abcd1234`
- Auto-detection when only one project exists in lake
- Discovery via `rpax projects` to list all available project slugs

**Multi-Project Query Workflow:**
```bash
# 1. Discover available projects
rpax projects

# 2. Query single project
rpax list workflows --project my-calc-abcd1234

# 3. Query multiple projects (cross-project)
rpax list workflows --projects "proj1,proj2,proj3"
# OR
rpax list workflows --projects proj1 --projects proj2

# ❌ INVALID: Cannot mix --project and --projects
# rpax list --project proj1 --projects proj2  # Error: conflicting options
```

**Error Handling:**
- Path errors (parse): "Project file not found", "Invalid project.json"
- Slug errors (query): "Project 'my-proj-xyz' not found in lake"

## Output Format Standards

### Table Format (Interactive)
- **Rich Console** - Colors, styling, and formatting
- **Headers** - Clear column names with units
- **Pagination** - Automatic handling for large datasets
- **Summary Information** - Count totals, status indicators

### JSON Format (Programmatic)
- **Consistent Structure** - Always return arrays per ADR-019
- **Complete Data** - Include all available fields
- **Schema Validation** - Conform to published JSON schemas
- **Versioning** - Include `schemaVersion` field

### CSV Format (Data Export)
- **Standard Delimiter** - Comma-separated with proper quoting
- **Header Row** - Field names in first row
- **Consistent Fields** - Same columns across similar commands

## Future Extensions

### Planned Commands (v0.2+)
- `rpax diff` - Compare scans for PR impact analysis
- `rpax summarize` - Generate LLM-friendly project outlines
- `rpax mcp-export` - Export MCP resources (API layer)

### Parameter Evolution
- **Deprecation Policy** - 2-version deprecation cycle for breaking changes
- **Alias Support** - Maintain backward compatibility with parameter aliases
- **Configuration Integration** - Allow CLI parameters to override config file values

## Implementation Notes

### Framework: Typer
- **Rich Integration** - Colored output and progress indicators
- **Type Safety** - Full type annotations with runtime validation
- **Help Generation** - Automatic help text from type hints and docstrings

### Code Organization
- **Command Functions** - One function per command with clear signatures
- **Helper Functions** - Shared utilities with `_` prefix (private)
- **Error Handling** - Consistent exception handling and user feedback

### Testing Strategy
- **Integration Tests** - Full command execution with various parameters
- **Help Text Validation** - Ensure all parameters have adequate documentation
- **Exit Code Testing** - Verify correct error reporting

## Status

This ADR establishes the formal specification for rpax CLI commands and parameters. All current commands conform to these patterns, and future commands must follow these conventions for consistency and user experience.