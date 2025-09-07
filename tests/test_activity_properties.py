#!/usr/bin/env python3
"""Test comprehensive activity property extraction from complex UiPath XAML."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List


def extract_comprehensive_activity_properties(xaml_path: str) -> List[Dict[str, Any]]:
    """Extract comprehensive activity properties from XAML workflow.
    
    Analyzes both visible and invisible properties including:
    - Basic properties (DisplayName, etc.)
    - ViewState properties (IsExpanded, IsPinned, etc.)
    - Configuration properties (nested elements)
    - Type-specific properties (assignments, conditions, etc.)
    - Annotation properties
    
    Args:
        xaml_path: Path to XAML file
        
    Returns:
        List of activity dictionaries with comprehensive property analysis
    """
    try:
        tree = ET.parse(xaml_path)
        root = tree.getroot()
        
        # Define namespaces
        sap2010_ns = "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        sap_ns = "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
        ui_ns = "http://schemas.uipath.com/workflow/activities"
        x_ns = "http://schemas.microsoft.com/winfx/2006/xaml"
        
        activities = []
        
        # Skip non-activity elements
        skip_elements = {
            'NamespacesForImplementation', 'ReferencesForImplementation', 
            'Members', 'Variables', 'ViewState', 'Collection', 'AssemblyReference',
            'VirtualizedContainerService.HintSize', 'WorkflowViewState.IdRef',
            'WorkflowViewStateService.ViewState', 'Dictionary', 'Boolean', 'String'
        }
        
        # UiPath activity patterns
        activity_prefixes = {'ui:', 'Sequence', 'If', 'ForEach', 'TryCatch', 'Parallel', 'While'}
        
        activity_count = 0
        for elem in root.iter():
            # Get clean tag name
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            # Skip metadata elements
            if (tag in skip_elements or 
                tag.startswith('x:') or 
                tag == 'Activity' or
                '.' in tag or  # Property elements like AssignOperation.To
                tag in ['Property', 'AssignOperation', 'InArgument', 'OutArgument']):
                continue
            
            # Only process actual workflow activities
            is_activity = (
                any(tag.startswith(prefix.replace(':', '')) for prefix in activity_prefixes) or
                tag in ['Sequence', 'If', 'ForEach', 'TryCatch', 'Parallel', 'While', 'InvokeMethod'] or
                elem.get('DisplayName') is not None  # Activities usually have DisplayName
            )
            
            if not is_activity:
                continue
                
            activity_count += 1
            if activity_count > 20:  # Limit for analysis
                break
                
            # Basic properties
            properties = {
                "tag": tag,
                "display_name": elem.get('DisplayName', None),
                "position": activity_count
            }
            
            # Collect all direct attributes
            visible_attrs = {}
            invisible_attrs = {}
            
            for attr_name, attr_value in elem.attrib.items():
                clean_attr = attr_name.split('}')[-1] if '}' in attr_name else attr_name
                
                # Categorize attributes
                if clean_attr in ['DisplayName', 'x:TypeArguments']:
                    visible_attrs[clean_attr] = attr_value
                elif 'ViewState' in clean_attr or 'VirtualizedContainer' in clean_attr:
                    invisible_attrs[clean_attr] = attr_value
                elif 'Annotation' in clean_attr:
                    properties["annotation"] = attr_value
                else:
                    visible_attrs[clean_attr] = attr_value
            
            properties["visible_attributes"] = visible_attrs
            properties["invisible_attributes"] = invisible_attrs
            
            # Analyze nested configuration
            nested_config = {}
            child_elements = []
            
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                
                # ViewState analysis
                if 'ViewState' in child_tag:
                    viewstate = extract_viewstate_properties(child)
                    if viewstate:
                        nested_config["viewstate"] = viewstate
                
                # Property elements (like AssignOperation.To/Value)
                elif '.' in child_tag:
                    prop_name = child_tag.split('.')[-1]
                    prop_value = extract_property_value(child)
                    nested_config[prop_name.lower()] = prop_value
                
                # Child activities
                elif child_tag not in skip_elements:
                    child_elements.append(child_tag)
            
            if nested_config:
                properties["nested_configuration"] = nested_config
            if child_elements:
                properties["child_activities"] = child_elements
                
            # Type-specific analysis
            if tag == 'GetIMAPMailMessages':
                properties["activity_type"] = "mail_operation"
                properties["complexity"] = "high"
            elif tag in ['LogMessage', 'InvokeMethod']:
                properties["activity_type"] = "utility"
                properties["complexity"] = "medium"
            elif tag in ['Sequence', 'If', 'ForEach']:
                properties["activity_type"] = "control_flow"
                properties["complexity"] = "low"
            
            activities.append(properties)
        
        print(f"OK Analyzed {len(activities)} activities with comprehensive properties")
        return activities
        
    except Exception as e:
        print(f"ERROR Error analyzing activity properties: {e}")
        return []


def extract_viewstate_properties(viewstate_elem) -> Optional[Dict]:
    """Extract ViewState dictionary properties."""
    try:
        viewstate_props = {}
        
        # Look for Dictionary elements
        for child in viewstate_elem.iter():
            if child.tag.endswith('Boolean') or child.tag.endswith('String'):
                key = child.get('{http://schemas.microsoft.com/winfx/2006/xaml}Key')
                if key:
                    value = child.text or child.get('Value', child.tag)
                    viewstate_props[key] = value
        
        return viewstate_props if viewstate_props else None
    except:
        return None


def extract_property_value(prop_elem) -> str:
    """Extract value from property elements."""
    try:
        # Try direct text content first
        if prop_elem.text and prop_elem.text.strip():
            return prop_elem.text.strip()
        
        # Look for nested argument elements
        for child in prop_elem:
            if 'Argument' in child.tag:
                if child.text:
                    return child.text.strip()
                # Look for nested expressions
                for grandchild in child:
                    if grandchild.text:
                        return grandchild.text.strip()
        
        return f"<{prop_elem.tag}> complex structure"
    except:
        return "extraction_failed"


def analyze_activity_complexity(activities: List[Dict]) -> Dict[str, int]:
    """Analyze complexity distribution of activities."""
    complexity_count = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    type_count = {}
    
    for activity in activities:
        complexity = activity.get("complexity", "unknown")
        complexity_count[complexity] += 1
        
        activity_type = activity.get("activity_type", "unknown")
        type_count[activity_type] = type_count.get(activity_type, 0) + 1
    
    return {
        "complexity_distribution": complexity_count,
        "type_distribution": type_count,
        "total_activities": len(activities)
    }


# Test with the complex PurposefulPromethium XAML
if __name__ == "__main__":
    xaml_file = r"D:\github.com\rpapub\PurposefulPromethium\Process\IMAP\GetSingleMailMessageImapByMessageId.xaml"
    
    print(f"Analyzing comprehensive activity properties in: {Path(xaml_file).name}")
    print("=" * 80)
    
    # Extract comprehensive properties
    activities = extract_comprehensive_activity_properties(xaml_file)
    
    # Show detailed analysis of first few activities
    print(f"\nDetailed Analysis of First 5 Activities:")
    print("-" * 50)
    
    for i, activity in enumerate(activities[:5], 1):
        print(f"\n{i}. {activity['tag']} - '{activity.get('display_name', 'unnamed')}'")
        print(f"   Type: {activity.get('activity_type', 'unknown')} | Complexity: {activity.get('complexity', 'unknown')}")
        
        # Visible attributes
        if activity.get('visible_attributes'):
            print(f"   Visible Attributes: {len(activity['visible_attributes'])}")
            for key, value in list(activity['visible_attributes'].items())[:3]:
                preview = value[:50] + "..." if len(str(value)) > 50 else value
                print(f"     {key}: {preview}")
        
        # Invisible attributes  
        if activity.get('invisible_attributes'):
            print(f"   Invisible Attributes: {len(activity['invisible_attributes'])}")
            for key, value in list(activity['invisible_attributes'].items())[:2]:
                print(f"     {key}: {value}")
        
        # Nested configuration
        if activity.get('nested_configuration'):
            print(f"   Nested Config: {list(activity['nested_configuration'].keys())}")
            
        # Annotation
        if activity.get('annotation'):
            annotation_preview = activity['annotation'][:60] + "..." if len(activity['annotation']) > 60 else activity['annotation']
            print(f"   Annotation: {annotation_preview}")
        
        # Child activities
        if activity.get('child_activities'):
            print(f"   Child Activities: {activity['child_activities']}")
    
    # Overall complexity analysis
    print(f"\n\nComplexity Analysis:")
    print("-" * 30)
    analysis = analyze_activity_complexity(activities)
    
    print(f"Total Activities Analyzed: {analysis['total_activities']}")
    print(f"Complexity Distribution:")
    for complexity, count in analysis['complexity_distribution'].items():
        print(f"  {complexity.title()}: {count}")
    
    print(f"\nActivity Type Distribution:")
    for activity_type, count in analysis['type_distribution'].items():
        print(f"  {activity_type.replace('_', ' ').title()}: {count}")