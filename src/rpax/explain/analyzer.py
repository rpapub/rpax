"""Workflow analysis and explanation engine."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..config import RpaxConfig
from ..validation.framework import ArtifactSet

logger = logging.getLogger(__name__)


@dataclass
class ArgumentInfo:
    """Information about workflow arguments."""
    name: str
    direction: str  # "In", "Out", "InOut"
    type_name: str | None = None
    default_value: str | None = None
    description: str | None = None


@dataclass
class InvocationInfo:
    """Information about workflow invocations."""
    target_workflow: str
    kind: str  # "invoke", "invoke-missing", "invoke-dynamic"
    arguments: dict[str, str] = field(default_factory=dict)
    line_number: int | None = None


@dataclass
class CallerInfo:
    """Information about workflows that call this one."""
    caller_workflow: str
    kind: str
    arguments_passed: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowExplanation:
    """Complete explanation of a workflow."""
    workflow_id: str
    display_name: str
    file_path: str
    relative_path: str
    project_name: str

    # Basic metadata
    file_size: int
    last_modified: str | None = None
    parse_successful: bool = True
    parse_errors: list[str] = field(default_factory=list)

    # Arguments and variables
    arguments: list[ArgumentInfo] = field(default_factory=list)

    # Invocations and relationships
    invokes: list[InvocationInfo] = field(default_factory=list)
    called_by: list[CallerInfo] = field(default_factory=list)

    # Role and classification
    is_entry_point: bool = False
    is_orphan: bool = False
    is_test: bool = False
    folder_category: str | None = None

    # Statistics
    total_invocations: int = 0
    unique_dependencies: int = 0

    @property
    def has_dependencies(self) -> bool:
        return len(self.invokes) > 0

    @property
    def is_reusable(self) -> bool:
        return len(self.called_by) > 1

    @property
    def complexity_score(self) -> str:
        """Simple complexity assessment."""
        if self.total_invocations == 0:
            return "Simple"
        elif self.total_invocations <= 3:
            return "Moderate"
        elif self.total_invocations <= 8:
            return "Complex"
        else:
            return "Very Complex"


class WorkflowAnalyzer:
    """Analyzes workflows from parser artifacts."""

    def __init__(self, config: RpaxConfig):
        self.config = config

    def explain_workflow(self, artifacts_dir: Path, workflow_identifier: str) -> WorkflowExplanation:
        """Explain a specific workflow by ID or path.
        
        Args:
            artifacts_dir: Directory containing parser artifacts
            workflow_identifier: Workflow ID, file name, or partial path
            
        Returns:
            WorkflowExplanation with detailed analysis
        """
        logger.info(f"Analyzing workflow: {workflow_identifier}")

        # Load artifacts
        artifacts = ArtifactSet.load(artifacts_dir)

        if not artifacts.manifest or not artifacts.workflows_index:
            raise ValueError("Required artifacts (manifest.json, workflows.index.json) not found")

        # Find the workflow
        workflow = self._find_workflow(artifacts, workflow_identifier)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_identifier}")

        # Create explanation
        explanation = self._create_base_explanation(workflow, artifacts)

        # Analyze invocations
        self._analyze_invocations(explanation, artifacts)

        # Analyze callers
        self._analyze_callers(explanation, artifacts)

        # Classify workflow
        self._classify_workflow(explanation, artifacts)

        # Calculate statistics
        self._calculate_statistics(explanation)

        logger.info(f"Analysis complete for {explanation.display_name}")
        return explanation

    def list_all_workflows(self, artifacts_dir: Path) -> list[str]:
        """List all available workflow identifiers."""
        artifacts = ArtifactSet.load(artifacts_dir)

        if not artifacts.workflows_index:
            return []

        workflows = []
        for workflow in artifacts.workflows_index.get("workflows", []):
            workflows.append(workflow.get("id", ""))
            # Also add relative paths for easier reference
            if workflow.get("relativePath"):
                workflows.append(workflow.get("relativePath"))

        return [w for w in workflows if w]  # Remove empty strings

    def _find_workflow(self, artifacts: ArtifactSet, identifier: str) -> dict | None:
        """Find workflow by various identifiers."""
        workflows = artifacts.workflows_index.get("workflows", [])

        # First try exact ID match
        for workflow in workflows:
            if workflow.get("id") == identifier:
                return workflow

        # Try relative path match
        for workflow in workflows:
            if workflow.get("relativePath") == identifier:
                return workflow

        # Try file name match
        for workflow in workflows:
            if workflow.get("fileName") == identifier:
                return workflow

        # Try partial path match
        for workflow in workflows:
            rel_path = workflow.get("relativePath", "")
            if identifier.lower() in rel_path.lower():
                return workflow

        # Try display name match
        for workflow in workflows:
            display_name = workflow.get("displayName", "")
            if identifier.lower() in display_name.lower():
                return workflow

        return None

    def _create_base_explanation(self, workflow: dict, artifacts: ArtifactSet) -> WorkflowExplanation:
        """Create base explanation from workflow data."""
        return WorkflowExplanation(
            workflow_id=workflow.get("id", ""),
            display_name=workflow.get("displayName", workflow.get("fileName", "")),
            file_path=workflow.get("filePath", ""),
            relative_path=workflow.get("relativePath", ""),
            project_name=artifacts.manifest.get("projectName", ""),
            file_size=workflow.get("fileSize", 0),
            last_modified=workflow.get("lastModified"),
            parse_successful=workflow.get("parseSuccessful", True),
            parse_errors=workflow.get("parseErrors", [])
        )

    def _analyze_invocations(self, explanation: WorkflowExplanation, artifacts: ArtifactSet) -> None:
        """Analyze what workflows this one invokes."""
        for invocation in artifacts.invocations:
            if invocation.get("from") == explanation.workflow_id:
                invocation_info = InvocationInfo(
                    target_workflow=invocation.get("to", ""),
                    kind=invocation.get("kind", "invoke"),
                    arguments=invocation.get("arguments", {})
                )
                explanation.invokes.append(invocation_info)

    def _analyze_callers(self, explanation: WorkflowExplanation, artifacts: ArtifactSet) -> None:
        """Analyze what workflows call this one."""
        for invocation in artifacts.invocations:
            if invocation.get("to") == explanation.workflow_id:
                caller_info = CallerInfo(
                    caller_workflow=invocation.get("from", ""),
                    kind=invocation.get("kind", "invoke"),
                    arguments_passed=invocation.get("arguments", {})
                )
                explanation.called_by.append(caller_info)

    def _classify_workflow(self, explanation: WorkflowExplanation, artifacts: ArtifactSet) -> None:
        """Classify workflow role and category."""
        # Check if entry point
        entry_points = artifacts.manifest.get("entryPoints", [])
        main_workflow = artifacts.manifest.get("mainWorkflow")

        if main_workflow and main_workflow in explanation.relative_path:
            explanation.is_entry_point = True

        for entry in entry_points:
            if isinstance(entry, dict) and entry.get("filePath") == explanation.relative_path:
                explanation.is_entry_point = True
                break

        # Check if orphan (not called by anyone)
        explanation.is_orphan = len(explanation.called_by) == 0 and not explanation.is_entry_point

        # Check if test workflow
        rel_path = explanation.relative_path.lower()
        explanation.is_test = any(keyword in rel_path for keyword in ["test", "spec", "unit", "integration"])

        # Determine folder category
        if "/" in explanation.relative_path:
            explanation.folder_category = explanation.relative_path.split("/")[0]

    def _calculate_statistics(self, explanation: WorkflowExplanation) -> None:
        """Calculate workflow statistics."""
        explanation.total_invocations = len(explanation.invokes)
        explanation.unique_dependencies = len(set(inv.target_workflow for inv in explanation.invokes))
