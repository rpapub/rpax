"""Tests for enhanced XAML parser integration."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rpax.config import RpaxConfig, ParserConfig, ProjectConfig, ProjectType
from rpax.artifacts import ArtifactGenerator
from rpax.models.project import UiPathProject
from rpax.models.workflow import WorkflowIndex, Workflow
from rpax.parser.enhanced_xaml_analyzer import EnhancedXamlAnalyzer, EnhancedActivityNode


class TestEnhancedParserIntegration:
    """Test enhanced parser integration with artifact generation."""
    
    def test_parser_config_defaults(self):
        """Test parser configuration has correct defaults."""
        config = RpaxConfig(
            project=ProjectConfig(type=ProjectType.PROCESS)
        )
        
        # Verify parser config defaults
        assert config.parser.use_enhanced == True
        assert config.parser.visual_detection == True
        assert config.parser.include_structural == False
        assert config.parser.max_depth == 50
        assert config.parser.custom_blacklist == []
        assert config.parser.custom_whitelist == []
    
    def test_parser_config_validation(self):
        """Test parser configuration validation."""
        with pytest.raises(ValueError, match="parser max_depth must be >= 1"):
            ParserConfig(max_depth=0)
            
    def test_artifact_generator_uses_enhanced_parser(self, tmp_path):
        """Test that artifact generator uses enhanced parser when configured."""
        config = RpaxConfig(
            project=ProjectConfig(type=ProjectType.PROCESS),
            parser=ParserConfig(use_enhanced=True)
        )
        
        generator = ArtifactGenerator(config, tmp_path)
        
        # Create mock workflow data
        workflow = Workflow(
            id="test-project#TestWorkflow#abcd1234",
            project_slug="test-project",
            workflow_id="TestWorkflow",
            content_hash="abcd1234567890123456789012345678",
            file_path="TestWorkflow.xaml",
            file_name="TestWorkflow.xaml",
            relative_path="TestWorkflow.xaml",
            discovered_at="2024-01-01T00:00:00Z",
            file_size=1024,
            last_modified="2024-01-01T00:00:00Z"
        )
        workflow_index = WorkflowIndex(
            project_name="TestProject",
            project_root=str(tmp_path),
            scan_timestamp="2024-01-01T00:00:00Z",
            workflows=[workflow],
            total_workflows=1,
            successful_parses=1,
            failed_parses=0
        )
        
        project = Mock(spec=UiPathProject)
        project.name = "TestProject"
        project.generate_project_slug.return_value = "test-project-abcd1234"
        
        # Create a simple XAML file for testing
        xaml_content = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence DisplayName="Main Sequence">
    <Assign DisplayName="Set Variable">
      <Assign.To>[myVar]</Assign.To>
      <Assign.Value>"Hello World"</Assign.Value>
    </Assign>
  </Sequence>
</Activity>'''
        
        project_root = tmp_path / "project"
        project_root.mkdir()
        xaml_file = project_root / "TestWorkflow.xaml"
        xaml_file.write_text(xaml_content, encoding="utf-8")
        
        with patch('rpax.artifacts.EnhancedXamlAnalyzer') as mock_analyzer:
            # Mock the enhanced analyzer
            mock_instance = Mock()
            mock_analyzer.return_value = mock_instance
            
            # Mock enhanced analyzer methods
            mock_instance.extract_activity_tree.return_value = Mock()
            mock_instance.extract_control_flow.return_value = None
            mock_instance.extract_resources.return_value = None
            mock_instance.calculate_metrics.return_value = None
            
            # Generate artifacts
            artifacts = generator._generate_activities_artifacts(workflow_index, project_root)
            
            # Verify enhanced analyzer was created and used
            mock_analyzer.assert_called_once()
            mock_instance.extract_activity_tree.assert_called_once()
    
    def test_artifact_generator_uses_legacy_parser(self, tmp_path):
        """Test that artifact generator uses legacy parser when configured."""
        config = RpaxConfig(
            project=ProjectConfig(type=ProjectType.PROCESS),
            parser=ParserConfig(use_enhanced=False)
        )
        
        generator = ArtifactGenerator(config, tmp_path)
        
        # Create mock workflow data
        workflow = Workflow(
            id="test-project#TestWorkflow#abcd1234",
            project_slug="test-project",
            workflow_id="TestWorkflow",
            content_hash="abcd1234567890123456789012345678",
            file_path="TestWorkflow.xaml",
            file_name="TestWorkflow.xaml",
            relative_path="TestWorkflow.xaml",
            discovered_at="2024-01-01T00:00:00Z",
            file_size=1024,
            last_modified="2024-01-01T00:00:00Z"
        )
        workflow_index = WorkflowIndex(
            project_name="TestProject",
            project_root=str(tmp_path),
            scan_timestamp="2024-01-01T00:00:00Z",
            workflows=[workflow],
            total_workflows=1,
            successful_parses=1,
            failed_parses=0
        )
        
        project_root = tmp_path / "project"
        project_root.mkdir()
        xaml_file = project_root / "TestWorkflow.xaml"
        xaml_file.write_text("<Activity />", encoding="utf-8")
        
        with patch('rpax.artifacts.XamlAnalyzer') as mock_analyzer:
            # Mock the legacy analyzer
            mock_instance = Mock()
            mock_analyzer.return_value = mock_instance
            mock_instance.extract_activity_tree.return_value = None
            mock_instance.extract_control_flow.return_value = None
            mock_instance.extract_resources.return_value = None
            mock_instance.calculate_metrics.return_value = None
            
            # Generate artifacts
            artifacts = generator._generate_activities_artifacts(workflow_index, project_root)
            
            # Verify legacy analyzer was used
            mock_analyzer.assert_called_once()
    
    def test_enhanced_activity_tree_serialization(self, tmp_path):
        """Test that enhanced activity trees are properly serialized."""
        config = RpaxConfig(
            project=ProjectConfig(type=ProjectType.PROCESS),
            parser=ParserConfig(use_enhanced=True)
        )
        
        generator = ArtifactGenerator(config, tmp_path)
        
        # Create mock enhanced activity tree with .data attribute
        mock_tree = Mock()
        mock_tree.data = {
            "workflowId": "TestWorkflow",
            "extractorVersion": "0.1.0-enhanced", 
            "totalVisualActivities": 2,
            "parseMethod": "enhanced-visual-detection",
            "rootNode": {
                "nodeId": "/Sequence[0]",
                "activityType": "Sequence",
                "displayName": "Main Sequence",
                "isVisual": True,
                "children": []
            }
        }
        
        # Test serialization
        result = generator._serialize_activity_tree(mock_tree)
        
        # Verify enhanced data is returned directly
        assert result == mock_tree.data
        assert result["extractorVersion"] == "0.1.0-enhanced"
        assert result["parseMethod"] == "enhanced-visual-detection"
        assert result["totalVisualActivities"] == 2


class TestEnhancedXamlAnalyzer:
    """Test enhanced XAML analyzer functionality."""
    
    def test_visual_activity_detection(self):
        """Test visual vs structural activity detection."""
        analyzer = EnhancedXamlAnalyzer()
        
        # Test whitelist activities (structural containers)
        assert analyzer._is_visual_activity(Mock(attrib={}), "Sequence") == True
        assert analyzer._is_visual_activity(Mock(attrib={}), "TryCatch") == True
        assert analyzer._is_visual_activity(Mock(attrib={}), "Flowchart") == True
        
        # Test activities with DisplayName are visual
        assert analyzer._is_visual_activity(Mock(attrib={"DisplayName": "My Task"}), "InvokeWorkflowFile") == True
        
        # Test activities without DisplayName (except containers) are not visual
        assert analyzer._is_visual_activity(Mock(attrib={}), "InvokeWorkflowFile") == False
        
        # Test blacklist activities
        assert analyzer._is_visual_activity(Mock(attrib={}), "Variables") == False
        assert analyzer._is_visual_activity(Mock(attrib={}), "ViewState") == False
        
        # Test DisplayName heuristic
        mock_elem = Mock(attrib={"DisplayName": "My Activity"})
        assert analyzer._is_visual_activity(mock_elem, "CustomActivity") == True
    
    def test_expression_detection(self):
        """Test VB.NET/C# expression detection.""" 
        analyzer = EnhancedXamlAnalyzer()
        
        # Test expression patterns
        assert analyzer._is_expression_value("[myVar.ToString()]") == True
        assert analyzer._is_expression_value("Path.Combine(folder, file)") == True
        assert analyzer._is_expression_value("String.Format(\"Hello {0}\", name)") == True
        assert analyzer._is_expression_value("myVar = someValue") == True
        assert analyzer._is_expression_value("new List(Of String)") == True
        
        # Test literal values
        assert analyzer._is_expression_value("\"Hello World\"") == False
        assert analyzer._is_expression_value("123") == False
        assert analyzer._is_expression_value("") == False
        
    def test_stable_node_id_generation(self):
        """Test stable node ID generation with sibling indexing."""
        analyzer = EnhancedXamlAnalyzer()
        
        # Reset sibling counters
        analyzer.sibling_counters = {}
        
        mock_elem = Mock()
        
        # First occurrence should not have index
        node_id = analyzer._generate_stable_node_id("Sequence", mock_elem)
        assert node_id == "Sequence"
        
        # Second occurrence should have index
        node_id = analyzer._generate_stable_node_id("Sequence", mock_elem) 
        assert node_id == "Sequence[1]"
        
        # Third occurrence should increment index
        node_id = analyzer._generate_stable_node_id("Sequence", mock_elem)
        assert node_id == "Sequence[2]"
    
    def test_invocation_classification(self):
        """Test workflow invocation classification."""
        analyzer = EnhancedXamlAnalyzer()
        
        # Test normal invocation
        assert analyzer._classify_invocation("MyWorkflow.xaml") == "invoke"
        
        # Test dynamic invocation
        assert analyzer._classify_invocation("[workflowPath]") == "invoke-dynamic"
        assert analyzer._classify_invocation("Path.Combine(folder, \"workflow.xaml\")") == "invoke-dynamic"
        
        # Test missing invocation
        assert analyzer._classify_invocation("") == "invoke-missing"
        assert analyzer._classify_invocation(None) == "invoke-missing"