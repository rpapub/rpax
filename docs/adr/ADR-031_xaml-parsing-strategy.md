# ADR-031: XAML Parsing Package Architecture for Workflow Metadata Extraction

**Status:** Accepted  
**Date:** 2024-01-01  
**Updated:** 2025-09-08

## Context

During Layer 1 stabilization with corpus projects, we discovered that rpax workflows.index.json is missing essential metadata:

- **Arguments**: Input/output parameters with types and annotations
- **Variables**: Workflow variables with names and types
- **Activity annotations**: Business logic descriptions for each activity
- **Root annotations**: Main workflow purpose and documentation
- **Activity structure**: Complete activity tree with annotations

Current rpax only extracts file-level metadata (size, modified date, path) but no XAML content analysis. This limits downstream tools and the MCP layer from understanding workflow interfaces and business logic.

## Decision

Create a **standalone XAML parsing package** at `src/xaml_parser/` within the rpax repository, designed for independent reuse and potential future publishing.

### Core Strategy: Standalone Package Architecture

**Choice**: Independent package `src/xaml_parser/` with zero external dependencies
**Alternative Rejected**: Embedded parsing within rpax modules (tight coupling, not reusable)

**Rationale**:
- **True Independence**: Package has no knowledge of rpax, uses only Python stdlib
- **Reusability**: Can be copied to any project or published to PyPI independently  
- **Zero Dependencies**: Uses dataclasses instead of Pydantic, xml.etree.ElementTree for parsing
- **Clear Boundaries**: Separate package with own models, tests, and documentation
- **Future Publishing**: Ready for pip publishing without modification
- **SDK Independence**: Direct XAML parsing, no UiPath Studio runtime required

### Parsing Architecture

#### 1. Namespace Handling
```python
# Standard UiPath XAML namespaces
NAMESPACES = {
    'x': 'http://schemas.microsoft.com/winfx/2006/xaml',
    'sap2010': 'http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation',
    'activities': 'http://schemas.microsoft.com/netfx/2009/xaml/activities'
}
```

#### 2. Root Annotation Detection Rules
1. **Primary**: Check root `<Activity>` element for `sap2010:Annotation.AnnotationText`
2. **Fallback**: Find first `<Sequence>` with annotation (main workflow logic)
3. **Handle encoding**: Parse HTML entities (`&#xA;` → newlines) automatically

#### 3. Argument Extraction Pattern
```python
# Extract from x:Members/x:Property elements
members = root.find(f"{{{x_ns}}}Members")
for prop in members.findall(f"{{{x_ns}}}Property"):
    name = prop.get("Name")
    type_attr = prop.get("Type")  # InArgument, OutArgument, InOutArgument
    annotation = prop.get(f"{{{sap2010_ns}}}Annotation.AnnotationText")
    direction = parse_direction_from_type(type_attr)
```

#### 4. Activity Annotation Extraction
```python
# Extract annotations from ALL activities
for elem in root.iter():
    annotation = elem.get(f"{{{sap2010_ns}}}Annotation.AnnotationText")
    if annotation:
        # Store with activity type, display name, and business context
```

#### 5. Variable Extraction Pattern (Future)
```python
# Extract workflow variables from <Variable> elements
for var_elem in root.iter():
    if var_elem.tag.endswith('Variable'):
        name = var_elem.get('Name')
        type_attr = var_elem.get('Type')
```

### Package Structure and Architecture

#### Standalone Package Layout
```
src/xaml_parser/                    # Independent package
├── __init__.py                     # Package exports
├── parser.py                       # Main XamlParser class  
├── models.py                       # All data models (dataclasses)
├── extractors.py                   # Extraction logic modules
├── constants.py                    # Namespaces, patterns, config
├── utils.py                        # Helper utilities
├── __version__.py                  # Version information
├── README.md                       # Package documentation  
└── pyproject.toml                  # Pip publishing config
```

#### Package Models (Zero Dependencies)
```python
@dataclass
class WorkflowContent:
    """Complete parsed workflow content from XAML file."""
    arguments: List[WorkflowArgument] = field(default_factory=list)
    variables: List[WorkflowVariable] = field(default_factory=list)
    activities: List[ActivityContent] = field(default_factory=list)
    root_annotation: Optional[str] = None
    namespaces: Dict[str, str] = field(default_factory=dict)
    assembly_references: List[str] = field(default_factory=list)
    expression_language: str = 'VisualBasic'
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass  
class ActivityContent:
    """Complete activity with all XAML data preserved."""
    tag: str
    activity_id: str  
    display_name: Optional[str] = None
    annotation: Optional[str] = None
    visible_attributes: Dict[str, str] = field(default_factory=dict)
    invisible_attributes: Dict[str, str] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    variables: List[WorkflowVariable] = field(default_factory=list)
    parent_activity_id: Optional[str] = None
    child_activities: List[str] = field(default_factory=list)
    depth_level: int = 0
```

#### Integration Pattern
```python
# In rpax/parser/xaml.py - treat as external package
from xaml_parser import XamlParser

class XamlDiscovery:
    def _create_workflow_entry(self, xaml_file: Path) -> Workflow:
        # Existing code...
        
        # Use standalone parser
        parser = XamlParser()
        content = parser.parse_file(xaml_file)
        
        # Map to rpax models or store complete content
        workflow.xaml_content = content
```

### Error Handling and Resilience

#### Graceful Degradation
- **Malformed XAML**: Log warning, continue with file metadata
- **Missing namespaces**: Skip annotation extraction, preserve other metadata
- **Base64 annotations**: Detect and decode (UiPath Studio Enterprise)
- **Large files**: Memory-efficient streaming for complex workflows

#### Validation Rules
- **Required elements**: `<Activity>` root element must exist
- **Namespace validation**: Warn if expected namespaces missing
- **Type parsing**: Handle malformed argument types gracefully

### Integration Points

#### 1. Workflow Discovery Pipeline
Extend `XamlDiscovery.discover_workflows()`:
```python
def discover_workflows(self) -> WorkflowIndex:
    for xaml_file in self._find_xaml_files():
        # Existing file metadata extraction
        workflow = Workflow(...)
        
        # NEW: Content analysis
        xaml_content = self._parse_xaml_content(xaml_file)
        workflow.root_annotation = xaml_content.root_annotation
        workflow.arguments = xaml_content.arguments
        workflow.activity_annotations = xaml_content.activity_annotations
```

#### 2. Activity Analysis Integration
Link with existing enhanced activity parsing for complete workflow understanding.

#### 3. Call Graph Enhancement
Use argument information to improve invocation analysis and parameter flow tracking.

## Testing Strategy

### Comprehensive Validation Strategy

#### Corpus Project Validation
- **c25v001_CORE_00000001**: Complete extraction validation
  - 3 arguments from InitAllSettings.xaml with full type signatures
  - All activity properties (visible/invisible) preserved
  - Complete nested configuration captured
  - Variable scoping across all workflow elements
- **PurposefulPromethium**: Complex workflow validation  
  - 20+ activities with comprehensive property analysis
  - Complex types (Dictionary, List, SecureString) preserved
  - Nested configuration (AssignOperations, ViewState) extracted
  - Expression preservation (`[in_Config("Imap_Credentialname").ToString]`)

#### Real-World Complexity Testing
- **Large workflows**: 100+ activities with complete metadata
- **Deep nesting**: Multi-level Sequence/TryCatch/ForEach hierarchies
- **Complex expressions**: UiPath Studio-supported VB.NET/C# expressions with LINQ, lambdas, method calls, concatenation
- **Enterprise features**: Base64 annotations, OAuth configurations
- **All UiPath activity types**: UI Automation, Mail, Database, File operations

## Benefits

### Immediate Layer 1 Impact
- **Complete metadata fidelity**: No workflow interface information lost
- **Downstream tool enablement**: Full argument/annotation data for analysis
- **MCP layer preparation**: Rich context for LLM consumption

### Future Capabilities
- **Documentation generation**: Automated workflow documentation from annotations
- **Impact analysis**: Business logic understanding for change assessment  
- **Debugging support**: Activity-level context for troubleshooting
- **Compliance checking**: Annotation-based rule validation

## Risks and Mitigations

### Risk: XAML Schema Evolution
**Mitigation**: Namespace-agnostic parsing with fallback patterns

### Risk: Performance Impact
**Mitigation**: Optional content analysis (config flag), streaming for large files

### Risk: Base64 Annotations (Studio Enterprise)
**Mitigation**: Detection and decoding logic, graceful fallback

### Risk: Malformed XAML
**Mitigation**: Comprehensive error handling, graceful degradation

## Implementation Strategy: Complete Data Extraction

**Principle**: Extract ALL available XAML data immediately - no phases or artificial limitations.

**Rationale**: rpax serves as MCP server providing rich context to LLMs. LLMs excel at interpreting complex, comprehensive data rather than simplified abstractions. Any filtering or reduction loses potentially valuable context for AI understanding.

### Complete Extraction (ISSUE-060)
1. **Root annotation detection** with HTML entity decoding
2. **All workflow arguments** with full type information and annotations
3. **Complete activity analysis**:
   - All visible attributes (DisplayName, Message, Level, AssetName, etc.)
   - All invisible attributes (ViewState, HintSize, IdRef, etc.)
   - Complete nested configuration (Variables, AssignOperations, complex objects)
   - Activity hierarchy with parent-child relationships
   - All annotation text on every activity
4. **Variable extraction** from all scopes
5. **Expression preservation** - UiPath Studio-valid VB.NET/C# expressions including LINQ, lambdas, method calls
6. **Workflow structure** - complete activity tree with all metadata
7. **Type information** - full .NET type signatures preserved
8. **Configuration properties** - all activity configuration preserved

### Data Richness Over Simplification
- **No property filtering** - extract every attribute and nested element
- **No complexity reduction** - preserve full XAML structure
- **No type simplification** - maintain complete .NET type information  
- **No expression parsing** - preserve UiPath Studio-valid expressions as-is for LLM analysis
- **No hierarchy flattening** - preserve complete parent-child relationships

## References

- **WatchfulAnvil XamlParser.cs**: Proven argument extraction pattern
- **UiPath Studio SDK**: Reference for complete workflow model (not used for implementation)
- **Corpus Projects**: Real-world validation data from c25v001_CORE_00000001
- **Layer 1 Stabilization**: ISSUE-059 (manifest fidelity), ISSUE-060 (workflow metadata)