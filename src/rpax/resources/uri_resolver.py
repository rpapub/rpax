"""
Resource URI Resolver for rpax resource model.

Provides bidirectional mapping between logical URIs and physical file paths.
Implements the rpax:// URI scheme defined in the resource catalog.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


class ResourceUriResolver:
    """
    Resolves rpax:// URIs to file system paths and vice versa.
    
    URI Format: rpax://{lake_name}/{resource_type}[/{resource_id}[/{sub_resource}]]
    
    Examples:
        rpax://dev/projects                                    → .rpax-lake/projects.json
        rpax://dev/projects/calc-f4aa3834                     → .rpax-lake/calc-f4aa3834/v0/manifest.json
        rpax://dev/projects/calc-f4aa3834/workflows           → .rpax-lake/calc-f4aa3834/v0/workflows/index.json
        rpax://dev/projects/calc-f4aa3834/workflows/Main.xaml → .rpax-lake/calc-f4aa3834/v0/workflows/Main.xaml.json
    """
    
    def __init__(self, lake_root: Path, lake_name: str = "default"):
        """
        Initialize URI resolver.
        
        Args:
            lake_root: Path to .rpax-lake directory
            lake_name: Logical name for this lake (used in URIs)
        """
        self.lake_root = Path(lake_root)
        self.lake_name = lake_name
        self.scheme = "rpax"
        
        # Ensure lake directory exists
        self.lake_root.mkdir(parents=True, exist_ok=True)
    
    def resolve_uri(self, uri: str) -> Path:
        """
        Convert rpax:// URI to file system path.
        
        Args:
            uri: rpax:// URI string
            
        Returns:
            Path to the file that contains the resource
            
        Raises:
            ValueError: If URI format is invalid
            FileNotFoundError: If resolved file doesn't exist
        """
        parsed = self._parse_uri(uri)
        file_path = self._uri_to_path(parsed)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Resource not found: {uri} → {file_path}")
        
        return file_path
    
    def generate_uri(self, resource_type: str, project_slug: str = None, 
                    resource_name: str = None, sub_resource: str = None,
                    query_params: Dict[str, str] = None) -> str:
        """
        Generate standard URI for a resource.
        
        Args:
            resource_type: Type of resource (projects, workflows, entry_points, etc.)
            project_slug: Project identifier (required for project-level resources)
            resource_name: Specific resource name (workflows/Main.xaml, etc.)
            sub_resource: Sub-resource path (entry_points/non_test, etc.)
            query_params: Query parameters for filtering
            
        Returns:
            Formatted rpax:// URI
        """
        parts = [f"{self.scheme}://{self.lake_name}", resource_type]
        
        if project_slug:
            parts.append(project_slug)
        
        if resource_name:
            parts.append(resource_name)
        
        if sub_resource:
            parts.extend(sub_resource.split('/'))
        
        uri = '/'.join(parts)
        
        if query_params:
            query_string = '&'.join(f"{k}={v}" for k, v in query_params.items())
            uri = f"{uri}?{query_string}"
        
        return uri
    
    def path_to_uri(self, file_path: Path) -> str:
        """
        Convert file system path back to rpax:// URI.
        
        Args:
            file_path: File system path to resource
            
        Returns:
            Corresponding rpax:// URI
            
        Raises:
            ValueError: If path is not within lake or doesn't match expected structure
        """
        try:
            rel_path = file_path.relative_to(self.lake_root)
        except ValueError:
            raise ValueError(f"Path {file_path} is not within lake {self.lake_root}")
        
        return self._path_to_uri(rel_path)
    
    def list_resources(self, uri_pattern: str) -> List[str]:
        """
        List all resources matching a URI pattern.
        
        Args:
            uri_pattern: URI pattern (supports wildcards)
            
        Returns:
            List of matching URIs
        """
        # Implementation would scan filesystem and generate matching URIs
        # For now, return empty list (placeholder)
        return []
    
    def _parse_uri(self, uri: str) -> Dict[str, str]:
        """Parse rpax:// URI into components."""
        parsed = urlparse(uri)
        
        if parsed.scheme != self.scheme:
            raise ValueError(f"Invalid scheme: {parsed.scheme} (expected {self.scheme})")
        
        if parsed.netloc != self.lake_name:
            raise ValueError(f"Invalid lake name: {parsed.netloc} (expected {self.lake_name})")
        
        # Split path into components
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if not path_parts:
            raise ValueError(f"Invalid URI path: {parsed.path}")
        
        # Validate known resource types
        resource_type = path_parts[0]
        valid_resource_types = {'projects'}  # Add more as needed
        if resource_type not in valid_resource_types:
            raise ValueError(f"Unknown resource type: {resource_type}")
        
        result = {
            'lake_name': parsed.netloc,
            'resource_type': resource_type,
            'path_parts': path_parts,
        }
        
        # Parse query parameters
        if parsed.query:
            result['query_params'] = parse_qs(parsed.query)
        
        return result
    
    def _uri_to_path(self, parsed: Dict[str, str]) -> Path:
        """Convert parsed URI components to file system path."""
        path_parts = parsed['path_parts']
        resource_type = parsed['resource_type']
        
        if resource_type == 'projects':
            return self._resolve_projects_path(path_parts)
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")
    
    def _resolve_projects_path(self, path_parts: List[str]) -> Path:
        """Resolve projects resource path."""
        if len(path_parts) == 1:
            # rpax://dev/projects → projects.json
            return self.lake_root / "projects.json"
        
        elif len(path_parts) == 2:
            # rpax://dev/projects/calc-f4aa3834 → calc-f4aa3834/v0/manifest.json
            project_slug = path_parts[1]
            return self.lake_root / project_slug / "v0" / "manifest.json"
        
        elif len(path_parts) == 3:
            # rpax://dev/projects/calc-f4aa3834/workflows → calc-f4aa3834/v0/workflows/index.json
            project_slug = path_parts[1]
            collection_type = path_parts[2]
            return self.lake_root / project_slug / "v0" / collection_type / "index.json"
        
        elif len(path_parts) == 4:
            # rpax://dev/projects/calc-f4aa3834/workflows/Main.xaml → calc-f4aa3834/v0/workflows/Main.xaml.json
            project_slug = path_parts[1]
            collection_type = path_parts[2]
            resource_name = path_parts[3]
            
            if collection_type == 'workflows':
                return self.lake_root / project_slug / "v0" / "workflows" / f"{resource_name}.json"
            elif collection_type == 'entry_points':
                # For entry points, need to determine category and detail level
                # Default to non_test/medium for basic resolution
                return self.lake_root / project_slug / "v0" / "entry_points" / "non_test" / f"{resource_name}_medium.json"
            elif collection_type == 'dependencies':
                return self.lake_root / project_slug / "v0" / "dependencies.json"
            elif collection_type == 'call_graphs':
                # Default to medium detail level
                return self.lake_root / project_slug / "v0" / "call_graphs" / "project_medium.json"
            else:
                raise ValueError(f"Unknown collection type: {collection_type}")
        
        elif len(path_parts) >= 5:
            # Handle more complex paths like:
            # rpax://dev/projects/calc-f4aa3834/entry_points/non_test/_all_medium.json
            project_slug = path_parts[1]
            collection_type = path_parts[2]
            
            if collection_type == 'entry_points':
                category = path_parts[3]  # non_test, test
                resource_file = path_parts[4]  # _all_medium.json, Main.xaml_medium.json
                return self.lake_root / project_slug / "v0" / "entry_points" / category / resource_file
            elif collection_type == 'call_graphs':
                detail_level = path_parts[3]  # project_low.json, project_medium.json
                return self.lake_root / project_slug / "v0" / "call_graphs" / f"project_{detail_level}.json"
            else:
                raise ValueError(f"Complex path not supported for {collection_type}")
        
        else:
            raise ValueError(f"Invalid projects path: {'/'.join(path_parts)}")
    
    def _path_to_uri(self, rel_path: Path) -> str:
        """Convert relative path back to URI."""
        parts = rel_path.parts
        
        if parts[0] == "projects.json":
            # projects.json → rpax://dev/projects
            return f"{self.scheme}://{self.lake_name}/projects"
        
        elif len(parts) >= 3 and parts[1] == "v0":
            # calc-f4aa3834/v0/manifest.json → rpax://dev/projects/calc-f4aa3834
            project_slug = parts[0]
            
            if parts[2] == "manifest.json":
                return f"{self.scheme}://{self.lake_name}/projects/{project_slug}"
            
            elif len(parts) >= 4:
                collection_type = parts[2]
                
                if parts[3] == "index.json":
                    # workflows/index.json → rpax://dev/projects/calc-f4aa3834/workflows
                    return f"{self.scheme}://{self.lake_name}/projects/{project_slug}/{collection_type}"
                
                elif collection_type == "workflows" and parts[3].endswith(".json"):
                    # workflows/Main.xaml.json → rpax://dev/projects/calc-f4aa3834/workflows/Main.xaml
                    workflow_name = parts[3][:-5]  # Remove .json
                    return f"{self.scheme}://{self.lake_name}/projects/{project_slug}/workflows/{workflow_name}"
                
                elif collection_type == "entry_points" and len(parts) >= 5:
                    # entry_points/non_test/_all_medium.json → 
                    # rpax://dev/projects/calc-f4aa3834/entry_points/non_test/_all_medium.json
                    category = parts[3]
                    filename = parts[4]
                    return f"{self.scheme}://{self.lake_name}/projects/{project_slug}/entry_points/{category}/{filename}"
        
        raise ValueError(f"Cannot convert path to URI: {rel_path}")


# Convenience functions for common URI operations
def create_resolver(lake_root: Path, lake_name: str = "default") -> ResourceUriResolver:
    """Create a ResourceUriResolver instance."""
    return ResourceUriResolver(lake_root, lake_name)


def resolve_uri(uri: str, lake_root: Path, lake_name: str = "default") -> Path:
    """Quick URI resolution without creating resolver instance."""
    resolver = ResourceUriResolver(lake_root, lake_name)
    return resolver.resolve_uri(uri)


# URI generation helpers
class UriBuilder:
    """Builder pattern for constructing rpax:// URIs."""
    
    def __init__(self, resolver: ResourceUriResolver):
        self.resolver = resolver
    
    def lake(self) -> str:
        """URI for entire lake."""
        return self.resolver.generate_uri("projects")
    
    def project(self, project_slug: str) -> str:
        """URI for specific project."""
        return self.resolver.generate_uri("projects", project_slug)
    
    def workflows(self, project_slug: str, workflow_name: str = None) -> str:
        """URI for workflows collection or specific workflow."""
        return self.resolver.generate_uri("workflows", project_slug, workflow_name)
    
    def workflow(self, project_slug: str, workflow_name: str) -> str:
        """URI for specific workflow."""
        return self.resolver.generate_uri("projects", project_slug, workflow_name, "workflows")
    
    def entry_point(self, project_slug: str, entry_point_name: str, 
                   category: str = "non_test", detail: str = "medium") -> str:
        """URI for specific entry point."""
        sub_resource = f"{category}/{entry_point_name}_{detail}.json"
        return self.resolver.generate_uri("projects", project_slug, None, f"entry_points/{sub_resource}")
    
    def dependencies(self, project_slug: str) -> str:
        """URI for project dependencies."""
        return self.resolver.generate_uri("projects", project_slug, None, "dependencies")
    
    def call_graph(self, project_slug: str, detail: str = "medium") -> str:
        """URI for project call graph."""
        return self.resolver.generate_uri("projects", project_slug, None, f"call_graphs/project_{detail}.json")