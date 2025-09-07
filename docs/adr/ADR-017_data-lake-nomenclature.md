# ADR-017: Data Lake Nomenclature and Design Influence

**Status:** Proposed  
**Date:** 2025-09-05  

## Context

The parser and subsequent layers (Validation, Access API, MCP) will emit and consume structured artifacts (`manifest.json`, `workflows.index.json`, `invocations.jsonl`, etc.).  
When multiple projects and runs are collected together, these outputs must be stored in a shared repository.  
The term **“lake”** is used to describe this repository, borrowing from the data-lake pattern: append-only, multi-source, and neutral storage.  
To avoid ambiguity, a precise vocabulary is needed.

## Nomenclature

- **Lake** — Neutral, append-friendly filesystem area containing artifacts from many projects and runs; no in-place mutation.  
- **Project Root** — Directory with `project.json`; unit of parsing.  
- **Project Slug** — Stable identifier per project: `{slugName}-{hashPrefix}` where:
  - `slugName` = project name normalized (lowercase, alphanumeric + hyphens, max 32 chars)
  - `hashPrefix` = first 8 chars of SHA-256 hash of canonical `project.json` content
  - Example: `my-calculator-a1b2c3d4`
- **Run ID** — Unique identifier for one parser execution: `{timestamp}-{uuid4}` format:
  - `timestamp` = ISO8601 compact format (YYYYMMDD-HHMMSS)
  - `uuid4` = UUID4 without hyphens (32 hex chars)
  - Example: `20250905-143022-a1b2c3d4e5f6789012345678901234567890abcd`
- **Artifact** — A produced file (JSON/JSONL), e.g. `manifest.json`, `workflows.index.json`, `invocations.jsonl`.  
- **Record** — One logical entry in an artifact (especially for JSONL).  
- **Workflow ID (wfId)** — Canonical, repo-relative POSIX path to a `.xaml`; human-readable.  
- **Content Hash** — SHA-256 hash of normalized workflow content:
  - Includes XAML structure, activities, arguments, variables
  - Excludes metadata like ViewState, timestamps, file paths
  - Uses Unicode NFC normalization and consistent whitespace
  - Rename/move tolerant (same content = same hash)
- **Crosswalk (xwalk)** — JSON mapping file tracking wfId/hash changes across runs:
  - Format: `{"previous": {"wfId": "old/path.xaml", "hash": "abc123"}, "current": {"wfId": "new/path.xaml", "hash": "def456"}}`
  - Generated when workflows are renamed/moved between runs
- **Catalog** — Index artifact summarizing a topic (e.g. workflows, invocations).  
- **Refs** — Extracted external references (selectors, assets, queues, files, URLs).  
- **CFG** — Intra-workflow control-flow graph (edges within one workflow).  
- **Roots** — Entry points from `project.json` (`.main`, `.entryPoints[*]`) and test roots.  
- **Orphans** — Workflows not reachable from any root.  
- **Schema Version** — Version tag for artifact structure (semantic versioning: "1.2.3").  
- **Identity Version** — Version tag for identity/disambiguation rules (semantic versioning: "1.2.3").  
- **Lake Layout** — Conventional folder structure with content-addressable storage:  
    ```
    lake/{projectSlug}/runs/{runId}/[manifest.json | workflows.index.json | invocations.jsonl | activities.*/* | paths/*]
    lake/{projectSlug}/latest.json                    # JSON pointer to current runId
    lake/.cas/{contentHash[:2]}/{contentHash[2:]}     # Content-addressable storage
    lake/.index/projects.json                         # Project directory
    lake/.schemas/{schemaVersion}/                     # Schema definitions
    ```
- **Immutability** — Runs are write-once; any new parsing produces a new runId.
- **Content-Addressable Storage (CAS)** — Shared storage pool for deduplication:
  - Workflows with identical content stored once as hardlinks
  - Path: `.cas/{hash[:2]}/{hash[2:]}.xaml`
  - Artifacts reference by content hash, not file path

## Design Influence

- **Parser Layer**  
- Emits artifacts into `lake/{projectSlug}/runs/{runId}`.  
- Stores both `wfId` and `contentHash` for workflows.  
- Normalizes paths (POSIX, Unicode NFC).  
- Records parse errors as data, never aborts entire runs.  

- **Validation Layer**  
- Reads artifacts from runs; does not modify lake.  
- Uses `contentHash` for cross-run comparisons.  
- Surfaces `wfId` for readability.  

- **Access API**  
- Serves projects and runs from the lake read-only.  
- Provides discovery (`/projects`, `/projects/{slug}/runs`).  
- Uses ETags derived from content hashes.  

- **MCP/Integration**  
- Builds URIs scoped by `projectSlug` and `wfId`.  
- Treats the lake as canonical source.  
- Leverages hashes for deduplication and caching.  

- **Operations**  
- Append-only model supports history and reproducibility.  
- Retention policies may prune old runs, but immutability of runs is preserved.  
- `latest` pointer simplifies consumption defaults.  

## Implementation Details

### Slug Generation Algorithm
```python
def generate_project_slug(project_name: str, project_json_content: str) -> str:
    # Normalize project name
    slug_name = re.sub(r'[^a-zA-Z0-9\-]', '-', project_name.lower())
    slug_name = re.sub(r'-+', '-', slug_name).strip('-')[:32]
    
    # Generate hash prefix
    canonical_content = json.dumps(json.loads(project_json_content), sort_keys=True, separators=(',', ':'))
    hash_prefix = hashlib.sha256(canonical_content.encode('utf-8')).hexdigest()[:8]
    
    return f"{slug_name}-{hash_prefix}"
```

### Content Hash Algorithm
```python
def generate_content_hash(xaml_path: Path) -> str:
    # Parse and normalize XAML
    tree = ET.parse(xaml_path)
    
    # Remove volatile elements
    for elem in tree.iter():
        # Remove ViewState and other metadata
        elem.attrib.pop('sap2010:WorkflowViewState.IdRef', None)
        elem.attrib.pop('xmlns:sap2010', None)
    
    # Canonicalize and hash
    canonical_xml = ET.tostring(tree.getroot(), encoding='unicode', method='c14n')
    return hashlib.sha256(canonical_xml.encode('utf-8')).hexdigest()
```

### Storage Optimization
- **Deduplication**: Identical workflow content stored once in CAS, hardlinked to runs
- **Retention**: Old runs pruned based on policy (e.g., keep last 10 runs per project)  
- **Compression**: Large artifacts compressed with gzip (transparent to consumers)
- **Indexing**: SQLite index for fast project/workflow lookups

### Latest Pointer Strategy
```json
// lake/{projectSlug}/latest.json
{
  "runId": "20250905-143022-a1b2c3d4...",
  "timestamp": "2025-09-05T14:30:22Z",
  "schemaVersion": "1.0.0"
}
```

### Schema Migration Strategy
1. **Backward Compatible Changes**: New optional fields, maintain old field names
2. **Breaking Changes**: New schema version, migration utilities provided
3. **Graceful Degradation**: Older consumers ignore unknown fields
4. **Version Detection**: All artifacts include `schemaVersion` field

## Operational Examples

### Common Lake Operations
```bash
# Query all projects
rpax lake list-projects --lake-path ./lake

# Get latest run for project
rpax lake get-run my-calculator-a1b2c3d4 --latest

# Cleanup old runs (retain last 10)
rpax lake cleanup --retain 10 --dry-run

# Migrate schema version
rpax lake migrate --from 1.0.0 --to 1.1.0
```

### Storage Usage Estimates
- **Without CAS**: 100MB project × 50 runs = 5GB
- **With CAS**: 100MB unique content + 50MB run metadata = 150MB (97% savings)
- **Index Overhead**: ~1-5% of total storage

## Consequences

### Benefits
- Consistent vocabulary and layout across all layers  
- Easier onboarding and documentation for RPA developers  
- Append-only model ensures reproducibility and auditability  
- Content-addressable storage provides significant space savings  
- Well-defined algorithms enable consistent implementations  

### Costs
- Additional complexity in slug generation and normalization  
- Storage overhead for CAS index structures  
- Migration utilities required for schema evolution  
- Cross-platform compatibility concerns for hardlinks  

### Risks
- Hash collision handling not specified (low probability but high impact)
- CAS corruption could affect multiple runs
- Index rebuild costs for large lakes

## Related ADRs

- ADR-002: Layered Architecture  
- ADR-014: Identity & Disambiguation (Multi-Project Lake)  
- ADR-009: Parser Artifacts (defines artifact contents)
