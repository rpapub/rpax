"""Activity Resource Manager for integrated artifact generation.

Manages activity resource generation across legacy and V0 pipelines,
integrating ActivityPackageResolver, ContainerInfoParser, and ActivityResourceGenerator.
"""

import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Any

from rpax.config import RpaxConfig
from rpax.models.workflow import WorkflowIndex
from rpax.parser.enhanced_xaml_analyzer import EnhancedXamlAnalyzer
from .activity_package_resolver import ActivityPackageResolver
from .container_info_parser import ContainerInfoParser
from .activity_resource_generator import ActivityResourceGenerator

logger = logging.getLogger(__name__)


class ActivityResourceManager:
    """Manages activity resource generation across all pipelines."""
    
    def __init__(self, config: RpaxConfig):
        self.config = config
        self.package_resolver = ActivityPackageResolver()
        self.container_parser = ContainerInfoParser()
        self.resource_generator = ActivityResourceGenerator()
        self.enhanced_analyzer = EnhancedXamlAnalyzer()
        self.timestamp = datetime.now(UTC).isoformat()
    
    def generate_activity_resources(
        self,
        workflow_index: WorkflowIndex,
        project_root: Path,
        project_slug: str,
        output_dir: Path
    ) -> Dict[str, Path]:
        """Generate activity resources for all workflows.
        
        Args:
            workflow_index: Discovered workflows
            project_root: Root directory of project
            project_slug: Project slug identifier  
            output_dir: Output directory for artifacts
            
        Returns:
            Dict mapping artifact names to file paths
        """
        if not self.config.output.generate_activities:
            logger.debug("Activity resource generation disabled")
            return {}
        
        logger.info(f"Generating activity resources for {len(workflow_index.workflows)} workflows")
        
        # Create activities directory structure
        activities_dir = output_dir / "activities"
        activities_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts = {}
        activity_resources = []
        
        # Generate activity resources for each workflow
        for workflow in workflow_index.workflows:
            try:
                workflow_artifacts = self._generate_workflow_activity_resources(
                    workflow, project_root, project_slug, activities_dir
                )
                artifacts.update(workflow_artifacts)
                
                # Collect resource data for index
                if workflow_artifacts:
                    activity_resources.append({
                        "workflow_id": workflow.workflow_id,
                        "workflow_path": workflow.relative_path,
                        "resource_file": f"activities/{workflow.workflow_id}.json",
                        "activity_count": self._count_workflow_activities(workflow, project_root),
                        "generated_at": self.timestamp
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to generate activity resources for {workflow.workflow_id}: {e}")
                continue
        
        # Generate activity resources index
        if activity_resources:
            index_artifacts = self._generate_activity_index(
                activities_dir, project_slug, activity_resources
            )
            artifacts.update(index_artifacts)
        
        logger.info(f"Generated activity resources: {len(activity_resources)} workflows processed")
        return artifacts
    
    def _generate_workflow_activity_resources(
        self,
        workflow,
        project_root: Path,
        project_slug: str,
        activities_dir: Path
    ) -> Dict[str, Path]:
        """Generate activity resources for a single workflow."""
        workflow_path = project_root / workflow.relative_path
        
        if not workflow_path.exists():
            logger.warning(f"Workflow file not found: {workflow_path}")
            return {}
        
        try:
            # Use enhanced XAML analyzer to get activities
            activity_tree = self.enhanced_analyzer.extract_activity_tree(workflow_path)
            if not activity_tree or not hasattr(activity_tree, 'activities'):
                logger.debug(f"No activities found in {workflow.workflow_id}")
                return {}
            
            activities = activity_tree.activities
            if not activities:
                return {}
            
            # Generate activity resources using the resource generator
            activity_resource_data = []
            
            for activity in activities:
                try:
                    resource = self.resource_generator.generate_activity_resource(
                        activity, workflow.workflow_id, project_slug, activities, self.package_resolver
                    )
                    activity_resource_data.append(resource)
                    
                except Exception as e:
                    logger.debug(f"Failed to generate resource for activity {activity.node_id}: {e}")
                    continue
            
            if not activity_resource_data:
                return {}
            
            # Create activity resource artifact
            artifact_data = {
                "schema_version": "1.0.0",
                "workflow_id": workflow.workflow_id,
                "workflow_path": workflow.relative_path,
                "project_slug": project_slug,
                "generated_at": self.timestamp,
                "total_activities": len(activity_resource_data),
                "activities": activity_resource_data
            }
            
            # Write activity resource file
            safe_workflow_id = workflow.workflow_id.replace("/", "_").replace("\\", "_")
            resource_file = activities_dir / f"{safe_workflow_id}.json"
            
            # Ensure parent directory exists
            resource_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(resource_file, "w", encoding="utf-8") as f:
                json.dump(artifact_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Generated activity resources: {resource_file} ({len(activity_resource_data)} activities)")
            
            return {f"activity_resources_{safe_workflow_id}": resource_file}
            
        except Exception as e:
            logger.error(f"Failed to generate activity resources for {workflow.workflow_id}: {e}")
            return {}
    
    def _generate_activity_index(
        self,
        activities_dir: Path,
        project_slug: str,
        activity_resources: List[Dict[str, Any]]
    ) -> Dict[str, Path]:
        """Generate activity resource index."""
        
        # Calculate statistics
        total_activities = sum(
            res.get("activity_count", 0) for res in activity_resources
        )
        
        # Group by workflow directory for organization
        by_directory = {}
        for resource in activity_resources:
            workflow_path = Path(resource["workflow_path"])
            directory = str(workflow_path.parent) if workflow_path.parent != Path(".") else "root"
            
            if directory not in by_directory:
                by_directory[directory] = []
            by_directory[directory].append(resource)
        
        # Create index data
        index_data = {
            "schema_version": "1.0.0",
            "project_slug": project_slug,
            "generated_at": self.timestamp,
            "total_workflows": len(activity_resources),
            "total_activities": total_activities,
            "resources": activity_resources,
            "by_directory": by_directory,
            "navigation": {
                "individual_resources": "activities/{workflow_id}.json",
                "description": "Activity-centric resources with package relationships and container hierarchies"
            }
        }
        
        # Write index file
        index_file = activities_dir / "index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Generated activity resource index: {index_file}")
        return {"activity_resources_index": index_file}
    
    def _count_workflow_activities(self, workflow, project_root: Path) -> int:
        """Count activities in a workflow."""
        try:
            workflow_path = project_root / workflow.relative_path
            if not workflow_path.exists():
                return 0
            
            activity_tree = self.enhanced_analyzer.extract_activity_tree(workflow_path)
            if not activity_tree or not hasattr(activity_tree, 'activities'):
                return 0
            
            return len(activity_tree.activities)
            
        except Exception as e:
            logger.debug(f"Failed to count activities for {workflow.workflow_id}: {e}")
            return 0
    
    def generate_v0_activity_resources(
        self,
        workflow_index: WorkflowIndex,
        project_root: Path,
        project_slug: str,
        v0_dir: Path
    ) -> Dict[str, Path]:
        """Generate activity resources for V0 schema with progressive disclosure.
        
        Args:
            workflow_index: Discovered workflows
            project_root: Root directory of project
            project_slug: Project slug identifier
            v0_dir: V0 schema directory
            
        Returns:
            Dict mapping artifact names to file paths
        """
        if not self.config.output.generate_activities:
            return {}
        
        # Create V0 activities directory structure
        v0_activities_dir = v0_dir / "activities"
        v0_activities_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts = {}
        
        # Generate activity resources using the same logic but in V0 structure
        activity_artifacts = self.generate_activity_resources(
            workflow_index, project_root, project_slug, v0_activities_dir.parent
        )
        
        # Move activities to V0 structure and update artifact names
        v0_artifacts = {}
        for artifact_name, artifact_path in activity_artifacts.items():
            if artifact_name.startswith("activity_resources"):
                # Move to V0 directory structure
                new_artifact_name = f"v0_{artifact_name}"
                v0_artifacts[new_artifact_name] = artifact_path
        
        return v0_artifacts
    
    def get_activity_resource_navigation(
        self,
        project_slug: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Get navigation URIs for activity resources.
        
        Args:
            project_slug: Project identifier
            workflow_id: Optional specific workflow ID
            
        Returns:
            Dictionary of navigation URIs
        """
        base_uri = f"rpax://projects/{project_slug}/activities"
        
        if workflow_id:
            return {
                "activity_resource": f"{base_uri}/{workflow_id}",
                "index": f"{base_uri}/index"
            }
        else:
            return {
                "index": f"{base_uri}/index",
                "individual_pattern": f"{base_uri}/{{workflow_id}}"
            }