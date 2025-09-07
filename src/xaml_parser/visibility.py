"""XAML visibility utilities for distinguishing visible from invisible elements.

Based on graphical activity extractor by Christian Prior-Mamulyan.
Used to filter out technical metadata and focus on business logic elements.
"""

from typing import Set
import xml.etree.ElementTree as ET


# Blacklist of non-visual tags that represent metadata or structural elements
# not shown in the visual workflow designer (e.g., variable declarations, layout hints)
BLACKLIST_TAGS: Set[str] = {
    "Members",
    "HintSize", 
    "Property",
    "TypeArguments",
    "WorkflowFileInfo",
    "Annotation",
    "ViewState", 
    "Collection",
    "Dictionary",
    "ActivityAction",
    # Additional UiPath metadata elements
    "VisualBasic.Settings",
    "TextExpression.NamespacesForImplementation",
    "TextExpression.ReferencesForImplementation", 
    "AssemblyReference",
    "WorkflowViewStateService.ViewState",
    "VirtualizedContainerService.HintSize",
    "WorkflowViewState.IdRef",
    "Annotation.AnnotationText",
    "ViewStateData",  # ViewState metadata
}

# Visual container activities that are always shown
VISUAL_CONTAINERS: Set[str] = {
    "Sequence",
    "TryCatch", 
    "Flowchart",
    "Parallel",
    "StateMachine",
    "If",
    "Switch",
    "While",
    "DoWhile",
    "ForEach",
}


def get_local_tag(element: ET.Element) -> str:
    """Extract local tag name without namespace prefix.
    
    Args:
        element: XML element
        
    Returns:
        Local tag name without namespace
        
    Examples:
        >>> elem.tag = "{http://schemas.microsoft.com/netfx/2009/xaml/activities}Sequence"
        >>> get_local_tag(elem)
        "Sequence"
    """
    return element.tag.split('}')[-1] if '}' in element.tag else element.tag


def is_visible_element(element: ET.Element) -> bool:
    """Determine if XML element represents a visually shown activity.
    
    Args:
        element: XML element from XAML tree
        
    Returns:
        True if element should be shown in visual designer
    """
    tag = get_local_tag(element)
    
    # Skip blacklisted metadata tags
    if tag in BLACKLIST_TAGS:
        return False
    
    # Visual containers are always visible
    if tag in VISUAL_CONTAINERS:
        return True
        
    # Elements with DisplayName are typically visible activities
    if "DisplayName" in element.attrib:
        return True
        
    # Additional heuristics for UiPath activities
    # Most UiPath activities have these namespaces
    if element.tag.startswith('{http://schemas.uipath.com/workflow/activities}'):
        return True
        
    return False


def get_visible_elements(root: ET.Element) -> list[ET.Element]:
    """Get all visible elements from XAML tree.
    
    Args:
        root: Root XML element
        
    Returns:
        List of visible elements only
    """
    visible_elements = []
    
    def traverse(elem: ET.Element) -> None:
        if is_visible_element(elem):
            visible_elements.append(elem)
        
        # Continue traversing children regardless of visibility
        # (visible elements can contain invisible metadata)
        for child in elem:
            traverse(child)
    
    traverse(root)
    return visible_elements


def get_visible_text_content(root: ET.Element) -> str:
    """Extract text content only from visible elements.
    
    Args:
        root: Root XML element
        
    Returns:
        Concatenated text from visible elements only
    """
    visible_elements = get_visible_elements(root)
    visible_text = []
    
    for elem in visible_elements:
        # Get element text
        if elem.text:
            visible_text.append(elem.text.strip())
            
        # Get attribute values (these contain the business logic)
        for attr_value in elem.attrib.values():
            if attr_value:
                visible_text.append(attr_value.strip())
    
    return " ".join(visible_text)


def is_visible_attribute(element: ET.Element, attr_name: str) -> bool:
    """Check if an attribute represents visible business logic.
    
    Args:
        element: XML element
        attr_name: Attribute name to check
        
    Returns:
        True if attribute contains business logic (not technical metadata)
    """
    # These attributes contain technical metadata, not business logic
    invisible_attrs = {
        'mc:Ignorable',
        'x:Class', 
        'sap:VirtualizedContainerService.HintSize',
        'sap2010:WorkflowViewState.IdRef',
        'xmlns',  # and any xmlns:* attributes
    }
    
    # Direct matches
    if attr_name in invisible_attrs:
        return False
        
    # Namespace declarations
    if attr_name.startswith('xmlns'):
        return False
        
    # ViewState and layout attributes  
    if 'ViewState' in attr_name or 'HintSize' in attr_name:
        return False
        
    # Most other attributes contain business logic
    return True


def extract_visible_activity_data(element: ET.Element) -> dict[str, str]:
    """Extract visible attribute data from an activity element.
    
    Args:
        element: Activity XML element
        
    Returns:
        Dictionary of visible attribute name/value pairs
    """
    visible_attrs = {}
    
    for attr_name, attr_value in element.attrib.items():
        if is_visible_attribute(element, attr_name):
            visible_attrs[attr_name] = attr_value
    
    return visible_attrs