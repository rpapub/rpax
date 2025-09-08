"""
Container Information Parser for UiPath activity containers.

Parses container information from activity paths and parent relationships
to identify container types, branches (Then/Else/Catch), and hierarchies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from rpax.parser.enhanced_xaml_analyzer import EnhancedActivityNode


@dataclass
class ContainerInfo:
    """Container relationship information for an activity."""
    parent_container: str | None = None      # node_id of parent container
    container_type: str | None = None        # Sequence, If, TryCatch, etc.
    container_branch: str | None = None      # Then, Else, Catch, Finally, Body
    is_container: bool = False               # True if this activity contains others


class ContainerInfoParser:
    """Parse container information from activity paths and parent relationships."""
    
    # Container activity types that can contain other activities
    CONTAINER_TYPES = {
        "Sequence", "If", "TryCatch", "Parallel", "Pick", "Switch", 
        "ForEach", "While", "DoWhile", "Flowchart", "State", "StateMachine"
    }
    
    # Branch identifiers in container paths
    CONTAINER_BRANCHES = {
        "Then", "Else", "Catch", "Finally", "Body", "Default", 
        "Cases", "Activities", "Triggers", "Actions"
    }
    
    def parse_container_info(self, activity: EnhancedActivityNode, 
                           all_activities: List[EnhancedActivityNode]) -> ContainerInfo:
        """Extract container relationship information."""
        
        # Determine if this activity is a container
        is_container = activity.tag in self.CONTAINER_TYPES
        
        # Parse container branch from path
        container_branch = self._extract_container_branch(activity.path)
        
        # Find parent container information
        parent_container = None
        container_type = None
        
        if activity.parent_id:
            parent = self._find_activity_by_node_id(activity.parent_id, all_activities)
            if parent and self._is_meaningful_container(parent):
                parent_container = parent.node_id
                container_type = parent.tag
        
        return ContainerInfo(
            parent_container=parent_container,
            container_type=container_type,
            container_branch=container_branch,
            is_container=is_container
        )
    
    def _extract_container_branch(self, path: str) -> str | None:
        """Extract container branch from hierarchical path."""
        # Split path and look for branch indicators
        path_parts = path.split('/')
        
        for part in path_parts:
            # Remove array indices for comparison
            clean_part = part.split('[')[0] if '[' in part else part
            if clean_part in self.CONTAINER_BRANCHES:
                return clean_part
        
        return None
    
    def _find_activity_by_node_id(self, node_id: str, 
                                 all_activities: List[EnhancedActivityNode]) -> Optional[EnhancedActivityNode]:
        """Find activity by its node_id."""
        for activity in all_activities:
            if activity.node_id == node_id:
                return activity
        return None
    
    def _is_meaningful_container(self, activity: EnhancedActivityNode) -> bool:
        """Determine if activity is a meaningful container (not just structural)."""
        # Only count visual containers that actually organize workflow logic
        return (activity.is_visual and 
                activity.tag in self.CONTAINER_TYPES)
    
    def build_container_hierarchy(self, all_activities: List[EnhancedActivityNode]) -> Dict[str, List[str]]:
        """Build container hierarchy mapping container_id -> child_activity_ids."""
        hierarchy = {}
        
        for activity in all_activities:
            container_info = self.parse_container_info(activity, all_activities)
            
            if container_info.is_container:
                # Find all direct children of this container
                children = []
                for potential_child in all_activities:
                    if potential_child.parent_id == activity.node_id:
                        children.append(potential_child.node_id)
                
                hierarchy[activity.node_id] = children
        
        return hierarchy
    
    def get_container_statistics(self, container_id: str, 
                               all_activities: List[EnhancedActivityNode]) -> Dict[str, int]:
        """Get statistics about activities within a container."""
        container_activity = self._find_activity_by_node_id(container_id, all_activities)
        if not container_activity:
            return {}
        
        # Find all descendant activities (not just direct children)
        descendants = self._find_all_descendants(container_id, all_activities)
        
        # Count activity types
        activity_type_counts = {}
        visual_count = 0
        max_depth = container_activity.depth
        
        for activity in descendants:
            # Count by activity type
            activity_type = activity.tag
            activity_type_counts[activity_type] = activity_type_counts.get(activity_type, 0) + 1
            
            # Count visual activities
            if activity.is_visual:
                visual_count += 1
            
            # Track maximum depth
            if activity.depth > max_depth:
                max_depth = activity.depth
        
        return {
            "total_child_activities": len(descendants),
            "visual_activities": visual_count,
            "max_depth": max_depth - container_activity.depth,  # Relative depth
            "activity_type_counts": activity_type_counts
        }
    
    def _find_all_descendants(self, container_id: str, 
                            all_activities: List[EnhancedActivityNode]) -> List[EnhancedActivityNode]:
        """Find all descendant activities of a container (recursive)."""
        descendants = []
        
        # Find direct children
        direct_children = [a for a in all_activities if a.parent_id == container_id]
        
        for child in direct_children:
            descendants.append(child)
            
            # If child is also a container, find its descendants recursively
            if child.tag in self.CONTAINER_TYPES:
                descendants.extend(self._find_all_descendants(child.node_id, all_activities))
        
        return descendants
    
    def organize_by_branches(self, container_id: str, 
                           all_activities: List[EnhancedActivityNode]) -> Dict[str, List[str]]:
        """Organize container's child activities by branch (Then/Else/Catch/etc.)."""
        branches = {}
        
        # Find direct children of the container
        direct_children = [a for a in all_activities if a.parent_id == container_id]
        
        for child in direct_children:
            container_info = self.parse_container_info(child, all_activities)
            branch = container_info.container_branch or "Body"  # Default to Body if no specific branch
            
            if branch not in branches:
                branches[branch] = []
            branches[branch].append(child.node_id)
        
        return branches