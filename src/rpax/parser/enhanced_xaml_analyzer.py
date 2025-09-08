"""Enhanced XAML analysis with visual/structural activity detection.

Incorporates learnings from Christian Prior-Mamulyan's graphical activity extractor
for robust, parser-grade XAML processing with visual vs. structural distinction.
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import parse as defused_parse

logger = logging.getLogger(__name__)

# Enhanced blacklist based on gist learnings - metadata/structural elements not shown in visual designer
BLACKLIST_TAGS = {
    # Original gist blacklist
    "Members", "HintSize", "Property", "TypeArguments", "WorkflowFileInfo", 
    "Annotation", "ViewState", "Collection", "Dictionary", "ActivityAction",
    
    # Extended blacklist for parser-grade robustness
    "Variables", "Arguments", "Imports", "NamespacesForImplementation", 
    "ReferencesForImplementation", "TextExpression", "VisualBasic",
    
    # SAP annotations (all sap2010:*)
    "WorkflowViewState", "WorkflowViewStateService", "Ignorable",
    
    # Container edge elements (not activities themselves)
    "Then", "Else", "Catches", "Catch", "Finally", "States", "Transitions",
    "Body", "Handler", "Condition", "Default"
}

# Whitelist of core visual activities that should always be included
VISUAL_ACTIVITY_WHITELIST = {
    "Sequence", "Flowchart", "StateMachine", "TryCatch", "Parallel", 
    "ParallelForEach", "ForEach", "While", "DoWhile", "If", "Switch",
    "InvokeWorkflowFile", "Assign", "Delay", "LogMessage", "RetryScope",
    "Pick", "PickBranch", "WriteLine", "InputDialog", "MessageBox",
    "Click", "Type", "GetText", "SetText", "OpenBrowser", "NavigateTo"
}

@dataclass
class EnhancedActivityNode:
    """Enhanced activity node with stable IDs and visual classification."""
    node_id: str  # Stable indexed path like /Sequence[0]/If[1]/Then/Click[0]
    tag: str  # Activity type without namespace
    display_name: str
    path: str  # Hierarchical path for debugging
    depth: int
    is_visual: bool  # True if shown in visual designer
    attributes: dict[str, str] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    children: list["EnhancedActivityNode"] = field(default_factory=list)
    parent_id: str | None = None
    line_number: int | None = None
    
    # Invocation-specific data
    invocation_target: str | None = None
    invocation_kind: str | None = None  # "invoke", "invoke-missing", "invoke-dynamic"


class EnhancedXamlAnalyzer:
    """Enhanced XAML analyzer with visual/structural distinction."""
    
    def __init__(self):
        self.current_workflow_id = ""
        self.sibling_counters = {}  # Track sibling indices for stable nodeIds
        
    def analyze_workflow(self, xaml_path: Path) -> tuple[list[EnhancedActivityNode], dict]:
        """Analyze workflow and return visual activities and metadata.
        
        Returns:
            tuple: (visual_activities, workflow_metadata)
        """
        try:
            self.current_workflow_id = xaml_path.stem
            self.sibling_counters = {}
            
            tree = defused_parse(str(xaml_path))
            root = tree.getroot()
            
            # Extract workflow-level metadata
            workflow_metadata = self._extract_workflow_metadata(root)
            
            # Extract visual activities with enhanced parsing
            visual_activities = self._extract_visual_activities(root)
            
            return visual_activities, workflow_metadata
            
        except Exception as e:
            logger.error(f"Failed to analyze {xaml_path}: {e}")
            return [], {"parse_error": str(e), "workflow_id": xaml_path.stem}
    
    def _extract_workflow_metadata(self, root: ET.Element) -> dict:
        """Extract workflow-level metadata (variables, arguments, imports)."""
        metadata = {
            "workflow_id": self.current_workflow_id,
            "variables": [],
            "arguments": [],
            "imports": [],
            "namespace_map": dict(root.attrib) if root.attrib else {}
        }
        
        # Extract variables
        for var_elem in root.iter():
            tag = self._get_local_tag(var_elem)
            if tag == "Variable":
                var_data = {
                    "name": var_elem.get("Name", ""),
                    "type": var_elem.get("x:TypeArguments", ""),
                    "default": var_elem.get("Default", ""),
                    "scope": "Workflow"  # Could be enhanced to detect actual scope
                }
                metadata["variables"].append(var_data)
        
        # Extract arguments (similar pattern)
        # ... implementation details
        
        return metadata
    
    def _extract_visual_activities(self, elem: ET.Element, parent_path: str = "", 
                                 depth: int = 0, parent_id: str | None = None, 
                                 parent_elem: ET.Element | None = None) -> list[EnhancedActivityNode]:
        """Recursively extract visual activities using proven gist approach with stable indexed paths."""
        tag = self._get_local_tag(elem)
        
        results = []
        
        # Determine if this element should be treated as a visual activity (using gist logic)
        is_visual = self._is_visual_activity(elem, tag)
        
        # Build hierarchical path (all elements contribute to path, like original gist)
        current_path = f"{parent_path}/{tag}" if parent_path else tag
        
        if is_visual:
            # Generate stable indexed node ID like /Sequence[0]/If[1]/Then/Click[0]
            node_id = self._generate_stable_node_id(elem, parent_path, tag, parent_elem)
            
            # Create enhanced activity node
            activity_node = self._create_activity_node(
                elem, tag, node_id, current_path, depth, parent_id
            )
            results.append(activity_node)
            
            # Set parent for children - use node_id for visual parent
            parent_for_children = node_id
        else:
            # Non-visual element - pass through parent ID
            parent_for_children = parent_id
        
        # All elements contribute to path (like original gist)
        path_for_children = current_path
        
        # Process children (simple recursion like in gist)
        for child_elem in elem:
            child_activities = self._extract_visual_activities(
                child_elem, path_for_children, depth + 1, parent_for_children, elem
            )
            results.extend(child_activities)
        
        return results
    
    def _generate_stable_node_id(self, elem: ET.Element, parent_path: str, tag: str, 
                                parent_elem: ET.Element | None = None) -> str:
        """Generate stable indexed node ID like /Sequence[0]/If[1]/Then/Click[0]."""        
        if parent_elem is None:
            # Root element
            return f"/{tag}[0]"
        
        # Count preceding siblings of the same type that are visual
        sibling_count = 0
        for sibling in parent_elem:
            if sibling is elem:
                break
            sibling_tag = self._get_local_tag(sibling)
            if sibling_tag == tag and self._is_visual_activity(sibling, sibling_tag):
                sibling_count += 1
        
        # Build indexed path
        if parent_path:
            return f"{parent_path}/{tag}[{sibling_count}]"
        else:
            return f"/{tag}[{sibling_count}]"
    
    def _is_visual_activity(self, elem: ET.Element, tag: str) -> bool:
        """Visual activity detection using exact gist logic."""
        return tag not in BLACKLIST_TAGS and (
            "DisplayName" in elem.attrib or tag in {
                "Sequence", "TryCatch", "Flowchart", "Parallel", "StateMachine"
            }
        )
    
    def _create_activity_node(self, elem: ET.Element, tag: str, node_id: str, 
                            path: str, depth: int, parent_id: str | None) -> EnhancedActivityNode:
        """Create enhanced activity node with full metadata."""
        
        display_name = elem.get("DisplayName", "") or f"<{tag}>"
        
        # Extract properties (non-xmlns attributes)
        properties = {}
        attributes = {}
        
        for attr_name, attr_value in elem.attrib.items():
            attr_local = attr_name.split('}')[-1] if '}' in attr_name else attr_name
            
            # Skip xmlns declarations
            if attr_name.startswith(('xmlns', '{http://www.w3.org/2000/xmlns/}')):
                continue
                
            attributes[attr_local] = attr_value
            
            # Mark expressions vs literals
            is_expression = self._is_expression_value(attr_value)
            properties[attr_local] = {
                "value": attr_value,
                "isExpression": is_expression
            }
        
        # Create node
        node = EnhancedActivityNode(
            node_id=node_id,
            tag=tag,
            display_name=display_name,
            path=path,
            depth=depth,
            is_visual=True,  # This method only called for visual activities
            attributes=attributes,
            properties=properties,
            parent_id=parent_id,
            line_number=getattr(elem, 'sourceline', None)
        )
        
        # Special handling for InvokeWorkflowFile
        if tag == "InvokeWorkflowFile":
            workflow_filename = attributes.get("WorkflowFileName", "")
            node.invocation_target = workflow_filename
            node.invocation_kind = self._classify_invocation(workflow_filename)
        
        return node
    
    
    def _get_local_tag(self, elem: ET.Element) -> str:
        """Extract local tag name without namespace."""
        return elem.tag.rsplit('}', 1)[-1]
    
    def _is_expression_value(self, value: str) -> bool:
        """Detect if attribute value is VB.NET/C# expression."""
        if not value:
            return False
        
        # VB.NET/C# expressions are typically enclosed in brackets
        if value.startswith('[') and value.endswith(']') and len(value) > 2:
            return True
        
        # Method calls with parentheses (like Path.Combine(...), .ToString())
        if ('.ToString()' in value or 
            'Path.Combine(' in value or 
            'String.Format(' in value or
            'new ' in value):
            return True
        
        # Assignment expressions
        if ' = ' in value:
            return True
            
        return False
    
    def _classify_invocation(self, workflow_filename: str) -> str:
        """Classify invocation type based on filename pattern."""
        if not workflow_filename:
            return "invoke-missing"
        
        # Dynamic if contains expressions
        if self._is_expression_value(workflow_filename):
            return "invoke-dynamic"
        
        # Could add additional logic to check if file exists
        # For now, assume literal paths are valid
        return "invoke"
    
    def extract_activity_tree(self, xaml_path: Path):
        """Bridge method to provide compatibility with legacy analyzer interface.
        
        Returns ActivityTree-like structure compatible with existing artifact generation.
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: Starting analyze_workflow for {xaml_path}")
        
        visual_activities, metadata = self.analyze_workflow(xaml_path)
        logger.info(f"DEBUG: analyze_workflow returned {len(visual_activities) if visual_activities else 0} activities")
        
        if not visual_activities:
            return None
            
        # Convert to legacy format for compatibility
        logger.info(f"DEBUG: Starting generate_activity_tree_json")
        tree_json = self.generate_activity_tree_json(visual_activities, metadata)
        logger.info(f"DEBUG: generate_activity_tree_json completed")
        
        # Create a simple object with the expected interface
        class EnhancedActivityTree:
            def __init__(self, data):
                self.data = data
                self.root_node = data.get("rootNode")
                self.workflow_id = data.get("workflowId", "")
        
        return EnhancedActivityTree(tree_json)
        
    def extract_control_flow(self, xaml_path: Path):
        """Bridge method for control flow extraction (placeholder for now)."""
        # For now, return None - would implement CFG extraction later
        return None
        
    def extract_resources(self, xaml_path: Path):
        """Bridge method for resource extraction (placeholder for now).""" 
        # For now, return None - would implement resource extraction later
        return None
        
    def calculate_metrics(self, activity_tree):
        """Calculate workflow metrics from enhanced activity tree."""
        from ..models.activity import WorkflowMetrics
        
        metrics = WorkflowMetrics()
        
        if not activity_tree or not hasattr(activity_tree, 'data'):
            return metrics
            
        # Get all nodes from the enhanced activity tree structure
        tree_data = activity_tree.data
        all_nodes = []
        
        def collect_nodes(node_data):
            """Recursively collect all nodes from tree structure."""
            if not node_data:
                return
                
            all_nodes.append(node_data)
            
            # Process children if they exist
            if "children" in node_data:
                for child in node_data["children"]:
                    collect_nodes(child)
        
        # Start collection from root
        if "rootNode" in tree_data:
            collect_nodes(tree_data["rootNode"])
        
        # Calculate basic metrics
        metrics.total_nodes = len(all_nodes)
        
        # Calculate max depth
        def calculate_depth(node_data):
            """Calculate maximum depth of tree."""
            if not node_data or "children" not in node_data:
                return 1
            
            max_child_depth = 0
            for child in node_data["children"]:
                child_depth = calculate_depth(child)
                max_child_depth = max(max_child_depth, child_depth)
            
            return 1 + max_child_depth
        
        if "rootNode" in tree_data:
            metrics.max_depth = calculate_depth(tree_data["rootNode"])
        
        # Count activity types and specific patterns
        for node in all_nodes:
            activity_type = node.get("tag", "Unknown")
            metrics.increment_activity_type(activity_type)
            
            # Count specific activity patterns based on tag
            tag_lower = activity_type.lower()
            if any(loop_type in tag_lower for loop_type in ["loop", "while", "foreach"]):
                metrics.loop_count += 1
            elif "invokeworkflowfile" in tag_lower:
                metrics.invoke_count += 1
            elif any(log_type in tag_lower for log_type in ["writeline", "logmessage"]):
                metrics.log_count += 1
            elif "trycatch" in tag_lower:
                metrics.try_catch_count += 1
            elif "selector" in tag_lower:
                metrics.selector_count += 1
        
        return metrics

    def generate_activity_tree_json(self, visual_activities: list[EnhancedActivityNode], 
                                   metadata: dict) -> dict:
        """Generate activities.tree JSON structure."""
        
        # Find root activities (those with no parent)
        root_activities = [act for act in visual_activities if act.parent_id is None]
        
        def serialize_node(node: EnhancedActivityNode) -> dict:
            # Find children
            children = [act for act in visual_activities if act.parent_id == node.node_id]
            
            return {
                "nodeId": node.node_id,
                "activityType": node.tag,
                "displayName": node.display_name,
                "properties": node.properties,
                "arguments": {},  # Could be enhanced
                "parentId": node.parent_id,
                "continueOnError": None,
                "timeout": None,
                "viewStateId": node.attributes.get("WorkflowViewState.IdRef"),
                "children": [serialize_node(child) for child in children],
                
                # Enhanced fields
                "isVisual": node.is_visual,
                "lineNumber": node.line_number,
                "invocationTarget": node.invocation_target,
                "invocationKind": node.invocation_kind
            }
        
        # Build tree structure
        root_node = None
        if root_activities:
            if len(root_activities) == 1:
                root_node = serialize_node(root_activities[0])
            else:
                # Multiple roots - create synthetic root
                root_node = {
                    "nodeId": "root",
                    "activityType": "Activity",
                    "displayName": "Activity", 
                    "children": [serialize_node(root) for root in root_activities]
                }
        
        return {
            "workflowId": metadata.get("workflow_id", ""),
            "contentHash": "",  # Would be filled by caller
            "extractedAt": "",  # Would be filled by caller
            "extractorVersion": "0.1.0-enhanced",
            "variables": metadata.get("variables", []),
            "arguments": metadata.get("arguments", []),
            "imports": metadata.get("imports", []),
            "rootNode": root_node,
            
            # Enhanced metadata
            "totalVisualActivities": len([a for a in visual_activities if a.is_visual]),
            "parseMethod": "enhanced-visual-detection"
        }


# Integration function for existing rpax codebase
def enhance_existing_analyzer():
    """
    Integration point to upgrade existing XamlAnalyzer with enhanced capabilities.
    This would replace or extend the current implementation.
    """
    pass