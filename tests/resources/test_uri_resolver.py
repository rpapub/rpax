"""
Tests for ResourceUriResolver with concrete examples.

Validates the bidirectional mapping between rpax:// URIs and file system paths.
"""
import pytest
from pathlib import Path
from rpax.resources.uri_resolver import ResourceUriResolver, UriBuilder


class TestResourceUriResolver:
    """Test URI resolution with real lake structure."""
    
    def setup_method(self):
        """Set up test lake structure."""
        self.test_lake = Path("/tmp/test-lake")  # Would be temp directory
        self.resolver = ResourceUriResolver(self.test_lake, "dev")
        self.builder = UriBuilder(self.resolver)
        
        # Mock lake structure for testing
        self.mock_files = {
            "projects.json": {"projects": []},
            "calc-f4aa3834/v0/manifest.json": {"project_info": {}},
            "calc-f4aa3834/v0/workflows/index.json": {"workflows": []},
            "calc-f4aa3834/v0/workflows/Main.xaml.json": {"workflow_info": {}},
            "calc-f4aa3834/v0/entry_points/non_test/_all_medium.json": {"entry_points": []},
            "calc-f4aa3834/v0/dependencies.json": {"dependencies": []},
        }
    
    def test_lake_level_uri_resolution(self):
        """Test lake-level resource URI resolution."""
        uri = "rpax://dev/projects"
        expected_path = self.test_lake / "projects.json"
        
        # Test URI → Path
        with pytest.raises(FileNotFoundError):  # File doesn't exist yet
            self.resolver.resolve_uri(uri)
        
        # Test Path → URI  
        rel_path = Path("projects.json")
        result_uri = self.resolver._path_to_uri(rel_path)
        assert result_uri == uri
    
    def test_project_level_uri_resolution(self):
        """Test project manifest URI resolution."""
        uri = "rpax://dev/projects/calc-f4aa3834"
        expected_path = self.test_lake / "calc-f4aa3834" / "v0" / "manifest.json"
        
        parsed = self.resolver._parse_uri(uri)
        actual_path = self.resolver._uri_to_path(parsed)
        assert actual_path == expected_path
        
        # Test Path → URI
        rel_path = Path("calc-f4aa3834/v0/manifest.json")
        result_uri = self.resolver._path_to_uri(rel_path)
        assert result_uri == uri
    
    def test_workflow_collection_uri_resolution(self):
        """Test workflow collection URI resolution."""
        uri = "rpax://dev/projects/calc-f4aa3834/workflows"
        expected_path = self.test_lake / "calc-f4aa3834" / "v0" / "workflows" / "index.json"
        
        parsed = self.resolver._parse_uri(uri)
        actual_path = self.resolver._uri_to_path(parsed)
        assert actual_path == expected_path
    
    def test_specific_workflow_uri_resolution(self):
        """Test specific workflow URI resolution."""
        uri = "rpax://dev/projects/calc-f4aa3834/workflows/Main.xaml"
        expected_path = self.test_lake / "calc-f4aa3834" / "v0" / "workflows" / "Main.xaml.json"
        
        parsed = self.resolver._parse_uri(uri)
        actual_path = self.resolver._uri_to_path(parsed)
        assert actual_path == expected_path
        
        # Test Path → URI
        rel_path = Path("calc-f4aa3834/v0/workflows/Main.xaml.json")
        result_uri = self.resolver._path_to_uri(rel_path)
        assert result_uri == uri
    
    def test_entry_point_uri_resolution(self):
        """Test entry point URI resolution with categories."""
        uri = "rpax://dev/projects/calc-f4aa3834/entry_points/non_test/_all_medium.json"
        expected_path = self.test_lake / "calc-f4aa3834" / "v0" / "entry_points" / "non_test" / "_all_medium.json"
        
        parsed = self.resolver._parse_uri(uri)
        actual_path = self.resolver._uri_to_path(parsed)
        assert actual_path == expected_path
        
        # Test Path → URI
        rel_path = Path("calc-f4aa3834/v0/entry_points/non_test/_all_medium.json")
        result_uri = self.resolver._path_to_uri(rel_path)
        assert result_uri == uri
    
    def test_uri_generation_via_builder(self):
        """Test URI generation using UriBuilder."""
        # Lake URI
        assert self.builder.lake() == "rpax://dev/projects"
        
        # Project URI
        assert self.builder.project("calc-f4aa3834") == "rpax://dev/projects/calc-f4aa3834"
        
        # Workflow collection URI
        assert self.builder.workflows("calc-f4aa3834") == "rpax://dev/workflows/calc-f4aa3834"
        
        # Specific workflow URI
        assert self.builder.workflows("calc-f4aa3834", "Main.xaml") == "rpax://dev/workflows/calc-f4aa3834/Main.xaml"
        
        # Dependencies URI
        assert self.builder.dependencies("calc-f4aa3834") == "rpax://dev/projects/calc-f4aa3834/dependencies"
    
    def test_invalid_uris(self):
        """Test error handling for invalid URIs."""
        invalid_uris = [
            "http://dev/projects",           # Wrong scheme
            "rpax://wrong-lake/projects",    # Wrong lake name
            "rpax://dev",                    # Missing resource type
            "rpax://dev/invalid",            # Unknown resource type
        ]
        
        for uri in invalid_uris:
            with pytest.raises(ValueError):
                self.resolver._parse_uri(uri)
    
    def test_uri_parsing_components(self):
        """Test URI component parsing."""
        uri = "rpax://dev/projects/calc-f4aa3834/workflows/Main.xaml"
        parsed = self.resolver._parse_uri(uri)
        
        assert parsed['lake_name'] == 'dev'
        assert parsed['resource_type'] == 'projects'
        assert parsed['path_parts'] == ['projects', 'calc-f4aa3834', 'workflows', 'Main.xaml']
    
    def test_complex_entry_point_paths(self):
        """Test complex entry point URI patterns."""
        test_cases = [
            {
                'uri': "rpax://dev/projects/calc-f4aa3834/entry_points/non_test/_all_medium.json",
                'path': "calc-f4aa3834/v0/entry_points/non_test/_all_medium.json"
            },
            {
                'uri': "rpax://dev/projects/calc-f4aa3834/entry_points/test/TestMain.xaml_high.json", 
                'path': "calc-f4aa3834/v0/entry_points/test/TestMain.xaml_high.json"
            }
        ]
        
        for case in test_cases:
            parsed = self.resolver._parse_uri(case['uri'])
            actual_path = self.resolver._uri_to_path(parsed)
            expected_path = self.test_lake / case['path']
            assert actual_path == expected_path
    
    def test_generate_cross_reference_uris(self):
        """Test generating URIs for cross-referencing resources."""
        project_slug = "calc-f4aa3834"
        
        # Generate URIs that could be used in resource JSON files
        cross_refs = {
            'project_manifest': self.builder.project(project_slug),
            'workflow_collection': self.builder.workflows(project_slug),
            'main_workflow': self.builder.workflows(project_slug, "Main.xaml"),
            'entry_points': self.builder.entry_point(project_slug, "Main.xaml"),
            'dependencies': self.builder.dependencies(project_slug),
            'call_graph': self.builder.call_graph(project_slug, "medium")
        }
        
        expected = {
            'project_manifest': "rpax://dev/projects/calc-f4aa3834",
            'workflow_collection': "rpax://dev/workflows/calc-f4aa3834", 
            'main_workflow': "rpax://dev/workflows/calc-f4aa3834/Main.xaml",
            'entry_points': "rpax://dev/projects/calc-f4aa3834/entry_points/non_test/Main.xaml_medium.json",
            'dependencies': "rpax://dev/projects/calc-f4aa3834/dependencies",
            'call_graph': "rpax://dev/projects/calc-f4aa3834/call_graphs/project_medium.json"
        }
        
        for key in expected:
            assert cross_refs[key] == expected[key], f"Mismatch for {key}: {cross_refs[key]} != {expected[key]}"


class TestResourceUriIntegration:
    """Integration tests with real resource examples."""
    
    def test_workflow_with_uri_cross_references(self):
        """Test workflow resource with URI cross-references."""
        resolver = ResourceUriResolver(Path("/tmp/test"), "dev")
        builder = UriBuilder(resolver)
        
        # Example workflow resource with URI cross-references
        workflow_resource = {
            "workflow_info": {
                "name": "Main.xaml",
                "path": "Main.xaml", 
                "type": "xaml"
            },
            "invocations": [
                {
                    "target": "Setup.xaml",
                    "target_uri": builder.workflows("calc-f4aa", "Setup.xaml"),
                    "entry_point_uri": builder.entry_point("calc-f4aa", "Setup.xaml")
                }
            ],
            "project_uri": builder.project("calc-f4aa"),
            "dependencies_uri": builder.dependencies("calc-f4aa")
        }
        
        # Validate URI structure
        assert "rpax://dev/" in workflow_resource["invocations"][0]["target_uri"]
        assert "rpax://dev/" in workflow_resource["project_uri"]
        assert "rpax://dev/" in workflow_resource["dependencies_uri"]
    
    def test_manifest_with_navigation_uris(self):
        """Test manifest resource with navigation URIs."""
        resolver = ResourceUriResolver(Path("/tmp/test"), "dev")
        builder = UriBuilder(resolver)
        project_slug = "calc-f4aa3834"
        
        # Example manifest with proper navigation
        manifest_resource = {
            "project_info": {
                "name": "Calculator Process",
                "slug": project_slug
            },
            "resources": {
                "workflows": builder.workflows(project_slug),
                "entry_points": f"rpax://dev/projects/{project_slug}/entry_points",
                "dependencies": builder.dependencies(project_slug),
                "call_graphs": f"rpax://dev/projects/{project_slug}/call_graphs"
            },
            "quick_access": {
                "non_test_entry_points": builder.entry_point(project_slug, "_all", "non_test", "medium"),
                "workflow_index": f"rpax://dev/projects/{project_slug}/workflows/index.json"
            }
        }
        
        # All URIs should be well-formed rpax:// URIs
        for section in ["resources", "quick_access"]:
            for key, uri in manifest_resource[section].items():
                assert uri.startswith("rpax://dev/"), f"Invalid URI in {section}.{key}: {uri}"