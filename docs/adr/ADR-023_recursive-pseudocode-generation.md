# ADR-023: Recursive Pseudocode Generation at Parse Time

**Status:** Approved  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  

## Context

Current pseudocode generation (ISSUE-027, lake-data-model.md) produces individual workflow representations but does not expand `InvokeWorkflowFile` activities to show complete call trees. Users expect recursive expansion where invoked workflows are inline-expanded to provide full context without requiring separate lookups.

ISSUE-035 implemented CLI infrastructure with `--recursive` flag, but runtime expansion causes infinite loops and performance issues. The proper solution is to generate expanded pseudocode during parsing using call graph relationships from `invocations.jsonl`.

## Problem Analysis

### Current Architecture Issues
- **Runtime Complexity**: CLI-time expansion creates nested data structure traversal complexity
- **Performance Impact**: Multiple file system lookups during display rendering
- **Infinite Loops**: Complex nested children structures cause recursive expansion failures  
- **Data Duplication**: Current artifacts contain redundant nested representations

### Lake Data Model Integration
The existing lake architecture provides necessary components:
- **Call Graph Data**: `invocations.jsonl` contains workflow relationships
- **Content-Addressable Storage**: Efficient workflow lookup by content hash (ADR-017)
- **Pseudocode Artifacts**: First-class entities with structured representation
- **Identity System**: Composite IDs enable cross-workflow resolution

## Decision

Implement recursive pseudocode generation during the **parsing phase** using call graph relationships from `invocations.jsonl`. Generate both basic and expanded pseudocode variants as separate artifacts, pre-computed for instant CLI access.

## Architectural Integration

### Parse-Time Generation Strategy
1. **Standard Pseudocode**: Generate individual workflow pseudocode as currently implemented
2. **Call Graph Analysis**: Process `invocations.jsonl` to build workflow dependency tree
3. **Recursive Expansion**: Traverse dependency tree and inline referenced workflows
4. **Depth Limiting**: Implement configurable maximum expansion depth (default: 3 levels)
5. **Cycle Detection**: Use visited set to handle circular references gracefully

### Lake Artifact Extensions

#### Enhanced Pseudocode Index
```json
// pseudocode/index.json
{
  "projectSlug": "my-calculator-a1b2c3d4",
  "schemaVersion": "1.1.0",
  "generatedAt": "2025-09-06T10:30:00Z",
  "totalWorkflows": 15,
  "expansionConfig": {
    "maxDepth": 3,
    "enableRecursion": true,
    "cycleDetection": true
  },
  "workflows": [
    {
      "workflowId": "StandardCalculator",
      "basicFile": "StandardCalculator.xaml.json",
      "expandedFile": "StandardCalculator.xaml.expanded.json",
      "expansionDepth": 2,
      "invokeCount": 3,
      "expandedInvokeCount": 47
    }
  ]
}
```

#### Expanded Pseudocode Artifacts
```json  
// pseudocode/StandardCalculator.xaml.expanded.json
{
  "workflowId": "StandardCalculator",
  "formatVersion": "gist-style-expanded",
  "totalLines": 89,
  "totalActivities": 47,
  "expansionDepth": 2,
  "expansionConfig": {
    "maxDepth": 3,
    "cycleDetection": true,
    "visitedWorkflows": ["Initialization", "AdditionOf2Terms", "Teardown"]
  },
  "entries": [
    {
      "indent": 0,
      "displayName": "StandardCalculator Sequence",
      "tag": "Sequence", 
      "path": "Activity/Sequence",
      "formattedLine": "- [StandardCalculator Sequence] Sequence (Path: Activity/Sequence)",
      "nodeId": "Activity/Sequence_1",
      "depth": 1,
      "isVisual": true,
      "expansion": null
    },
    {
      "indent": 1,
      "displayName": "Process\\Initialization.xaml - Invoke Workflow File",
      "tag": "InvokeWorkflowFile",
      "path": "Activity/Sequence/InvokeWorkflowFile", 
      "formattedLine": "  - [Process\\Initialization.xaml - Invoke Workflow File] InvokeWorkflowFile (Path: Activity/Sequence/InvokeWorkflowFile)",
      "nodeId": "Activity/Sequence/InvokeWorkflowFile_2",
      "depth": 2,
      "isVisual": true,
      "expansion": {
        "targetWorkflow": "Process/Initialization",
        "expansionLevel": 1,
        "inlinedEntries": [
          // Nested pseudocode entries from Initialization workflow
        ]
      }
    }
  ]
}
```

### Configuration Integration

Extend `.rpax.json` configuration schema (ADR-004):

```json
{
  "pseudocode": {
    "generateExpanded": true,
    "maxExpansionDepth": 3,
    "cycleHandling": "detect_and_mark",
    "expansionFormats": ["gist-style-expanded"]
  }
}
```

**Configuration Options**:
- `generateExpanded`: Enable recursive expansion generation
- `maxExpansionDepth`: Maximum nesting levels (prevents excessive expansion)
- `cycleHandling`: `"detect_and_mark"` | `"detect_and_skip"` | `"allow"`
- `expansionFormats`: Output formats for expanded pseudocode

## Implementation Strategy

### Phase 1: Core Expansion Engine

#### Call Graph Processing
```python
class CallGraphProcessor:
    def __init__(self, invocations_file: Path, workflows_index: Dict):
        self.call_graph = self._build_call_graph(invocations_file)
        self.workflow_index = workflows_index
        
    def _build_call_graph(self, invocations_file: Path) -> Dict[str, List[str]]:
        """Build adjacency list from invocations.jsonl"""
        graph = defaultdict(list)
        with open(invocations_file) as f:
            for line in f:
                invocation = json.loads(line)
                if invocation['invocationType'] == 'literal':
                    graph[invocation['invokerWorkflow']].append(
                        invocation['targetWorkflow']
                    )
        return graph
        
    def get_dependencies(self, workflow_id: str) -> List[str]:
        """Get direct dependencies for workflow"""
        return self.call_graph.get(workflow_id, [])
```

#### Recursive Expansion Logic
```python
class RecursivePseudocodeGenerator:
    def __init__(self, config: ExpansionConfig, call_graph: CallGraphProcessor):
        self.config = config
        self.call_graph = call_graph
        
    def expand_workflow(self, workflow_id: str, visited: Set[str] = None, 
                       depth: int = 0) -> ExpandedPseudocode:
        """Generate expanded pseudocode with inline InvokeWorkflowFile content"""
        if visited is None:
            visited = set()
            
        if depth >= self.config.max_depth:
            return self._generate_basic(workflow_id)
            
        if workflow_id in visited:
            return self._generate_cycle_marker(workflow_id)
            
        visited.add(workflow_id)
        
        try:
            # Load basic pseudocode
            basic_artifact = self._load_basic_pseudocode(workflow_id)
            expanded_entries = []
            
            for entry in basic_artifact.entries:
                expanded_entries.append(entry)
                
                # Check for InvokeWorkflowFile expansion
                if (entry.tag == "InvokeWorkflowFile" and 
                    self._should_expand(entry)):
                    
                    target_workflow = self._extract_target_workflow(entry)
                    if target_workflow:
                        nested_pseudocode = self.expand_workflow(
                            target_workflow, visited.copy(), depth + 1
                        )
                        
                        # Inline the nested content with proper indentation
                        expanded_entries.extend(
                            self._inline_nested_content(
                                nested_pseudocode, entry.indent + 1
                            )
                        )
            
            return ExpandedPseudocode(
                workflow_id=workflow_id,
                entries=expanded_entries,
                expansion_depth=depth,
                visited_workflows=list(visited)
            )
            
        finally:
            visited.remove(workflow_id)
```

### Phase 2: CLI Integration

#### Enhanced CLI Commands
```bash
# Default behavior - show expanded if available
rpax pseudocode --project my-calc-1234 StandardCalculator.xaml

# Explicit basic pseudocode
rpax pseudocode --project my-calc-1234 StandardCalculator.xaml --basic

# Explicit expanded pseudocode  
rpax pseudocode --project my-calc-1234 StandardCalculator.xaml --expanded

# Control expansion depth
rpax pseudocode --project my-calc-1234 StandardCalculator.xaml --max-depth 2
```

#### Backward Compatibility
- Existing `--recursive` flag maps to `--expanded` for compatibility
- Default behavior shows expanded pseudocode when available
- Graceful fallback to basic pseudocode if expansion unavailable

### Phase 3: Advanced Features

#### Smart Expansion Strategies
- **Selective Expansion**: Only expand workflows below configured complexity threshold
- **Context-Aware Depth**: Adjust depth based on workflow call tree characteristics
- **Partial Expansion**: Show first N levels, provide "..." indicators for deeper content

#### Performance Optimizations
- **Caching**: Cache expanded pseudocode during parsing session
- **Incremental Generation**: Only regenerate when dependencies change
- **Parallel Processing**: Generate expanded pseudocode for multiple workflows concurrently

## Error Handling & Edge Cases

### Cycle Detection Strategy
```json
// Cycle detected representation
{
  "indent": 2,
  "displayName": "[RECURSIVE REFERENCE]",
  "tag": "InvokeWorkflowFile",
  "formattedLine": "    - [RECURSIVE: Initialization already expanded above]",
  "expansion": {
    "cycleDetected": true,
    "targetWorkflow": "Process/Initialization",
    "visitedPath": ["StandardCalculator", "Initialization"]
  }
}
```

### Missing Workflow Handling
- **Dynamic Invocations**: Mark as `[DYNAMIC INVOCATION: {expression}]`
- **Missing Files**: Mark as `[MISSING WORKFLOW: {target}]`  
- **Cross-Project References**: Mark as `[EXTERNAL: {project}#{workflow}]`

### Configuration Validation
- Validate `maxExpansionDepth` is reasonable (1-10 range)
- Warn if call tree depth exceeds configuration limits
- Provide clear error messages for invalid expansion configurations

## Migration & Deployment

### Backward Compatibility
- Existing basic pseudocode artifacts remain unchanged
- New expanded artifacts are additive (no breaking changes)
- CLI maintains compatibility with existing `--recursive` flag
- Schema version increment: `pseudocode.v1.schema.json` → `pseudocode.v2.schema.json`

### Migration Strategy
1. **Phase 1**: Generate expanded artifacts alongside basic ones
2. **Phase 2**: Update CLI to prefer expanded when available  
3. **Phase 3**: Deprecate runtime recursive expansion (remove complex CLI logic)
4. **Phase 4**: Optional cleanup of redundant basic artifacts

### Configuration Migration
```json
// Legacy configuration (still supported)
{
  "validation": {
    "pseudocode": {
      "enabled": true
    }
  }
}

// New configuration (enhanced)
{
  "pseudocode": {
    "generateBasic": true,
    "generateExpanded": true,
    "maxExpansionDepth": 3
  }
}
```

## Performance Characteristics

### Generation Time Impact
- **Baseline**: Basic pseudocode generation time
- **Expected**: 2-3x generation time for expanded pseudocode
- **Worst Case**: Linear with expansion depth × workflow count
- **Mitigation**: Parallel generation, caching, depth limits

### Storage Impact
- **Basic Artifacts**: Current storage usage (baseline)
- **Expanded Artifacts**: 3-5x storage for typical expansion depths
- **Optimization**: Content deduplication for shared subtrees
- **Trade-off**: Storage cost vs. runtime performance improvement

### Runtime Performance
- **CLI Response**: Instant (pre-computed artifacts)
- **Memory Usage**: Reduced (no runtime expansion complexity)
- **I/O Operations**: Single file read vs. multiple lookups
- **Scalability**: Linear with artifact size, not call graph complexity

## Quality Assurance

### Test Strategy
- **Unit Tests**: Expansion algorithm with various call graph structures
- **Integration Tests**: End-to-end parsing → CLI display validation
- **Edge Case Tests**: Cycles, missing workflows, deep nesting
- **Performance Tests**: Large projects with complex call trees
- **Regression Tests**: Ensure basic pseudocode remains unchanged

### Validation Criteria  
- Expanded pseudocode contains all activities from basic + inlined workflows
- Indentation hierarchy correctly represents call tree structure
- Cycle detection prevents infinite expansion
- Performance within acceptable bounds (< 5x basic generation time)
- CLI backward compatibility maintained

## Consequences

### Positive Outcomes
- **Instant CLI Response**: Pre-computed expansion eliminates runtime complexity
- **Complete Context**: Users see full call tree without manual navigation  
- **Reliable Expansion**: Parse-time generation avoids infinite loops
- **Scalable Architecture**: Leverages existing lake infrastructure
- **Enhanced UiPath Understanding**: Provides comprehensive workflow insight

### Trade-offs Accepted
- **Increased Storage**: 3-5x storage for expanded artifacts
- **Longer Parse Time**: 2-3x generation time during parsing
- **Configuration Complexity**: Additional options for expansion behavior
- **Schema Evolution**: New artifact versions require migration support

### Risk Mitigation
- **Storage Optimization**: Content-addressable deduplication for shared subtrees
- **Performance Monitoring**: Track generation time metrics and optimization opportunities  
- **Graceful Degradation**: Fallback to basic pseudocode if expansion fails
- **Configuration Validation**: Prevent excessive expansion through reasonable defaults

## Compliance & Integration

### Architectural Alignment
- **ADR-002**: Maintains 4-layer architecture (Parser layer enhancement)
- **ADR-004**: Leverages existing configuration system
- **ADR-017**: Uses established lake nomenclature and storage patterns
- **Lake Data Model**: Extends pseudocode entities with expansion support

### Standards Compliance
- **JSON Schema**: Versioned schemas for new expanded artifact format
- **Gist Format**: Maintains human-readable pseudocode representation
- **Content Addressing**: Leverages content hashes for workflow resolution
- **Identity System**: Uses composite IDs for cross-workflow references

This decision provides a robust foundation for recursive pseudocode generation while maintaining compatibility with existing rpax architecture and enabling future enhancements to workflow understanding capabilities.