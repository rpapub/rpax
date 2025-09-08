"""
Activity Resource Generator for converting enhanced activity data to resource format.

Generates individual activity resources from EnhancedActivityNode data,
including package source information and container relationships.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from rpax.parser.activity_package_resolver import ActivityPackageResolver
from rpax.parser.container_info_parser import ContainerInfoParser
from rpax.parser.enhanced_xaml_analyzer import EnhancedActivityNode
from rpax.resources.uri_resolver import ResourceUriResolver, UriBuilder


class ActivityResourceGenerator:
    """Generate individual activity resources from enhanced activity data."""
    
    def __init__(self, output_dir: Path, uri_resolver: ResourceUriResolver):
        self.output_dir = output_dir
        self.uri_resolver = uri_resolver
        self.uri_builder = UriBuilder(uri_resolver)
        self.container_parser = ContainerInfoParser()
    
    def generate_activity_resource(self, activity: EnhancedActivityNode, 
                                 workflow_name: str, project_slug: str,
                                 all_activities: List[EnhancedActivityNode],
                                 package_resolver: ActivityPackageResolver) -> Dict[str, Any]:
        """Generate complete activity resource."""
        
        # Resolve package source
        package_source = package_resolver.resolve_activity_package(activity.tag)
        
        # Parse container information
        container_info = self.container_parser.parse_container_info(activity, all_activities)
        
        # Generate URIs
        workflow_uri = self.uri_builder.workflow(project_slug, workflow_name)
        package_uri = None
        if package_source:
            package_uri = self.uri_resolver.generate_uri("projects", project_slug, package_source.package_name, "packages")
        
        # Find child activities
        child_activities = [child.node_id for child in all_activities if child.parent_id == activity.node_id]
        
        # Build the activity resource
        resource = {
            "activity_info": {
                "node_id": activity.node_id,
                "activity_type": activity.tag,
                "display_name": activity.display_name,
                "path": activity.path,
                "depth": activity.depth,
                "line_number": activity.line_number
            },
            "package_source": {
                "package_name": package_source.package_name if package_source else None,
                "package_version": package_source.package_version if package_source else None,
                "classification": package_source.classification if package_source else None,
                "assembly": package_source.assembly if package_source else None
            },
            "properties": activity.properties,  # Already has is_expression detection ✅
            "container_info": {
                "parent_container": container_info.parent_container,
                "container_type": container_info.container_type,
                "container_branch": container_info.container_branch,
                "is_container": container_info.is_container
            },
            "relationships": {
                "workflow_uri": workflow_uri,
                "package_uri": package_uri,
                "invokes_workflow": activity.invocation_target if hasattr(activity, 'invocation_target') and activity.invocation_target else None,
                "child_activities": child_activities
            }
        }
        
        return resource
    
    def generate_activity_collection(self, activities: List[EnhancedActivityNode],
                                   project_slug: str, workflow_name: str,
                                   package_resolver: ActivityPackageResolver) -> Dict[str, Any]:
        """Generate activity collection resource for a workflow."""
        
        # Generate statistics
        total_activities = len(activities)
        visual_activities = sum(1 for a in activities if a.is_visual)
        container_activities = sum(1 for a in activities if a.tag in ContainerInfoParser.CONTAINER_TYPES)
        
        # Count activities by package
        package_counts = {}
        activity_type_counts = {}
        
        for activity in activities:
            # Count by activity type
            activity_type = activity.tag
            activity_type_counts[activity_type] = activity_type_counts.get(activity_type, 0) + 1
            
            # Count by package
            package_source = package_resolver.resolve_activity_package(activity.tag)
            if package_source:
                package_name = package_source.package_name
                package_counts[package_name] = package_counts.get(package_name, 0) + 1
        
        # Find root container (usually the first Sequence)
        root_container = None
        for activity in activities:
            if activity.depth == 1 and activity.tag in ContainerInfoParser.CONTAINER_TYPES:
                root_container = activity.node_id
                break
        
        # Generate URIs for individual activities
        activity_uris = []
        for activity in activities:
            # Generate a safe activity ID from node_id
            activity_id = self._generate_activity_id(activity.node_id)
            activity_uri = self.uri_resolver.generate_uri(
                "projects", project_slug, workflow_name, f"activities/{activity_id}")
            activity_uris.append({
                "node_id": activity.node_id,
                "activity_type": activity.tag,
                "display_name": activity.display_name,
                "uri": activity_uri
            })
        
        return {
            "collection_info": {
                "workflow_name": workflow_name,
                "project_slug": project_slug,
                "total_activities": total_activities,
                "visual_activities": visual_activities,
                "container_activities": container_activities
            },
            "statistics": {
                "activity_type_counts": activity_type_counts,
                "package_counts": package_counts,
                "max_depth": max(a.depth for a in activities) if activities else 0,
                "root_container": root_container
            },
            "activities": activity_uris,
            "relationships": {
                "workflow_uri": self.uri_builder.workflow(project_slug, workflow_name),
                "project_uri": self.uri_builder.project(project_slug)
            }
        }
    
    def generate_activities_by_package(self, activities: List[EnhancedActivityNode],
                                     project_slug: str, package_name: str,
                                     package_resolver: ActivityPackageResolver) -> Dict[str, Any]:
        """Generate activity collection filtered by package."""
        
        # Filter activities by package
        package_activities = []
        for activity in activities:
            package_source = package_resolver.resolve_activity_package(activity.tag)
            if package_source and package_source.package_name == package_name:
                package_activities.append(activity)
        
        # Count by workflow
        workflow_counts = {}
        activity_type_counts = {}
        
        for activity in package_activities:
            # Count by activity type
            activity_type = activity.tag
            activity_type_counts[activity_type] = activity_type_counts.get(activity_type, 0) + 1
            
            # Extract workflow name from path (would need workflow context)
            # For now, we'll use a placeholder
            workflow_name = "unknown"  # This would be passed in from context
            workflow_counts[workflow_name] = workflow_counts.get(workflow_name, 0) + 1
        
        return {
            "package_info": {
                "package_name": package_name,
                "project_slug": project_slug,
                "total_activities": len(package_activities)
            },
            "statistics": {
                "activity_type_counts": activity_type_counts,
                "workflow_counts": workflow_counts,
                "activity_types": list(activity_type_counts.keys())
            },
            "activities": [
                {
                    "node_id": activity.node_id,
                    "activity_type": activity.tag,
                    "display_name": activity.display_name,
                    "workflow": "unknown",  # Would be passed from context
                    "uri": self.uri_resolver.generate_uri(
                        "projects", project_slug, "unknown", 
                        f"activities/{self._generate_activity_id(activity.node_id)}")
                }
                for activity in package_activities
            ],
            "relationships": {
                "package_uri": self.uri_resolver.generate_uri("projects", project_slug, package_name, "packages"),
                "project_uri": self.uri_builder.project(project_slug)
            }
        }
    
    def _generate_activity_id(self, node_id: str) -> str:
        """Generate a safe file-system friendly ID from node_id."""
        # Convert /Sequence[0]/If[1]/Then/Assign[0] to seq0-if1-then-assign0
        parts = []
        for part in node_id.split('/'):
            if not part:  # Skip empty parts from leading /
                continue
            
            # Extract type and index
            if '[' in part and ']' in part:
                activity_type = part.split('[')[0]
                index = part.split('[')[1].split(']')[0]
                safe_part = f"{activity_type.lower()}{index}"
            else:
                safe_part = part.lower()
            
            parts.append(safe_part)
        
        return '-'.join(parts)
    
    def save_activity_resource(self, resource: Dict[str, Any], 
                             workflow_name: str, activity_node_id: str) -> Path:
        """Save activity resource to file system."""
        activity_id = self._generate_activity_id(activity_node_id)
        
        # Create activities directory structure
        activities_dir = self.output_dir / "activities" / workflow_name
        activities_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        output_path = activities_dir / f"{activity_id}.json"
        
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resource, f, indent=2, ensure_ascii=False)
        
        return output_path