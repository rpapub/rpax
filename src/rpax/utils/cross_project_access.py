"""Cross-project access utilities for MCP-optimized interactions.

Provides fuzzy project resolution, disambiguation, and cross-project summaries
optimized for MCP request-response patterns.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class ProjectMatch:
    """Represents a project match with confidence score."""
    slug: str
    name: str
    display_name: str
    project_type: str
    confidence: float
    match_type: str  # "exact", "partial", "fuzzy"
    

class CrossProjectAccessor:
    """Provides MCP-optimized cross-project access patterns."""
    
    def __init__(self, lake_root: Path):
        self.lake_root = Path(lake_root)
        self.lake_index = self._load_lake_index()
        
    def _load_lake_index(self) -> Optional[Dict[str, Any]]:
        """Load lake index if it exists."""
        lake_index_path = self.lake_root / "lake_index.json"
        if not lake_index_path.exists():
            return None
            
        try:
            with open(lake_index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load lake index: {e}")
            return None
    
    def resolve_project(self, query: str, max_results: int = 5) -> List[ProjectMatch]:
        """Resolve project from partial name with fuzzy matching.
        
        Args:
            query: Partial project name or identifier
            max_results: Maximum number of matches to return
            
        Returns:
            List of ProjectMatch objects ordered by confidence
        """
        if not self.lake_index:
            return []
            
        matches = []
        query_lower = query.lower()
        
        # Get projects from lake index
        projects = self.lake_index.get("projects", [])
        search_indices = self.lake_index.get("search_indices", {})
        
        # 1. Exact match by slug or name
        for project in projects:
            slug = project.get("project_slug", "")
            name = project.get("name", "")
            display_name = project.get("display_name", name)
            project_type = project.get("project_type", "unknown")
            
            if query_lower == slug.lower() or query_lower == name.lower():
                matches.append(ProjectMatch(
                    slug=slug,
                    name=name,
                    display_name=display_name,
                    project_type=project_type,
                    confidence=1.0,
                    match_type="exact"
                ))
        
        # 2. Partial name matching (using existing indices)
        partial_matches = search_indices.get("by_partial_name", {}).get(query_lower, [])
        for slug in partial_matches:
            if any(m.slug == slug for m in matches):
                continue  # Already have exact match
                
            project = next((p for p in projects if p.get("project_slug") == slug), None)
            if project:
                confidence = len(query_lower) / len(slug)  # Longer query = higher confidence
                matches.append(ProjectMatch(
                    slug=project.get("project_slug", ""),
                    name=project.get("name", ""),
                    display_name=project.get("display_name", project.get("name", "")),
                    project_type=project.get("project_type", "unknown"),
                    confidence=confidence,
                    match_type="partial"
                ))
        
        # 3. Fuzzy matching for other projects
        for project in projects:
            slug = project.get("project_slug", "")
            name = project.get("name", "")
            
            if any(m.slug == slug for m in matches):
                continue  # Already matched
                
            # Calculate fuzzy match confidence
            slug_similarity = SequenceMatcher(None, query_lower, slug.lower()).ratio()
            name_similarity = SequenceMatcher(None, query_lower, name.lower()).ratio()
            confidence = max(slug_similarity, name_similarity)
            
            # Only include if reasonably similar
            if confidence >= 0.4:
                matches.append(ProjectMatch(
                    slug=slug,
                    name=name,
                    display_name=project.get("display_name", name),
                    project_type=project.get("project_type", "unknown"),
                    confidence=confidence,
                    match_type="fuzzy"
                ))
        
        # Sort by confidence (descending) and limit results
        matches.sort(key=lambda m: (-m.confidence, m.slug))
        return matches[:max_results]
    
    def get_project_entry_points(self, project_slug: str, detail_level: str = "medium") -> Optional[Dict[str, Any]]:
        """Get entry points for a specific project.
        
        Args:
            project_slug: Project slug identifier
            detail_level: Detail level ("low", "medium", "high")
            
        Returns:
            Entry points data or None if not found
        """
        if not self.lake_index:
            return None
            
        # Find project in lake index
        project = next((p for p in self.lake_index.get("projects", []) 
                       if p.get("project_slug") == project_slug), None)
        if not project:
            return None
        
        # Get entry points resource path
        resources = project.get("resources", {})
        if detail_level == "medium":
            entry_points_path = resources.get("entry_points_all_medium")
        else:
            # For now, default to medium if other levels not available
            entry_points_path = resources.get("entry_points_all_medium")
            
        if not entry_points_path:
            return None
        
        # Load entry points file
        try:
            full_path = self.lake_root / entry_points_path.replace('\\', '/')
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load entry points for {project_slug}: {e}")
            return None
    
    def get_cross_project_summary(self, detail_level: str = "low") -> Dict[str, Any]:
        """Get cross-project summary for governance use cases.
        
        Args:
            detail_level: Detail level for summary
            
        Returns:
            Cross-project summary data
        """
        if not self.lake_index:
            return {"error": "No lake index available"}
        
        projects = self.lake_index.get("projects", [])
        statistics = self.lake_index.get("statistics", {})
        
        summary = {
            "lake_overview": {
                "total_projects": statistics.get("total_projects", 0),
                "total_workflows": statistics.get("total_workflows", 0),
                "total_entry_points": statistics.get("total_entry_points", 0),
                "schema_versions": statistics.get("schema_versions", {}),
                "project_types": statistics.get("project_types", {})
            },
            "projects": []
        }
        
        for project in projects:
            project_summary = {
                "slug": project.get("project_slug"),
                "name": project.get("name"),
                "display_name": project.get("display_name"),
                "type": project.get("project_type"),
                "statistics": project.get("statistics", {})
            }
            
            if detail_level in ["medium", "high"]:
                project_summary["entry_points"] = project.get("entry_points", [])
                project_summary["resources"] = project.get("resources", {})
            
            if detail_level == "high":
                project_summary["last_updated"] = project.get("last_updated")
                project_summary["schema_version"] = project.get("schema_version")
                
            summary["projects"].append(project_summary)
        
        return summary
    
    def get_disambiguation_prompt(self, matches: List[ProjectMatch]) -> str:
        """Generate disambiguation prompt for multiple matches.
        
        Args:
            matches: List of project matches
            
        Returns:
            Human-readable disambiguation prompt
        """
        if not matches:
            return "No projects found matching your query."
        
        if len(matches) == 1:
            return f"Found 1 project: {matches[0].display_name} ({matches[0].slug})"
        
        prompt = f"Found {len(matches)} matching projects:\n"
        for i, match in enumerate(matches, 1):
            confidence_pct = int(match.confidence * 100)
            prompt += f"  {i}. {match.display_name} ({match.slug}) - {match.project_type} [{confidence_pct}% match]\n"
        
        prompt += "\nPlease specify which project you want to access."
        return prompt
    
    def build_resource_uri(self, project_slug: str, resource_type: str, resource_path: str = "") -> str:
        """Build MCP-compatible resource URI for cross-project navigation.
        
        Args:
            project_slug: Project slug identifier
            resource_type: Type of resource (entry_points, workflows, manifest, etc.)
            resource_path: Optional specific resource path
            
        Returns:
            MCP-compatible resource URI
        """
        base_uri = f"uipath://proj/{project_slug}/{resource_type}"
        if resource_path:
            base_uri += f"/{resource_path}"
        return base_uri
    
    def get_project_resources(self, project_slug: str) -> Dict[str, str]:
        """Get available resources for a project as URI mappings.
        
        Args:
            project_slug: Project slug identifier
            
        Returns:
            Dictionary mapping resource names to URIs
        """
        if not self.lake_index:
            return {}
            
        # Find project in lake index
        project = next((p for p in self.lake_index.get("projects", []) 
                       if p.get("project_slug") == project_slug), None)
        if not project:
            return {}
        
        resources = project.get("resources", {})
        resource_uris = {}
        
        # Build URIs for available resources
        if "manifest" in resources:
            resource_uris["manifest"] = self.build_resource_uri(project_slug, "manifest")
        
        if "entry_points_all_medium" in resources:
            resource_uris["entry_points_all_medium"] = self.build_resource_uri(project_slug, "entry_points", "non_test/_all_medium.json")
        
        if "call_graph_medium" in resources:
            resource_uris["call_graph_medium"] = self.build_resource_uri(project_slug, "call_graphs", "project_medium.json")
        
        return resource_uris