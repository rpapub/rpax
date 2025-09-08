#!/usr/bin/env python3
"""Tests for v0/ experimental schema generation.

Validates the v0 output module generates correct structure and content
as specified in ADR-032 v0 Experimental Schema.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime

import pytest

from rpax.output.base import ParsedProjectData
from rpax.output.v0 import V0LakeGenerator
from rpax.output.v0.manifest_builder import ManifestBuilder
from rpax.output.v0.entry_point_builder import EntryPointBuilder
from rpax.output.v0.detail_levels import DetailLevelExtractor
from rpax.models.project import UiPathProject, EntryPoint
from rpax.models.workflow import WorkflowIndex, Workflow


# Global fixtures available to all test classes
@pytest.fixture
def mock_project():
    """Create mock UiPath project for testing."""
    return UiPathProject(
        name="TestProject",
        main="Main.xaml",
        project_id="test-id",
        project_version="1.0.0",
        studio_version="23.10.0.0",
        uipath_schema_version="4.0",
        expression_language="VisualBasic",
        entry_points=[
            EntryPoint(file_path="Main.xaml", unique_id="main-id"),
            EntryPoint(file_path="Test.xaml", unique_id="test-id")
        ]
    )


@pytest.fixture
def mock_workflow_index():
    """Create mock workflow index for testing."""
    from datetime import datetime
    now = datetime.now().isoformat()
    
    workflows = [
        Workflow(
            id="test_main",
            project_slug="testproject",
            workflow_id="Main.xaml",
            content_hash="hash1",
            file_path="/test/Main.xaml",
            file_name="Main.xaml",
            relative_path="Main.xaml",
            display_name="Main Workflow",
            discovered_at=now,
            file_size=1000,
            last_modified=now
        ),
        Workflow(
            id="test_test",
            project_slug="testproject", 
            workflow_id="Test.xaml",
            content_hash="hash2",
            file_path="/test/Test.xaml",
            file_name="Test.xaml",
            relative_path="Test.xaml",
            display_name="Test Workflow",
            discovered_at=now,
            file_size=800,
            last_modified=now
        ),
        Workflow(
            id="test_helper",
            project_slug="testproject",
            workflow_id="Utils/Helper.xaml", 
            content_hash="hash3",
            file_path="/test/Utils/Helper.xaml",
            file_name="Helper.xaml",
            relative_path="Utils/Helper.xaml",
            display_name="Helper Workflow",
            discovered_at=now,
            file_size=600,
            last_modified=now
        )
    ]
    return WorkflowIndex(
        project_name="TestProject",
        project_root="/test/project",
        scan_timestamp=now,
        total_workflows=3,
        successful_parses=3,
        failed_parses=0,
        workflows=workflows
    )


@pytest.fixture
def parsed_data(mock_project, mock_workflow_index):
    """Create ParsedProjectData for testing."""
    return ParsedProjectData(
        project=mock_project,
        workflow_index=mock_workflow_index,
        project_root=Path("/test/project"),
        project_slug="testproject",
        timestamp=datetime.now()
    )


class TestV0SchemaGeneration:
    """Test v0/ schema generation with mock data."""
    
    def test_v0_directory_structure(self, parsed_data):
        """Test that v0 generator creates expected directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            project_dir = output_dir / "testproject"
            v0_dir = project_dir / "v0"
            
            # Check core directories exist
            assert project_dir.exists()
            assert v0_dir.exists()
            assert (project_dir / "_meta").exists()
            assert (v0_dir / "entry_points").exists()
            assert (v0_dir / "call_graphs").exists()
            assert (v0_dir / "workflows").exists()
            assert (v0_dir / "resources").exists()
            
            # Check key files exist
            assert (v0_dir / "manifest.json").exists()
            assert (v0_dir / "entry_points" / "index.json").exists()
            assert (v0_dir / "entry_points" / "non_test" / "_all_medium.json").exists()
    
    def test_manifest_structure(self, parsed_data):
        """Test manifest.json has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            manifest_file = output_dir / "testproject" / "v0" / "manifest.json"
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            # Check required top-level fields
            assert manifest["schema_version"] == "v0"
            assert "rpax_version" in manifest
            assert "generated_at" in manifest
            assert "project" in manifest
            assert "navigation" in manifest
            assert "statistics" in manifest
            assert "entry_points" in manifest
            
            # Check project metadata
            project = manifest["project"]
            assert project["name"] == "TestProject"
            assert project["project_id"] == "test-id"
            assert project["project_version"] == "1.0.0"
            
            # Check navigation structure
            nav = manifest["navigation"]
            assert "entry_points" in nav
            assert "call_graphs" in nav
            assert "workflows" in nav
            assert "resources" in nav
            
            # Check statistics
            stats = manifest["statistics"]
            assert stats["total_workflows"] == 3
            assert stats["entry_points"] == 2
    
    def test_entry_points_all_medium(self, parsed_data):
        """Test _all_medium.json contains all non-test entry points."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            all_medium_file = output_dir / "testproject" / "v0" / "entry_points" / "non_test" / "_all_medium.json"
            with open(all_medium_file) as f:
                data = json.load(f)
            
            assert data["detail_level"] == "medium"
            assert "entry_points" in data
            
            # Should have non-test entry points
            entry_points = data["entry_points"]
            assert len(entry_points) >= 1  # At least Main.xaml should be non-test
            
            # Check structure of each entry point
            for ep in entry_points:
                assert "file" in ep
                assert "type" in ep
                assert "detail_level" in ep
                assert "call_tree" in ep
                assert ep["detail_level"] == "medium"
    
    def test_call_graphs_detail_levels(self, parsed_data):
        """Test call graphs are generated at all detail levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            call_graphs_dir = output_dir / "testproject" / "v0" / "call_graphs"
            
            # Check all detail levels exist
            low_file = call_graphs_dir / "project_low.json"
            medium_file = call_graphs_dir / "project_medium.json"
            high_file = call_graphs_dir / "project_high.json"
            
            assert low_file.exists()
            assert medium_file.exists()
            assert high_file.exists()
            
            # Check each has correct detail level
            with open(low_file) as f:
                low_data = json.load(f)
                assert low_data["detail_level"] == "low"
            
            with open(medium_file) as f:
                medium_data = json.load(f)
                assert medium_data["detail_level"] == "medium"
            
            with open(high_file) as f:
                high_data = json.load(f)
                assert high_data["detail_level"] == "high"
    
    def test_workflows_individual_resources(self, parsed_data):
        """Test individual workflow resources maintain directory hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            workflows_dir = output_dir / "testproject" / "v0" / "workflows"
            
            # Check workflow index
            assert (workflows_dir / "index.json").exists()
            
            # Check hierarchical structure preserved
            # Utils/Helper.xaml should create Utils/Helper/ directory
            helper_dir = workflows_dir / "Utils" / "Helper"
            assert helper_dir.exists()
            assert (helper_dir / "medium.json").exists()
            assert (helper_dir / "high.json").exists()
    
    def test_resources_generation(self, parsed_data):
        """Test resource files are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            resources_dir = output_dir / "testproject" / "v0" / "resources"
            
            # Check resource files exist
            assert (resources_dir / "static_invocations.json").exists()
            assert (resources_dir / "package_usage.json").exists()
            
            # Check structure
            with open(resources_dir / "static_invocations.json") as f:
                static = json.load(f)
                assert "total_invocations" in static
                assert "invocations" in static
            
            with open(resources_dir / "package_usage.json") as f:
                packages = json.load(f)
                assert "total_packages" in packages
                assert "packages" in packages
    
    def test_meta_directory(self, parsed_data):
        """Test _meta directory contains version information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            meta_dir = output_dir / "testproject" / "_meta"
            
            # Check version files
            assert (meta_dir / "schema_version.txt").exists()
            assert (meta_dir / "rpax_version.txt").exists()
            
            # Check content
            schema_version = (meta_dir / "schema_version.txt").read_text().strip()
            assert schema_version == "v0"
    
    def test_legacy_compatibility(self, parsed_data):
        """Test legacy directory is created for compatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            artifacts = generator.generate(parsed_data)
            
            legacy_dir = output_dir / "testproject" / "legacy"
            assert legacy_dir.exists()
            assert (legacy_dir / "README.md").exists()
            
            # Check README content mentions v0/
            readme_content = (legacy_dir / "README.md").read_text()
            assert "v0/" in readme_content
            assert "v0-experimental-schema" in readme_content.lower()


class TestManifestBuilder:
    """Test ManifestBuilder component."""
    
    @pytest.fixture
    def builder(self):
        return ManifestBuilder()
    
    def test_project_metadata(self, builder, mock_project, mock_workflow_index):
        """Test project metadata extraction."""
        parsed_data = ParsedProjectData(
            project=mock_project,
            workflow_index=mock_workflow_index,
            project_root=Path("/test"),
            project_slug="test",
            timestamp=datetime.now()
        )
        
        manifest = builder.build_v0_manifest(parsed_data)
        project = manifest["project"]
        
        assert project["name"] == "TestProject"
        assert project["display_name"] == "TestProject"  # Falls back to name
        assert project["project_id"] == "test-id"
        assert project["language"] == "VisualBasic"
    
    def test_entry_points_summary(self, builder, mock_project, mock_workflow_index):
        """Test entry points summary generation."""
        parsed_data = ParsedProjectData(
            project=mock_project,
            workflow_index=mock_workflow_index,
            project_root=Path("/test"),
            project_slug="test",
            timestamp=datetime.now()
        )
        
        manifest = builder.build_v0_manifest(parsed_data)
        entry_points = manifest["entry_points"]
        
        assert len(entry_points) == 2
        assert entry_points[0]["file"] == "Main.xaml"
        assert entry_points[0]["type"] == "xaml"
        assert entry_points[0]["is_test"] == False
        assert "resource_medium" in entry_points[0]


class TestEntryPointBuilder:
    """Test EntryPointBuilder component."""
    
    @pytest.fixture
    def builder(self, mock_project, mock_workflow_index):
        parsed_data = ParsedProjectData(
            project=mock_project,
            workflow_index=mock_workflow_index,
            project_root=Path("/test"),
            project_slug="test",
            timestamp=datetime.now()
        )
        return EntryPointBuilder(parsed_data)
    
    def test_entry_points_index(self, builder):
        """Test entry points index generation."""
        index = builder.build_entry_points_index()
        
        assert "total_entry_points" in index
        assert "non_test_entry_points" in index
        assert "test_entry_points" in index
        assert "available_resources" in index
        
        assert index["total_entry_points"] == 2
    
    def test_all_non_test_medium(self, builder):
        """Test all non-test entry points medium detail."""
        all_medium = builder.build_all_non_test_medium()
        
        assert all_medium["detail_level"] == "medium"
        assert "entry_points" in all_medium
        
        # Should have at least Main.xaml as non-test
        assert len(all_medium["entry_points"]) >= 1


class TestDetailLevelExtractor:
    """Test DetailLevelExtractor component."""
    
    @pytest.fixture
    def extractor(self, mock_project, mock_workflow_index):
        parsed_data = ParsedProjectData(
            project=mock_project,
            workflow_index=mock_workflow_index,
            project_root=Path("/test"),
            project_slug="test",
            timestamp=datetime.now()
        )
        return DetailLevelExtractor(parsed_data)
    
    def test_call_graph_low(self, extractor):
        """Test low detail call graph extraction."""
        low = extractor.extract_call_graph_low()
        
        assert low["detail_level"] == "low"
        assert "project" in low
        assert "overview" in low
        assert low["project"]["total_workflows"] == 3
    
    def test_call_graph_medium(self, extractor):
        """Test medium detail call graph extraction."""
        medium = extractor.extract_call_graph_medium()
        
        assert medium["detail_level"] == "medium"
        assert "workflows" in medium
        assert "call_relationships" in medium
        assert "packages" in medium
    
    def test_call_graph_high(self, extractor):
        """Test high detail call graph extraction."""
        high = extractor.extract_call_graph_high()
        
        assert high["detail_level"] == "high"
        assert "workflows" in high
        assert "call_relationships" in high
        assert "packages" in high
        assert "variables" in high
        assert "arguments" in high


# Integration test fixtures for pytest - removed duplicates


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])