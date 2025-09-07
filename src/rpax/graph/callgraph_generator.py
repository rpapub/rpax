"""Call graph generator for creating first-class call graph artifacts."""

import json
import logging
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from rpax import __version__
from rpax.config import RpaxConfig
from rpax.models.callgraph import (
    CallGraphArtifact,
    CallGraphCycle,
    CallGraphMetrics,
    WorkflowDependency,
    WorkflowNode,
)
from rpax.models.manifest import ProjectManifest
from rpax.models.workflow import WorkflowIndex
from rpax.utils.paths import normalize_path

logger = logging.getLogger(__name__)


class CallGraphGenerator:
    """Generates call graph artifacts from invocations and project data."""

    def __init__(self, config: RpaxConfig):
        self.config = config

    def generate_call_graph(
        self,
        manifest: ProjectManifest,
        workflow_index: WorkflowIndex,
        invocations_file: Path,
    ) -> CallGraphArtifact:
        """Generate complete call graph artifact from project data.
        
        Args:
            manifest: Project manifest with metadata and entry points
            workflow_index: Index of all discovered workflows
            invocations_file: Path to invocations.jsonl file
            
        Returns:
            CallGraphArtifact: Complete call graph with cycles and metrics
        """
        logger.info(f"Generating call graph for project {manifest.project_name}")

        # Load invocations data
        invocations = self._load_invocations(invocations_file)
        
        # Extract entry point file paths from EntryPoint objects
        entry_point_paths = [ep.file_path for ep in manifest.entry_points]
        
        # Build workflow nodes
        workflows = self._build_workflow_nodes(workflow_index, entry_point_paths)
        
        # Process invocations into dependencies
        self._process_invocations(workflows, invocations)
        
        # Calculate call depths from entry points
        self._calculate_call_depths(workflows, entry_point_paths)
        
        # Detect cycles
        cycles = self._detect_cycles(workflows)
        
        # Calculate metrics
        metrics = self._calculate_metrics(workflows, cycles)
        
        # Create artifact
        # Generate fallback project_id if not available (for older UiPath projects)
        project_id = manifest.project_id or f"project-{manifest.project_name.lower()}"
        
        call_graph = CallGraphArtifact(
            project_id=project_id,
            project_slug=f"{project_id or manifest.project_name.lower()}-generated",
            generated_at=datetime.now(UTC),
            rpax_version=__version__,
            workflows=workflows,
            entry_points=entry_point_paths,
            cycles=cycles,
            metrics=metrics,
            generation_config=self._get_generation_config(),
        )

        logger.info(
            f"Call graph generated: {metrics.total_workflows} workflows, "
            f"{metrics.total_dependencies} dependencies, {metrics.cycles_detected} cycles"
        )

        return call_graph

    def _load_invocations(self, invocations_file: Path) -> List[Dict[str, Any]]:
        """Load invocations from JSONL file."""
        if not invocations_file.exists():
            logger.warning(f"Invocations file not found: {invocations_file}")
            return []

        invocations = []
        try:
            with open(invocations_file, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip comment lines
                        try:
                            invocation = json.loads(line)
                            invocations.append(invocation)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON on line {line_num}: {e}")

        except Exception as e:
            logger.error(f"Error reading invocations file: {e}")

        logger.debug(f"Loaded {len(invocations)} invocations")
        return invocations

    def _build_workflow_nodes(
        self, workflow_index: WorkflowIndex, entry_points: List[str]
    ) -> Dict[str, WorkflowNode]:
        """Build workflow nodes from workflow index."""
        workflows = {}
        
        # Normalize entry points for flexible matching
        entry_point_set = set(entry_points)
        # Also add normalized versions for case-insensitive and path-flexible matching
        normalized_entry_points = set()
        for ep in entry_points:
            normalized_entry_points.add(ep.lower())  # case insensitive
            normalized_entry_points.add(ep.split("/")[-1].lower())  # filename only
        
        def is_entry_point(workflow_id: str, relative_path: str) -> bool:
            """Check if workflow is an entry point using flexible matching."""
            return (
                workflow_id in entry_point_set or
                workflow_id.lower() in normalized_entry_points or
                relative_path in entry_point_set or
                relative_path.lower() in normalized_entry_points or
                relative_path.split("/")[-1].lower() in normalized_entry_points
            )

        for workflow in workflow_index.workflows:
            workflow_id = workflow.workflow_id
            is_ep = is_entry_point(workflow_id, workflow.relative_path)
            
            node = WorkflowNode(
                workflow_id=workflow_id,
                workflow_path=workflow.relative_path,
                display_name=workflow.display_name or workflow.file_name,
                is_entry_point=is_ep,
                call_depth=0 if is_ep else -1,  # -1 means not calculated yet
            )
            workflows[workflow_id] = node

        return workflows

    def _process_invocations(
        self, workflows: Dict[str, WorkflowNode], invocations: List[Dict[str, Any]]
    ) -> None:
        """Process invocations into workflow dependencies."""
        for invocation in invocations:
            source_id = invocation.get("source_workflow_id")
            target_path = invocation.get("target_workflow_path", "")
            invocation_type = invocation.get("invocation_type", "unknown")
            activity_id = invocation.get("activity_id", "")
            arguments = invocation.get("arguments", {})

            if not source_id:
                continue

            # Find target workflow by path
            target_id = self._find_target_workflow_id(workflows, target_path)

            if not target_id and invocation_type != "missing":
                invocation_type = "missing"  # Mark as missing if we can't resolve it

            # Create dependency
            dependency = WorkflowDependency(
                source_workflow_id=source_id,
                target_workflow_id=target_id or "",
                target_workflow_path=target_path,
                invocation_type=invocation_type,
                call_sites=[activity_id] if activity_id else [],
                arguments=arguments,
            )

            # Add to source workflow
            if source_id in workflows:
                workflows[source_id].dependencies.append(dependency)

                # Add to target workflow's dependents (if target exists)
                if target_id and target_id in workflows:
                    if source_id not in workflows[target_id].dependents:
                        workflows[target_id].dependents.append(source_id)

    def _find_target_workflow_id(
        self, workflows: Dict[str, WorkflowNode], target_path: str
    ) -> str | None:
        """Find workflow ID by path or partial path matching."""
        if not target_path:
            return None

        # Normalize path for comparison using central utility
        target_path = normalize_path(target_path)

        # First try exact path match
        for workflow_id, node in workflows.items():
            node_path = normalize_path(node.workflow_path)
            if node_path == target_path:
                return workflow_id

        # Try filename match (always try this for both simple and complex paths)
        target_filename = target_path.split("/")[-1]
        for workflow_id, node in workflows.items():
            node_filename = normalize_path(node.workflow_path).split("/")[-1]
            if node_filename == target_filename:
                return workflow_id

        return None

    def _calculate_call_depths(
        self, workflows: Dict[str, WorkflowNode], entry_points: List[str]
    ) -> None:
        """Calculate call depth for each workflow using BFS from entry points."""
        # Reset depths
        for node in workflows.values():
            node.call_depth = -1

        # Set entry points to depth 0
        queue = deque(entry_points)
        for entry_point in entry_points:
            if entry_point in workflows:
                workflows[entry_point].call_depth = 0

        # BFS to calculate depths
        visited = set()
        while queue:
            current_id = queue.popleft()
            
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id not in workflows:
                continue

            current_node = workflows[current_id]
            current_depth = current_node.call_depth

            # Process dependencies
            for dependency in current_node.dependencies:
                target_id = dependency.target_workflow_id
                if target_id and target_id in workflows:
                    target_node = workflows[target_id]
                    new_depth = current_depth + 1

                    # Update depth if this is a shorter path or first time calculating
                    if target_node.call_depth == -1 or new_depth < target_node.call_depth:
                        target_node.call_depth = new_depth
                        queue.append(target_id)

    def _detect_cycles(self, workflows: Dict[str, WorkflowNode]) -> List[CallGraphCycle]:
        """Detect cycles in the call graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        current_path = []

        def dfs_cycle_detection(workflow_id: str) -> bool:
            if workflow_id not in workflows:
                return False

            if workflow_id in rec_stack:
                # Found cycle - extract it from current path
                cycle_start = current_path.index(workflow_id)
                cycle_workflows = current_path[cycle_start:] + [workflow_id]
                
                # Determine cycle type
                cycle_type = "self" if len(cycle_workflows) == 2 else "mutual" if len(cycle_workflows) == 3 else "complex"
                
                cycle = CallGraphCycle(
                    cycle_id=f"cycle_{len(cycles) + 1}",
                    workflow_ids=cycle_workflows[:-1],  # Remove duplicate end node
                    cycle_type=cycle_type,
                )
                cycles.append(cycle)
                return True

            if workflow_id in visited:
                return False

            visited.add(workflow_id)
            rec_stack.add(workflow_id)
            current_path.append(workflow_id)

            # Check all dependencies
            node = workflows[workflow_id]
            for dependency in node.dependencies:
                target_id = dependency.target_workflow_id
                if target_id and dfs_cycle_detection(target_id):
                    # Continue searching for more cycles
                    pass

            rec_stack.remove(workflow_id)
            current_path.pop()
            return False

        # Run DFS from each unvisited node
        for workflow_id in workflows:
            if workflow_id not in visited:
                dfs_cycle_detection(workflow_id)

        return cycles

    def _calculate_metrics(
        self, workflows: Dict[str, WorkflowNode], cycles: List[CallGraphCycle]
    ) -> CallGraphMetrics:
        """Calculate call graph metrics and statistics."""
        total_workflows = len(workflows)
        entry_points = sum(1 for node in workflows.values() if node.is_entry_point)
        orphaned_workflows = sum(1 for node in workflows.values() if node.call_depth == -1)
        max_call_depth = max((node.call_depth for node in workflows.values() if node.call_depth >= 0), default=0)
        
        # Count dependencies by type
        total_dependencies = 0
        static_invocations = 0
        dynamic_invocations = 0
        missing_invocations = 0

        for node in workflows.values():
            for dependency in node.dependencies:
                total_dependencies += 1
                if dependency.invocation_type == "static":
                    static_invocations += 1
                elif dependency.invocation_type == "dynamic":
                    dynamic_invocations += 1
                elif dependency.invocation_type == "missing":
                    missing_invocations += 1

        return CallGraphMetrics(
            total_workflows=total_workflows,
            total_dependencies=total_dependencies,
            entry_points=entry_points,
            orphaned_workflows=orphaned_workflows,
            max_call_depth=max_call_depth,
            cycles_detected=len(cycles),
            static_invocations=static_invocations,
            dynamic_invocations=dynamic_invocations,
            missing_invocations=missing_invocations,
        )

    def _get_generation_config(self) -> Dict[str, Any]:
        """Get configuration snapshot used for generation."""
        return {
            "parser_enhanced": self.config.parser.use_enhanced,
            "max_scan_depth": self.config.scan.max_depth,
            "follow_dynamic": self.config.scan.follow_dynamic,
        }