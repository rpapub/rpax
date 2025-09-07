# ISSUE-027: Extend Lake Data Model to Include Pseudocode Type

**Status:** Planning  
**Priority:** High  
**Date:** 2025-09-06  

## Problem Statement

The enhanced XAML parser now provides excellent activity detection and structure analysis. However, for documentation, onboarding, and AI/LLM consumption, we need a **human-readable pseudocode representation** of workflows that abstracts away UiPath-specific implementation details while preserving logical flow.

## Proposed Solution

Add a new artifact type `pseudocode` to the lake data model with flexible line-based structure that can evolve over time.

## Detailed Design

### 1. New Artifact Type: `activities.pseudocode/`

Add to the standard artifact inventory (ADR-009):
- `activities.pseudocode/<wfId>.jsonl` - Line-by-line pseudocode representation

**Structure:**
```jsonl
{"lineNumber": 1, "indent": 0, "type": "start", "content": "BEGIN Main Workflow", "nodeId": "/Sequence[0]", "metadata": {}}
{"lineNumber": 2, "indent": 1, "type": "assign", "content": "SET variable myVar = \"Hello World\"", "nodeId": "/Sequence[0]/Assign[0]", "metadata": {"variableName": "myVar", "value": "\"Hello World\"", "isExpression": false}}
{"lineNumber": 3, "indent": 1, "type": "log", "content": "LOG message \"Processing started\"", "nodeId": "/Sequence[0]/LogMessage[0]", "metadata": {"message": "\"Processing started\"", "level": "Info"}}
{"lineNumber": 4, "indent": 1, "type": "condition", "content": "IF user input is valid THEN", "nodeId": "/Sequence[0]/If[0]", "metadata": {"condition": "[userInput IsNot Nothing]"}}
{"lineNumber": 5, "indent": 2, "type": "invoke", "content": "CALL ProcessUserInput.xaml", "nodeId": "/Sequence[0]/If[0]/Then/InvokeWorkflowFile[0]", "metadata": {"target": "ProcessUserInput.xaml", "invocationType": "invoke"}}
{"lineNumber": 6, "indent": 1, "type": "condition_end", "content": "END IF", "nodeId": "/Sequence[0]/If[0]", "metadata": {}}
{"lineNumber": 7, "indent": 0, "type": "end", "content": "END Main Workflow", "nodeId": "/Sequence[0]", "metadata": {}}
```

### 2. Pseudocode Line Structure

Each pseudocode line is a flexible JSON object supporting extensibility:

```typescript
interface PseudocodeLine {
  lineNumber: number;           // Sequential line number (1-based)
  indent: number;              // Indentation level (0-based)
  type: PseudocodeLineType;    // Semantic type of line
  content: string;             // Human-readable pseudocode text
  nodeId: string;              // Link to source activity node
  metadata: Record<string, any>; // Extensible metadata container
}
```

**Core Line Types (v1.0):**
- `start` / `end` - Workflow/sequence boundaries
- `assign` - Variable assignments  
- `log` - Logging statements
- `condition` / `condition_end` - If/then/else blocks
- `loop` / `loop_end` - Iteration constructs
- `invoke` - Workflow invocations
- `try` / `catch` / `finally` / `try_end` - Error handling
- `comment` - Comments and annotations
- `ui_action` - UI automation activities
- `data_action` - Data manipulation activities
- `flow_control` - Switch/case, break, continue

**Future Extensions (v1.1+):**
- `parallel_start` / `parallel_end` - Parallel execution blocks
- `state_transition` - State machine transitions
- `event_handler` - Event-driven activities
- `custom_activity` - Extensions and custom activities
- `assertion` - Test/validation activities
- `breakpoint` - Debugging markers

### 3. Pseudocode Generation Rules

The enhanced XAML parser will generate pseudocode using these rules:

**Content Generation:**
- Use imperative, present-tense verbs (SET, CALL, LOG, CHECK)
- Abstract away UiPath-specific syntax to generic actions
- Preserve logical flow and nesting structure
- Use consistent terminology across all workflows
- Include human-meaningful descriptions from DisplayNames

**Indentation Rules:**
- Each nested container increases indent by 1
- Container end markers match container start indent
- Parallel branches use same indent level
- Maximum indent depth: 10 levels (prevents excessive nesting)

**Abstraction Mapping:**
```
Sequence -> No pseudocode line (structure only)
Assign -> "SET variable = value"
LogMessage -> "LOG message \"text\""
InvokeWorkflowFile -> "CALL workflow.xaml"
If -> "IF condition THEN" ... "END IF"
While -> "WHILE condition DO" ... "END WHILE"
ForEach -> "FOR EACH item IN collection DO" ... "END FOR"
TryCatch -> "TRY" ... "CATCH exception" ... "END TRY"
Click -> "CLICK element \"selector\""
TypeText -> "TYPE text \"value\" into element"
GetText -> "GET text from element into variable"
```

### 4. Lake Data Model Updates

**New Entity: PseudocodeLine**

```json
{
  "entityType": "PseudocodeLine",
  "properties": {
    "lineNumber": {"type": "integer", "minimum": 1},
    "indent": {"type": "integer", "minimum": 0, "maximum": 10},
    "type": {"type": "string", "enum": ["start", "end", "assign", "log", "condition", "condition_end", "loop", "loop_end", "invoke", "try", "catch", "finally", "try_end", "comment", "ui_action", "data_action", "flow_control"]},
    "content": {"type": "string", "minLength": 1, "maxLength": 500},
    "nodeId": {"type": "string", "pattern": "^/.*"},
    "metadata": {"type": "object", "additionalProperties": true}
  }
}
```

**Updated Artifact Entity:**
- Add `activities_pseudocode` to `artifactType` enum
- Add `activities.pseudocode/*.jsonl` to standard artifacts list

**Updated CLI Support:**
- `rpax list pseudocode [--project PROJECT]` - List pseudocode for workflows
- `rpax explain pseudocode WORKFLOW` - Show pseudocode for specific workflow
- `rpax export pseudocode [--format markdown|text]` - Export pseudocode to readable format

### 5. ADRs Requiring Updates

**ADR-009: Parser Artifacts** - Add pseudocode to artifact inventory
```diff
+ * `activities.pseudocode/<wfId>.jsonl` — human-readable pseudocode representation with extensible line metadata
```

**ADR-017: Data Lake Nomenclature** - Add pseudocode terminology
```diff
+ - **Pseudocode** — Human-readable abstraction of workflow logic with line-by-line structure
+ - **Pseudocode Line** — Individual pseudocode statement with semantic type and extensible metadata
```

**ADR-002: Layered Architecture** - Update parser layer responsibilities  
```diff  
+ - Emits pseudocode artifacts for documentation and AI consumption
```

**ADR-012: MCP Layer** - Add pseudocode resource types
```diff
+ - `uipath://proj/{slug}/pseudocode/{wfId}` — Pseudocode representation resource
```

**New ADR-022: Pseudocode Generation Rules**
- Define semantic mapping from UiPath activities to pseudocode
- Establish extensibility patterns for future line types
- Document abstraction principles and consistency rules

### 6. Implementation Strategy

**Phase 1: Core Infrastructure**
1. Add `PseudocodeGenerator` class to enhanced parser
2. Implement core line types and generation rules
3. Update artifact generation to produce pseudocode files
4. Add pseudocode validation schemas

**Phase 2: CLI Integration**
1. Add pseudocode listing and explanation commands
2. Implement export formats (Markdown, plain text)
3. Update help documentation and examples

**Phase 3: Advanced Features**  
1. Add metadata enrichment for debugging and tracing
2. Implement pseudocode diff analysis between runs
3. Add pseudocode search and indexing capabilities

**Phase 4: Extensibility**
1. Plugin system for custom pseudocode line types
2. Configuration-driven content templates
3. Language localization support

### 7. Future Flexibility Considerations

**Metadata Extensibility:**
- All metadata is stored in unstructured `metadata` object
- New properties can be added without schema changes
- Consumers should handle unknown metadata gracefully
- Standard metadata fields should be well-documented

**Line Type Evolution:**
- Core line types are fixed for v1.0 compatibility
- New line types can be added in minor versions
- Unknown line types should be treated as `comment` by older consumers
- Line type registry enables validation and tooling

**Content Format Evolution:**
- Content text format should remain human-readable
- Structured content can be added via metadata
- Template-based generation enables customization
- Multi-language support via content localization

**Schema Versioning:**
- Pseudocode artifacts include schema version field
- Breaking changes require major version increment
- Migration utilities provided for schema upgrades
- Backward compatibility within major versions

### 8. Benefits

**For Developers:**
- Clear, readable documentation of workflow logic
- Language-agnostic representation of automation
- Easy onboarding for new team members
- Debugging aid with activity traceability

**For AI/LLM:**
- Structured, parseable workflow representation  
- Semantic understanding without UiPath expertise
- Training data for workflow analysis models
- Context for code generation and suggestions

**For Documentation:**
- Automatic generation of workflow documentation
- Consistent representation across projects
- Export to various documentation formats
- Version control friendly text format

**For Analysis:**
- Pattern detection across workflows
- Complexity analysis and metrics
- Change impact assessment
- Test coverage mapping

### 9. Implementation Effort

**Estimated Work:**
- Core pseudocode generator: 3-4 days
- CLI integration: 1-2 days  
- Schema and validation: 1 day
- Testing and documentation: 2-3 days
- **Total: ~7-10 days**

**Testing Strategy:**
- Unit tests for all pseudocode line types
- Integration tests with real UiPath workflows
- Schema validation testing
- CLI command testing
- Export format validation

### 10. Success Metrics

- [ ] All major UiPath activity types have pseudocode mappings
- [ ] Generated pseudocode is human-readable and accurate
- [ ] Metadata extensibility supports future enhancements
- [ ] CLI commands provide intuitive pseudocode access
- [ ] Export formats are suitable for documentation
- [ ] Schema versioning enables backward compatibility
- [ ] Performance impact <20% on artifact generation

## Next Steps

1. **Approve Design** - Review and approve this design document
2. **Update ADRs** - Modify affected ADRs with pseudocode additions
3. **Implement Core** - Build pseudocode generation in enhanced parser
4. **Test Integration** - Validate with real UiPath projects
5. **Document Usage** - Create user guide for pseudocode features
6. **Plan v1.1** - Design advanced features and extensibility