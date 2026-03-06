"""Pseudocode generator using enhanced XAML analysis."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rpax import __version__
from rpax.parser.enhanced_xaml_analyzer import (
    EnhancedActivityNode,
    EnhancedXamlAnalyzer,
)

from .models import PseudocodeArtifact, PseudocodeEntry, PseudocodeIndex

logger = logging.getLogger(__name__)


class PseudocodeGenerator:
    """Generate gist-style pseudocode from enhanced XAML analysis."""

    def __init__(self):
        self.analyzer = EnhancedXamlAnalyzer()

    def generate_workflow_pseudocode(
        self, xaml_path: Path, workflow_id: str | None = None, relative_path: str = ""
    ) -> PseudocodeArtifact:
        """Generate pseudocode for a single workflow.

        Args:
            xaml_path: Path to workflow XAML file
            workflow_id: Stable relative workflow ID (e.g. "Framework/CheckExists").
                         Defaults to the file stem when not provided, which loses
                         subdirectory context and causes filename collisions.
            relative_path: Source XAML relative path (e.g. "Framework/CloseAllApplications.xaml")

        Returns:
            PseudocodeArtifact with structured pseudocode entries
        """
        effective_id = workflow_id or xaml_path.stem
        try:
            # Analyze workflow with enhanced parser
            visual_activities, metadata = self.analyzer.analyze_workflow(xaml_path)

            if not visual_activities:
                logger.warning(f"No visual activities found in {xaml_path}")
                return self._create_empty_artifact(
                    effective_id, relative_path=relative_path
                )

            # Generate pseudocode entries
            entries = self._generate_pseudocode_entries(visual_activities)

            # Create artifact
            artifact = PseudocodeArtifact(
                workflow_id=effective_id,
                project_id="unknown",  # Default when no project context
                project_slug="unknown",  # Default when no project context
                relative_path=relative_path,
                generated_at=datetime.now(UTC).isoformat(),
                rpax_version=__version__,
                activities=[self._serialize_entry(entry) for entry in entries],
                activity_count=len(visual_activities),
                total_lines=len(entries),
                total_activities=len(visual_activities),
                entries=[self._serialize_entry(entry) for entry in entries],
                metadata={
                    "source_file": str(xaml_path),
                    "generation_method": "enhanced-visual-detection",
                    "parser_metadata": metadata,
                },
            )

            return artifact

        except Exception as e:
            logger.error(f"Failed to generate pseudocode for {xaml_path}: {e}")
            return self._create_empty_artifact(
                effective_id, error=str(e), relative_path=relative_path
            )

    def generate_project_pseudocode_index(
        self,
        project_slug: str,
        project_id: str,
        pseudocode_summaries: list[dict],
    ) -> PseudocodeIndex:
        """Generate index of all pseudocode artifacts in project.

        Args:
            project_slug: Project slug identifier
            project_id: Project ID
            pseudocode_summaries: Lightweight list of dicts with keys workflowId,
                totalLines, totalActivities, hasError — full artifacts not required.

        Returns:
            PseudocodeIndex with project-level metadata
        """
        workflows = [
            {
                "workflowId": s["workflowId"],
                "totalLines": s.get("totalLines", 0),
                "totalActivities": s.get("totalActivities", 0),
                "hasError": s.get("hasError", False),
            }
            for s in pseudocode_summaries
        ]

        return PseudocodeIndex(
            project_id=project_id,
            project_slug=project_slug,
            total_workflows=len(pseudocode_summaries),
            workflows=workflows,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def _generate_pseudocode_entries(
        self, activities: list[EnhancedActivityNode]
    ) -> list[PseudocodeEntry]:
        """Generate pseudocode entries from activity nodes.

        Args:
            activities: List of enhanced activity nodes

        Returns:
            List of pseudocode entries with hierarchy
        """
        entries = []

        # Find root activities (those with no parent)
        root_activities = [act for act in activities if act.parent_id is None]

        for root in root_activities:
            entries.extend(self._process_activity_recursive(root, activities, 0))

        return entries

    def _process_activity_recursive(
        self,
        activity: EnhancedActivityNode,
        all_activities: list[EnhancedActivityNode],
        indent: int,
    ) -> list[PseudocodeEntry]:
        """Recursively process activity and its children.

        Args:
            activity: Current activity node
            all_activities: All activity nodes for finding children
            indent: Current indentation level

        Returns:
            List of pseudocode entries for this activity and children
        """
        entries = []

        # Generate pseudocode line for current activity
        formatted_line = self._format_pseudocode_line(activity, indent)

        # Create entry
        entry = PseudocodeEntry(
            indent=indent,
            display_name=activity.display_name,
            tag=activity.tag,
            activity_path=activity.path,
            formatted_line=formatted_line,
            node_id=activity.node_id,
            depth=activity.depth,
            is_visual=activity.is_visual,
        )

        entries.append(entry)

        # Process children with increased indentation
        children = [act for act in all_activities if act.parent_id == activity.node_id]

        for child in children:
            child_entries = self._process_activity_recursive(
                child, all_activities, indent + 1
            )
            entries.extend(child_entries)
            entry.children.extend(child_entries)

        return entries

    def _format_pseudocode_line(
        self, activity: EnhancedActivityNode, indent: int
    ) -> str:
        """Format single pseudocode line in gist style.

        Args:
            activity: Activity node to format
            indent: Indentation level

        Returns:
            Formatted pseudocode line
        """
        # Create indentation with hyphens (gist style)
        indent_str = "  " * indent + "- " if indent > 0 else "- "

        # Format: - [DisplayName] Tag (ActivityPath: Activity/...)
        return f"{indent_str}[{activity.display_name}] {activity.tag} (ActivityPath: {activity.path})"

    def _serialize_entry(self, entry: PseudocodeEntry) -> dict[str, Any]:
        """Serialize pseudocode entry to dictionary.

        Args:
            entry: PseudocodeEntry to serialize

        Returns:
            Dictionary representation
        """
        return {
            "indent": entry.indent,
            "displayName": entry.display_name,
            "tag": entry.tag,
            "activityPath": entry.activity_path,
            "formattedLine": entry.formatted_line,
            "nodeId": entry.node_id,
            "depth": entry.depth,
            "isVisual": entry.is_visual,
            "children": [self._serialize_entry(child) for child in entry.children],
        }

    def _create_empty_artifact(
        self, workflow_id: str, error: str = None, relative_path: str = ""
    ) -> PseudocodeArtifact:
        """Create empty pseudocode artifact for error cases.

        Args:
            workflow_id: Workflow identifier
            error: Optional error message
            relative_path: Source XAML relative path

        Returns:
            Empty PseudocodeArtifact
        """
        metadata = {}
        if error:
            metadata["error"] = error

        return PseudocodeArtifact(
            workflow_id=workflow_id,
            project_id="unknown",  # Default when no project context
            project_slug="unknown",  # Default when no project context
            relative_path=relative_path,
            generated_at=datetime.now(UTC).isoformat(),
            rpax_version=__version__,
            activities=[],
            activity_count=0,
            total_lines=0,
            total_activities=0,
            entries=[],
            metadata=metadata,
        )

    def render_as_text(self, artifact: PseudocodeArtifact) -> str:
        """Render pseudocode artifact as formatted text.

        Args:
            artifact: PseudocodeArtifact to render

        Returns:
            Formatted text representation
        """
        if not artifact.entries:
            return f"# No pseudocode available for {artifact.workflow_id}"

        lines = []

        for entry_data in artifact.entries:
            lines.append(entry_data["formattedLine"])

        return "\n".join(lines)
