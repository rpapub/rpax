# rpax-lake Data Model

**Version:** 0.0.1  
**Date:** 2025-09-06  

This document defines the entities, relationships, properties, and rules for the rpax-lake data architecture.

## Overview

The rpax-lake follows a **content-hash identified** pattern with structured artifacts from UiPath project parsing. The model supports multi-project lakes with immutable artifacts and content-based identity.

## Core Entities

### 1. Project

Represents a UiPath Studio project (Process or Library).

**Properties:**
- `name`: Human-readable project name
- `projectId`: Optional UUID from project.json (nullable due to template cloning)
- `projectType`: Enum `process` | `library`
- `projectSlug`: Stable identifier (`projectId[:8]` or `normalizedName-hash[:8]`)
- `main`: Entry point workflow path
- `dependencies`: Dict of dependency names to versions
- `schemaVersion`: UiPath project.json schema version
- `studioVersion`: UiPath Studio version used
- `targetFramework`: Runtime framework (Windows/.NET)
- `entryPoints`: List of configured entry points with arguments

**Identity:** Project slug generation follows ADR-014/ADR-017:
1. If `projectId` exists: use first 8 characters
2. Otherwise: `normalizedName-contentHash[:8]` from project.json

**Rules:**
- Project slugs must be unique within a lake
- Names are normalized: lowercase, alphanumeric + hyphens, max 20 chars
- Content hashing uses canonical JSON (sorted keys, no whitespace)

### 2. Run

Represents one execution of the rpax parser on a project.

**Properties:**
- `runId`: Unique identifier `{timestamp}-{uuid4}` (ISO8601 + UUID4)
- `projectSlug`: Reference to parsed project
- `startedAt`: ISO timestamp of run start
- `completedAt`: ISO timestamp of run completion
- `rpaxVersion`: Version of rpax that generated the run
- `parseResults`: Summary statistics (workflows parsed, errors, etc.)
- `configSnapshot`: Configuration used for parsing

**Identity:** Run IDs are globally unique across all projects and time

**Rules:**
- Runs are immutable once completed
- Each run generates a complete set of artifacts
- Runs can be compared for diff analysis

### 3. Artifact

Represents generated output files from parsing.

**Properties:**
- `artifactType`: Enum `manifest` | `workflow_index` | `invocations` | `call_graph` | `activity_tree` | `control_flow` | `resources` | `metrics` | `paths` | `pseudocode`
- `fileName`: Physical file name
- `filePath`: Full path within project run directory
- `contentHash`: SHA-256 hash of artifact content
- `schemaVersion`: Version of artifact schema
- `generatedAt`: ISO timestamp of generation
- `fileSize`: Size in bytes

**Standard Artifacts:**
- `manifest.json`: Project metadata and summary
- `workflows.index.json`: Complete workflow inventory
- `invocations.jsonl`: Workflow call relationships
- `call-graph.json`: Project-level call graph with dependency relationships
- `activities.tree/*.json`: Per-workflow activity trees
- `activities.cfg/*.jsonl`: Per-workflow control flow graphs
- `activities.refs/*.json`: Per-workflow resource references
- `metrics/*.json`: Per-workflow complexity metrics
- `paths/*.json`: Call paths from entry points
- `pseudocode/*.json`: Per-workflow human-readable pseudocode representations
- `pseudocode/index.json`: Project-level pseudocode metadata and inventory

**Rules:**
- All artifacts must validate against their JSON schemas
- Artifacts are immutable and content-addressable
- Schema versions follow semantic versioning

### 4. Record

Represents individual entries within JSONL artifacts.

**Properties:**
- `recordType`: Type of record (varies by artifact)
- `recordId`: Unique identifier within artifact
- `timestamp`: When record was created
- `data`: The actual record payload
- `sourceWorkflow`: Workflow that generated this record (if applicable)

**JSONL Record Types:**
- **Invocation Record**: Workflow call relationship
  - `invokerWorkflow`: Calling workflow ID
  - `targetWorkflow`: Called workflow ID (may be unresolved)
  - `invocationType`: `literal` | `dynamic` | `missing`
  - `nodeId`: Activity node that makes the call
  - `arguments`: Passed arguments (if resolvable)

**Rules:**
- Records in JSONL files are append-only
- Each record is self-contained with provenance
- Records maintain referential integrity to source workflows

### 5. Identity

Represents the unique identification system for workflows and content.

**Properties:**
- `compositeId`: Full identity `projectSlug#workflowId#contentHash`
- `projectSlug`: Project identifier
- `workflowId`: POSIX-normalized relative path (wfId)
- `contentHash`: SHA-256 hash of normalized XAML content
- `originalPath`: Original file path for provenance
- `disambiguationStrategy`: How conflicts are resolved

**Identity Rules (ADR-014):**
- **Composite ID Format**: `{projectSlug}#{workflowId}#{contentHash[:16]}`
- **Workflow ID**: Relative POSIX path from project root
- **Content Hash**: SHA-256 of normalized XAML (structure only, no ViewState)
- **Path Normalization**: Always use forward slashes, relative to project root
- **Case Handling**: Preserve original casing in metadata, normalize for identity

**Examples:**
```
f4aa3834#Main.xaml#a1b2c3d4e5f6789a
my-calc-1234#workflows/Calculator.xaml#deadbeefcafebabe
```

### 6. Reference

Represents external resources referenced by workflows.

**Properties:**
- `resourceType`: Enum `selector` | `asset` | `queue` | `file` | `url` | `application`
- `resourceName`: Logical name or identifier
- `resourceValue`: Actual value (path, URL, selector string)
- `nodeId`: Activity node that contains reference
- `propertyName`: Activity property containing reference
- `isDynamic`: True if contains variables/expressions
- `rawValue`: Original value before processing

**Resource Types:**
- **Selectors**: UI element identifiers for automation
- **Assets**: Orchestrator assets (credentials, text, databases)
- **Queues**: Orchestrator work queues
- **Files**: File system paths
- **URLs**: Web endpoints
- **Applications**: Target applications for automation

**Rules:**
- Dynamic references (containing variables) are marked but not resolved
- References maintain link to source activity node
- File paths are normalized to project-relative where possible

### 7. Metric

Represents complexity and quality metrics for workflows.

**Properties:**
- `workflowId`: Target workflow identifier
- `totalNodes`: Count of all activity nodes
- `maxDepth`: Maximum nesting depth of activities
- `loopCount`: Number of loop constructs
- `invokeCount`: Number of workflow invocations
- `logCount`: Number of logging activities
- `tryCatchCount`: Number of error handling blocks
- `selectorCount`: Number of UI selectors
- `activityTypes`: Map of activity type names to counts

**Derived Metrics:**
- **Complexity Score**: Weighted sum based on activity types and nesting
- **Maintainability Index**: Readability and complexity assessment
- **Test Coverage**: Percentage of paths covered by tests (future)

**Rules:**
- Metrics are computed deterministically from activity trees
- All counts are non-negative integers
- Metrics enable comparison across workflow versions

### 8. Error

Represents parsing errors and warnings encountered during analysis. **Redaction-safe for MCP server diagnostics.**

**Properties (MCP-Safe):**
- `category`: Enum `parser` | `env` | `config` | `api` | `mcp` | `access` | `other`
- `code`: Machine-readable code (e.g., `PARSER.XML.MALFORMED`)
- `severity`: Enum `fatal` | `major` | `minor` | `info`
- `artifact`: Target artifact (e.g., `manifest` | `workflows.index` | `activities.tree`)
- `runId`: The producing run identifier
- `redactedMessage`: Safe, concise vendor-controlled text
- `hint`: Optional remediation tip (vendor text only)
- `wfToken`: Redaction token for workflow (replaces raw path/name)
- `nodeToken`: Redaction token for activity node
- `extras`: Additional structured context (vendor-safe only)

**Properties (Lake-Only, Deprecated for IssueSaniBundle):**
- `errorType`: Legacy enum (replaced by `category`)
- `message`: Raw error description (contains user data)
- `sourceFile`: File path (contains user data)  
- `lineNumber`: Line number (if available)
- `contextInfo`: Free-text context (contains user data)

**Error Code Taxonomy:**
- **PARSER**: `XML.MALFORMED`, `XAML.UNSUPPORTED`, `INVOKE.MISSING`, `INVOKE.DYNAMIC`
- **ENV**: `PYTHON.MISSING_DEP`, `DOTNET.VERSION_MISMATCH`
- **CONFIG**: `POLICY.INVALID`, `SCHEMA.MISMATCH`
- **API**: `PORT.BIND_FAIL`, `STATUS.READ_ERROR`
- **MCP**: `RESOURCE.MAP_FAIL`, `URI.INVALID`

**Storage Pattern:**
- **Local Lake**: `errors.jsonl` (complete records with both MCP-safe and raw fields)
- **IssueSaniBundle**: Only MCP-safe fields (redacted form)

**Redaction Contract:**
- Never include: raw paths, selectors, arg/var names, host/user info
- Replace with tokens: `wfToken` (WF001), `nodeToken` (N01A) 
- Only `redactedMessage` appears; raw `message`/`sourceFile` omitted
- Deterministic ordering: sort by (`category`, `code`, `wfToken`, `nodeToken`)

**Migration Mapping (Old → New):**
```json
{
  "errorType": "parse_error" → "category": "parser",
  "severity": "error" → "severity": "major",  
  "message": "Missing workflow 'Invoice.xaml'" → "redactedMessage": "Missing workflow reference.",
  "sourceFile": "/path/to/Main.xaml" → "wfToken": "WF001",
  "contextInfo": "InvokeWorkflowFile_1" → "nodeToken": "N01A",
  "errorCode": null → "code": "PARSER.INVOKE.MISSING"
}
```

**Rules:**
- Errors don't prevent artifact generation (graceful degradation)
- All redacted messages use vendor-controlled text only
- Error codes enable programmatic error handling across MCP servers
- **Timestamp Policy:** Full ISO8601 timestamps allowed in lake storage for debugging; coarse-grained (date only) or omitted entirely in IssueSaniBundle for privacy

### 9. CallGraph

Represents the project-level call graph showing workflow dependency relationships and invocation patterns.

**Properties:**
- `projectSlug`: Target project identifier
- `schemaVersion`: Call graph schema version (default: "1.0.0")
- `generatedAt`: ISO timestamp of generation
- `totalWorkflows`: Count of workflows in project
- `totalEdges`: Count of direct call relationships
- `hasCircularDependencies`: Boolean indicating if cycles exist
- `entryPoints`: List of root workflows (from manifest)
- `orphanWorkflows`: List of workflows not reachable from roots
- `dependencyGraph`: Map of workflow dependencies
- `invocationGraph`: Map of specific invocation relationships
- `callDepths`: Map of workflow maximum call depths from roots
- `circularDependencies`: List of detected circular dependency chains

**Dependency Graph Structure:**
```json
{
  "dependencyGraph": {
    "StandardCalculator": {
      "dependencies": ["Process/Initialization", "Process/AdditionOf2Terms", "Process/Teardown"],
      "dependents": [],
      "maxDepth": 0,
      "isRoot": true
    },
    "Process/Initialization": {
      "dependencies": ["Framework/InitAllSettings", "Framework/InitAllApplications"],
      "dependents": ["StandardCalculator"],
      "maxDepth": 1,
      "isRoot": false
    }
  }
}
```

**Invocation Graph Structure:**
```json
{
  "invocationGraph": {
    "StandardCalculator -> Process/Initialization": {
      "sourceWorkflow": "StandardCalculator",
      "targetWorkflow": "Process/Initialization", 
      "invocationType": "literal",
      "sourceNodeId": "Activity/Sequence/InvokeWorkflowFile_2",
      "displayName": "Process\\Initialization.xaml - Invoke Workflow File",
      "arguments": {},
      "isResolved": true
    }
  }
}
```

**Rules:**
- Generated after invocations.jsonl analysis and workflow discovery
- Provides optimized data structure for recursive operations
- Enables cycle detection, path analysis, and impact assessment
- Supports both graph traversal and workflow resolution operations

### 10. Pseudocode

Represents human-readable pseudocode generated from workflow activities using gist-style format.

**Properties:**
- `workflowId`: Target workflow identifier
- `formatVersion`: Pseudocode format version (default: "gist-style")
- `totalLines`: Total number of pseudocode lines
- `totalActivities`: Total number of activities represented
- `entries`: List of pseudocode line entries with hierarchy
- `generatedAt`: ISO timestamp of generation  
- `parsingMethod`: Method used for generation (e.g., "enhanced-visual-detection")
- `expandedPseudocode`: List of recursively expanded pseudocode lines (when enabled)
- `expansionConfig`: Configuration used for recursive expansion (depth, cycle handling)

**Pseudocode Entry Properties:**
- `indent`: Indentation level (0-based)
- `displayName`: Human-readable activity name from UiPath
- `tag`: Activity type without namespace (Sequence, LogMessage, etc.)
- `path`: Hierarchical path (e.g., "Activity/Sequence/LogMessage")
- `formattedLine`: Complete gist-style line (e.g., "- [Log Message] LogMessage (Path: Activity/Sequence/LogMessage)")
- `nodeId`: Stable node identifier for reference
- `depth`: Activity depth in workflow hierarchy
- `isVisual`: True if activity appears in visual designer
- `children`: Nested child entries maintaining hierarchy

**Gist Format Specification:**
```
- [DisplayName] Tag (Path: Activity/Sequence/...)
  - [Child DisplayName] ChildTag (Path: Activity/Sequence/Child...)
    - [Grandchild DisplayName] GrandchildTag (Path: Activity/Sequence/Child/Grandchild...)
```

**Expanded Pseudocode (Recursive Generation):**
- When `generateExpanded` is enabled in configuration, pseudocode artifacts include recursively expanded content
- `expandedPseudocode` contains lines that expand InvokeWorkflowFile activities with target workflow content
- Expansion respects `maxExpansionDepth` setting to prevent infinite recursion
- Cycle handling strategies: "detect_and_mark", "detect_and_stop", "ignore"
- Expansion uses call graph data for efficient recursive traversal

**Rules:**
- Always generated alongside other artifacts (first-class status)
- Maintains visual hierarchy through indentation with hyphens
- Uses DisplayName from UiPath activities for human readability
- Supports both structured JSON and formatted text representations
- Enables LLM-friendly workflow understanding and documentation
- Recursive expansion provides complete call tree context for analysis

### 11. Activity Instances

Represents first-class Activity entities extracted from workflow XAML for MCP/LLM consumption (ADR-009). Activities are individual automation steps with complete business logic configuration.

**Properties:**
- `activityId`: Composite ID format `{projectId}#{workflowId}#{nodeId}#{contentHash}`
- `workflowId`: Parent workflow identifier (normalized path without .xaml)
- `activityType`: UiPath activity type (e.g., "InvokeWorkflowFile", "Assign", "Click")
- `arguments`: Dictionary of input/output arguments with values
- `configuration`: Activity-specific configuration properties  
- `properties`: XAML properties (DisplayName, ContinueOnError, Timeout, etc.)
- `expressions`: List of VB.NET/C# expressions used in activity
- `variablesReferenced`: Variables accessed by this activity
- `selectors`: UI selectors for automation activities (Click, Type, etc.)

**File Locations:**
- `activities.instances/{workflow-path}.json`: Activity instances per workflow
- `activities.tree/{workflow-path}.json`: Hierarchical activity trees
- `activities.refs/{workflow-path}.json`: External references per workflow

**Content Hash Generation:**
Activities use SHA-256 of complete XML element content to detect changes. Same business logic across workflows/projects generates identical content hashes for deduplication.

**Business Logic Extraction:**
- **Arguments**: Input/output parameters with default values and types
- **Configuration**: Activity-specific settings (timeouts, retry policies, conditions)
- **Expressions**: Complete VB.NET/C# expressions for data manipulation
- **UI Selectors**: Full selectors for UI automation (not just element IDs)
- **Variable References**: All variables read/written by activity

### 12. Object Repository

Represents UiPath Object Repository libraries containing GUI selectors and UI automation targets for MCP integration. Object Repositories are reusable libraries of UI elements.

**Properties:**
- `libraryId`: Unique identifier for the Object Repository library
- `libraryType`: Always "Library" for Object Repository projects
- `apps`: List of applications defined in the repository
- `created`: ISO timestamp when library was created
- `updated`: ISO timestamp when library was last modified

**Application Structure:**
- `appId`: Unique identifier for application within repository
- `name`: Human-readable application name (e.g., "Calculator", "Chrome")
- `description`: Application description and context
- `targets`: List of UI targets/elements for automation

**UI Target Structure:**
- `targetId`: Unique identifier for UI element
- `friendlyName`: Display name for UI element (e.g., "'Add' button", "'Username' textbox")
- `elementType`: Type of UI element (Button, Text, TextBox, etc.)
- `selectors`: Array of selectors (full, fuzzy, scope) with automation properties
- `designProperties`: Visual properties (coordinates, size, screenshot references)
- `contentHash`: SHA-256 of target definition for change detection

**Selector Structure:**
- `type`: Selector type ("full", "fuzzy", "scope")  
- `value`: Raw selector XML/string
- `properties`: Parsed automation properties (automationid, cls, name, role, app, appid)

**File Locations:**
- `object-repository/repository-summary.json`: Library overview and statistics
- `object-repository/apps/{app-name}.json`: Detailed app definitions with all targets
- `object-repository/mcp-resources.json`: MCP resource definitions for external integration

**MCP Resource Generation:**
- Library-level resource: `rpax://{projectId}/object-repository`
- App-level resources: `rpax://{projectId}/object-repository/apps/{appId}`
- Resources include complete selector definitions and automation properties
- Suitable for LLM consumption and UI automation guidance

### 13. API Service Discovery

Represents API server metadata for external tool integration when Access API is enabled.

**Properties:**
- `url`: Full API server URL (e.g., "http://127.0.0.1:8623")
- `pid`: Process ID of running API server
- `startedAt`: ISO timestamp when API server started
- `rpaxVersion`: Version of rpax running the API server
- `lakes`: List of mounted lake directory paths  
- `projectCount`: Total number of projects across all mounted lakes
- `configPath`: Path to configuration file used (if any)

**File Location:**
- Windows: `%LOCALAPPDATA%\rpax\api-info.json`
- Unix/Linux: `~/.local/share/rpax/api-info.json`

**Rules:**
- Only created when API server is running
- Automatically cleaned up on graceful server shutdown
- Used by external tools for service discovery and integration
- Provides real-time metadata about running rpax API instance

## Entity Relationships

### Project → Run (1:N)
- Projects can have multiple runs over time
- Each run belongs to exactly one project
- Runs are ordered chronologically

### Run → Artifact (1:N)
- Each run generates a fixed set of artifacts
- Artifacts belong to exactly one run
- Standard artifact types are always generated

### Artifact → Record (1:N) 
- JSONL artifacts contain multiple records
- JSON artifacts contain single structured objects
- Records are ordered within artifacts

### Project → Workflow → Activity (1:N:N)
- Projects contain multiple workflows
- Workflows contain hierarchical activity trees
- Activities can reference external resources

### Workflow → Identity (1:1)
- Each workflow has exactly one composite identity
- Identity uniquely identifies workflow content
- Identity enables change detection across runs

### Workflow → Metrics (1:1)
- Each workflow has associated complexity metrics
- Metrics are computed from activity analysis
- Metrics enable quality assessment

### Activity → Reference (1:N)
- Activities can reference multiple external resources
- References track dependencies outside the project
- References enable impact analysis

### Project → CallGraph (1:1)
- Each project has exactly one call graph artifact
- Call graph represents all workflow dependencies within project
- Generated from invocations analysis for optimization
- Enables efficient recursive operations and cycle detection

### Activity → Instance (1:1)
- Each XML activity node generates exactly one Activity instance
- Activity instances have content-based identity for change detection
- Same business logic across workflows generates identical content hashes
- Enables activity-level deduplication and analysis

### Library → ObjectRepository (1:1)
- UiPath Library projects may contain exactly one Object Repository
- Object Repository contains hierarchical app/target structure
- UI targets include complete selector definitions and automation properties
- Enables MCP resource generation for external tool integration

### ObjectRepository → App (1:N)
- Object Repository contains multiple application definitions
- Each app represents a distinct software application (Calculator, Chrome, etc.)
- Apps group related UI targets for organizational purposes

### App → UITarget (1:N) 
- Applications contain multiple UI automation targets
- UI targets represent specific elements (buttons, textboxes, etc.)
- Each target includes multiple selector types (full, fuzzy, scope)
- Targets enable precise UI automation across different contexts

## Lake Layout Structure

```
lake/
├── projects.json                    # Multi-project index (derived, regenerated on scan)
├── {projectSlug}/                   # Project-specific artifacts
│   ├── manifest.json               # Current project metadata
│   ├── workflows.index.json        # Current workflow inventory
│   ├── invocations.jsonl           # Current workflow calls
│   ├── errors.jsonl                # Parse errors and warnings
│   ├── call-graph.json             # Project-level call graph and dependencies
│   ├── activities.tree/*.json      # Activity trees per workflow
│   ├── activities.cfg/*.jsonl      # Control flows per workflow  
│   ├── activities.refs/*.json      # Resource references per workflow
│   ├── activities.instances/*.json # Activity instances per workflow (ADR-009)
│   ├── metrics/*.json              # Metrics per workflow
│   ├── paths/*.json                # Call paths from entry points
│   ├── pseudocode/                 # Human-readable pseudocode artifacts
│   │   ├── index.json              # Project-level pseudocode metadata
│   │   └── *.json                  # Per-workflow pseudocode files
│   ├── expanded-pseudocode/        # Recursive pseudocode expansion
│   │   ├── index.json              # Expansion metadata and configuration
│   │   └── *.expanded.json         # Per-workflow expanded pseudocode
│   └── object-repository/          # Object Repository artifacts (Library projects only)
│       ├── repository-summary.json # Library overview and statistics
│       ├── apps/*.json             # Detailed app definitions with UI targets
│       └── mcp-resources.json      # MCP resource definitions
└── .schemas/                       # JSON schemas for validation
    ├── manifest.v1.schema.json
    ├── workflow-index.v1.schema.json
    ├── invocation.v1.schema.json
    ├── call-graph.v1.schema.json   # Call graph artifact schema
    ├── pseudocode.v1.schema.json   # Pseudocode artifact schema
    ├── activity-instances.v1.schema.json # Activity instances schema (ADR-009)
    ├── object-repository.v1.schema.json # Object Repository schema
    └── error.v0.schema.json        # MCP-safe error record schema
```

## Business Rules

### Identity and Uniqueness
1. **Composite IDs** must be globally unique within a lake
2. **Project slugs** must be unique within a lake
3. **Content hashes** are deterministic and reproducible
4. **Path normalization** always uses POSIX forward slashes

### Immutability and Versioning
1. **Artifacts** are immutable once generated
2. **Schema versions** follow semantic versioning
3. **Breaking changes** require new schema versions
4. **Backward compatibility** is maintained within major versions

### Error Handling and Graceful Degradation  
1. **Parse failures** don't prevent artifact generation
2. **Missing workflows** are recorded as `invoke-missing` invocations; **Expressions/variables** are recorded as `invoke-dynamic` invocations; **Coded workflows (.cs)** are recorded as `invoke-coded` invocations
3. **Invalid XAML** generates error records but continues processing
4. **Validation rules** are configurable per project

### Multi-Project Support
1. **Projects index** maintains canonical project list
2. **Subdirectories** isolate project artifacts
3. **Cross-project references** are supported but marked
4. **Lake operations** work across all projects

### Content Addressability
1. **Content changes** generate new identities
2. **Identical content** maps to same identity across projects
3. **Deduplication** is possible at content level
4. **Change detection** is content-based, not timestamp-based

## IssueSaniBundle Export Format

The **IssueSaniBundle** is a redacted export of lake data suitable for sharing in public issue trackers without exposing user/corporate information (ADR-026).

### Redaction Strategy

**Vendor-Safe (Retained):**
- Activity types and UiPath package information
- Schema/version metadata (UiPath, rpax)  
- Error categories, codes, and redacted messages
- Metrics and statistical counts
- Workflow tokens (WF001, WF002) and node tokens (N01A, N02B)

**User-Originated (Dropped):**
- Raw workflow paths and names
- Display names, argument names, variable names
- File paths, selectors, assets, queue names
- Host/user information, comments

**Pseudonymized (Future):**
- Deterministic tokens for workflow/node references
- Cross-reference consistency maintained

### Token Generation

**Specification:** Deterministic per-bundle via `HMAC-SHA256(salt, value)`. Salt is bundle-specific, stored in `metadata.json`, never included in public bundle. Ensures consistent tokenization within bundle while preventing cross-bundle correlation.

**Implementation:**
- `wfToken`: `WF` + first 3 chars of HMAC-SHA256(salt, workflow_path)
- `nodeToken`: `N` + first 2 chars of HMAC-SHA256(salt, node_id) + activity_type[0]
- Salt format: 32-byte random value, base64-encoded, unique per bundle
- Cross-reference consistency maintained within single bundle

### Error Records in IssueSaniBundle

Error records are filtered to include only MCP-safe fields:

```json
{
  "category": "parser",
  "code": "PARSER.XML.MALFORMED",
  "severity": "major", 
  "artifact": "activities.tree",
  "runId": "2025-09-06T07:40:12Z-7f0c2d26",
  "wfToken": "WF003",
  "nodeToken": "N01A", 
  "redactedMessage": "Malformed XAML near Sequence[0].",
  "hint": "Open the workflow in Studio and re-save to normalize."
}
```

**Omitted from IssueSaniBundle:**
- `message` (raw error text)
- `sourceFile` (user file paths)
- `contextInfo` (free-text context)
- `lineNumber` (fine-grained location info)

### Bundle Structure

```
issue-sani-bundle.zip
├── metadata.json          # Bundle version, rpax version, timestamps
├── projects-redacted.json # Project list with tokens only
├── errors.jsonl           # MCP-safe error records only
├── metrics-summary.json   # Aggregated metrics (no user paths)
├── call-graph-redacted.json  # Tokenized workflow IDs, no raw paths
├── pseudocode-index.json     # Tokenized references only
└── policy.json           # Redaction policy used
```

**Call Graph & Pseudocode Redaction:** Call graphs and pseudocode artifacts use wfTokens exclusively; raw workflow paths, display names, and arguments are never included. Only tokenized workflow references and activity type information is retained for structural analysis.

## Future Extensions

### Planned Entities (v0.2+)
- **ChangeSet**: Diff analysis between runs  
- **TestCase**: Test workflow identification
- **Deployment**: Release and environment tracking
- **Usage**: Runtime statistics and performance data

### Advanced Features (v0.3+)
- **Cross-Project Dependencies**: Library resolution across projects
- **Temporal Queries**: Point-in-time lake state reconstruction  
- **Content Deduplication**: CAS-based storage optimization
- **Federation**: Multi-lake queries and synchronization