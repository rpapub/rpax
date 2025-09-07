"""Pseudocode generator using enhanced XAML analysis."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rpax import __version__
from rpax.parser.enhanced_xaml_analyzer import EnhancedActivityNode, EnhancedXamlAnalyzer
from .models import PseudocodeEntry, PseudocodeArtifact, PseudocodeIndex

logger = logging.getLogger(__name__)


class PseudocodeGenerator:
    """Generate gist-style pseudocode from enhanced XAML analysis."""
    
    def __init__(self):
        self.analyzer = EnhancedXamlAnalyzer()
    
    def generate_workflow_pseudocode(self, xaml_path: Path) -> PseudocodeArtifact:
        """Generate pseudocode for a single workflow.
        
        Args:
            xaml_path: Path to workflow XAML file
            
        Returns:
            PseudocodeArtifact with structured pseudocode entries
        """
        try:
            # Analyze workflow with enhanced parser
            visual_activities, metadata = self.analyzer.analyze_workflow(xaml_path)
            
            if not visual_activities:
                logger.warning(f"No visual activities found in {xaml_path}")
                return self._create_empty_artifact(xaml_path.stem)
            
            # Generate pseudocode entries
            entries = self._generate_pseudocode_entries(visual_activities)
            
            # Create artifact
            artifact = PseudocodeArtifact(
                workflow_id=xaml_path.stem,
                project_id="unknown",  # Default when no project context
                project_slug="unknown",  # Default when no project context
                generated_at=datetime.now(timezone.utc).isoformat(),
                rpax_version=__version__,
                activities=[self._serialize_entry(entry) for entry in entries],
                activity_count=len(visual_activities),
                total_lines=len(entries),
                total_activities=len(visual_activities),
                entries=[self._serialize_entry(entry) for entry in entries],
                metadata={
                    "source_file": str(xaml_path),
                    "generation_method": "enhanced-visual-detection",
                    "parser_metadata": metadata
                }
            )
            
            return artifact
            
        except Exception as e:
            logger.error(f"Failed to generate pseudocode for {xaml_path}: {e}")
            return self._create_empty_artifact(xaml_path.stem, error=str(e))
    
    def generate_project_pseudocode_index(self, project_slug: str, project_id: str, 
                                        pseudocode_artifacts: list[PseudocodeArtifact]) -> PseudocodeIndex:
        """Generate index of all pseudocode artifacts in project.
        
        Args:
            project_slug: Project slug identifier
            project_id: Project ID
            pseudocode_artifacts: List of generated pseudocode artifacts
            
        Returns:
            PseudocodeIndex with project-level metadata
        """
        workflows = []
        
        for artifact in pseudocode_artifacts:
            workflows.append({
                "workflowId": artifact.workflow_id,
                "totalLines": artifact.total_lines,
                "totalActivities": artifact.total_activities,
                "hasError": "error" in artifact.metadata
            })
        
        return PseudocodeIndex(
            project_id=project_id,
            project_slug=project_slug,
            total_workflows=len(pseudocode_artifacts),
            workflows=workflows,
            generated_at=datetime.now(timezone.utc).isoformat()
        )
    
    def _generate_pseudocode_entries(self, activities: list[EnhancedActivityNode]) -> list[PseudocodeEntry]:
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
    
    def _process_activity_recursive(self, activity: EnhancedActivityNode, 
                                  all_activities: list[EnhancedActivityNode], 
                                  indent: int) -> list[PseudocodeEntry]:
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
            path=activity.path,
            formatted_line=formatted_line,
            node_id=activity.node_id,
            depth=activity.depth,
            is_visual=activity.is_visual
        )
        
        entries.append(entry)
        
        # Process children with increased indentation
        children = [act for act in all_activities if act.parent_id == activity.node_id]
        
        for child in children:
            child_entries = self._process_activity_recursive(child, all_activities, indent + 1)
            entries.extend(child_entries)
            entry.children.extend(child_entries)
        
        return entries
    
    def _format_pseudocode_line(self, activity: EnhancedActivityNode, indent: int) -> str:
        """Format single pseudocode line in gist style.
        
        Args:
            activity: Activity node to format
            indent: Indentation level
            
        Returns:
            Formatted pseudocode line
        """
        # Create indentation with hyphens (gist style)
        indent_str = "  " * indent + "- " if indent > 0 else "- "
        
        # Format: - [DisplayName] Tag (Path: Activity/...)
        return f"{indent_str}[{activity.display_name}] {activity.tag} (Path: {activity.path})"
    
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
            "path": entry.path,
            "formattedLine": entry.formatted_line,
            "nodeId": entry.node_id,
            "depth": entry.depth,
            "isVisual": entry.is_visual,
            "children": [self._serialize_entry(child) for child in entry.children]
        }
    
    def _create_empty_artifact(self, workflow_id: str, error: str = None) -> PseudocodeArtifact:
        """Create empty pseudocode artifact for error cases.
        
        Args:
            workflow_id: Workflow identifier
            error: Optional error message
            
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
            generated_at=datetime.now(timezone.utc).isoformat(),
            rpax_version=__version__,
            activities=[],
            activity_count=0,
            total_lines=0,
            total_activities=0,
            entries=[],
            metadata=metadata
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