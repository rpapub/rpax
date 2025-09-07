#!/usr/bin/env python3
"""Test XAML parsing for root annotation extraction."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


def find_root_annotation(xaml_path: str) -> Optional[str]:
    """Find and extract root annotation from XAML workflow.
    
    Rules for determining root element:
    1. First, try the root <Activity> element for direct annotation
    2. If no annotation, find the first <Sequence> with annotation (main workflow logic)
    3. Look for sap2010:Annotation.AnnotationText attribute
    
    Args:
        xaml_path: Path to XAML file
        
    Returns:
        Root annotation text or None if not found
    """
    try:
        tree = ET.parse(xaml_path)
        root = tree.getroot()
        
        # Define namespaces
        sap2010_ns = "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        
        # Rule 1: Check root Activity element for annotation
        annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"
        root_annotation = root.get(annotation_attr)
        
        if root_annotation:
            print("OK Found root annotation on Activity element")
            return root_annotation
        
        # Rule 2: Find first Sequence with annotation (main workflow logic)
        for elem in root.iter():
            if elem.tag.endswith("Sequence"):
                seq_annotation = elem.get(annotation_attr)
                if seq_annotation:
                    print(f"OK Found root annotation on Sequence element: {elem.get('DisplayName', 'unnamed')}")
                    return seq_annotation
        
        print("ERROR No root annotation found")
        return None
        
    except Exception as e:
        print(f"ERROR Error parsing XAML: {e}")
        return None


def extract_arguments(xaml_path: str) -> list[dict]:
    """Extract workflow arguments from XAML x:Members section.
    
    Args:
        xaml_path: Path to XAML file
        
    Returns:
        List of argument dictionaries with name, type, annotation, direction
    """
    try:
        tree = ET.parse(xaml_path)
        root = tree.getroot()
        
        # Define namespaces
        x_ns = "http://schemas.microsoft.com/winfx/2006/xaml"
        sap2010_ns = "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        
        arguments = []
        
        # Find x:Members section
        members = root.find(f"{{{x_ns}}}Members")
        if not members:
            print("ERROR No x:Members section found")
            return arguments
        
        # Extract x:Property elements (arguments)
        for prop in members.findall(f"{{{x_ns}}}Property"):
            name = prop.get("Name", "unknown")
            type_attr = prop.get("Type", "unknown")
            annotation = prop.get(f"{{{sap2010_ns}}}Annotation.AnnotationText", "")
            
            # Parse direction from type (InArgument, OutArgument, InOutArgument)
            direction = "unknown"
            if "InArgument" in type_attr and "OutArgument" not in type_attr:
                direction = "in"
            elif "OutArgument" in type_attr:
                direction = "out" 
            elif "InOutArgument" in type_attr:
                direction = "inout"
            
            arguments.append({
                "name": name,
                "type": type_attr,
                "annotation": annotation,
                "direction": direction
            })
            
        print(f"OK Found {len(arguments)} arguments")
        return arguments
        
    except Exception as e:
        print(f"ERROR Error extracting arguments: {e}")
        return []


def extract_activity_annotations(xaml_path: str) -> list[dict]:
    """Extract annotations from all activities in the XAML workflow.
    
    Args:
        xaml_path: Path to XAML file
        
    Returns:
        List of activity dictionaries with tag, display_name, annotation
    """
    try:
        tree = ET.parse(xaml_path)
        root = tree.getroot()
        
        # Define namespaces
        sap2010_ns = "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
        annotation_attr = f"{{{sap2010_ns}}}Annotation.AnnotationText"
        
        activities = []
        
        # Find all elements with annotations
        for elem in root.iter():
            annotation = elem.get(annotation_attr)
            if annotation:
                # Get activity type (remove namespace prefix)
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                display_name = elem.get('DisplayName', 'unnamed')
                
                activities.append({
                    "tag": tag,
                    "display_name": display_name,
                    "annotation": annotation,
                    "has_children": len(list(elem)) > 0
                })
        
        print(f"OK Found {len(activities)} activities with annotations")
        return activities
        
    except Exception as e:
        print(f"ERROR Error extracting activity annotations: {e}")
        return []


# Test with InitAllSettings.xaml
if __name__ == "__main__":
    xaml_file = r"D:\github.com\rpapub\rpax-corpuses\c25v001_CORE_00000001\Framework\InitAllSettings.xaml"
    
    print(f"Testing XAML parser with: {Path(xaml_file).name}")
    print("=" * 50)
    
    # Test root annotation extraction
    print("\n1. Root Annotation Extraction:")
    root_annotation = find_root_annotation(xaml_file)
    if root_annotation:
        print(f"Annotation: {root_annotation}")
    
    # Test argument extraction  
    print("\n2. Argument Extraction:")
    arguments = extract_arguments(xaml_file)
    for i, arg in enumerate(arguments, 1):
        print(f"  {i}. {arg['name']} ({arg['direction']}) - {arg['type']}")
        if arg['annotation']:
            print(f"     Annotation: {arg['annotation']}")
    
    # Test activity annotation extraction
    print("\n3. Activity Annotation Extraction:")
    activities = extract_activity_annotations(xaml_file)
    for i, activity in enumerate(activities, 1):
        print(f"  {i}. {activity['tag']} - '{activity['display_name']}'")
        # Show first 80 chars of annotation
        annotation_preview = activity['annotation'][:80] + "..." if len(activity['annotation']) > 80 else activity['annotation']
        print(f"     Annotation: {annotation_preview}")
        print(f"     Has children: {activity['has_children']}")