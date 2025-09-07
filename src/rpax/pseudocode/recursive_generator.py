"""Recursive pseudocode generator using call graph data (ISSUE-040)."""

import logging
from pathlib import Path
from typing import Dict, List, Set

from rpax.config import RpaxConfig
from rpax.models.callgraph import CallGraphArtifact, WorkflowNode
from rpax.pseudocode.models import PseudocodeArtifact

logger = logging.getLogger(__name__)


class RecursivePseudocodeGenerator:
    """Generates recursive pseudocode by expanding InvokeWorkflowFile activities using call graph data."""

    def __init__(self, config: RpaxConfig, call_graph: CallGraphArtifact):
        self.config = config
        self.call_graph = call_graph
        self.pseudocode_config = config.pseudocode

    def generate_recursive_pseudocode(
        self,
        workflow_id: str,
        pseudocode_artifacts: Dict[str, PseudocodeArtifact],
        visited: Set[str] = None,
        current_depth: int = 0,
        indent_level: int = 0
    ) -> List[str]:
        """Generate recursive pseudocode for a workflow.
        
        Args:
            workflow_id: Starting workflow ID
            pseudocode_artifacts: Map of workflow_id -> PseudocodeArtifact
            visited: Set of visited workflow IDs to detect cycles
            current_depth: Current recursion depth
            indent_level: Current indentation level
            
        Returns:
            List of pseudocode lines with recursive expansion
        """
        if visited is None:
            visited = set()

        # Check depth limit
        if current_depth >= self.pseudocode_config.max_expansion_depth:
            return [self._create_depth_limit_message(workflow_id, indent_level)]

        # Check for cycles
        if workflow_id in visited:
            return self._handle_cycle(workflow_id, indent_level)

        # Get base pseudocode for this workflow
        if workflow_id not in pseudocode_artifacts:
            return [self._create_missing_workflow_message(workflow_id, indent_level)]

        base_artifact = pseudocode_artifacts[workflow_id]
        expanded_lines = []

        # Mark as visited for cycle detection
        visited.add(workflow_id)

        try:
            # Process each line of the base pseudocode
            for activity in base_artifact.activities:
                activity_line = self._format_activity_line(activity, indent_level)
                expanded_lines.append(activity_line)

                # Check if this is an InvokeWorkflowFile activity
                if self._is_invoke_workflow_activity(activity):
                    invoked_workflow_id = self._extract_invoked_workflow_id(activity)
                    
                    if invoked_workflow_id:
                        # Get recursive expansion
                        recursive_lines = self.generate_recursive_pseudocode(
                            invoked_workflow_id,
                            pseudocode_artifacts,
                            visited.copy(),  # Copy to allow different branches
                            current_depth + 1,
                            indent_level + 1
                        )
                        expanded_lines.extend(recursive_lines)

        finally:
            # Remove from visited when backtracking
            visited.discard(workflow_id)

        return expanded_lines

    def _is_invoke_workflow_activity(self, activity: Dict) -> bool:
        """Check if activity is an InvokeWorkflowFile."""
        activity_type = activity.get("type", "")
        display_name = activity.get("displayName", "")
        
        return (
            "InvokeWorkflowFile" in activity_type or
            "Invoke Workflow File" in display_name or
            "invoke" in activity_type.lower()
        )

    def _extract_invoked_workflow_id(self, activity: Dict) -> str | None:
        """Extract the target workflow ID from InvokeWorkflowFile activity."""
        workflow_id = activity.get("workflowId")
        if workflow_id:
            return workflow_id

        # Try to extract from activity path or other fields
        activity_path = activity.get("path", "")
        if "InvokeWorkflowFile" in activity_path:
            # Look for the workflow being invoked in the call graph
            return self._find_target_from_call_graph(activity)

        return None

    def _find_target_from_call_graph(self, activity: Dict) -> str | None:
        """Find target workflow using call graph dependencies."""
        # Get the workflow that contains this activity
        source_workflow_id = activity.get("sourceWorkflowId")
        if not source_workflow_id:
            return None

        # Look in call graph for dependencies from this workflow
        if source_workflow_id in self.call_graph.workflows:
            source_node = self.call_graph.workflows[source_workflow_id]
            
            # Find dependency that matches this activity
            activity_id = activity.get("activityId", "")
            for dependency in source_node.dependencies:
                if activity_id in dependency.call_sites:
                    return dependency.target_workflow_id

        return None

    def _format_activity_line(self, activity: Dict, indent_level: int) -> str:
        """Format an activity as a pseudocode line with proper indentation."""
        indent = "  " * indent_level
        display_name = activity.get("displayName", "")
        activity_type = activity.get("type", "")
        path = activity.get("path", "")

        # Create pseudocode line in gist format
        if display_name:
            line = f"{indent}- [{display_name}] {activity_type}"
        else:
            line = f"{indent}- {activity_type}"

        if path:
            line += f" (Path: {path})"

        return line

    def _create_depth_limit_message(self, workflow_id: str, indent_level: int) -> str:
        """Create message for depth limit reached."""
        indent = "  " * indent_level
        return f"{indent}[DEPTH LIMIT REACHED: {workflow_id}] (max depth: {self.pseudocode_config.max_expansion_depth})"

    def _create_missing_workflow_message(self, workflow_id: str, indent_level: int) -> str:
        """Create message for missing workflow."""
        indent = "  " * indent_level
        return f"{indent}[MISSING WORKFLOW: {workflow_id}] (pseudocode not found)"

    def _handle_cycle(self, workflow_id: str, indent_level: int) -> List[str]:
        """Handle cycle detection based on configuration."""
        indent = "  " * indent_level
        
        if self.pseudocode_config.cycle_handling == "detect_and_mark":
            return [f"{indent}[CYCLE DETECTED: {workflow_id}] (already expanded above)"]
        elif self.pseudocode_config.cycle_handling == "detect_and_stop":
            return [f"{indent}[CYCLE DETECTED: {workflow_id}] (expansion stopped)"]
        elif self.pseudocode_config.cycle_handling == "ignore":
            # Continue expansion but log warning
            logger.warning(f"Cycle detected for {workflow_id}, ignoring cycle handling")
            return []
        else:
            return [f"{indent}[CYCLE DETECTED: {workflow_id}] (unknown handling: {self.pseudocode_config.cycle_handling})"]

    def generate_expanded_artifact(
        self,
        workflow_id: str,
        base_artifact: PseudocodeArtifact,
        pseudocode_artifacts: Dict[str, PseudocodeArtifact]
    ) -> PseudocodeArtifact:
        """Generate expanded pseudocode artifact with recursive content."""
        
        # Generate recursive pseudocode
        expanded_lines = self.generate_recursive_pseudocode(
            workflow_id, pseudocode_artifacts
        )

        # Create expanded artifact
        expanded_artifact = PseudocodeArtifact(
            workflow_id=base_artifact.workflow_id,
            project_id=base_artifact.project_id,
            project_slug=base_artifact.project_slug,
            schema_version="1.1.0",  # Increment for expanded format
            generated_at=base_artifact.generated_at,
            rpax_version=base_artifact.rpax_version,
            activities=base_artifact.activities,  # Keep original activities
            activity_count=base_artifact.activity_count,
            generation_config=base_artifact.generation_config,
            # Add expanded content
            expanded_pseudocode=expanded_lines,
            expansion_config={
                "max_depth": self.pseudocode_config.max_expansion_depth,
                "cycle_handling": self.pseudocode_config.cycle_handling,
                "generated_recursive": True
            }
        )

        return expanded_artifact


def load_call_graph_artifact(call_graph_file: Path) -> CallGraphArtifact:
    """Load call graph artifact from file."""
    import json
    
    with open(call_graph_file, encoding="utf-8") as f:
        call_graph_data = json.load(f)
    
    return CallGraphArtifact(**call_graph_data)


def load_pseudocode_artifacts(pseudocode_dir: Path) -> Dict[str, PseudocodeArtifact]:
    """Load all pseudocode artifacts from directory."""
    artifacts = {}
    
    for pseudocode_file in pseudocode_dir.rglob("*.json"):
        if pseudocode_file.name == "index.json":
            continue  # Skip index file
            
        try:
            import json
            with open(pseudocode_file, encoding="utf-8") as f:
                artifact_data = json.load(f)
            
            artifact = PseudocodeArtifact(**artifact_data)
            artifacts[artifact.workflow_id] = artifact
            
        except Exception as e:
            logger.warning(f"Failed to load pseudocode artifact {pseudocode_file}: {e}")
    
    return artifacts