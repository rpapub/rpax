"""Advanced XAML analysis for extracting InvokeWorkflowFile activities.

This module implements actual XAML parsing to extract workflow invocations,
arguments, and activity details according to ADR-001 pattern-matching approach.
"""

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import parse as defused_parse

from rpax.models.activity import (
    ActivityNode,
    ActivityTree,
    WorkflowControlFlow,
    WorkflowMetrics,
    WorkflowResources,
)
from rpax.utils.paths import normalize_path

logger = logging.getLogger(__name__)


@dataclass
class InvocationData:
    """Data about a workflow invocation found in XAML."""
    target_path: str
    kind: str  # "invoke", "invoke-missing", "invoke-dynamic", "invoke-coded"
    arguments: dict[str, str] = field(default_factory=dict)
    line_number: int | None = None
    activity_name: str | None = None


@dataclass
class ArgumentData:
    """Data about workflow arguments."""
    name: str
    direction: str  # "In", "Out", "InOut"
    type_name: str | None = None
    default_value: str | None = None


class XamlAnalyzer:
    """Analyzes XAML workflow files to extract invocations and structure."""

    def __init__(self):
        self.namespace_patterns = self._build_namespace_patterns()

    def analyze_workflow(self, xaml_path: Path) -> tuple[list[InvocationData], list[ArgumentData]]:
        """Analyze XAML file and extract invocations and arguments.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            Tuple of (invocations, arguments)
        """
        logger.debug(f"Analyzing XAML: {xaml_path}")

        try:
            # Parse XAML safely using defusedxml
            tree = defused_parse(xaml_path)
            root = tree.getroot()

            # Extract invocations
            invocations = self._extract_invocations(root, xaml_path)

            # Extract arguments
            arguments = self._extract_arguments(root)

            logger.debug(f"Found {len(invocations)} invocations and {len(arguments)} arguments")
            return invocations, arguments

        except Exception as e:
            logger.warning(f"Failed to analyze XAML {xaml_path}: {e}")
            return [], []

    def extract_activity_tree(self, xaml_path: Path) -> ActivityTree | None:
        """Extract complete activity tree from XAML workflow.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            ActivityTree with full activity structure, or None if parsing fails
        """
        logger.debug(f"Extracting activity tree from: {xaml_path}")

        try:
            # Parse XAML safely using defusedxml
            tree = defused_parse(xaml_path)
            root = tree.getroot()

            # Calculate content hash
            with open(xaml_path, "rb") as f:
                import hashlib
                content_hash = hashlib.sha256(f.read()).hexdigest()

            # Extract workflow ID (relative path)
            workflow_id = xaml_path.name  # For now, just use filename

            # Extract variables and arguments
            variables = self._extract_variables(root)
            arguments = [arg.__dict__ for arg in self._extract_arguments(root)]

            # Extract imports
            imports = self._extract_imports(root)

            # Extract root activity node
            root_activity = self._extract_activity_node(root, "root")

            # Create activity tree
            activity_tree = ActivityTree(
                workflow_id=workflow_id,
                root_node=root_activity,
                variables=variables,
                arguments=arguments,
                imports=imports,
                content_hash=content_hash
            )

            logger.debug(f"Extracted activity tree with {len(activity_tree.get_all_nodes())} nodes")
            return activity_tree

        except Exception as e:
            logger.warning(f"Failed to extract activity tree from {xaml_path}: {e}")
            return None

    def extract_control_flow(self, xaml_path: Path) -> WorkflowControlFlow | None:
        """Extract control flow graph from XAML workflow.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            WorkflowControlFlow with control flow edges, or None if parsing fails
        """
        logger.debug(f"Extracting control flow from: {xaml_path}")

        try:
            # Parse XAML safely using defusedxml
            tree = defused_parse(xaml_path)
            root = tree.getroot()

            workflow_id = xaml_path.name
            control_flow = WorkflowControlFlow(workflow_id=workflow_id)

            # Extract control flow edges
            self._extract_control_flow_edges(root, control_flow, parent_id="root")

            logger.debug(f"Extracted {len(control_flow.edges)} control flow edges")
            return control_flow

        except Exception as e:
            logger.warning(f"Failed to extract control flow from {xaml_path}: {e}")
            return None

    def extract_resources(self, xaml_path: Path) -> WorkflowResources | None:
        """Extract resource references from XAML workflow.
        
        Args:
            xaml_path: Path to XAML workflow file
            
        Returns:
            WorkflowResources with resource references, or None if parsing fails  
        """
        logger.debug(f"Extracting resources from: {xaml_path}")

        try:
            # Parse XAML safely using defusedxml
            tree = defused_parse(xaml_path)
            root = tree.getroot()

            workflow_id = xaml_path.name
            resources = WorkflowResources(workflow_id=workflow_id)

            # Extract resource references
            self._extract_resource_references(root, resources, parent_id="root")

            logger.debug(f"Extracted {len(resources.references)} resource references")
            return resources

        except Exception as e:
            logger.warning(f"Failed to extract resources from {xaml_path}: {e}")
            return None

    def calculate_metrics(self, activity_tree: ActivityTree) -> WorkflowMetrics:
        """Calculate workflow metrics from activity tree.
        
        Args:
            activity_tree: Activity tree to analyze
            
        Returns:
            WorkflowMetrics with calculated metrics
        """
        metrics = WorkflowMetrics()

        if not activity_tree:
            return metrics

        all_nodes = activity_tree.get_all_nodes()
        metrics.total_nodes = len(all_nodes)
        metrics.max_depth = activity_tree.root_node.get_depth()

        # Count activity types and specific patterns
        for node in all_nodes:
            metrics.increment_activity_type(node.activity_type)

            # Count specific activity patterns
            if "Loop" in node.activity_type or "While" in node.activity_type or "ForEach" in node.activity_type:
                metrics.loop_count += 1
            elif "InvokeWorkflowFile" in node.activity_type:
                metrics.invoke_count += 1
            elif "WriteLine" in node.activity_type or "LogMessage" in node.activity_type:
                metrics.log_count += 1
            elif "TryCatch" in node.activity_type:
                metrics.try_catch_count += 1
            elif "selector" in str(node.properties).lower():
                metrics.selector_count += 1

        return metrics

    def _extract_invocations(self, root: ET.Element, xaml_path: Path) -> list[InvocationData]:
        """Extract InvokeWorkflowFile activities from XAML."""
        invocations = []

        # Find all InvokeWorkflowFile elements (namespace-agnostic)
        invoke_elements = self._find_elements_by_local_name(root, "InvokeWorkflowFile")

        for element in invoke_elements:
            invocation = self._analyze_invoke_element(element, xaml_path)
            if invocation:
                invocations.append(invocation)

        # Also look for dynamic invocations (Path.Combine, variables)
        dynamic_invocations = self._find_dynamic_invocations(root, xaml_path)
        invocations.extend(dynamic_invocations)

        return invocations

    def _extract_arguments(self, root: ET.Element) -> list[ArgumentData]:
        """Extract workflow arguments from XAML."""
        arguments = []

        # Look for x:Members section which contains arguments
        members = self._find_elements_by_local_name(root, "Members")

        for member_section in members:
            # Find Property elements which represent arguments
            properties = self._find_elements_by_local_name(member_section, "Property")

            for prop in properties:
                arg_data = self._analyze_argument_property(prop)
                if arg_data:
                    arguments.append(arg_data)

        return arguments

    def _analyze_invoke_element(self, element: ET.Element, xaml_path: Path) -> InvocationData | None:
        """Analyze a single InvokeWorkflowFile element."""
        # Get workflow file path
        workflow_file = element.get("WorkflowFileName")
        if not workflow_file:
            return None

        # Determine invocation kind
        kind = self._determine_invocation_kind(workflow_file, xaml_path)

        # Extract arguments
        arguments = self._extract_invoke_arguments(element)

        # Get activity display name and normalize paths within it
        activity_name = element.get("DisplayName")
        if activity_name:
            from rpax.utils.paths import normalize_path
            activity_name = normalize_path(activity_name)

        return InvocationData(
            target_path=normalize_path(workflow_file),
            kind=kind,
            arguments=arguments,
            activity_name=activity_name
        )

    def _determine_invocation_kind(self, workflow_file: str, xaml_path: Path) -> str:
        """Determine if invocation is direct, missing, dynamic, or coded."""

        # Check for dynamic paths (variables, expressions)
        if any(indicator in workflow_file for indicator in ["{", "}", "[", "]", "Path.Combine", "+"]):
            return "invoke-dynamic"

        # Check for coded workflows (.cs files)
        if workflow_file.lower().endswith('.cs'):
            # Try to resolve the coded workflow file
            try:
                current_dir = xaml_path.parent
                possible_paths = [
                    current_dir / workflow_file,
                    current_dir.parent / workflow_file,
                    # Framework folder is common for coded workflows
                    current_dir / "Framework" / Path(workflow_file).name,
                    current_dir.parent / "Framework" / Path(workflow_file).name,
                ]

                for path in possible_paths:
                    if path.exists():
                        return "invoke-coded"
                
                # File doesn't exist, but it's still a coded workflow reference
                return "invoke-coded"
            except Exception:
                return "invoke-coded"

        # Try to resolve XAML path relative to current workflow
        try:
            current_dir = xaml_path.parent
            
            # Find project root by looking for project.json
            project_root = current_dir
            while project_root != project_root.parent:  # Not at filesystem root
                if (project_root / "project.json").exists():
                    break
                project_root = project_root.parent
            
            # Try different relative paths including project root
            possible_paths = [
                current_dir / workflow_file,               # Relative to current workflow
                current_dir.parent / workflow_file,        # Relative to parent directory
                project_root / workflow_file,              # Relative to project root (for test workflows)
                # Add more common patterns as needed
            ]

            for path in possible_paths:
                if path.exists():
                    return "invoke"

            return "invoke-missing"

        except Exception:
            return "invoke-missing"

    def _extract_invoke_arguments(self, element: ET.Element) -> dict[str, str]:
        """Extract arguments passed to InvokeWorkflowFile."""
        arguments = {}

        # Look for argument assignments in properties
        for child in element:
            if child.tag.endswith("Arguments"):
                # Parse argument dictionary
                args_dict = self._parse_arguments_dict(child)
                arguments.update(args_dict)

        # Also check direct attribute arguments
        for attr_name, attr_value in element.attrib.items():
            if attr_name.startswith("arg_") or attr_name.endswith("Argument"):
                arguments[attr_name] = attr_value

        return arguments

    def _parse_arguments_dict(self, args_element: ET.Element) -> dict[str, str]:
        """Parse UiPath arguments dictionary structure."""
        arguments = {}

        # UiPath uses different structures for arguments - try to handle common ones
        for child in args_element:
            # Look for key-value pairs
            if "Key" in child.attrib and "Value" in child.attrib:
                arguments[child.attrib["Key"]] = child.attrib["Value"]
            elif child.tag.endswith("String") or child.tag.endswith("Object"):
                # Extract from element text or attributes
                key = child.get("Key", child.get("x:Key", ""))
                if key:
                    value = child.text or child.get("Value", "")
                    arguments[key] = value

        return arguments

    def _find_dynamic_invocations(self, root: ET.Element, xaml_path: Path) -> list[InvocationData]:
        """Find dynamic workflow invocations using variables or expressions.
        
        Only searches in VISIBLE elements to avoid false positives from
        technical metadata like assembly references.
        """
        dynamic_invocations = []

        # Get static invoke targets to exclude from dynamic detection
        static_targets = set()
        invoke_elements = self._find_elements_by_local_name(root, "InvokeWorkflowFile")
        for element in invoke_elements:
            workflow_file = element.get("WorkflowFileName") or element.get("FileName")
            if workflow_file:
                # Add full path
                static_targets.add(workflow_file.lower())
                static_targets.add(normalize_path(workflow_file).lower())
                # Add just filename (for Variable Reference matches)
                filename_only = Path(workflow_file).name.lower()
                static_targets.add(filename_only)

        # Import visibility utilities from xaml_parser package
        try:
            import sys
            from pathlib import Path as PathLib
            xaml_parser_path = PathLib(__file__).parent.parent.parent / "xaml_parser"
            sys.path.insert(0, str(xaml_parser_path))
            from visibility import get_visible_text_content
            sys.path.pop(0)
        except ImportError:
            # Fallback to old behavior if visibility module not available
            text_content = ET.tostring(root, encoding="unicode", method="text")
        else:
            # Use visibility-filtered text content only
            text_content = get_visible_text_content(root)

        # Pattern for Path.Combine expressions - actual dynamic code
        path_combine_pattern = r"Path\.Combine\([^)]+\.xaml[^)]*\)"
        for match in re.finditer(path_combine_pattern, text_content, re.IGNORECASE):
            target_path = normalize_path(match.group())
            invocation = InvocationData(
                target_path=target_path,
                kind="invoke-dynamic",
                activity_name="Dynamic Path.Combine"
            )
            dynamic_invocations.append(invocation)

        # Pattern for variable expressions in brackets - actual VB/C# expressions
        # Look for [variableName.xaml] or [expression + ".xaml"]
        bracket_pattern = r'\[([^]]*\.xaml[^]]*)\]'
        for match in re.finditer(bracket_pattern, text_content, re.IGNORECASE):
            expression = match.group(1).strip()
            # Skip if this looks like a simple static reference
            if not any(op in expression for op in ['+', '&', '"', "'", 'Path.', 'IO.', 'System.']):
                # This is likely a static reference, not a dynamic expression
                continue
                
            invocation = InvocationData(
                target_path=normalize_path(expression),
                kind="invoke-dynamic", 
                activity_name="Variable Expression"
            )
            dynamic_invocations.append(invocation)

        # Don't use generic .xaml pattern matching - too many false positives

        return dynamic_invocations

    def _analyze_argument_property(self, prop: ET.Element) -> ArgumentData | None:
        """Analyze a workflow argument property."""
        prop_name = prop.get("Name")
        if not prop_name:
            return None

        prop_type = prop.get("Type", "Object")

        # Determine direction from attribute or name conventions
        direction = "In"  # Default
        if prop.get("Direction"):
            direction = prop.get("Direction")
        elif prop_name.lower().startswith("out_"):
            direction = "Out"
        elif prop_name.lower().startswith("io_"):
            direction = "InOut"

        # Extract default value
        default_value = prop.get("DefaultValue")

        return ArgumentData(
            name=prop_name,
            direction=direction,
            type_name=prop_type,
            default_value=default_value
        )

    def _find_elements_by_local_name(self, root: ET.Element, local_name: str) -> list[ET.Element]:
        """Find elements by local name, ignoring namespaces (ADR-001 pattern-matching)."""
        elements = []

        def search_recursive(element: ET.Element):
            # Check if current element matches (local name only)
            if element.tag.split("}")[-1] == local_name:
                elements.append(element)

            # Search children
            for child in element:
                search_recursive(child)

        search_recursive(root)
        return elements

    def _build_namespace_patterns(self) -> dict[str, re.Pattern]:
        """Build regex patterns for common UiPath namespaces."""
        return {
            "uipath_activities": re.compile(r"UiPath\.Core\.Activities", re.IGNORECASE),
            "system_activities": re.compile(r"System\.Activities", re.IGNORECASE),
            "invoke_workflow": re.compile(r"InvokeWorkflowFile", re.IGNORECASE),
            "workflow_file": re.compile(r"\.xaml$", re.IGNORECASE)
        }

    def _extract_variables(self, root: ET.Element) -> list[dict[str, Any]]:
        """Extract workflow variables from XAML."""
        variables = []

        # Look for Variable elements (namespace-agnostic)
        variable_elements = self._find_elements_by_local_name(root, "Variable")

        for var_element in variable_elements:
            var_data = {
                "name": var_element.get("Name", ""),
                "type": var_element.get("TypeArguments", ""),
                "default": var_element.get("Default", ""),
                "scope": "Workflow"  # Default scope
            }
            variables.append(var_data)

        return variables

    def _extract_imports(self, root: ET.Element) -> list[str]:
        """Extract namespace imports from XAML."""
        imports = []

        # Extract namespace declarations from root element
        for key, value in root.attrib.items():
            if key.startswith("xmlns:") and key != "xmlns:x":
                imports.append(f"{key[6:]} = {value}")

        # Look for TextExpression.NamespacesForImplementation elements
        import_elements = self._find_elements_by_local_name(root, "TextExpression.NamespacesForImplementation")
        for import_element in import_elements:
            for child in import_element:
                if hasattr(child, "text") and child.text:
                    imports.append(child.text.strip())

        return imports

    def _extract_activity_node(self, element: ET.Element, node_id: str, parent_id: str = None) -> ActivityNode:
        """Extract activity node from XML element."""
        # Get activity type (local name without namespace)
        activity_type = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        # Get display name
        display_name = element.get("DisplayName", activity_type)

        # Extract all properties as a dictionary
        properties = dict(element.attrib)

        # Extract activity arguments (child elements that aren't activities themselves)
        arguments = {}
        for child in element:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            # Skip nested activities, focus on property elements
            if not self._is_activity_element(child):
                if child.text:
                    arguments[child_tag] = child.text.strip()
                elif child.get("Value"):
                    arguments[child_tag] = child.get("Value")

        # Create activity node
        activity_node = ActivityNode(
            node_id=node_id,
            activity_type=activity_type,
            display_name=display_name,
            properties=properties,
            arguments=arguments,
            parent_id=parent_id
        )

        # Extract UiPath-specific properties
        activity_node.continue_on_error = properties.get("ContinueOnError")
        activity_node.timeout = properties.get("Timeout")
        activity_node.view_state_id = properties.get("{http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation}WorkflowViewState.IdRef")

        # Extract child activities
        child_index = 0
        for child in element:
            if self._is_activity_element(child):
                child_node_id = f"{node_id}.{child_index}"
                child_node = self._extract_activity_node(child, child_node_id, node_id)
                activity_node.add_child(child_node)
                child_index += 1

        return activity_node

    def _is_activity_element(self, element: ET.Element) -> bool:
        """Check if XML element represents an activity."""
        # Simple heuristic: activities usually have DisplayName or are known activity types
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        # Known activity types
        activity_patterns = [
            "Sequence", "Flowchart", "If", "While", "ForEach", "DoWhile",
            "TryCatch", "Assign", "WriteLine", "InvokeWorkflowFile",
            "Click", "Type", "GetText", "Delay", "LogMessage"
        ]

        return (tag in activity_patterns or
                element.get("DisplayName") is not None or
                "Activity" in tag)

    def _extract_control_flow_edges(self, element: ET.Element, control_flow: WorkflowControlFlow,
                                   parent_id: str, index: int = 0) -> None:
        """Extract control flow edges from XML element."""
        current_id = f"{parent_id}.{index}" if parent_id != "root" else f"root.{index}"

        # Get activity type
        activity_type = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        child_index = 0
        prev_child_id = None

        for child in element:
            if self._is_activity_element(child):
                child_id = f"{current_id}.{child_index}"

                # Add edge based on parent activity type
                if activity_type == "Sequence" and prev_child_id:
                    # Sequential flow
                    control_flow.add_edge(prev_child_id, child_id, "seq-next")
                elif activity_type == "If":
                    # Conditional flow
                    condition = "then" if child_index == 0 else "else"
                    control_flow.add_edge(current_id, child_id, f"branch-{condition}")
                elif activity_type in ["While", "DoWhile", "ForEach"]:
                    # Loop flow
                    control_flow.add_edge(current_id, child_id, "loop-enter")
                    control_flow.add_edge(child_id, current_id, "loop-back")
                elif activity_type == "TryCatch":
                    # Exception handling flow
                    flow_type = "try" if child_index == 0 else "catch"
                    control_flow.add_edge(current_id, child_id, flow_type)
                else:
                    # Default flow
                    control_flow.add_edge(current_id, child_id, "contains")

                # Recursively process child
                self._extract_control_flow_edges(child, control_flow, current_id, child_index)

                prev_child_id = child_id
                child_index += 1

    def _extract_resource_references(self, element: ET.Element, resources: WorkflowResources,
                                   parent_id: str, index: int = 0) -> None:
        """Extract resource references from XML element."""
        current_id = f"{parent_id}.{index}" if parent_id != "root" else f"root.{index}"

        # Check element attributes for resource references
        for attr_name, attr_value in element.attrib.items():
            if attr_value and isinstance(attr_value, str):
                # Check for different resource types
                if attr_value.endswith((".xaml", ".json", ".txt", ".csv", ".xlsx")):
                    resources.add_reference("file", attr_name, attr_value, current_id, attr_name)
                elif attr_value.startswith("http"):
                    resources.add_reference("url", attr_name, attr_value, current_id, attr_name)
                elif "selector" in attr_name.lower():
                    resources.add_reference("selector", attr_name, attr_value, current_id, attr_name)
                elif "queue" in attr_name.lower():
                    resources.add_reference("queue", attr_name, attr_value, current_id, attr_name)
                elif "{" in attr_value and "}" in attr_value:
                    # Dynamic reference with variables
                    resources.add_reference("dynamic", attr_name, attr_value, current_id, attr_name, is_dynamic=True)

        # Check element text content
        if element.text and element.text.strip():
            text = element.text.strip()
            if any(ext in text for ext in [".xaml", ".json", ".txt", ".csv"]):
                resources.add_reference("file", "text_content", text, current_id, "text")

        # Recursively process children
        child_index = 0
        for child in element:
            if self._is_activity_element(child):
                self._extract_resource_references(child, resources, current_id, child_index)
                child_index += 1
