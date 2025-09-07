"""Core XAML parser for workflow automation projects.

This module provides the main XamlParser class that extracts complete
workflow metadata from XAML files using only Python stdlib.
"""

import html
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Use secure XML parsing
import xml.etree.ElementTree as ET
try:
    from defusedxml.ElementTree import fromstring as defused_fromstring
except ImportError:
    # Fallback to standard library if defusedxml not available
    from xml.etree.ElementTree import fromstring as defused_fromstring

from .constants import (
    ARGUMENT_DIRECTIONS,
    CORE_VISUAL_ACTIVITIES,
    DEFAULT_CONFIG,
    EXPRESSION_PATTERNS,
    INVISIBLE_ATTRIBUTE_PATTERNS,
    SKIP_ELEMENTS,
    STANDARD_NAMESPACES,
    VIEWSTATE_PROPERTIES,
)
from .models import (
    Activity,
    Expression,
    ParseResult,
    ParseDiagnostics,
    WorkflowArgument,
    WorkflowContent,
    WorkflowVariable,
)
from .validation import validate_output


class XamlParser:
    """Complete XAML workflow parser for automation projects.
    
    Extracts all workflow metadata including arguments, variables, activities,
    annotations, and expressions from XAML workflow files.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize parser with configuration.
        
        Args:
            config: Parser configuration dict, uses DEFAULT_CONFIG if None
        """
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self._activity_counter = 0
        self._diagnostics = None  # Will be initialized per parse operation
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse XAML workflow file.
        
        Args:
            file_path: Path to XAML file
            
        Returns:
            ParseResult with extracted content or error information
        """
        start_time = time.time()
        result = ParseResult(file_path=str(file_path), config_used=self.config.copy())
        
        # Initialize diagnostics
        self._diagnostics = ParseDiagnostics()
        self._diagnostics.processing_steps.append("parse_file_started")
        
        try:
            # Read file and collect diagnostics
            file_size = file_path.stat().st_size
            self._diagnostics.file_size_bytes = file_size
            self._diagnostics.processing_steps.append("file_read")
            
            # Read and parse XAML
            content = file_path.read_text(encoding='utf-8')
            self._diagnostics.encoding_detected = 'utf-8'
            
            parse_start = time.time()
            root = defused_fromstring(content)
            self._diagnostics.performance_metrics['xml_parse_ms'] = (time.time() - parse_start) * 1000
            self._diagnostics.root_element_tag = root.tag
            self._diagnostics.processing_steps.append("xml_parsed")
            
            # Extract all workflow content
            extract_start = time.time()
            workflow_content = self._extract_workflow_content(root, str(file_path))
            self._diagnostics.performance_metrics['content_extract_ms'] = (time.time() - extract_start) * 1000
            
            result.content = workflow_content
            self._diagnostics.processing_steps.append("content_extracted")
            
        except ET.ParseError as e:
            result.success = False
            result.errors.append(f"XML parse error: {e}")
            self._diagnostics.processing_steps.append("xml_parse_failed")
        except UnicodeDecodeError as e:
            result.success = False
            result.errors.append(f"Encoding error: {e}")
            self._diagnostics.processing_steps.append("encoding_error")
        except Exception as e:
            result.success = False
            result.errors.append(f"Unexpected error: {e}")
            self._diagnostics.processing_steps.append("unexpected_error")
        
        result.parse_time_ms = (time.time() - start_time) * 1000
        result.diagnostics = self._diagnostics
        
        # Validate output if in strict mode
        if self.config.get('strict_mode', False):
            try:
                validation_errors = validate_output(result, strict=False)
                if validation_errors:
                    result.warnings.extend([f"Validation: {err}" for err in validation_errors])
                    self._diagnostics.processing_steps.append("validation_warnings_added")
            except Exception as e:
                result.warnings.append(f"Validation failed: {str(e)}")
        
        return result
    
    def parse_content(self, xml_content: str, file_path: str = "<string>") -> ParseResult:
        """Parse XAML content from string.
        
        Args:
            xml_content: Raw XAML content
            file_path: Virtual file path for error reporting
            
        Returns:
            ParseResult with extracted content or error information
        """
        start_time = time.time()
        result = ParseResult(file_path=file_path, config_used=self.config.copy())
        
        # Initialize diagnostics
        self._diagnostics = ParseDiagnostics()
        self._diagnostics.processing_steps.append("parse_content_started")
        
        try:
            # Parse XAML securely with defusedxml
            parse_start = time.time()
            root = defused_fromstring(xml_content)
            self._diagnostics.performance_metrics['xml_parse_ms'] = (time.time() - parse_start) * 1000
            self._diagnostics.root_element_tag = root.tag
            self._diagnostics.processing_steps.append("xml_parsed")
            
            # Extract workflow content
            extract_start = time.time()
            workflow_content = self._extract_workflow_content(root, file_path)
            self._diagnostics.performance_metrics['content_extract_ms'] = (time.time() - extract_start) * 1000
            
            result.content = workflow_content
            self._diagnostics.processing_steps.append("content_extracted")
            
        except ET.ParseError as e:
            result.success = False
            result.errors.append(f"XML parse error: {e}")
            self._diagnostics.processing_steps.append("xml_parse_failed")
        except Exception as e:
            result.success = False
            result.errors.append(f"Unexpected error: {e}")
            self._diagnostics.processing_steps.append("unexpected_error")
        
        result.parse_time_ms = (time.time() - start_time) * 1000
        result.diagnostics = self._diagnostics
        
        # Validate output if in strict mode
        if self.config.get('strict_mode', False):
            try:
                validation_errors = validate_output(result, strict=False)
                if validation_errors:
                    result.warnings.extend([f"Validation: {err}" for err in validation_errors])
                    self._diagnostics.processing_steps.append("validation_warnings_added")
            except Exception as e:
                result.warnings.append(f"Validation failed: {str(e)}")
        
        return result
    
    def _extract_workflow_content(self, root: ET.Element, file_path: str) -> WorkflowContent:
        """Extract complete workflow content from XML root.
        
        Args:
            root: XML root element
            file_path: Source file path
            
        Returns:
            WorkflowContent with all extracted metadata
        """
        content = WorkflowContent()
        self._activity_counter = 0
        
        # Count total elements for diagnostics
        total_elements = sum(1 for _ in root.iter())
        self._diagnostics.total_elements_processed = total_elements
        
        # Calculate XML depth
        max_depth = 0
        def get_depth(elem, depth=0):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for child in elem:
                get_depth(child, depth + 1)
        get_depth(root)
        self._diagnostics.xml_depth = max_depth
        
        # Extract namespaces
        content.namespaces = self._extract_namespaces(root)
        self._diagnostics.namespaces_detected = len(content.namespaces)
        self._diagnostics.processing_steps.append("namespaces_extracted")
        
        # Extract arguments from x:Members
        if self.config['extract_arguments']:
            content.arguments = self._extract_arguments(root, content.namespaces)
            self._diagnostics.arguments_found = len(content.arguments)
            self._diagnostics.processing_steps.append("arguments_extracted")
        
        # Extract variables from all scopes
        if self.config['extract_variables']:
            content.variables = self._extract_variables(root, content.namespaces)
            self._diagnostics.variables_found = len(content.variables)
            self._diagnostics.processing_steps.append("variables_extracted")
        
        # Extract activities with complete metadata
        if self.config['extract_activities']:
            content.activities = self._extract_activities(root, content.namespaces)
            self._diagnostics.activities_found = len(content.activities)
            # Count activities with annotations
            self._diagnostics.annotations_found = sum(1 for a in content.activities if a.annotation)
            # Count expressions
            self._diagnostics.expressions_found = sum(len(a.expressions) for a in content.activities)
            self._diagnostics.processing_steps.append("activities_extracted")
        
        # Extract root annotation
        content.root_annotation = self._extract_root_annotation(root, content.namespaces)
        if content.root_annotation:
            self._diagnostics.annotations_found += 1
        self._diagnostics.processing_steps.append("root_annotation_extracted")
        
        # Extract assembly references
        if self.config['extract_assembly_references']:
            content.assembly_references = self._extract_assembly_references(root)
            self._diagnostics.processing_steps.append("assembly_references_extracted")
        
        # Extract expression language
        content.expression_language = self._extract_expression_language(root)
        self._diagnostics.processing_steps.append("expression_language_detected")
        
        # Calculate statistics
        content.total_activities = len(content.activities)
        content.total_arguments = len(content.arguments)
        content.total_variables = len(content.variables)
        
        return content
    
    def _extract_namespaces(self, root: ET.Element) -> Dict[str, str]:
        """Extract all XML namespaces from root element."""
        namespaces = {}
        
        # Get namespaces from root attributes
        for key, value in root.attrib.items():
            if key.startswith('xmlns:'):
                prefix = key[6:]  # Remove 'xmlns:' prefix
                namespaces[prefix] = value
            elif key == 'xmlns':
                namespaces[''] = value  # Default namespace
        
        # Merge with standard namespaces
        return {**STANDARD_NAMESPACES, **namespaces}
    
    def _extract_arguments(self, root: ET.Element, namespaces: Dict[str, str]) -> List[WorkflowArgument]:
        """Extract workflow arguments from x:Members section."""
        arguments = []
        
        # Find x:Members element
        x_ns = namespaces.get('x', '')
        if not x_ns:
            return arguments
        
        members = root.find(f"{{{x_ns}}}Members")
        if members is None:
            return arguments
        
        # Extract each x:Property (argument definition)
        sap2010_ns = namespaces.get('sap2010', '')
        for prop in members.findall(f"{{{x_ns}}}Property"):
            name = prop.get("Name")
            type_attr = prop.get("Type", "")
            
            if not name:
                continue
            
            # Parse direction from type (InArgument, OutArgument, InOutArgument)
            direction = "in"  # Default
            for type_prefix, dir_value in ARGUMENT_DIRECTIONS.items():
                if type_prefix in type_attr:
                    direction = dir_value
                    break
            
            # Extract annotation
            annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText" if sap2010_ns else None
            annotation = None
            if annotation_attr:
                annotation = prop.get(annotation_attr)
                if annotation:
                    annotation = html.unescape(annotation)  # Decode HTML entities
            
            # Extract default value
            default_value = prop.get("default") or prop.text
            
            argument = WorkflowArgument(
                name=name,
                type=type_attr,
                direction=direction,
                annotation=annotation,
                default_value=default_value
            )
            arguments.append(argument)
        
        return arguments
    
    def _extract_variables(self, root: ET.Element, namespaces: Dict[str, str]) -> List[WorkflowVariable]:
        """Extract all variables from workflow scopes."""
        variables = []
        
        # Find all Variable elements throughout the tree
        for elem in root.iter():
            if elem.tag.endswith('Variable') or 'Variable' in elem.tag:
                name = elem.get('Name')
                type_attr = elem.get('Type', 'Object')
                default_value = elem.get('Default') or elem.text
                
                if name:
                    # Determine scope from parent context
                    scope = self._determine_variable_scope(elem)
                    
                    variable = WorkflowVariable(
                        name=name,
                        type=type_attr,
                        default_value=default_value,
                        scope=scope
                    )
                    variables.append(variable)
        
        return variables
    
    def _extract_activities(self, root: ET.Element, namespaces: Dict[str, str]) -> List[Activity]:
        """Extract all activities with complete metadata."""
        activities = []
        sap2010_ns = namespaces.get('sap2010', '')
        
        def process_element(elem: ET.Element, parent_id: Optional[str] = None, depth: int = 0):
            """Recursively process elements to find activities."""
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Skip non-activity elements
            if tag_name in SKIP_ELEMENTS:
                # Still process children for nested activities
                for child in elem:
                    process_element(child, parent_id, depth)
                return
            
            # Check if this is an activity (either in whitelist or has activity-like attributes)
            is_activity = (
                tag_name in CORE_VISUAL_ACTIVITIES or
                elem.get('DisplayName') is not None or
                any(attr.endswith('Annotation.AnnotationText') for attr in elem.attrib) or
                self._looks_like_activity(elem, tag_name)
            )
            
            if is_activity:
                self._activity_counter += 1
                activity_id = f"activity_{self._activity_counter}"
                
                # Extract all attributes
                visible_attrs, invisible_attrs = self._categorize_attributes(elem.attrib)
                
                # Extract annotation
                annotation = None
                if sap2010_ns:
                    annotation_key = f"{{{sap2010_ns}}}Annotation.AnnotationText"
                    annotation = elem.get(annotation_key)
                    if annotation:
                        annotation = html.unescape(annotation)
                
                # Extract expressions from this activity
                expressions = []
                if self.config['extract_expressions']:
                    expressions = self._extract_expressions_from_element(elem)
                
                # Extract activity-scoped variables
                activity_variables = []
                for child in elem:
                    if child.tag.endswith('Variable'):
                        var_name = child.get('Name')
                        if var_name:
                            activity_variables.append(WorkflowVariable(
                                name=var_name,
                                type=child.get('Type', 'Object'),
                                default_value=child.get('Default'),
                                scope=activity_id
                            ))
                
                # Create activity content
                activity = Activity(
                    activity_id=activity_id,
                    workflow_id="unknown",  # Will be set by caller
                    activity_type=tag_name,
                    display_name=elem.get('DisplayName'),
                    node_id=activity_id,  # Use activity_id as node_id for legacy compatibility
                    parent_activity_id=parent_id,
                    depth=depth,
                    arguments=visible_attrs,  # Map visible attributes to arguments
                    configuration=self._extract_configuration(elem),
                    properties=visible_attrs,  # Map to properties
                    metadata=invisible_attrs,  # Map to metadata
                    expressions=[expr.content for expr in expressions] if expressions else [],
                    variables_referenced=[],  # Extract separately
                    selectors={},  # Extract separately
                    annotation=annotation,
                    is_visible=True,  # Default to visible
                    container_type=None,  # Will be determined by hierarchy
                    visible_attributes=visible_attrs,
                    invisible_attributes=invisible_attrs,
                    variables=activity_variables,
                    expression_objects=expressions,
                    xpath_location=self._get_xpath_location(elem, root)
                )
                
                activities.append(activity)
                
                # Process children with this activity as parent
                for child in elem:
                    process_element(child, activity_id, depth + 1)
                
                # Update parent-child relationships
                if parent_id:
                    for parent_activity in activities:
                        if parent_activity.activity_id == parent_id:
                            parent_activity.child_activities.append(activity_id)
                            break
            else:
                # Not an activity, but process children
                for child in elem:
                    process_element(child, parent_id, depth)
        
        # Start processing from root
        process_element(root)
        return activities
    
    def _extract_root_annotation(self, root: ET.Element, namespaces: Dict[str, str]) -> Optional[str]:
        """Extract root workflow annotation."""
        sap2010_ns = namespaces.get('sap2010', '')
        if not sap2010_ns:
            return None
        
        annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"
        
        # Try root element first
        annotation = root.get(annotation_attr)
        if annotation:
            return html.unescape(annotation)
        
        # Fallback: find first Sequence with annotation
        for elem in root.iter():
            if elem.tag.endswith('Sequence'):
                annotation = elem.get(annotation_attr)
                if annotation:
                    return html.unescape(annotation)
        
        return None
    
    def _extract_assembly_references(self, root: ET.Element) -> List[str]:
        """Extract assembly references from workflow."""
        references = []
        
        for elem in root.iter():
            if elem.tag.endswith('AssemblyReference'):
                ref = elem.text or elem.get('Assembly')
                if ref:
                    references.append(ref)
        
        return references
    
    def _extract_expression_language(self, root: ET.Element) -> str:
        """Extract expression language from workflow metadata."""
        # Check for ExpressionActivityEditor attribute
        lang = root.get('ExpressionActivityEditor')
        if lang:
            return 'CSharp' if 'CSharp' in lang else 'VisualBasic'
        
        # Check for VisualBasic elements
        for elem in root.iter():
            if 'VisualBasic' in elem.tag:
                return 'VisualBasic'
            elif 'CSharp' in elem.tag:
                return 'CSharp'
        
        return self.config['expression_language']
    
    def _determine_variable_scope(self, var_element: ET.Element) -> str:
        """Determine the scope context for a variable."""
        parent = var_element.getparent() if hasattr(var_element, 'getparent') else None
        if parent is not None:
            parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
            if parent_tag in CORE_VISUAL_ACTIVITIES:
                return parent_tag
        return "workflow"
    
    def _categorize_attributes(self, attrib: Dict[str, str]) -> tuple[Dict[str, str], Dict[str, str]]:
        """Categorize attributes into visible and invisible."""
        visible = {}
        invisible = {}
        
        for key, value in attrib.items():
            # Remove namespace prefixes for comparison
            clean_key = key.split('}')[-1] if '}' in key else key
            
            # Check if attribute matches invisible patterns
            is_invisible = (
                any(pattern in key for pattern in INVISIBLE_ATTRIBUTE_PATTERNS) or
                clean_key in VIEWSTATE_PROPERTIES or
                'ViewState' in key or
                'HintSize' in key or
                'IdRef' in key
            )
            
            if is_invisible:
                invisible[key] = value
            else:
                visible[key] = value
        
        return visible, invisible
    
    def _looks_like_activity(self, elem: ET.Element, tag_name: str) -> bool:
        """Heuristic to determine if element is an activity."""
        # Has typical activity attributes
        if any(attr in elem.attrib for attr in ['DisplayName', 'Result', 'Value', 'Text']):
            return True
        
        # Has child elements that suggest it's a container activity
        child_tags = {child.tag.split('}')[-1] for child in elem}
        if child_tags & CORE_VISUAL_ACTIVITIES:
            return True
        
        # Namespace suggests it's an activity
        if elem.tag.startswith('{http://schemas.uipath.com/workflow/activities}'):
            return True
        
        return False
    
    def _extract_configuration(self, elem: ET.Element) -> Dict[str, Any]:
        """Extract nested configuration from activity element."""
        config = {}
        
        for child in elem:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            # Skip variable definitions (handled separately)
            if child_tag.endswith('Variable'):
                continue
            
            # Extract nested configuration
            if len(child) > 0:  # Has children
                config[child_tag] = self._extract_nested_config(child)
            else:
                # Simple value
                config[child_tag] = child.text or child.attrib
        
        return config
    
    def _extract_nested_config(self, elem: ET.Element) -> Any:
        """Recursively extract nested configuration."""
        if len(elem) == 0:
            return elem.text or elem.attrib
        
        if len(elem.attrib) > 0 and len(elem) > 0:
            # Has both attributes and children
            return {
                'attributes': elem.attrib,
                'children': {
                    child.tag.split('}')[-1]: self._extract_nested_config(child)
                    for child in elem
                }
            }
        elif len(elem) > 0:
            # Only children
            return {
                child.tag.split('}')[-1]: self._extract_nested_config(child)
                for child in elem
            }
        else:
            # Only attributes
            return elem.attrib
    
    def _extract_expressions_from_element(self, elem: ET.Element) -> List[Expression]:
        """Extract all expressions from an activity element."""
        expressions = []
        
        # Check attributes for expressions
        for key, value in elem.attrib.items():
            if self._is_expression(value):
                expr = Expression(
                    content=value,
                    expression_type=self._classify_expression_type(key),
                    language=self.config['expression_language'],
                    context=key
                )
                expressions.append(expr)
        
        # Check text content for expressions
        if elem.text and self._is_expression(elem.text):
            expr = Expression(
                content=elem.text.strip(),
                expression_type='text_content',
                language=self.config['expression_language'],
                context='text'
            )
            expressions.append(expr)
        
        return expressions
    
    def _is_expression(self, text: str) -> bool:
        """Check if text contains expression patterns."""
        if not text or len(text.strip()) < 2:
            return False
        
        # Look for expression patterns
        return any(pattern in text for pattern in EXPRESSION_PATTERNS)
    
    def _classify_expression_type(self, context: str) -> str:
        """Classify expression type based on context."""
        context_lower = context.lower()
        
        if 'condition' in context_lower:
            return 'condition'
        elif 'value' in context_lower or 'result' in context_lower:
            return 'assignment'
        elif 'message' in context_lower or 'text' in context_lower:
            return 'message'
        else:
            return 'general'
    
    def _get_xpath_location(self, elem: ET.Element, root: ET.Element) -> str:
        """Generate XPath location for debugging."""
        # Simple XPath generation - could be enhanced
        path_parts = []
        current = elem
        
        # Walk up the tree to build path
        while current is not None and current != root:
            tag = current.tag.split('}')[-1] if '}' in current.tag else current.tag
            path_parts.insert(0, tag)
            current = current.getparent() if hasattr(current, 'getparent') else None
        
        return '/' + '/'.join(path_parts) if path_parts else '/root'