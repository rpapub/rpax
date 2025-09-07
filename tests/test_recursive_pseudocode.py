"""Tests for recursive pseudocode generation."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict

import pytest

from rpax.config import PseudocodeConfig, RpaxConfig, ProjectConfig, ProjectType
from rpax.models.callgraph import CallGraphArtifact, CallGraphMetrics, WorkflowDependency, WorkflowNode
from rpax.pseudocode.models import PseudocodeArtifact
from rpax.pseudocode.recursive_generator import RecursivePseudocodeGenerator


class TestRecursivePseudocodeGenerator:
    """Tests for recursive pseudocode generator."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        project_config = ProjectConfig(name="TestProject", type=ProjectType.PROCESS)
        pseudocode_config = PseudocodeConfig(
            generate_expanded=True,
            max_expansion_depth=3,
            cycle_handling="detect_and_mark"
        )
        return RpaxConfig(project=project_config, pseudocode=pseudocode_config)

    @pytest.fixture
    def sample_call_graph(self):
        """Create sample call graph."""
        workflows = {
            "main.xaml": WorkflowNode(
                workflow_id="main.xaml",
                workflow_path="Main.xaml",
                display_name="Main Process",
                is_entry_point=True,
                call_depth=0,
                dependencies=[
                    WorkflowDependency(
                        source_workflow_id="main.xaml",
                        target_workflow_id="process.xaml",
                        target_workflow_path="Process.xaml",
                        invocation_type="static",
                        call_sites=["invoke_1"]
                    )
                ]
            ),
            "process.xaml": WorkflowNode(
                workflow_id="process.xaml",
                workflow_path="Process.xaml",
                display_name="Process",
                call_depth=1,
                dependencies=[
                    WorkflowDependency(
                        source_workflow_id="process.xaml",
                        target_workflow_id="helper.xaml",
                        target_workflow_path="Helper.xaml",
                        invocation_type="static",
                        call_sites=["invoke_2"]
                    )
                ],
                dependents=["main.xaml"]
            ),
            "helper.xaml": WorkflowNode(
                workflow_id="helper.xaml",
                workflow_path="Helper.xaml",
                display_name="Helper",
                call_depth=2,
                dependents=["process.xaml"]
            )
        }

        metrics = CallGraphMetrics(
            total_workflows=3,
            total_dependencies=2,
            entry_points=1,
            orphaned_workflows=0,
            max_call_depth=2,
            cycles_detected=0,
            static_invocations=2,
            dynamic_invocations=0,
            missing_invocations=0
        )

        return CallGraphArtifact(
            project_id="test-project",
            project_slug="test-project-abcd1234",
            generated_at=datetime.now(UTC),
            rpax_version="0.0.1",
            workflows=workflows,
            entry_points=["main.xaml"],
            cycles=[],
            metrics=metrics
        )

    @pytest.fixture
    def sample_pseudocode_artifacts(self):
        """Create sample pseudocode artifacts."""
        artifacts = {}

        # Main workflow pseudocode
        main_artifact = PseudocodeArtifact(
            workflow_id="main.xaml",
            project_id="test-project",
            project_slug="test-project-abcd1234",
            schema_version="1.0.0",
            generated_at=datetime.now(UTC).isoformat(),
            rpax_version="0.0.1",
            activities=[
                {
                    "displayName": "Start Main",
                    "type": "LogMessage",
                    "path": "Main/Start",
                    "activityId": "start_1"
                },
                {
                    "displayName": "Call Process",
                    "type": "InvokeWorkflowFile",
                    "path": "Main/InvokeWorkflowFile",
                    "activityId": "invoke_1",
                    "workflowId": "process.xaml"
                },
                {
                    "displayName": "End Main",
                    "type": "LogMessage", 
                    "path": "Main/End",
                    "activityId": "end_1"
                }
            ],
            activity_count=3
        )
        artifacts["main.xaml"] = main_artifact

        # Process workflow pseudocode
        process_artifact = PseudocodeArtifact(
            workflow_id="process.xaml",
            project_id="test-project",
            project_slug="test-project-abcd1234",
            schema_version="1.0.0",
            generated_at=datetime.now(UTC).isoformat(),
            rpax_version="0.0.1",
            activities=[
                {
                    "displayName": "Process Step 1",
                    "type": "Assign",
                    "path": "Process/Assign",
                    "activityId": "assign_1"
                },
                {
                    "displayName": "Call Helper",
                    "type": "InvokeWorkflowFile", 
                    "path": "Process/InvokeWorkflowFile",
                    "activityId": "invoke_2",
                    "workflowId": "helper.xaml"
                }
            ],
            activity_count=2
        )
        artifacts["process.xaml"] = process_artifact

        # Helper workflow pseudocode
        helper_artifact = PseudocodeArtifact(
            workflow_id="helper.xaml",
            project_id="test-project",
            project_slug="test-project-abcd1234",
            schema_version="1.0.0",
            generated_at=datetime.now(UTC).isoformat(),
            rpax_version="0.0.1",
            activities=[
                {
                    "displayName": "Helper Task",
                    "type": "LogMessage",
                    "path": "Helper/Task",
                    "activityId": "task_1"
                }
            ],
            activity_count=1
        )
        artifacts["helper.xaml"] = helper_artifact

        return artifacts

    def test_generator_initialization(self, config, sample_call_graph):
        """Test generator initialization."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        assert generator.config == config
        assert generator.call_graph == sample_call_graph
        assert generator.pseudocode_config.max_expansion_depth == 3

    def test_is_invoke_workflow_activity(self, config, sample_call_graph):
        """Test detection of InvokeWorkflowFile activities."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)

        # Test positive cases
        invoke_activity = {
            "type": "InvokeWorkflowFile",
            "displayName": "Call Process"
        }
        assert generator._is_invoke_workflow_activity(invoke_activity) is True

        invoke_activity_2 = {
            "type": "SomeOtherActivity",
            "displayName": "Invoke Workflow File: Process"
        }
        assert generator._is_invoke_workflow_activity(invoke_activity_2) is True

        # Test negative cases
        regular_activity = {
            "type": "LogMessage",
            "displayName": "Log something"
        }
        assert generator._is_invoke_workflow_activity(regular_activity) is False

    def test_extract_invoked_workflow_id(self, config, sample_call_graph):
        """Test extraction of target workflow ID."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)

        # Test with workflowId field
        activity_with_id = {
            "type": "InvokeWorkflowFile",
            "workflowId": "process.xaml"
        }
        result = generator._extract_invoked_workflow_id(activity_with_id)
        assert result == "process.xaml"

        # Test without workflowId field
        activity_without_id = {
            "type": "InvokeWorkflowFile",
            "path": "Main/InvokeWorkflowFile"
        }
        result = generator._extract_invoked_workflow_id(activity_without_id)
        assert result is None  # Would need call graph lookup

    def test_format_activity_line(self, config, sample_call_graph):
        """Test activity line formatting."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)

        activity = {
            "displayName": "Test Activity",
            "type": "LogMessage",
            "path": "Main/Test"
        }

        # Test with no indentation
        line = generator._format_activity_line(activity, 0)
        assert line == "- [Test Activity] LogMessage (Path: Main/Test)"

        # Test with indentation
        line = generator._format_activity_line(activity, 2)
        assert line == "    - [Test Activity] LogMessage (Path: Main/Test)"

        # Test without display name
        activity_no_name = {
            "type": "LogMessage",
            "path": "Main/Test"
        }
        line = generator._format_activity_line(activity_no_name, 0)
        assert line == "- LogMessage (Path: Main/Test)"

    def test_depth_limit_handling(self, config, sample_call_graph):
        """Test depth limit handling."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        message = generator._create_depth_limit_message("test.xaml", 1)
        assert "DEPTH LIMIT REACHED" in message
        assert "test.xaml" in message
        assert "max depth: 3" in message

    def test_cycle_handling_detect_and_mark(self, config, sample_call_graph):
        """Test cycle handling with detect_and_mark strategy."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        messages = generator._handle_cycle("test.xaml", 1)
        assert len(messages) == 1
        assert "CYCLE DETECTED" in messages[0]
        assert "test.xaml" in messages[0]

    def test_cycle_handling_detect_and_stop(self, config, sample_call_graph):
        """Test cycle handling with detect_and_stop strategy."""
        # Update config for different cycle handling
        config.pseudocode.cycle_handling = "detect_and_stop"
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        messages = generator._handle_cycle("test.xaml", 1)
        assert len(messages) == 1
        assert "expansion stopped" in messages[0]

    def test_cycle_handling_ignore(self, config, sample_call_graph):
        """Test cycle handling with ignore strategy."""
        config.pseudocode.cycle_handling = "ignore"
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        messages = generator._handle_cycle("test.xaml", 1)
        assert len(messages) == 0  # Should ignore and continue

    def test_generate_recursive_pseudocode_simple(self, config, sample_call_graph, sample_pseudocode_artifacts):
        """Test basic recursive pseudocode generation."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        lines = generator.generate_recursive_pseudocode(
            "main.xaml", sample_pseudocode_artifacts
        )
        
        # Should have base activities plus expanded invocations
        assert len(lines) > 3  # More than just the main workflow activities
        
        # Check that it includes main workflow activities
        activity_lines = [line for line in lines if "Start Main" in line or "Call Process" in line or "End Main" in line]
        assert len(activity_lines) >= 3

    def test_generate_recursive_pseudocode_depth_limit(self, config, sample_call_graph, sample_pseudocode_artifacts):
        """Test recursive generation with depth limits."""
        # Set very low depth limit
        config.pseudocode.max_expansion_depth = 1
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        lines = generator.generate_recursive_pseudocode(
            "main.xaml", sample_pseudocode_artifacts
        )
        
        # Should hit depth limit when trying to expand process.xaml -> helper.xaml
        depth_limit_lines = [line for line in lines if "DEPTH LIMIT REACHED" in line]
        assert len(depth_limit_lines) > 0

    def test_generate_recursive_pseudocode_missing_workflow(self, config, sample_call_graph, sample_pseudocode_artifacts):
        """Test handling of missing workflow."""
        # Remove helper artifact to simulate missing workflow
        limited_artifacts = sample_pseudocode_artifacts.copy()
        del limited_artifacts["helper.xaml"]
        
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        lines = generator.generate_recursive_pseudocode(
            "main.xaml", limited_artifacts
        )
        
        # Should have message about missing workflow
        missing_lines = [line for line in lines if "MISSING WORKFLOW" in line]
        assert len(missing_lines) > 0

    def test_generate_expanded_artifact(self, config, sample_call_graph, sample_pseudocode_artifacts):
        """Test generation of expanded artifact."""
        generator = RecursivePseudocodeGenerator(config, sample_call_graph)
        
        base_artifact = sample_pseudocode_artifacts["main.xaml"]
        
        expanded = generator.generate_expanded_artifact(
            "main.xaml", base_artifact, sample_pseudocode_artifacts
        )
        
        # Check expanded artifact properties
        assert expanded.workflow_id == "main.xaml"
        assert expanded.schema_version == "1.1.0"  # Should be incremented
        assert len(expanded.expanded_pseudocode) > 0
        assert expanded.expansion_config["generated_recursive"] is True
        assert expanded.expansion_config["max_depth"] == 3