"""Integration test for end-to-end activity resource generation.

Tests the complete pipeline from project parsing through activity resource
generation with error collection and both legacy/V0 schema support.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rpax.config import RpaxConfig
from rpax.output.base import ParsedProjectData
from rpax.cli_integration import create_integrated_pipeline
from rpax.models.project import UiPathProject
from rpax.models.workflow import WorkflowIndex, Workflow
from rpax.parser.enhanced_xaml_analyzer import EnhancedActivityNode


class TestActivityResourceIntegration:
    """Integration tests for activity resource generation pipeline."""
    
    def test_end_to_end_activity_resource_generation_legacy(self):
        """Test complete activity resource generation with legacy schema."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            lake_root = Path(temp_dir)
            
            # Create test configuration
            config = self._create_test_config(lake_root)
            config.output.generate_activities = True
            
            # Initialize integrated pipeline
            pipeline = create_integrated_pipeline(config, lake_root, "parse")
            
            # Create test project data
            parsed_data = self._create_test_parsed_data(lake_root)
            
            # Mock the enhanced XAML analyzer to return test activities
            with patch.object(pipeline.activity_resource_manager, 'enhanced_analyzer') as mock_analyzer:
                mock_analyzer.extract_activity_tree.return_value = self._create_mock_activity_tree()
                
                # Generate artifacts with integrated pipeline
                artifacts = pipeline.generate_project_artifacts(parsed_data, "legacy")
                
                # Verify core artifacts generated
                assert len(artifacts) > 0, "Should generate artifacts"
                
                # Verify activity resource artifacts generated
                activity_artifacts = {k: v for k, v in artifacts.items() if "activity_resources" in k}
                assert len(activity_artifacts) > 0, "Should generate activity resource artifacts"
                
                # Verify activity resource index generated
                index_artifacts = {k: v for k, v in activity_artifacts.items() if k.endswith("_index")}
                assert len(index_artifacts) > 0, "Should generate activity resource index"
                
                # Verify activity resource files exist
                for artifact_name, artifact_path in activity_artifacts.items():
                    assert artifact_path.exists(), f"Activity resource file should exist: {artifact_path}"
                    
                    # Verify file contains valid JSON
                    with open(artifact_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        assert "schema_version" in data, "Should have schema version"
                        assert data["schema_version"] == "1.0.0", "Should have correct schema version"
                
                # Verify activity resource index structure
                index_file = next(path for name, path in index_artifacts.items())
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    
                    assert "project_slug" in index_data, "Index should have project slug"
                    assert "total_workflows" in index_data, "Index should have workflow count"
                    assert "resources" in index_data, "Index should have resource list"
                    assert "navigation" in index_data, "Index should have navigation"
            
            # Finalize pipeline and check error collection
            error_file = pipeline.finalize_run()
            
            # Verify no critical errors occurred
            assert not pipeline.has_critical_errors(), "Should not have critical errors"
            
            # If any warnings/info messages, verify error file exists
            if pipeline.has_errors():
                assert error_file is not None, "Should create error file if errors exist"
                assert error_file.exists(), "Error file should exist"
                
                # Verify error file structure
                with open(error_file, 'r', encoding='utf-8') as f:
                    error_data = json.load(f)
                    assert "schema_version" in error_data, "Error file should have schema"
                    assert "run_id" in error_data, "Error file should have run ID"
                    assert "command" in error_data, "Error file should have command"
    
    def test_end_to_end_activity_resource_generation_v0(self):
        """Test complete activity resource generation with V0 schema."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            lake_root = Path(temp_dir)
            
            # Create test configuration
            config = self._create_test_config(lake_root)
            config.output.generate_activities = True
            
            # Initialize integrated pipeline
            pipeline = create_integrated_pipeline(config, lake_root, "parse")
            
            # Create test project data
            parsed_data = self._create_test_parsed_data(lake_root)
            
            # Mock the enhanced XAML analyzer and V0 generator
            with patch.object(pipeline.activity_resource_manager, 'enhanced_analyzer') as mock_analyzer:
                mock_analyzer.extract_activity_tree.return_value = self._create_mock_activity_tree()
                
                with patch('rpax.cli_integration.V0LakeGenerator') as mock_v0_generator:
                    # Mock V0 generator to return test artifacts
                    mock_generator_instance = Mock()
                    mock_generator_instance.generate.return_value = {
                        "v0_manifest": Path(temp_dir) / "v0" / "manifest.json",
                        "v0_entry_points_index": Path(temp_dir) / "v0" / "entry_points" / "index.json"
                    }
                    mock_v0_generator.return_value = mock_generator_instance
                    
                    # Generate artifacts with V0 schema
                    artifacts = pipeline.generate_project_artifacts(parsed_data, "v0")
                    
                    # Verify V0 generator was called
                    mock_v0_generator.assert_called_once()
                    mock_generator_instance.generate.assert_called_once_with(parsed_data)
                    
                    # Verify activity resources were attempted to be generated
                    mock_analyzer.extract_activity_tree.assert_called()
            
            # Verify no critical errors
            assert not pipeline.has_critical_errors(), "Should not have critical errors in V0 schema"
    
    def test_error_collection_during_activity_resource_generation(self):
        """Test error collection when activity resource generation fails."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            lake_root = Path(temp_dir)
            
            # Create test configuration
            config = self._create_test_config(lake_root)
            config.output.generate_activities = True
            
            # Initialize integrated pipeline
            pipeline = create_integrated_pipeline(config, lake_root, "parse")
            
            # Create test project data
            parsed_data = self._create_test_parsed_data(lake_root)
            
            # Mock the activity resource manager to raise an exception
            with patch.object(pipeline.activity_resource_manager, 'generate_activity_resources') as mock_generate:
                mock_generate.side_effect = Exception("Test activity resource generation failure")
                
                # Mock legacy artifact generator to succeed
                with patch('rpax.cli_integration.ArtifactGenerator') as mock_artifact_generator:
                    mock_generator_instance = Mock()
                    mock_generator_instance.generate_all_artifacts.return_value = {
                        "legacy_manifest": Path(temp_dir) / "manifest.json"
                    }
                    mock_artifact_generator.return_value = mock_generator_instance
                    
                    # Generate artifacts - should succeed despite activity resource failure
                    artifacts = pipeline.generate_project_artifacts(parsed_data, "legacy")
                    
                    # Verify core artifacts still generated
                    assert len(artifacts) > 0, "Should still generate core artifacts"
                    
                    # Verify activity resource generation was attempted
                    mock_generate.assert_called_once()
            
            # Verify error was collected
            assert pipeline.has_errors(), "Should have collected the error"
            
            # Verify error details
            error_summary = pipeline.get_error_summary()
            assert error_summary.get("warning", 0) > 0, "Should have warning-level error"
            
            # Finalize and verify error file
            error_file = pipeline.finalize_run()
            assert error_file is not None, "Should create error file"
            assert error_file.exists(), "Error file should exist"
            
            # Verify error details in file
            with open(error_file, 'r', encoding='utf-8') as f:
                error_data = json.load(f)
                assert error_data["total_errors"] > 0, "Should record errors"
                
                # Find the activity resource error
                activity_errors = [
                    err for err in error_data["errors"]
                    if err["context"].get("operation") == "generate_activity_resources"
                ]
                assert len(activity_errors) > 0, "Should record activity resource error"
                assert activity_errors[0]["severity"] == "warning", "Should be warning severity"
    
    def test_uri_resolver_integration(self):
        """Test URI resolver integration with activity resources."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            lake_root = Path(temp_dir)
            
            # Create test configuration
            config = self._create_test_config(lake_root)
            
            # Initialize pipeline and test URI resolution
            pipeline = create_integrated_pipeline(config, lake_root, "parse")
            
            # Test activity resource URI generation
            from rpax.resources import ActivityResourceManager
            manager = ActivityResourceManager(config)
            
            # Test navigation URI generation
            navigation = manager.get_activity_resource_navigation("test-project", "Main")
            
            assert "activity_resource" in navigation, "Should have activity resource URI"
            assert "index" in navigation, "Should have index URI"
            assert navigation["activity_resource"] == "rpax://projects/test-project/activities/Main"
            assert navigation["index"] == "rpax://projects/test-project/activities/index"
            
            # Test index navigation
            index_navigation = manager.get_activity_resource_navigation("test-project")
            assert "index" in index_navigation, "Should have index navigation"
            assert "individual_pattern" in index_navigation, "Should have individual pattern"
    
    def _create_test_config(self, lake_root: Path) -> RpaxConfig:
        """Create test configuration."""
        config = RpaxConfig()
        config.output.dir = str(lake_root / "test-project")
        config.output.generate_activities = True
        config.output.summaries = False
        return config
    
    def _create_test_parsed_data(self, lake_root: Path) -> ParsedProjectData:
        """Create test parsed project data."""
        # Create mock project
        project = Mock(spec=UiPathProject)
        project.name = "Test Project"
        project.project_id = "test-project-id"
        project.project_type = "Process"
        
        # Create mock workflow
        workflow = Mock(spec=Workflow)
        workflow.workflow_id = "Main"
        workflow.relative_path = "Main.xaml"
        workflow.file_path = str(lake_root / "project" / "Main.xaml")
        
        # Create mock workflow index
        workflow_index = Mock(spec=WorkflowIndex)
        workflow_index.workflows = [workflow]
        workflow_index.total_workflows = 1
        workflow_index.failed_parses = 0
        
        return ParsedProjectData(
            project=project,
            workflow_index=workflow_index,
            project_root=lake_root / "project",
            project_slug="test-project",
            timestamp=datetime.now()
        )
    
    def _create_mock_activity_tree(self):
        """Create mock activity tree with test activities."""
        mock_tree = Mock()
        
        # Create mock activity
        mock_activity = Mock(spec=EnhancedActivityNode)
        mock_activity.node_id = "test-activity-1"
        mock_activity.activity_type = "UiPath.Core.Activities.Sequence"
        mock_activity.display_name = "Test Sequence"
        mock_activity.arguments = {}
        mock_activity.properties = {}
        mock_activity.children = []
        
        mock_tree.activities = [mock_activity]
        return mock_tree


# Run integration tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])