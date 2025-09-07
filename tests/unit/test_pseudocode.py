"""Tests for pseudocode generation functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rpax.parser.enhanced_xaml_analyzer import EnhancedActivityNode
from rpax.pseudocode import PseudocodeGenerator, PseudocodeEntry, PseudocodeArtifact


class TestPseudocodeModels:
    """Test pseudocode data models."""
    
    def test_pseudocode_entry_creation(self):
        """Test creating pseudocode entry."""
        entry = PseudocodeEntry(
            indent=1,
            display_name="Log Message INFO",
            tag="LogMessage",
            path="Activity/Sequence/LogMessage",
            formatted_line="  - [Log Message INFO] LogMessage (Path: Activity/Sequence/LogMessage)",
            node_id="/Sequence[0]/LogMessage[0]",
            depth=2,
            is_visual=True
        )
        
        assert entry.indent == 1
        assert entry.display_name == "Log Message INFO"
        assert entry.tag == "LogMessage"
        assert entry.path == "Activity/Sequence/LogMessage"
        assert entry.children == []  # default empty list
    
    def test_pseudocode_artifact_validation(self):
        """Test pseudocode artifact model validation."""
        artifact = PseudocodeArtifact(
            workflow_id="Main.xaml",
            project_id="test-project",
            project_slug="test-project-123",
            generated_at="2024-01-01T00:00:00Z",
            rpax_version="0.1.0",
            activities=[],
            activity_count=3,
            total_lines=5,
            total_activities=3,
            entries=[
                {
                    "indent": 0,
                    "displayName": "Main Sequence",
                    "tag": "Sequence",
                    "path": "Activity/Sequence",
                    "formattedLine": "- [Main Sequence] Sequence (Path: Activity/Sequence)",
                    "nodeId": "/Sequence[0]",
                    "depth": 0,
                    "isVisual": True,
                    "children": []
                }
            ]
        )
        
        assert artifact.workflow_id == "Main.xaml"
        assert artifact.format_version == "gist-style"
        assert artifact.total_lines == 5
        assert len(artifact.entries) == 1


class TestPseudocodeGenerator:
    """Test pseudocode generation functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.generator = PseudocodeGenerator()
    
    def test_format_pseudocode_line_root(self):
        """Test formatting pseudocode line for root activity."""
        activity = EnhancedActivityNode(
            node_id="/Sequence[0]",
            tag="Sequence",
            display_name="Main Process",
            path="Activity/Sequence",
            depth=0,
            is_visual=True
        )
        
        result = self.generator._format_pseudocode_line(activity, 0)
        expected = "- [Main Process] Sequence (Path: Activity/Sequence)"
        
        assert result == expected
    
    def test_format_pseudocode_line_nested(self):
        """Test formatting pseudocode line for nested activity."""
        activity = EnhancedActivityNode(
            node_id="/Sequence[0]/LogMessage[0]",
            tag="LogMessage",
            display_name="Log start message",
            path="Activity/Sequence/LogMessage",
            depth=1,
            is_visual=True
        )
        
        result = self.generator._format_pseudocode_line(activity, 1)
        expected = "  - [Log start message] LogMessage (Path: Activity/Sequence/LogMessage)"
        
        assert result == expected
    
    def test_format_pseudocode_line_deep_nested(self):
        """Test formatting pseudocode line for deeply nested activity."""
        activity = EnhancedActivityNode(
            node_id="/Sequence[0]/TryCatch[0]/Sequence[0]/Assign[0]",
            tag="Assign",
            display_name="Set username",
            path="Activity/Sequence/TryCatch/TryCatch.Try/Sequence/Assign",
            depth=3,
            is_visual=True
        )
        
        result = self.generator._format_pseudocode_line(activity, 3)
        expected = "      - [Set username] Assign (Path: Activity/Sequence/TryCatch/TryCatch.Try/Sequence/Assign)"
        
        assert result == expected
    
    def test_generate_workflow_pseudocode_success(self):
        """Test successful pseudocode generation."""
        # Create test activities
        root_activity = EnhancedActivityNode(
            node_id="/Sequence[0]",
            tag="Sequence", 
            display_name="Main Sequence",
            path="Activity/Sequence",
            depth=0,
            is_visual=True,
            parent_id=None
        )
        
        child_activity = EnhancedActivityNode(
            node_id="/Sequence[0]/LogMessage[0]",
            tag="LogMessage",
            display_name="Log Message INFO begin", 
            path="Activity/Sequence/LogMessage",
            depth=1,
            is_visual=True,
            parent_id="/Sequence[0]"
        )
        
        # Mock the analyzer method directly on the generator instance
        with patch.object(self.generator.analyzer, 'analyze_workflow') as mock_analyze:
            mock_analyze.return_value = (
                [root_activity, child_activity],
                {"workflow_id": "TestWorkflow.xaml"}
            )
            
            # Generate pseudocode
            xaml_path = Path("TestWorkflow.xaml")
            result = self.generator.generate_workflow_pseudocode(xaml_path)
        
        # Verify result
        assert result.workflow_id == "TestWorkflow"
        assert result.total_activities == 2
        assert result.total_lines == 2
        assert len(result.entries) == 2
        
        # Check formatted lines
        root_entry = result.entries[0]
        assert root_entry["displayName"] == "Main Sequence"
        assert root_entry["formattedLine"] == "- [Main Sequence] Sequence (Path: Activity/Sequence)"
        assert root_entry["indent"] == 0
        
        child_entry = result.entries[1]
        assert child_entry["displayName"] == "Log Message INFO begin"
        assert child_entry["formattedLine"] == "  - [Log Message INFO begin] LogMessage (Path: Activity/Sequence/LogMessage)"
        assert child_entry["indent"] == 1
    
    def test_generate_pseudocode_entries_hierarchy(self):
        """Test pseudocode entry generation with proper hierarchy."""
        # Create parent activity
        parent = EnhancedActivityNode(
            node_id="/Sequence[0]",
            tag="Sequence",
            display_name="Parent Sequence",
            path="Activity/Sequence", 
            depth=0,
            is_visual=True,
            parent_id=None
        )
        
        # Create child activity
        child = EnhancedActivityNode(
            node_id="/Sequence[0]/LogMessage[0]",
            tag="LogMessage",
            display_name="Child LogMessage",
            path="Activity/Sequence/LogMessage",
            depth=1,
            is_visual=True,
            parent_id="/Sequence[0]"
        )
        
        activities = [parent, child]
        entries = self.generator._generate_pseudocode_entries(activities)
        
        # Should have 2 entries total
        assert len(entries) == 2
        
        # Parent should be first
        parent_entry = entries[0]
        assert parent_entry.display_name == "Parent Sequence"
        assert parent_entry.indent == 0
        assert len(parent_entry.children) == 1
        
        # Child should be second
        child_entry = entries[1]
        assert child_entry.display_name == "Child LogMessage"
        assert child_entry.indent == 1
        assert len(child_entry.children) == 0
        
        # Parent should contain child in its children list
        assert parent_entry.children[0] == child_entry
    
    def test_render_as_text(self):
        """Test rendering pseudocode artifact as text."""
        artifact = PseudocodeArtifact(
            workflow_id="TestWorkflow",
            project_id="test-project",
            project_slug="test-project-123",
            generated_at="2024-01-01T00:00:00Z",
            rpax_version="0.1.0",
            activities=[],
            activity_count=2,
            total_lines=2,
            total_activities=2,
            entries=[
                {
                    "indent": 0,
                    "displayName": "Main Sequence",
                    "tag": "Sequence",
                    "path": "Activity/Sequence",
                    "formattedLine": "- [Main Sequence] Sequence (Path: Activity/Sequence)",
                    "nodeId": "/Sequence[0]",
                    "depth": 0,
                    "isVisual": True,
                    "children": []
                },
                {
                    "indent": 1,
                    "displayName": "Log Message",
                    "tag": "LogMessage", 
                    "path": "Activity/Sequence/LogMessage",
                    "formattedLine": "  - [Log Message] LogMessage (Path: Activity/Sequence/LogMessage)",
                    "nodeId": "/Sequence[0]/LogMessage[0]",
                    "depth": 1,
                    "isVisual": True,
                    "children": []
                }
            ]
        )
        
        result = self.generator.render_as_text(artifact)
        expected = "- [Main Sequence] Sequence (Path: Activity/Sequence)\n  - [Log Message] LogMessage (Path: Activity/Sequence/LogMessage)"
        
        assert result == expected
    
    def test_render_as_text_empty(self):
        """Test rendering empty pseudocode artifact."""
        artifact = PseudocodeArtifact(
            workflow_id="EmptyWorkflow",
            project_id="test-project",
            project_slug="test-project-123",
            generated_at="2024-01-01T00:00:00Z",
            rpax_version="0.1.0",
            activities=[],
            activity_count=0,
            total_lines=0,
            total_activities=0,
            entries=[]
        )
        
        result = self.generator.render_as_text(artifact)
        assert result == "# No pseudocode available for EmptyWorkflow"
    
    def test_create_empty_artifact_with_error(self):
        """Test creating empty artifact with error message."""
        result = self.generator._create_empty_artifact("FailedWorkflow", error="Parse failed")
        
        assert result.workflow_id == "FailedWorkflow"
        assert result.total_lines == 0
        assert result.total_activities == 0
        assert result.entries == []
        assert result.metadata["error"] == "Parse failed"
    
    def test_serialize_entry(self):
        """Test serializing pseudocode entry to dictionary."""
        child_entry = PseudocodeEntry(
            indent=2,
            display_name="Child",
            tag="Assign",
            path="Activity/Sequence/Assign",
            formatted_line="    - [Child] Assign (Path: Activity/Sequence/Assign)",
            node_id="/Sequence[0]/Assign[0]",
            depth=2,
            is_visual=True
        )
        
        parent_entry = PseudocodeEntry(
            indent=1,
            display_name="Parent",
            tag="Sequence", 
            path="Activity/Sequence",
            formatted_line="  - [Parent] Sequence (Path: Activity/Sequence)",
            node_id="/Sequence[0]",
            depth=1,
            is_visual=True,
            children=[child_entry]
        )
        
        result = self.generator._serialize_entry(parent_entry)
        
        assert result["displayName"] == "Parent"
        assert result["tag"] == "Sequence"
        assert result["indent"] == 1
        assert len(result["children"]) == 1
        assert result["children"][0]["displayName"] == "Child"
    
    def test_generate_project_pseudocode_index(self):
        """Test generating project pseudocode index."""
        artifacts = [
            PseudocodeArtifact(
                workflow_id="Main",
                project_id="test-project-id",
                project_slug="test-project-abcd1234",
                generated_at="2024-01-01T00:00:00Z",
                rpax_version="0.1.0",
                activities=[],
                activity_count=3,
                total_lines=5,
                total_activities=3,
                entries=[]
            ),
            PseudocodeArtifact(
                workflow_id="Helper",
                project_id="test-project-id", 
                project_slug="test-project-abcd1234",
                generated_at="2024-01-01T00:00:00Z",
                rpax_version="0.1.0",
                activities=[],
                activity_count=1,
                total_lines=2,
                total_activities=1,
                entries=[],
                metadata={"error": "Failed to parse"}
            )
        ]
        
        result = self.generator.generate_project_pseudocode_index(
            "test-project-abcd1234", "test-project-id", artifacts
        )
        
        assert result.project_slug == "test-project-abcd1234"
        assert result.project_id == "test-project-id" 
        assert result.total_workflows == 2
        assert len(result.workflows) == 2
        
        # Check workflow entries
        main_workflow = result.workflows[0]
        assert main_workflow["workflowId"] == "Main"
        assert main_workflow["totalLines"] == 5
        assert main_workflow["hasError"] is False
        
        helper_workflow = result.workflows[1]
        assert helper_workflow["workflowId"] == "Helper"
        assert helper_workflow["hasError"] is True