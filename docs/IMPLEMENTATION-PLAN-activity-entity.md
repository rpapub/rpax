# Activity Entity Implementation Plan

**Status:** Ready for Implementation  
**Date:** 2025-09-07  
**Context:** Layer 1 Stabilization - Complete Activity entity as first-class artifact

## Overview

Implement **Activity instances** as first-class entities in rpax data model, addressing the critical gap identified during Layer 1 stabilization corpus testing.

## Background

**Problem Identified:** Current data model captures workflow structural hierarchy (`activities.tree`) but lacks complete individual Activity configurations with business logic - the true atomic units of interest for MCP/LLM consumption.

**Evidence:** Real XAML activities like `<uix:NClick>`, `<ui:GetIMAPMailMessages>`, `<ui:ForEach>` contain rich business logic (arguments, expressions, selectors, configurations) not captured in existing artifacts.

## Implementation Strategy

### Phase 1: Foundation (v0.1.0) 

#### 1.1 Extend XamlParser (src/xaml_parser/)

**File: `src/xaml_parser/models.py`**
```python
@dataclass
class ActivityInstance:
    """Complete activity instance with full business logic configuration."""
    activity_id: str                                    # Unique activity identifier
    workflow_id: str                                   # Parent workflow
    activity_type: str                                 # e.g., "uix:NClick"
    display_name: Optional[str] = None                 # User-visible name
    node_id: str = ""                                  # Hierarchical path
    parent_activity_id: Optional[str] = None           # Parent in hierarchy
    depth: int = 0                                     # Nesting level
    
    # Complete business logic extraction
    arguments: Dict[str, Any] = field(default_factory=dict)      # All activity arguments
    configuration: Dict[str, Any] = field(default_factory=dict)  # Nested objects (Target, etc.)
    properties: Dict[str, Any] = field(default_factory=dict)     # All visible properties
    metadata: Dict[str, Any] = field(default_factory=dict)       # ViewState, IdRef, etc.
    
    # Business logic analysis
    expressions: List[str] = field(default_factory=list)         # UiPath expressions found
    variables_referenced: List[str] = field(default_factory=list) # Variables used
    selectors: Dict[str, str] = field(default_factory=dict)      # UI selectors
    
    annotation: Optional[str] = None                   # Activity annotation
    is_visible: bool = True                           # Visual designer visibility
    container_type: Optional[str] = None              # Parent container type
```

**File: `src/xaml_parser/extractors.py`**
```python
class ActivityExtractor:
    """Extract complete activity configurations from XAML elements."""
    
    def extract_activity_instances(self, root: ET.Element) -> List[ActivityInstance]:
        """Extract all activity instances with complete configurations."""
        activities = []
        
        # Use visibility filtering for real business logic activities
        visible_activities = get_visible_elements(root)
        
        for element in visible_activities:
            activity = self._extract_single_activity(element)
            if activity:
                activities.append(activity)
        
        return activities
    
    def _extract_single_activity(self, element: ET.Element) -> Optional[ActivityInstance]:
        """Extract complete configuration from single activity element."""
        # Extract all attributes as arguments
        arguments = self._extract_arguments(element)
        
        # Extract nested configuration objects
        configuration = self._extract_nested_configuration(element)
        
        # Extract business logic expressions
        expressions = self._extract_expressions(element)
        
        # Extract selectors for UI activities
        selectors = self._extract_selectors(element)
        
        return ActivityInstance(
            activity_id=self._generate_activity_id(element),
            activity_type=get_local_tag(element),
            arguments=arguments,
            configuration=configuration,
            expressions=expressions,
            selectors=selectors,
            # ... other fields
        )
```

#### 1.2 Activity Identity System

**Stable Activity ID Generation:**
```python
def generate_activity_id(project_id: str, workflow_path: str, node_id: str, 
                        activity_content: str) -> str:
    """Generate stable activity identifier with content hash."""
    content_hash = hashlib.sha256(activity_content.encode()).hexdigest()[:8]
    workflow_id = workflow_path.replace("\\", "/").replace(".xaml", "")
    return f"{project_id}#{workflow_id}#{node_id}#{content_hash}"

# Examples:
# f4aa3834#Process/Calculator/ClickListOfCharacters#Activity/Sequence/ForEach/Sequence/NApplicationCard/Sequence/If/Sequence/NClick#abc123ef
# frozenchlorine-1082950b#StandardCalculator#Activity/Sequence/InvokeWorkflowFile_5#def456ab
```

#### 1.3 Artifact Generation Pipeline

**File: `src/rpax/artifacts.py`**
```python
def _generate_activity_instances(self, workflow: Workflow, 
                                workflow_path: Path) -> Path:
    """Generate activities.instances/{wfId}.json artifact."""
    
    # Use extended XamlParser for complete extraction
    parser = XamlParser()
    result = parser.parse_file(workflow_path)
    
    # Extract activity instances
    extractor = ActivityExtractor()
    activities = extractor.extract_activity_instances(result.root)
    
    # Generate artifact
    artifact = {
        "schemaVersion": "1.0.0",
        "workflowId": workflow.workflow_id,
        "generatedAt": datetime.utcnow().isoformat(),
        "totalActivities": len(activities),
        "activities": [asdict(activity) for activity in activities]
    }
    
    # Write to activities.instances/{wfId}.json
    instances_dir = self.output_dir / "activities.instances"
    instances_dir.mkdir(exist_ok=True)
    
    safe_workflow_id = workflow.workflow_id.replace("/", "_").replace("\\", "_")
    instances_file = instances_dir / f"{safe_workflow_id}.json"
    
    with open(instances_file, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)
    
    return instances_file
```

#### 1.4 Schema Definition

**File: `src/rpax/schemas/activity-instances.v1.schema.json`**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Activity Instances Artifact",
  "description": "Complete activity configurations with business logic",
  "type": "object",
  "properties": {
    "schemaVersion": {"type": "string", "const": "1.0.0"},
    "workflowId": {"type": "string"},
    "generatedAt": {"type": "string", "format": "date-time"},
    "totalActivities": {"type": "integer", "minimum": 0},
    "activities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "activity_id": {"type": "string"},
          "workflow_id": {"type": "string"},
          "activity_type": {"type": "string"},
          "display_name": {"type": ["string", "null"]},
          "arguments": {"type": "object"},
          "configuration": {"type": "object"},
          "expressions": {"type": "array", "items": {"type": "string"}},
          "selectors": {"type": "object"}
        },
        "required": ["activity_id", "workflow_id", "activity_type"]
      }
    }
  },
  "required": ["schemaVersion", "workflowId", "activities"]
}
```

### Phase 2: Integration & Testing (v0.1.1)

#### 2.1 Pipeline Integration
- **Modify `ArtifactGenerator.generate_all()`** to include activity instances generation
- **Update lake directory structure** to include `activities.instances/` folder
- **Extend schema validation** to validate activity instances artifacts

#### 2.2 Corpus Validation
```python
# Test against real projects
def test_activity_extraction_frozenchlorine():
    """Validate complete activity extraction against FrozenChlorine corpus."""
    # Parse ClickListOfCharacters.xaml
    activities = extract_activity_instances("FrozenChlorine/Process/Calculator/ClickListOfCharacters.xaml")
    
    # Validate NClick activity extraction
    nclick_activity = find_activity_by_type(activities, "uix:NClick")
    assert nclick_activity.arguments["ActivateBefore"] == "True"
    assert nclick_activity.arguments["ClickType"] == "Single"
    assert "string.Format" in nclick_activity.expressions[0]
    assert "FullSelectorArgument" in nclick_activity.selectors
    
    # Validate ForEach activity extraction
    foreach_activity = find_activity_by_type(activities, "ui:ForEach")
    assert foreach_activity.arguments["Values"] == "[CharacterList]"
    assert "CharacterList" in foreach_activity.variables_referenced
```

#### 2.3 Performance Testing
- **Large workflow testing**: Validate 1k+ activities extraction performance
- **Memory optimization**: Stream processing for complex workflows
- **Parallel processing**: Activity extraction parallelization

### Phase 3: MCP Integration (v0.1.2)

#### 3.1 MCP Resource Exposure
```python
# Extend MCP server to expose Activity instances
class ActivityResource:
    def list_activities(self, workflow_id: str) -> List[ActivityInstance]:
        """List all activities in workflow with complete configurations."""
        
    def get_activity(self, activity_id: str) -> ActivityInstance:
        """Get complete activity configuration by ID."""
        
    def search_activities(self, expression: str, activity_type: str = None) -> List[ActivityInstance]:
        """Search activities by expression content or type."""
```

#### 3.2 Cross-Reference Support
- **Link activities to invocations**: Connect InvokeWorkflowFile activities to invocation records
- **Activity dependency graph**: Track activities that reference variables/assets
- **Impact analysis**: Identify activities affected by workflow changes

## Success Criteria

### Phase 1 Complete
- [ ] XamlParser extracts complete activity configurations
- [ ] Activity instances artifacts generated for all workflows
- [ ] Schema validation passes for activity artifacts
- [ ] Stable activity ID generation working

### Phase 2 Complete  
- [ ] FrozenChlorine corpus validation passes
- [ ] PurposefulPromethium corpus validation passes
- [ ] Performance acceptable for 1k+ activity workflows
- [ ] Integration with existing rpax pipeline complete

### Phase 3 Complete
- [ ] MCP server exposes Activity resources
- [ ] Activity search and filtering working
- [ ] Cross-reference support implemented
- [ ] LLM consumption validation passes

## File Changes Required

### New Files
- `src/xaml_parser/extractors.py` - Activity extraction logic
- `src/rpax/schemas/activity-instances.v1.schema.json` - Schema
- `docs/schemas/activity-instances-example.json` - Example artifact

### Modified Files
- `src/xaml_parser/models.py` - Add ActivityInstance model
- `src/xaml_parser/parser.py` - Integrate activity extraction
- `src/rpax/artifacts.py` - Add activity instances generation
- `src/rpax/models.py` - Update artifact types
- `docs/lake-data-model.md` - Add Activity entity definition

### Test Files
- `tests/test_activity_extraction.py` - Activity extraction tests
- `tests/corpus/test_frozenchlorine_activities.py` - Corpus validation
- `tests/performance/test_large_workflow_activities.py` - Performance tests

## Risk Mitigation

### Performance Risk
- **Mitigation**: Stream processing, parallel extraction, configurable depth limits
- **Monitoring**: Activity extraction time metrics per workflow

### Schema Evolution Risk  
- **Mitigation**: Semantic versioning, backward compatibility validation
- **Monitoring**: Schema validation failure rates

### Storage Growth Risk
- **Mitigation**: Optional activity extraction (config flag), compression
- **Monitoring**: Lake size growth tracking

## Timeline Estimate

- **Phase 1**: 2-3 weeks (Foundation)
- **Phase 2**: 1-2 weeks (Integration & Testing)  
- **Phase 3**: 1 week (MCP Integration)
- **Total**: 4-6 weeks for complete Activity entity implementation

## Dependencies

- **ADR-031**: XAML parsing strategy (implemented)
- **Visibility filtering**: Business logic vs metadata distinction (implemented)
- **Invocation parsing fixes**: Clean foundation for activity relationships (completed)