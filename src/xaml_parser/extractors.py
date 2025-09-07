"""Specialized extraction modules for different XAML content types.

This module provides focused extractors for specific workflow metadata types,
allowing for modular and maintainable parsing logic.
"""

import html
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set, Tuple

from .constants import (
    ARGUMENT_DIRECTIONS,
    CORE_VISUAL_ACTIVITIES,
    EXPRESSION_PATTERNS,
    SKIP_ELEMENTS,
)
from .models import Activity, Expression, WorkflowArgument, WorkflowVariable
from .utils import ActivityUtils
from .visibility import get_visible_elements, get_local_tag, is_visible_element


class ArgumentExtractor:
    """Extracts workflow arguments from x:Members section."""
    
    @staticmethod
    def extract_arguments(root: ET.Element, namespaces: Dict[str, str]) -> List[WorkflowArgument]:
        """Extract all workflow arguments with complete metadata."""
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
            argument = ArgumentExtractor._extract_single_argument(prop, sap2010_ns)
            if argument:
                arguments.append(argument)
        
        return arguments
    
    @staticmethod
    def _extract_single_argument(prop: ET.Element, sap2010_ns: str) -> Optional[WorkflowArgument]:
        """Extract single argument from x:Property element."""
        name = prop.get("Name")
        type_attr = prop.get("Type", "")
        
        if not name:
            return None
        
        # Parse direction from type (InArgument, OutArgument, InOutArgument)
        direction = "in"  # Default
        for type_prefix, dir_value in ARGUMENT_DIRECTIONS.items():
            if type_prefix in type_attr:
                direction = dir_value
                break
        
        # Extract annotation with HTML entity decoding
        annotation = None
        if sap2010_ns:
            annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"
            annotation = prop.get(annotation_attr)
            if annotation:
                annotation = html.unescape(annotation)
        
        # Extract default value from multiple sources
        default_value = (
            prop.get("default") or 
            prop.get("Default") or 
            prop.text
        )
        
        return WorkflowArgument(
            name=name,
            type=type_attr,
            direction=direction,
            annotation=annotation,
            default_value=default_value
        )


class VariableExtractor:
    """Extracts workflow variables from all scopes."""
    
    @staticmethod
    def extract_variables(root: ET.Element, namespaces: Dict[str, str]) -> List[WorkflowVariable]:
        """Extract all variables from workflow with scope information."""
        variables = []
        
        # Find all Variable elements throughout the tree
        for elem in root.iter():
            if VariableExtractor._is_variable_element(elem):
                variable = VariableExtractor._extract_single_variable(elem)
                if variable:
                    variables.append(variable)
        
        return variables
    
    @staticmethod
    def _is_variable_element(elem: ET.Element) -> bool:
        """Check if element represents a variable definition."""
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        return (
            tag == 'Variable' or
            tag.endswith('Variable') or
            'Variable' in tag
        )
    
    @staticmethod
    def _extract_single_variable(elem: ET.Element) -> Optional[WorkflowVariable]:
        """Extract single variable from Variable element."""
        name = elem.get('Name')
        if not name:
            return None
        
        type_attr = elem.get('Type', 'Object')
        default_value = elem.get('Default') or elem.text
        
        # Determine scope from parent context
        scope = VariableExtractor._determine_scope(elem)
        
        return WorkflowVariable(
            name=name,
            type=type_attr,
            default_value=default_value,
            scope=scope
        )
    
    @staticmethod
    def _determine_scope(elem: ET.Element) -> str:
        """Determine variable scope from parent context."""
        parent = elem.getparent() if hasattr(elem, 'getparent') else None
        if parent is not None:
            parent_tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
            if parent_tag in CORE_VISUAL_ACTIVITIES:
                return parent_tag
        return "workflow"


class ActivityExtractor:
    """Extracts activity information with complete metadata."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with parser configuration."""
        self.config = config
        self._activity_counter = 0
        self._activity_cache = {}  # Cache for repeated element processing
        self._expression_cache = {}  # Cache for expression extraction
        self._max_depth = config.get('max_depth', 50)  # Prevent deep recursion
        self._batch_size = config.get('batch_size', 100)  # Process activities in batches
    
    def extract_activities(self, root: ET.Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract all activities with complete metadata."""
        activities = []
        self._activity_counter = 0
        
        def process_element(elem: ET.Element, parent_id: Optional[str] = None, depth: int = 0):
            """Recursively process elements to find activities."""
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Skip non-activity elements but continue processing children
            if tag_name in SKIP_ELEMENTS:
                for child in elem:
                    process_element(child, parent_id, depth)
                return
            
            # Check if this is an activity
            if self._is_activity(elem, tag_name):
                activity_data = self._extract_single_activity(elem, tag_name, namespaces, parent_id, depth)
                activities.append(activity_data)
                
                # Process children with this activity as parent
                activity_id = activity_data['activity_id']
                for child in elem:
                    process_element(child, activity_id, depth + 1)
                
                # Update parent-child relationships
                self._update_parent_child_relationships(activities, parent_id, activity_id)
            else:
                # Not an activity, but process children
                for child in elem:
                    process_element(child, parent_id, depth)
        
        process_element(root)
        return activities
    
    def _is_activity(self, elem: ET.Element, tag_name: str) -> bool:
        """Determine if element represents an activity."""
        # Check whitelist first
        if tag_name in CORE_VISUAL_ACTIVITIES:
            return True
        
        # Check for activity-like attributes
        activity_attributes = {'DisplayName', 'Result', 'Value', 'Text', 'Message', 'Level'}
        if any(attr in elem.attrib for attr in activity_attributes):
            return True
        
        # Check for annotation (activities can have annotations)
        if any('Annotation.AnnotationText' in attr for attr in elem.attrib):
            return True
        
        # Check namespace (UiPath activities)
        if elem.tag.startswith('{http://schemas.uipath.com/workflow/activities}'):
            return True
        
        # Check for child activities (container activities)
        child_tags = {child.tag.split('}')[-1] for child in elem}
        if child_tags & CORE_VISUAL_ACTIVITIES:
            return True
        
        return False
    
    def _extract_single_activity(
        self, 
        elem: ET.Element, 
        tag_name: str, 
        namespaces: Dict[str, str], 
        parent_id: Optional[str], 
        depth: int
    ) -> Dict[str, Any]:
        """Extract complete metadata from single activity."""
        self._activity_counter += 1
        activity_id = f"activity_{self._activity_counter}"
        
        # Categorize attributes
        visible_attrs, invisible_attrs = self._categorize_attributes(elem.attrib)
        
        # Extract annotation
        annotation = self._extract_annotation(elem, namespaces.get('sap2010', ''))
        
        # Extract nested configuration
        configuration = self._extract_configuration(elem)
        
        # Extract activity-scoped variables
        variables = self._extract_activity_variables(elem, activity_id)
        
        # Extract expressions
        expressions = []
        if self.config.get('extract_expressions', True):
            expressions = self._extract_expressions(elem)
        
        return {
            'tag': tag_name,
            'activity_id': activity_id,
            'display_name': elem.get('DisplayName'),
            'annotation': annotation,
            'visible_attributes': visible_attrs,
            'invisible_attributes': invisible_attrs,
            'configuration': configuration,
            'variables': variables,
            'expressions': expressions,
            'parent_activity_id': parent_id,
            'child_activities': [],
            'depth_level': depth,
            'xpath_location': self._get_xpath_location(elem)
        }
    
    def _categorize_attributes(self, attrib: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Categorize attributes into visible and invisible."""
        visible = {}
        invisible = {}
        
        # Define invisible patterns
        invisible_patterns = {
            'ViewState', 'HintSize', 'IdRef', 'VirtualizedContainerService',
            'WorkflowViewState', 'Annotation.AnnotationText'
        }
        
        for key, value in attrib.items():
            clean_key = key.split('}')[-1] if '}' in key else key
            
            # Check if attribute is invisible/technical
            is_invisible = any(pattern in key for pattern in invisible_patterns)
            
            if is_invisible:
                invisible[key] = value
            else:
                visible[key] = value
        
        return visible, invisible
    
    def _extract_annotation(self, elem: ET.Element, sap2010_ns: str) -> Optional[str]:
        """Extract annotation text from activity."""
        if not sap2010_ns:
            return None
        
        annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"
        annotation = elem.get(annotation_attr)
        
        if annotation:
            return html.unescape(annotation)
        
        return None
    
    def _extract_configuration(self, elem: ET.Element) -> Dict[str, Any]:
        """Extract nested configuration from activity."""
        config = {}
        
        for child in elem:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            # Skip variables (handled separately)
            if child_tag.endswith('Variable'):
                continue
            
            # Extract nested structure
            if len(child) > 0:
                config[child_tag] = self._extract_nested_element(child)
            else:
                # Simple value or attributes only
                if child.attrib and child.text:
                    config[child_tag] = {'attributes': child.attrib, 'text': child.text}
                elif child.attrib:
                    config[child_tag] = child.attrib
                else:
                    config[child_tag] = child.text
        
        return config
    
    def _extract_nested_element(self, elem: ET.Element) -> Any:
        """Recursively extract nested element structure."""
        if len(elem) == 0:
            # Leaf node
            if elem.attrib and elem.text:
                return {'attributes': elem.attrib, 'text': elem.text}
            elif elem.attrib:
                return elem.attrib
            else:
                return elem.text
        
        # Has children
        result = {}
        if elem.attrib:
            result['attributes'] = elem.attrib
        
        children = {}
        for child in elem:
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            children[child_tag] = self._extract_nested_element(child)
        
        if children:
            result['children'] = children
        
        return result
    
    def _extract_activity_variables(self, elem: ET.Element, activity_id: str) -> List[WorkflowVariable]:
        """Extract variables scoped to this activity."""
        variables = []
        
        for child in elem:
            if child.tag.endswith('Variable'):
                name = child.get('Name')
                if name:
                    var = WorkflowVariable(
                        name=name,
                        type=child.get('Type', 'Object'),
                        default_value=child.get('Default') or child.text,
                        scope=activity_id
                    )
                    variables.append(var)
        
        return variables
    
    def _extract_expressions(self, elem: ET.Element) -> List[Expression]:
        """Extract expressions from activity element."""
        expressions = []
        
        # Check attributes for expressions
        for key, value in elem.attrib.items():
            if self._is_expression(value):
                expr = Expression(
                    content=value,
                    expression_type=self._classify_expression(key),
                    language=self.config.get('expression_language', 'VisualBasic'),
                    context=key
                )
                expressions.append(expr)
        
        # Check text content
        if elem.text and self._is_expression(elem.text):
            expr = Expression(
                content=elem.text.strip(),
                expression_type='text_content',
                language=self.config.get('expression_language', 'VisualBasic'),
                context='text'
            )
            expressions.append(expr)
        
        return expressions
    
    def _is_expression(self, text: str) -> bool:
        """Check if text contains expression patterns."""
        if not text or len(text.strip()) < 2:
            return False
        
        return any(pattern in text for pattern in EXPRESSION_PATTERNS)
    
    def _classify_expression(self, context: str) -> str:
        """Classify expression type based on context."""
        context_lower = context.lower()
        
        if 'condition' in context_lower:
            return 'condition'
        elif any(term in context_lower for term in ['value', 'result', 'assign']):
            return 'assignment'
        elif any(term in context_lower for term in ['message', 'text', 'caption']):
            return 'message'
        elif 'timeout' in context_lower:
            return 'timeout'
        else:
            return 'general'
    
    def _get_xpath_location(self, elem: ET.Element) -> str:
        """Generate XPath-like location string for debugging."""
        # Simplified approach - just use the tag name
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        return f"/{tag}"
    
    def _update_parent_child_relationships(self, activities: List[Dict[str, Any]], parent_id: Optional[str], child_id: str):
        """Update parent-child relationships in activities list."""
        if not parent_id:
            return
        
        for activity in activities:
            if activity['activity_id'] == parent_id:
                activity['child_activities'].append(child_id)
                break
    
    def extract_activity_instances(self, root: ET.Element, namespaces: Dict[str, str], 
                                  workflow_id: str, project_id: str) -> List[Activity]:
        """Extract all activity instances with complete business logic configurations.
        
        This method implements the ActivityInstance extraction as specified in ADR-009,
        extracting the complete business logic from each activity for MCP/LLM consumption.
        
        Args:
            root: Root XML element of workflow
            namespaces: XML namespaces dictionary  
            workflow_id: Workflow identifier for activity IDs
            project_id: Project identifier for activity IDs
            
        Returns:
            List of Activity instances with complete business logic extraction
        """
        activities = []
        self._activity_counter = 0
        
        # Use visibility filtering for real business logic activities
        # Pre-compute visible activities once for performance
        visible_activities = get_visible_elements(root)
        
        # Pre-compute common namespace lookups for performance
        self._namespace_cache = self._precompute_namespace_cache(namespaces)
        
        def process_element(elem: ET.Element, parent_activity_id: Optional[str] = None, 
                          depth: int = 0, node_path: str = "Activity") -> None:
            """Recursively process visible elements to extract activities."""
            # Performance: Early depth check to prevent stack overflow
            if depth > self._max_depth:
                return
                
            if not is_visible_element(elem):
                # Skip invisible elements, but continue with children
                for child in elem:
                    process_element(child, parent_activity_id, depth, node_path)
                return
            
            # Performance: Check cache first
            element_id = id(elem)
            cache_key = (element_id, workflow_id, project_id, parent_activity_id, depth, node_path)
            if cache_key in self._activity_cache:
                cached_activity = self._activity_cache[cache_key]
                if cached_activity:
                    activities.append(cached_activity)
                return
            
            activity = self._extract_single_activity_instance(
                elem, namespaces, workflow_id, project_id, 
                parent_activity_id, depth, node_path
            )
            
            # Cache the result
            self._activity_cache[cache_key] = activity
            
            if activity:
                activities.append(activity)
                current_activity_id = activity.activity_id
                
                # Performance: Process children in batches if there are many
                children = list(elem)
                if len(children) > self._batch_size:
                    # Process large numbers of children in smaller batches
                    for i in range(0, len(children), self._batch_size):
                        batch = children[i:i + self._batch_size]
                        for child_index, child in enumerate(batch, start=i):
                            child_tag = get_local_tag(child)
                            child_node_path = f"{node_path}/{child_tag}"
                            if child_index > 0:
                                child_node_path += f"_{child_index}"
                            
                            process_element(child, current_activity_id, depth + 1, child_node_path)
                else:
                    # Process normally for smaller numbers of children
                    child_index = 0
                    for child in children:
                        child_tag = get_local_tag(child)
                        child_node_path = f"{node_path}/{child_tag}"
                        if child_index > 0:
                            child_node_path += f"_{child_index}"
                        
                        process_element(child, current_activity_id, depth + 1, child_node_path)
                        child_index += 1
        
        process_element(root)
        return activities
    
    def _extract_single_activity_instance(self, element: ET.Element, namespaces: Dict[str, str],
                                        workflow_id: str, project_id: str,
                                        parent_activity_id: Optional[str], depth: int,
                                        node_path: str) -> Optional[Activity]:
        """Extract complete configuration from single activity element.
        
        Implements complete business logic extraction as specified in ADR-009.
        """
        self._activity_counter += 1
        activity_type = get_local_tag(element)
        node_id = f"{node_path}_{self._activity_counter}"
        
        # Extract all attributes as arguments and properties
        arguments = self._extract_activity_arguments(element)
        properties = self._extract_visible_properties(element)
        metadata = self._extract_activity_metadata(element)
        
        # Extract nested configuration objects
        configuration = self._extract_nested_configuration(element)
        
        # Extract business logic expressions
        expressions = self._extract_business_logic_expressions(element)
        
        # Extract variables referenced in expressions and arguments
        variables_referenced = self._extract_variable_references(element, expressions, arguments)
        
        # Extract selectors for UI activities
        selectors = ActivityUtils.extract_selectors_from_config(configuration)
        
        # Extract annotation
        annotation = self._extract_annotation(element, namespaces.get('sap2010', ''))
        
        # Generate stable activity ID with content hashing
        activity_content = self._serialize_activity_for_hashing(
            activity_type, arguments, configuration, properties, metadata
        )
        activity_id = ActivityUtils.generate_activity_id(
            project_id, workflow_id, node_id, activity_content
        )
        
        # Determine visibility and container type
        is_visible = element in get_visible_elements(element.getroot() if hasattr(element, 'getroot') else element)
        container_type = self._determine_container_type(element)
        
        return Activity(
            activity_id=activity_id,
            workflow_id=workflow_id,
            activity_type=activity_type,
            display_name=element.get('DisplayName'),
            node_id=node_id,
            parent_activity_id=parent_activity_id,
            depth=depth,
            arguments=arguments,
            configuration=configuration,
            properties=properties,
            metadata=metadata,
            expressions=expressions,
            variables_referenced=variables_referenced,
            selectors=selectors,
            annotation=annotation,
            is_visible=is_visible,
            container_type=container_type,
            # Legacy fields for backward compatibility
            visible_attributes=properties,  # Map to legacy field
            invisible_attributes=metadata,  # Map to legacy field
            variables=[],  # Will be populated by workflow-level variable extraction
            child_activities=[],  # Will be populated by hierarchy analysis
            expression_objects=[],  # Legacy detailed expression objects
            xpath_location=self._get_xpath_location(element),
            source_line=None  # Could be implemented with line number tracking
        )
    
    def _extract_activity_arguments(self, element: ET.Element) -> Dict[str, Any]:
        """Extract all activity arguments from attributes and nested elements."""
        arguments = {}
        
        # Extract from XML attributes (direct arguments)
        for attr_name, attr_value in element.attrib.items():
            # Skip namespace declarations and technical attributes
            if not (attr_name.startswith('xmlns') or 
                    'ViewState' in attr_name or 
                    'HintSize' in attr_name or
                    'IdRef' in attr_name):
                clean_name = attr_name.split('}')[-1] if '}' in attr_name else attr_name
                arguments[clean_name] = attr_value
        
        return arguments
    
    def _extract_visible_properties(self, element: ET.Element) -> Dict[str, Any]:
        """Extract visible properties (user-facing business logic)."""
        properties = {}
        
        # Business logic properties (not technical metadata)
        business_logic_attrs = [
            'DisplayName', 'Value', 'Text', 'Message', 'Level', 'Result', 
            'Condition', 'Expression', 'AssetName', 'QueueName', 'FilePath',
            'WorkbookPath', 'SheetName', 'Range', 'ActivateBefore', 'ClickType',
            'DelayAfter', 'DelayBefore', 'TimeoutMS', 'WaitForReady', 'ContinueOnError'
        ]
        
        for attr_name, attr_value in element.attrib.items():
            clean_name = attr_name.split('}')[-1] if '}' in attr_name else attr_name
            if clean_name in business_logic_attrs:
                properties[clean_name] = attr_value
        
        return properties
    
    def _extract_activity_metadata(self, element: ET.Element) -> Dict[str, Any]:
        """Extract technical metadata (ViewState, IdRef, etc.)."""
        metadata = {}
        
        # Technical metadata attributes
        metadata_attrs = [
            'ViewState', 'HintSize', 'IdRef', 'VirtualizedContainerService'
        ]
        
        for attr_name, attr_value in element.attrib.items():
            clean_name = attr_name.split('}')[-1] if '}' in attr_name else attr_name
            if any(meta_attr in attr_name for meta_attr in metadata_attrs):
                metadata[attr_name] = attr_value
        
        return metadata
    
    def _extract_nested_configuration(self, element: ET.Element) -> Dict[str, Any]:
        """Extract nested configuration objects from activity element."""
        configuration = {}
        
        for child in element:
            child_tag = get_local_tag(child)
            
            # Skip variables (handled separately)
            if child_tag.endswith('Variable'):
                continue
            
            # Extract nested structure
            if len(child) > 0:
                configuration[child_tag] = self._extract_nested_element(child)
            else:
                # Simple value or attributes only
                if child.attrib and child.text:
                    configuration[child_tag] = {'attributes': child.attrib, 'text': child.text}
                elif child.attrib:
                    configuration[child_tag] = child.attrib
                else:
                    configuration[child_tag] = child.text
        
        return configuration
    
    def _extract_nested_element(self, elem: ET.Element) -> Any:
        """Recursively extract nested element structure."""
        if len(elem) == 0:
            # Leaf node
            if elem.attrib and elem.text:
                return {'attributes': elem.attrib, 'text': elem.text}
            elif elem.attrib:
                return elem.attrib
            else:
                return elem.text
        
        # Has children
        result = {}
        if elem.attrib:
            result['attributes'] = elem.attrib
        
        children = {}
        for child in elem:
            child_tag = get_local_tag(child)
            children[child_tag] = self._extract_nested_element(child)
        
        if children:
            result['children'] = children
        
        return result
    
    def _extract_business_logic_expressions(self, element: ET.Element) -> List[str]:
        """Extract UiPath expressions containing business logic."""
        expressions = []
        
        # Extract from all attribute values
        for attr_value in element.attrib.values():
            extracted_expressions = ActivityUtils.extract_expressions_from_text(attr_value)
            expressions.extend(extracted_expressions)
        
        # Extract from element text content
        if element.text:
            extracted_expressions = ActivityUtils.extract_expressions_from_text(element.text)
            expressions.extend(extracted_expressions)
        
        return list(set(expressions))  # Remove duplicates
    
    def _extract_variable_references(self, element: ET.Element, expressions: List[str], 
                                   arguments: Dict[str, Any]) -> List[str]:
        """Extract variable references from expressions and arguments."""
        variables = []
        
        # Extract from expressions
        for expr in expressions:
            vars_in_expr = ActivityUtils.extract_variable_references(expr)
            variables.extend(vars_in_expr)
        
        # Extract from argument values
        for arg_value in arguments.values():
            if isinstance(arg_value, str):
                vars_in_arg = ActivityUtils.extract_variable_references(arg_value)
                variables.extend(vars_in_arg)
        
        return list(set(variables))  # Remove duplicates
    
    def _serialize_activity_for_hashing(self, activity_type: str, arguments: Dict[str, Any],
                                      configuration: Dict[str, Any], properties: Dict[str, Any],
                                      metadata: Dict[str, Any]) -> str:
        """Serialize activity data for content hashing."""
        # Create a deterministic representation for hashing
        hash_data = {
            'type': activity_type,
            'arguments': sorted(arguments.items()) if arguments else [],
            'properties': sorted(properties.items()) if properties else [],
            # Include only stable parts of configuration and metadata
            'config_keys': sorted(configuration.keys()) if configuration else [],
        }
        
        # Convert to string for hashing (exclude metadata for stability)
        return str(hash_data)
    
    def _determine_container_type(self, element: ET.Element) -> Optional[str]:
        """Determine parent container type."""
        parent = element.getparent() if hasattr(element, 'getparent') else None
        if parent is not None:
            return get_local_tag(parent)
        return None
    
    def _precompute_namespace_cache(self, namespaces: Dict[str, str]) -> Dict[str, str]:
        """Pre-compute commonly used namespace lookups for performance."""
        cache = {}
        
        # Cache common namespace patterns
        for prefix, uri in namespaces.items():
            if 'sap2010' in prefix:
                cache['sap2010'] = uri
            elif 'uipath' in uri.lower():
                cache['uipath'] = uri
            elif 'xaml' in prefix or prefix == 'x':
                cache['xaml'] = uri
        
        return cache


class AnnotationExtractor:
    """Extracts annotations and documentation from workflows."""
    
    @staticmethod
    def extract_root_annotation(root: ET.Element, namespaces: Dict[str, str]) -> Optional[str]:
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
    
    @staticmethod
    def extract_all_annotations(root: ET.Element, namespaces: Dict[str, str]) -> Dict[str, str]:
        """Extract all annotations mapped by element ID or path."""
        annotations = {}
        sap2010_ns = namespaces.get('sap2010', '')
        
        if not sap2010_ns:
            return annotations
        
        annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"
        
        for elem in root.iter():
            annotation = elem.get(annotation_attr)
            if annotation:
                # Use element ID if available, otherwise generate path
                elem_id = elem.get('Id') or elem.get('sap2010:WorkflowViewState.IdRef')
                if not elem_id:
                    elem_id = f"element_{id(elem)}"
                
                annotations[elem_id] = html.unescape(annotation)
        
        return annotations


class MetadataExtractor:
    """Extracts technical metadata from workflows."""
    
    @staticmethod
    def extract_namespaces(root: ET.Element) -> Dict[str, str]:
        """Extract all XML namespaces."""
        namespaces = {}
        
        for key, value in root.attrib.items():
            if key.startswith('xmlns:'):
                prefix = key[6:]
                namespaces[prefix] = value
            elif key == 'xmlns':
                namespaces[''] = value
        
        return namespaces
    
    @staticmethod
    def extract_assembly_references(root: ET.Element) -> List[str]:
        """Extract assembly references."""
        references = []
        
        for elem in root.iter():
            if elem.tag.endswith('AssemblyReference'):
                ref = elem.text or elem.get('Assembly')
                if ref:
                    references.append(ref)
        
        return references
    
    @staticmethod
    def extract_expression_language(root: ET.Element, default: str = 'VisualBasic') -> str:
        """Extract expression language setting."""
        # Check root attributes
        lang = root.get('ExpressionActivityEditor')
        if lang:
            return 'CSharp' if 'CSharp' in lang else 'VisualBasic'
        
        # Check for language-specific elements
        for elem in root.iter():
            if 'VisualBasic' in elem.tag:
                return 'VisualBasic'
            elif 'CSharp' in elem.tag:
                return 'CSharp'
        
        return default