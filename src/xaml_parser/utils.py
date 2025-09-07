"""Utility functions for XAML parsing operations.

This module provides helper functions for common parsing tasks,
data validation, and text processing operations.
"""

import hashlib
import html
import re
from typing import Any, Dict, List, Optional, Set, Union
import xml.etree.ElementTree as ET


class XmlUtils:
    """XML processing utilities."""
    
    @staticmethod
    def safe_parse(content: str, encoding: str = 'utf-8') -> Optional[ET.Element]:
        """Safely parse XML content with error handling.
        
        Args:
            content: Raw XML string
            encoding: Text encoding to use
            
        Returns:
            Parsed root element or None if parsing failed
        """
        try:
            return ET.fromstring(content)
        except ET.ParseError:
            # Try with encoding declaration removed
            try:
                # Remove XML declaration that might have wrong encoding
                clean_content = re.sub(r'<\?xml[^>]*\?>', '', content, 1)
                return ET.fromstring(clean_content)
            except ET.ParseError:
                return None
    
    @staticmethod
    def get_element_text(elem: ET.Element, default: str = "") -> str:
        """Get element text content safely.
        
        Args:
            elem: XML element
            default: Default value if no text
            
        Returns:
            Element text or default value
        """
        return elem.text.strip() if elem.text else default
    
    @staticmethod
    def find_elements_by_attribute(root: ET.Element, attr_name: str, attr_value: str = None) -> List[ET.Element]:
        """Find all elements with specific attribute.
        
        Args:
            root: Root element to search from
            attr_name: Attribute name to search for
            attr_value: Specific attribute value (None = any value)
            
        Returns:
            List of matching elements
        """
        matches = []
        for elem in root.iter():
            if attr_name in elem.attrib:
                if attr_value is None or elem.get(attr_name) == attr_value:
                    matches.append(elem)
        return matches
    
    @staticmethod
    def get_namespace_prefix(tag: str) -> Optional[str]:
        """Extract namespace prefix from qualified tag name.
        
        Args:
            tag: Tag name (possibly namespaced)
            
        Returns:
            Namespace prefix or None
        """
        if '}' in tag:
            namespace = tag.split('}')[0][1:]  # Remove { and }
            return namespace
        return None
    
    @staticmethod
    def get_local_name(tag: str) -> str:
        """Extract local name from qualified tag.
        
        Args:
            tag: Tag name (possibly namespaced)
            
        Returns:
            Local tag name without namespace
        """
        return tag.split('}')[-1] if '}' in tag else tag


class TextUtils:
    """Text processing utilities."""
    
    @staticmethod
    def clean_annotation(text: str) -> str:
        """Clean annotation text by decoding HTML entities and normalizing whitespace.
        
        Args:
            text: Raw annotation text
            
        Returns:
            Cleaned annotation text
        """
        if not text:
            return ""
        
        # Decode HTML entities
        cleaned = html.unescape(text)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        # Convert HTML line breaks
        cleaned = cleaned.replace('&#xA;', '\n').replace('&#xa;', '\n')
        cleaned = cleaned.replace('<br>', '\n').replace('<br/>', '\n')
        
        return cleaned
    
    @staticmethod
    def extract_type_name(type_signature: str) -> str:
        """Extract simple type name from full .NET type signature.
        
        Args:
            type_signature: Full type signature like 'InArgument(x:String)'
            
        Returns:
            Simple type name like 'String'
        """
        if not type_signature:
            return "Object"
        
        # Extract from generic type syntax: Type(InnerType)
        match = re.search(r'\(([^)]+)\)', type_signature)
        if match:
            inner_type = match.group(1)
            # Remove namespace prefix if present
            if ':' in inner_type:
                inner_type = inner_type.split(':')[-1]
            return inner_type
        
        # Remove namespace prefix
        if ':' in type_signature:
            return type_signature.split(':')[-1]
        
        return type_signature
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize file path to POSIX format.
        
        Args:
            path: File path (Windows or POSIX)
            
        Returns:
            POSIX-normalized path
        """
        return path.replace('\\', '/') if path else ""
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated text with suffix if needed
        """
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix


class ValidationUtils:
    """Validation and data quality utilities."""
    
    @staticmethod
    def validate_workflow_content(content: Dict[str, Any]) -> List[str]:
        """Validate workflow content structure and data quality.
        
        Args:
            content: Workflow content dictionary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required fields
        required_fields = ['arguments', 'variables', 'activities']
        for field in required_fields:
            if field not in content:
                errors.append(f"Missing required field: {field}")
        
        # Validate arguments
        if 'arguments' in content:
            arg_errors = ValidationUtils._validate_arguments(content['arguments'])
            errors.extend(arg_errors)
        
        # Validate activities
        if 'activities' in content:
            activity_errors = ValidationUtils._validate_activities(content['activities'])
            errors.extend(activity_errors)
        
        return errors
    
    @staticmethod
    def _validate_arguments(arguments: List[Dict[str, Any]]) -> List[str]:
        """Validate argument definitions."""
        errors = []
        names = set()
        
        for i, arg in enumerate(arguments):
            # Check required fields
            if 'name' not in arg or not arg['name']:
                errors.append(f"Argument {i}: Missing or empty name")
            else:
                # Check for duplicates
                name = arg['name']
                if name in names:
                    errors.append(f"Argument {i}: Duplicate name '{name}'")
                names.add(name)
            
            # Validate direction
            if 'direction' in arg:
                valid_directions = {'in', 'out', 'inout'}
                if arg['direction'] not in valid_directions:
                    errors.append(f"Argument {i}: Invalid direction '{arg['direction']}'")
        
        return errors
    
    @staticmethod
    def _validate_activities(activities: List[Dict[str, Any]]) -> List[str]:
        """Validate activity definitions."""
        errors = []
        activity_ids = set()
        
        for i, activity in enumerate(activities):
            # Check required fields
            if 'activity_id' not in activity or not activity['activity_id']:
                errors.append(f"Activity {i}: Missing activity_id")
            else:
                # Check for duplicate IDs
                activity_id = activity['activity_id']
                if activity_id in activity_ids:
                    errors.append(f"Activity {i}: Duplicate activity_id '{activity_id}'")
                activity_ids.add(activity_id)
            
            if 'tag' not in activity or not activity['tag']:
                errors.append(f"Activity {i}: Missing tag")
        
        return errors
    
    @staticmethod
    def is_valid_expression(text: str) -> bool:
        """Check if text appears to be a valid expression.
        
        Args:
            text: Text to validate
            
        Returns:
            True if text looks like a valid expression
        """
        if not text or len(text.strip()) < 2:
            return False
        
        # Common expression patterns
        expression_indicators = [
            r'\[.*\]',  # VB.NET expressions in brackets
            r'New\s+\w+',  # Object creation
            r'\w+\.\w+',  # Method/property access
            r'\w+\s*[+\-*/]\s*\w+',  # Arithmetic
            r'If\s*\(',  # VB.NET If function
            r'\w+\s*=\s*',  # Assignment-like
            r'\.ToString\(\)',  # Common method call
        ]
        
        text_clean = text.strip()
        return any(re.search(pattern, text_clean) for pattern in expression_indicators)


class DataUtils:
    """Data structure and conversion utilities."""
    
    @staticmethod
    def merge_dictionaries(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two dictionaries with deep merging of nested dicts.
        
        Args:
            dict1: First dictionary
            dict2: Second dictionary (takes precedence)
            
        Returns:
            Merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.merge_dictionaries(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def flatten_nested_dict(nested_dict: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary structure.
        
        Args:
            nested_dict: Dictionary with nested structure
            separator: Separator for flattened keys
            
        Returns:
            Flattened dictionary
        """
        def _flatten(obj: Any, parent_key: str = '') -> Dict[str, Any]:
            items = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}{separator}{key}" if parent_key else key
                    items.extend(_flatten(value, new_key).items())
            else:
                return {parent_key: obj}
            
            return dict(items)
        
        return _flatten(nested_dict)
    
    @staticmethod
    def extract_unique_values(data: List[Dict[str, Any]], field: str) -> Set[str]:
        """Extract unique values for a field from list of dictionaries.
        
        Args:
            data: List of dictionaries
            field: Field name to extract
            
        Returns:
            Set of unique values
        """
        values = set()
        for item in data:
            if field in item and item[field]:
                if isinstance(item[field], (list, tuple)):
                    values.update(str(v) for v in item[field])
                else:
                    values.add(str(item[field]))
        return values
    
    @staticmethod
    def group_by_field(data: List[Dict[str, Any]], field: str) -> Dict[str, List[Dict[str, Any]]]:
        """Group list of dictionaries by field value.
        
        Args:
            data: List of dictionaries
            field: Field to group by
            
        Returns:
            Dictionary with field values as keys and lists as values
        """
        groups = {}
        for item in data:
            key = str(item.get(field, 'unknown'))
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return groups


class DebugUtils:
    """Debugging and diagnostic utilities."""
    
    @staticmethod
    def element_info(elem: ET.Element) -> Dict[str, Any]:
        """Get diagnostic information about XML element.
        
        Args:
            elem: XML element
            
        Returns:
            Dictionary with element information
        """
        return {
            'tag': elem.tag,
            'local_name': XmlUtils.get_local_name(elem.tag),
            'namespace': XmlUtils.get_namespace_prefix(elem.tag),
            'attributes': dict(elem.attrib),
            'text': elem.text.strip() if elem.text else None,
            'children_count': len(elem),
            'child_tags': [XmlUtils.get_local_name(child.tag) for child in elem]
        }
    
    @staticmethod
    def summarize_parsing_stats(content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate parsing statistics summary.
        
        Args:
            content: Parsed workflow content
            
        Returns:
            Statistics summary
        """
        stats = {
            'total_arguments': len(content.get('arguments', [])),
            'total_variables': len(content.get('variables', [])),
            'total_activities': len(content.get('activities', [])),
            'total_namespaces': len(content.get('namespaces', {})),
            'has_root_annotation': bool(content.get('root_annotation')),
            'expression_language': content.get('expression_language', 'Unknown')
        }
        
        # Activity type distribution
        activities = content.get('activities', [])
        if activities:
            activity_types = {}
            for activity in activities:
                tag = activity.get('tag', 'Unknown')
                activity_types[tag] = activity_types.get(tag, 0) + 1
            stats['activity_types'] = activity_types
        
        # Argument directions
        arguments = content.get('arguments', [])
        if arguments:
            directions = {}
            for arg in arguments:
                direction = arg.get('direction', 'unknown')
                directions[direction] = directions.get(direction, 0) + 1
            stats['argument_directions'] = directions
        
        return stats


class ActivityUtils:
    """Activity-specific utilities for business logic extraction."""
    
    @staticmethod
    def generate_activity_id(project_id: str, workflow_path: str, node_id: str, 
                            activity_content: str) -> str:
        """Generate stable activity identifier with content hash.
        
        Args:
            project_id: Project identifier or slug
            workflow_path: Path to workflow file
            node_id: Hierarchical node identifier
            activity_content: Serialized activity content for hashing
            
        Returns:
            Stable activity ID in format: {projectId}#{workflowId}#{nodeId}#{contentHash}
        
        Examples:
            f4aa3834#Process/Calculator/ClickListOfCharacters#Activity/Sequence/ForEach/Sequence/NApplicationCard/Sequence/If/Sequence/NClick#abc123ef
            frozenchlorine-1082950b#StandardCalculator#Activity/Sequence/InvokeWorkflowFile_5#def456ab
        """
        # Generate content hash
        content_hash = hashlib.sha256(activity_content.encode()).hexdigest()[:8]
        
        # Normalize workflow ID (POSIX paths, remove .xaml extension)
        workflow_id = workflow_path.replace("\\", "/").replace(".xaml", "")
        
        # Construct stable activity ID
        return f"{project_id}#{workflow_id}#{node_id}#{content_hash}"
    
    @staticmethod
    def extract_expressions_from_text(text: str) -> List[str]:
        """Extract UiPath expressions from text content.
        
        Args:
            text: Text content that may contain expressions
            
        Returns:
            List of extracted expressions
        """
        if not text:
            return []
        
        expressions = []
        
        # Pattern for VB.NET expressions in brackets [...]
        vb_expressions = re.findall(r'\[([^\]]+)\]', text)
        expressions.extend(vb_expressions)
        
        # Pattern for method calls
        method_calls = re.findall(r'\w+\.\w+\([^)]*\)', text)
        expressions.extend(method_calls)
        
        # Pattern for string.Format calls
        format_calls = re.findall(r'string\.Format\([^)]+\)', text, re.IGNORECASE)
        expressions.extend(format_calls)
        
        return list(set(expressions))  # Remove duplicates
    
    @staticmethod
    def extract_variable_references(text: str) -> List[str]:
        """Extract variable references from expressions.
        
        Args:
            text: Expression or text content
            
        Returns:
            List of variable names referenced
        """
        if not text:
            return []
        
        variables = []
        
        # Common variable patterns in UiPath expressions
        # Variables in brackets: [variableName]
        bracket_vars = re.findall(r'\[([a-zA-Z_]\w*)\]', text)
        variables.extend(bracket_vars)
        
        # Variables in expressions: variableName.Method or variableName(...).property
        # Handle both direct property access and method call property access
        var_refs = re.findall(r'([a-zA-Z_]\w*)(?:\([^)]*\))?\.', text)
        variables.extend(var_refs)
        
        # Variables in assignments (not comparisons)
        assignment_vars = re.findall(r'([a-zA-Z_]\w*)\s*=(?!=)', text)  # = but not ==
        variables.extend(assignment_vars)
        
        # Variables as standalone identifiers (function parameters, etc.)
        # Look for variables that appear after commas or parentheses but aren't method calls
        standalone_vars = re.findall(r'[,(]\s*([a-zA-Z_]\w*)(?![.(])', text)
        variables.extend(standalone_vars)
        
        # Filter out common method names and keywords
        filtered_vars = []
        excluded_names = {
            'string', 'String', 'DateTime', 'Convert', 'Path', 'File', 'Directory',
            'System', 'Microsoft', 'UiPath', 'New', 'True', 'False', 'Nothing',
            'If', 'Then', 'Else', 'End', 'For', 'Each', 'While', 'Do', 'Loop'
        }
        
        for var in variables:
            if var not in excluded_names and len(var) > 1:
                filtered_vars.append(var)
        
        return list(set(filtered_vars))  # Remove duplicates
    
    @staticmethod
    def extract_selectors_from_config(configuration: Dict[str, Any]) -> Dict[str, str]:
        """Extract UI selectors from activity configuration.
        
        Args:
            configuration: Activity configuration dictionary
            
        Returns:
            Dictionary mapping selector types to selector strings
        """
        selectors = {}
        
        # Common selector fields in UiPath activities
        selector_fields = [
            'FullSelector', 'FuzzySelector', 'Selector', 'TargetSelector',
            'FullSelectorArgument', 'FuzzySelectorArgument', 'TargetAnchorable'
        ]
        
        def _extract_from_dict(data: Any, path: str = '') -> None:
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if key in selector_fields and isinstance(value, str):
                        selectors[current_path] = value
                    else:
                        _extract_from_dict(value, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    _extract_from_dict(item, f"{path}[{i}]")
        
        _extract_from_dict(configuration)
        return selectors
    
    @staticmethod
    def classify_activity_type(activity_type: str) -> str:
        """Classify activity type into categories.
        
        Args:
            activity_type: Activity type name
            
        Returns:
            Activity category
        """
        activity_type_lower = activity_type.lower()
        
        # UI Automation activities - use more specific patterns to avoid false matches
        ui_patterns = [
            'click', 'typetext', 'typeinto', 'gettext', 'getfulltext', 'getvalue',
            'find', 'wait', 'hover', 'drag', 'select', 'image', 'application'
        ]
        if any(ui_pattern in activity_type_lower for ui_pattern in ui_patterns):
            return 'ui_automation'
        
        # Flow control activities
        if any(flow_term in activity_type_lower for flow_term in [
            'sequence', 'if', 'switch', 'while', 'foreach', 'parallel', 'flowchart'
        ]):
            return 'flow_control'
        
        # Data activities
        if any(data_term in activity_type_lower for data_term in [
            'assign', 'invoke', 'data', 'read', 'write', 'build', 'filter'
        ]):
            return 'data_processing'
        
        # System activities
        if any(sys_term in activity_type_lower for sys_term in [
            'log', 'message', 'delay', 'kill', 'start', 'environment'
        ]):
            return 'system'
        
        # Exception handling
        if any(exc_term in activity_type_lower for exc_term in [
            'try', 'catch', 'throw', 'rethrow', 'finally'
        ]):
            return 'exception_handling'
        
        return 'other'