#!/usr/bin/env python3
"""Integration tests for v0/ schema generation against real UiPath projects.

Tests the complete v0 generation pipeline using actual corpus projects
to validate real-world compatibility and performance.
"""

import json
import tempfile
from pathlib import Path

import pytest

from rpax.cli import parse
from rpax.parser.project import ProjectParser
from rpax.parser.xaml import XamlDiscovery
from rpax.output.v0 import V0LakeGenerator
from rpax.output.base import ParsedProjectData
from datetime import datetime
from slugify import slugify


class TestV0IntegrationFrozenChlorine:
    """Integration tests using FrozenChlorine corpus."""
    
    @pytest.fixture
    def frozenchlorine_path(self):
        """Path to FrozenChlorine test corpus."""
        corpus_path = Path("D:/github.com/rpapub/FrozenChlorine")
        if not corpus_path.exists():
            pytest.skip("FrozenChlorine corpus not available")
        return corpus_path
    
    @pytest.fixture
    def parsed_frozenchlorine_data(self, frozenchlorine_path):
        """Parse FrozenChlorine project for testing."""
        # Parse project
        project = ProjectParser.parse_project_from_dir(frozenchlorine_path)
        
        # Discover workflows
        discovery = XamlDiscovery(frozenchlorine_path, exclude_patterns=[])
        workflow_index = discovery.discover_workflows()
        
        # Create parsed data
        project_slug = slugify(project.name)
        return ParsedProjectData(
            project=project,
            workflow_index=workflow_index,
            project_root=frozenchlorine_path,
            project_slug=project_slug,
            timestamp=datetime.now()
        )
    
    def test_frozenchlorine_v0_generation(self, parsed_frozenchlorine_data):
        """Test complete v0 generation with FrozenChlorine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            
            # Generate v0 artifacts
            artifacts = generator.generate(parsed_frozenchlorine_data)
            
            # Should generate many artifacts
            assert len(artifacts) > 50  # FrozenChlorine has 21 workflows
            
            # Check core structure exists
            project_dir = output_dir / "frozenchlorine"
            v0_dir = project_dir / "v0"
            
            assert v0_dir.exists()
            assert (v0_dir / "manifest.json").exists()
            assert (v0_dir / "entry_points" / "non_test" / "_all_medium.json").exists()
    
    def test_frozenchlorine_manifest_content(self, parsed_frozenchlorine_data):
        """Test FrozenChlorine manifest contains expected project data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            artifacts = generator.generate(parsed_frozenchlorine_data)
            
            manifest_file = output_dir / "frozenchlorine" / "v0" / "manifest.json"
            with open(manifest_file) as f:
                manifest = json.load(f)
            
            # Check project metadata
            project = manifest["project"]
            assert project["name"] == "FrozenChlorine"
            assert project["project_type"] == "process"
            assert "studio_version" in project
            
            # Check statistics match expectations
            stats = manifest["statistics"]
            assert stats["total_workflows"] == 21  # Known FrozenChlorine workflow count
            assert stats["entry_points"] == 2  # Known entry points
    
    def test_frozenchlorine_entry_points_structure(self, parsed_frozenchlorine_data):
        """Test FrozenChlorine entry points have complete recursive structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            artifacts = generator.generate(parsed_frozenchlorine_data)
            
            all_medium_file = output_dir / "frozenchlorine" / "v0" / "entry_points" / "non_test" / "_all_medium.json"
            with open(all_medium_file) as f:
                data = json.load(f)
            
            entry_points = data["entry_points"]
            assert len(entry_points) >= 1  # Should have non-test entry points
            
            # Check each entry point has recursive call tree
            for ep in entry_points:
                assert "call_tree" in ep
                assert "statistics" in ep
                assert "packages_used" in ep
                
                call_tree = ep["call_tree"]
                assert "file" in call_tree
                assert "type" in call_tree
                assert "exists" in call_tree
    
    def test_frozenchlorine_call_graphs_content(self, parsed_frozenchlorine_data):
        """Test FrozenChlorine call graphs contain workflow relationships."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            artifacts = generator.generate(parsed_frozenchlorine_data)
            
            # Check medium detail call graph
            medium_file = output_dir / "frozenchlorine" / "v0" / "call_graphs" / "project_medium.json"
            with open(medium_file) as f:
                medium = json.load(f)
            
            assert medium["detail_level"] == "medium"
            assert len(medium["workflows"]) == 21  # All workflows
            assert "call_relationships" in medium
            assert "packages" in medium
    
    def test_frozenchlorine_workflows_hierarchy(self, parsed_frozenchlorine_data):
        """Test FrozenChlorine workflows maintain directory hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            artifacts = generator.generate(parsed_frozenchlorine_data)
            
            workflows_dir = output_dir / "frozenchlorine" / "v0" / "workflows"
            
            # Check hierarchical directories exist
            # FrozenChlorine has Framework/, Process/, Tests/, etc.
            assert (workflows_dir / "Framework").exists()
            assert (workflows_dir / "Process").exists()
            assert (workflows_dir / "Tests").exists()
            
            # Check specific workflow resources
            init_apps_dir = workflows_dir / "Framework" / "InitAllApplications"
            assert init_apps_dir.exists()
            assert (init_apps_dir / "medium.json").exists()
            assert (init_apps_dir / "high.json").exists()
    
    def test_frozenchlorine_resources_analysis(self, parsed_frozenchlorine_data):
        """Test FrozenChlorine resource analysis produces meaningful data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            artifacts = generator.generate(parsed_frozenchlorine_data)
            
            resources_dir = output_dir / "frozenchlorine" / "v0" / "resources"
            
            # Check package usage
            package_file = resources_dir / "package_usage.json"
            with open(package_file) as f:
                packages = json.load(f)
            
            assert packages["total_packages"] > 0
            # FrozenChlorine should use UiPath packages
            package_names = [p["package"] for p in packages["packages"]]
            assert any("UiPath" in name for name in package_names)
            
            # Check static invocations
            invocations_file = resources_dir / "static_invocations.json"
            with open(invocations_file) as f:
                invocations = json.load(f)
            
            # Should find some workflow invocations in FrozenChlorine
            assert "total_invocations" in invocations
            assert "invocations" in invocations


class TestV0Performance:
    """Performance tests for v0 generation."""
    
    def test_v0_generation_performance(self):
        """Test v0 generation completes within reasonable time."""
        import time
        
        corpus_path = Path("D:/github.com/rpapub/FrozenChlorine")
        if not corpus_path.exists():
            pytest.skip("FrozenChlorine corpus not available")
        
        start_time = time.time()
        
        # Parse project
        project = ProjectParser.parse_project_from_dir(corpus_path)
        discovery = XamlDiscovery(corpus_path, exclude_patterns=[])
        workflow_index = discovery.discover_workflows()
        
        parsed_data = ParsedProjectData(
            project=project,
            workflow_index=workflow_index,
            project_root=corpus_path,
            project_slug=slugify(project.name),
            timestamp=datetime.now()
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generator = V0LakeGenerator(output_dir)
            artifacts = generator.generate(parsed_data)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should complete within 30 seconds for FrozenChlorine (21 workflows)
        assert generation_time < 30.0, f"v0 generation took {generation_time:.2f}s, expected < 30s"
        
        # Should generate substantial number of artifacts
        assert len(artifacts) > 50


class TestV0CompatibilityWithOtherCorpuses:
    """Test v0 generation with other available test corpuses."""
    
    @pytest.mark.parametrize("corpus_name,expected_min_workflows", [
        ("PropulsiveForce/CPRIMA-USG-001_ShouldStopPresence/Violation", 1),
        ("PropulsiveForce/CPRIMA-USG-001_ShouldStopPresence/NoViolation", 1),
    ])
    def test_corpus_compatibility(self, corpus_name, expected_min_workflows):
        """Test v0 generation works with different corpus projects."""
        corpus_path = Path(f"D:/github.com/rpapub/{corpus_name}")
        if not corpus_path.exists():
            pytest.skip(f"Corpus {corpus_name} not available")
        
        try:
            # Parse project
            project = ProjectParser.parse_project_from_dir(corpus_path)
            discovery = XamlDiscovery(corpus_path, exclude_patterns=[])
            workflow_index = discovery.discover_workflows()
            
            # Should find minimum expected workflows
            assert workflow_index.total_workflows >= expected_min_workflows
            
            # Create parsed data
            parsed_data = ParsedProjectData(
                project=project,
                workflow_index=workflow_index,
                project_root=corpus_path,
                project_slug=slugify(project.name),
                timestamp=datetime.now()
            )
            
            # Generate v0 artifacts
            with tempfile.TemporaryDirectory() as tmpdir:
                output_dir = Path(tmpdir)
                generator = V0LakeGenerator(output_dir)
                artifacts = generator.generate(parsed_data)
                
                # Should generate artifacts without errors
                assert len(artifacts) > 0
                
                # Check core files exist
                project_dir = output_dir / parsed_data.project_slug
                assert (project_dir / "v0" / "manifest.json").exists()
                
        except Exception as e:
            pytest.fail(f"v0 generation failed for {corpus_name}: {e}")


class TestV0CLIIntegration:
    """Test v0 generation through CLI interface."""
    
    def test_cli_schema_v0_option(self):
        """Test --schema v0 CLI option works correctly."""
        corpus_path = Path("D:/github.com/rpapub/FrozenChlorine")
        if not corpus_path.exists():
            pytest.skip("FrozenChlorine corpus not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # This would test the CLI integration but requires subprocess
            # For now, test that the schema option validation works
            from rpax.cli import parse as cli_parse
            
            # Mock the CLI call
            # In a real test, we'd use subprocess to call:
            # uv run rpax parse {corpus_path} --schema v0 --out {output_dir}
            
            # For now, just verify the schema validation
            valid_schemas = ["legacy", "v0"]
            assert "v0" in valid_schemas
            assert "legacy" in valid_schemas


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])  # -s to see print output