"""Data models for XAML workflow parsing using only Python stdlib.

All models use dataclasses to avoid external dependencies, making this package
completely self-contained and reusable in any Python project.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowContent:
    """Complete parsed workflow content from XAML file.
    
    This is the main result object containing all extracted metadata
    from a workflow XAML file.
    """
    # Core workflow elements
    arguments: List['WorkflowArgument'] = field(default_factory=list)
    variables: List['WorkflowVariable'] = field(default_factory=list)
    activities: List['Activity'] = field(default_factory=list)
    
    # Workflow metadata
    root_annotation: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    
    # XAML technical metadata
    namespaces: Dict[str, str] = field(default_factory=dict)
    assembly_references: List[str] = field(default_factory=list)
    expression_language: str = 'VisualBasic'
    
    # Raw metadata for future extensions
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    total_activities: int = 0
    total_arguments: int = 0
    total_variables: int = 0


@dataclass
class WorkflowArgument:
    """Workflow argument definition from x:Members section."""
    name: str
    type: str                           # Full .NET type signature
    direction: str                      # 'in', 'out', 'inout'
    annotation: Optional[str] = None    # sap2010:Annotation.AnnotationText
    default_value: Optional[str] = None # From default attribute or this: prefix


@dataclass
class WorkflowVariable:
    """Variable definition from workflow scope."""
    name: str
    type: str                           # Full .NET type signature
    default_value: Optional[str] = None # Default value expression
    scope: str = "workflow"             # Which element scope owns this variable


@dataclass  
class Activity:
    """Complete activity instance with full business logic configuration.
    
    This model represents first-class Activity entities as specified in ADR-009,
    serving as the atomic units of interest for MCP/LLM consumption.
    """
    # Core identification (ActivityInstance requirements)
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
    
    # Legacy fields for backward compatibility  
    visible_attributes: Dict[str, str] = field(default_factory=dict)     # User-visible config (legacy)
    invisible_attributes: Dict[str, str] = field(default_factory=dict)   # ViewState, technical (legacy)
    variables: List[WorkflowVariable] = field(default_factory=list)      # Activity-scoped variables (legacy)
    child_activities: List[str] = field(default_factory=list)            # Legacy hierarchy
    expression_objects: List['Expression'] = field(default_factory=list)  # Detailed expression objects (legacy)
    
    # Position context
    xpath_location: Optional[str] = None    # XPath for debugging
    source_line: Optional[int] = None       # Line number in XAML


@dataclass
class Expression:
    """Expression found in XAML (VB.NET or C# syntax)."""
    content: str                        # Raw expression text
    expression_type: str                # 'assignment', 'condition', 'message', etc.
    language: str = 'VisualBasic'       # Expression language
    context: Optional[str] = None       # Which activity property contains this
    contains_variables: List[str] = field(default_factory=list)  # Variable references
    contains_methods: List[str] = field(default_factory=list)    # Method calls detected


@dataclass
class ViewStateData:
    """ViewState information (invisible UI metadata)."""
    is_expanded: Optional[bool] = None
    is_pinned: Optional[bool] = None
    is_annotation_docked: Optional[bool] = None
    hint_size: Optional[str] = None
    other_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseDiagnostics:
    """Detailed diagnostic information about parsing operation."""
    total_elements_processed: int = 0
    activities_found: int = 0
    arguments_found: int = 0
    variables_found: int = 0
    annotations_found: int = 0
    expressions_found: int = 0
    namespaces_detected: int = 0
    skipped_elements: int = 0
    xml_depth: int = 0
    file_size_bytes: int = 0
    encoding_detected: Optional[str] = None
    root_element_tag: Optional[str] = None
    processing_steps: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ParseResult:
    """Complete parsing result with success/error information and diagnostics."""
    content: Optional[WorkflowContent] = None
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parse_time_ms: float = 0.0
    file_path: Optional[str] = None
    # Enhanced diagnostics for troubleshooting
    diagnostics: Optional[ParseDiagnostics] = None
    config_used: Dict[str, Any] = field(default_factory=dict)