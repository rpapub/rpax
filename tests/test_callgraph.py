"""Tests for call graph generation and models."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List

import pytest

from rpax.config import RpaxConfig, ProjectConfig, ProjectType
from rpax.graph.callgraph_generator import CallGraphGenerator
from rpax.models.callgraph import (
    CallGraphArtifact,
    CallGraphCycle,
    CallGraphMetrics,
    WorkflowDependency,
    WorkflowNode,
)
from rpax.models.manifest import ProjectManifest
from rpax.models.workflow import WorkflowIndex, Workflow


class TestCallGraphModels:
    """Tests for call graph data models."""

    def test_workflow_dependency_creation(self):
        """Test workflow dependency model."""
        dependency = WorkflowDependency(
            source_workflow_id="main.xaml",
            target_workflow_id="process.xaml",
            target_workflow_path="Processes/Process.xaml",
            invocation_type="static",
            call_sites=["activity_123"],
            arguments={"input": "test"}
        )
        
        assert dependency.source_workflow_id == "main.xaml"
        assert dependency.target_workflow_id == "process.xaml"
        assert dependency.invocation_type == "static"
        assert len(dependency.call_sites) == 1
        assert dependency.arguments["input"] == "test"

    def test_workflow_node_creation(self):
        """Test workflow node model."""
        node = WorkflowNode(
            workflow_id="main.xaml",
            workflow_path="Main.xaml",
            display_name="Main Process",
            is_entry_point=True,
            call_depth=0
        )
        
        assert node.workflow_id == "main.xaml"
        assert node.is_entry_point is True
        assert node.call_depth == 0
        assert len(node.dependencies) == 0
        assert len(node.dependents) == 0

    def test_call_graph_cycle_creation(self):
        """Test call graph cycle model."""
        cycle = CallGraphCycle(
            cycle_id="cycle_1",
            workflow_ids=["a.xaml", "b.xaml", "c.xaml"],
            cycle_type="complex"
        )
        
        assert cycle.cycle_id == "cycle_1"
        assert len(cycle.workflow_ids) == 3
        assert cycle.cycle_type == "complex"

    def test_call_graph_metrics_creation(self):
        """Test call graph metrics model."""
        metrics = CallGraphMetrics(
            total_workflows=5,
            total_dependencies=8,
            entry_points=2,
            orphaned_workflows=1,
            max_call_depth=3,
            cycles_detected=1,
            static_invocations=6,
            dynamic_invocations=1,
            missing_invocations=1
        )
        
        assert metrics.total_workflows == 5
        assert metrics.cycles_detected == 1
        assert metrics.static_invocations == 6

    def test_call_graph_artifact_creation(self):
        """Test complete call graph artifact model."""
        workflows = {
            "main.xaml": WorkflowNode(
                workflow_id="main.xaml",
                workflow_path="Main.xaml",
                display_name="Main Process",
                is_entry_point=True,
                call_depth=0
            )
        }
        
        metrics = CallGraphMetrics(
            total_workflows=1,
            total_dependencies=0,
            entry_points=1,
            orphaned_workflows=0,
            max_call_depth=0,
            cycles_detected=0,
            static_invocations=0,
            dynamic_invocations=0,
            missing_invocations=0
        )
        
        artifact = CallGraphArtifact(
            project_id="test-project",
            project_slug="test-project-abcd1234",
            generated_at=datetime.now(UTC),
            rpax_version="0.0.1",
            workflows=workflows,
            entry_points=["main.xaml"],
            cycles=[],
            metrics=metrics
        )
        
        assert artifact.project_id == "test-project"
        assert len(artifact.workflows) == 1
        assert len(artifact.entry_points) == 1
        assert artifact.metrics.total_workflows == 1


class TestCallGraphGenerator:
    """Tests for call graph generator."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        project_config = ProjectConfig(name="TestProject", type=ProjectType.PROCESS)
        return RpaxConfig(project=project_config)

    @pytest.fixture
    def sample_workflow_index(self):
        """Create sample workflow index."""
        workflows = [
            Workflow(
                id="test-project-abcd1234#main.xaml#abc123",
                projectSlug="test-project-abcd1234",
                workflowId="main.xaml",
                contentHash="abc123456789",
                filePath="D:/test/Main.xaml",
                fileName="Main.xaml",
                relativePath="Main.xaml",
                displayName="Main",
                discoveredAt=datetime.now(UTC).isoformat(),
                fileSize=1000,
                lastModified=datetime.now(UTC).isoformat()
            ),
            Workflow(
                id="test-project-abcd1234#processes/process.xaml#def456",
                projectSlug="test-project-abcd1234", 
                workflowId="processes/process.xaml",
                contentHash="def456789012",
                filePath="D:/test/Processes/Process.xaml",
                fileName="Process.xaml",
                relativePath="Processes/Process.xaml",
                displayName="Process",
                discoveredAt=datetime.now(UTC).isoformat(),
                fileSize=2000,
                lastModified=datetime.now(UTC).isoformat()
            ),
            Workflow(
                id="test-project-abcd1234#common/helper.xaml#ghi789",
                projectSlug="test-project-abcd1234",
                workflowId="common/helper.xaml",
                contentHash="ghi789012345",
                filePath="D:/test/Common/Helper.xaml",
                fileName="Helper.xaml", 
                relativePath="Common/Helper.xaml",
                displayName="Helper",
                discoveredAt=datetime.now(UTC).isoformat(),
                fileSize=500,
                lastModified=datetime.now(UTC).isoformat()
            )
        ]
        
        return WorkflowIndex(
            projectName="Test Project",
            projectRoot="D:/test",
            scanTimestamp=datetime.now(UTC).isoformat(),
            totalWorkflows=3,
            successfulParses=3,
            failedParses=0,
            workflows=workflows
        )

    @pytest.fixture
    def sample_manifest(self):
        """Create sample project manifest."""
        from rpax.models.project import EntryPoint
        
        return ProjectManifest(
            project_name="Test Project",
            project_id="test-project",
            project_type="process",
            project_root="D:/test",
            rpax_version="0.0.1",
            generated_at=datetime.now(UTC).isoformat(),
            main_workflow="Main.xaml",
            entry_points=[
                EntryPoint(
                    file_path="Main.xaml",
                    unique_id="main-uuid",
                    input=[],
                    output=[]
                )
            ],
            total_workflows=3
        )

    @pytest.fixture
    def temp_invocations_file(self):
        """Create temporary invocations.jsonl file."""
        invocations_data = [
            {
                "source_workflow_id": "main.xaml",
                "target_workflow_path": "Processes/Process.xaml", 
                "invocation_type": "static",
                "activity_id": "invoke_1",
                "arguments": {"input": "test"}
            },
            {
                "source_workflow_id": "processes/process.xaml",
                "target_workflow_path": "Common/Helper.xaml",
                "invocation_type": "static", 
                "activity_id": "invoke_2",
                "arguments": {}
            },
            {
                "source_workflow_id": "processes/process.xaml",
                "target_workflow_path": "NonExistent.xaml",
                "invocation_type": "missing",
                "activity_id": "invoke_3",
                "arguments": {}
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for invocation in invocations_data:
                json.dump(invocation, f)
                f.write('\n')
            
        yield Path(f.name)
        Path(f.name).unlink()  # Cleanup

    def test_generator_initialization(self, config):
        """Test generator initialization."""
        generator = CallGraphGenerator(config)
        assert generator.config == config

    def test_load_invocations_missing_file(self, config):
        """Test loading invocations from non-existent file."""
        generator = CallGraphGenerator(config)
        invocations = generator._load_invocations(Path("nonexistent.jsonl"))
        assert len(invocations) == 0

    def test_load_invocations_valid_file(self, config, temp_invocations_file):
        """Test loading invocations from valid JSONL file."""
        generator = CallGraphGenerator(config)
        invocations = generator._load_invocations(temp_invocations_file)
        
        assert len(invocations) == 3
        assert invocations[0]["source_workflow_id"] == "main.xaml"
        assert invocations[1]["target_workflow_path"] == "Common/Helper.xaml"
        assert invocations[2]["invocation_type"] == "missing"

    def test_build_workflow_nodes(self, config, sample_workflow_index):
        """Test building workflow nodes from index."""
        generator = CallGraphGenerator(config)
        entry_points = ["main.xaml"]
        
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        assert len(workflows) == 3
        assert "main.xaml" in workflows
        assert workflows["main.xaml"].is_entry_point is True
        assert workflows["processes/process.xaml"].is_entry_point is False
        assert workflows["main.xaml"].call_depth == 0
        assert workflows["processes/process.xaml"].call_depth == -1  # Not calculated yet

    def test_find_target_workflow_id(self, config, sample_workflow_index):
        """Test finding target workflow by path."""
        generator = CallGraphGenerator(config)
        entry_points = ["main.xaml"]
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        # Exact path match
        target_id = generator._find_target_workflow_id(workflows, "Processes/Process.xaml")
        assert target_id == "processes/process.xaml"
        
        # Filename match
        target_id = generator._find_target_workflow_id(workflows, "Helper.xaml")
        assert target_id == "common/helper.xaml"
        
        # No match
        target_id = generator._find_target_workflow_id(workflows, "NonExistent.xaml")
        assert target_id is None

    def test_process_invocations(self, config, sample_workflow_index, temp_invocations_file):
        """Test processing invocations into dependencies."""
        generator = CallGraphGenerator(config)
        entry_points = ["main.xaml"]
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        invocations = generator._load_invocations(temp_invocations_file)
        generator._process_invocations(workflows, invocations)
        
        # Check main.xaml has dependency on processes/process.xaml
        main_node = workflows["main.xaml"]
        assert len(main_node.dependencies) == 1
        assert main_node.dependencies[0].target_workflow_id == "processes/process.xaml"
        
        # Check processes/process.xaml has dependencies
        process_node = workflows["processes/process.xaml"]
        assert len(process_node.dependencies) == 2
        
        # Check common/helper.xaml is in processes/process.xaml's dependents
        helper_node = workflows["common/helper.xaml"]
        assert "processes/process.xaml" in helper_node.dependents

    def test_calculate_call_depths(self, config, sample_workflow_index):
        """Test call depth calculation."""
        generator = CallGraphGenerator(config)
        entry_points = ["main.xaml"]
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        # Add some dependencies manually for testing
        main_dep = WorkflowDependency(
            source_workflow_id="main.xaml",
            target_workflow_id="processes/process.xaml",
            target_workflow_path="Processes/Process.xaml",
            invocation_type="static"
        )
        workflows["main.xaml"].dependencies.append(main_dep)
        
        process_dep = WorkflowDependency(
            source_workflow_id="processes/process.xaml", 
            target_workflow_id="common/helper.xaml",
            target_workflow_path="Common/Helper.xaml",
            invocation_type="static"
        )
        workflows["processes/process.xaml"].dependencies.append(process_dep)
        
        generator._calculate_call_depths(workflows, entry_points)
        
        assert workflows["main.xaml"].call_depth == 0
        assert workflows["processes/process.xaml"].call_depth == 1
        assert workflows["common/helper.xaml"].call_depth == 2

    def test_detect_cycles_no_cycles(self, config, sample_workflow_index):
        """Test cycle detection with no cycles."""
        generator = CallGraphGenerator(config) 
        entry_points = ["main.xaml"]
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        cycles = generator._detect_cycles(workflows)
        assert len(cycles) == 0

    def test_detect_cycles_self_cycle(self, config, sample_workflow_index):
        """Test detection of self-referencing cycle."""
        generator = CallGraphGenerator(config)
        entry_points = ["main.xaml"]
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        # Create self-referencing cycle
        self_dep = WorkflowDependency(
            source_workflow_id="main.xaml",
            target_workflow_id="main.xaml", 
            target_workflow_path="Main.xaml",
            invocation_type="static"
        )
        workflows["main.xaml"].dependencies.append(self_dep)
        
        cycles = generator._detect_cycles(workflows)
        assert len(cycles) == 1
        assert cycles[0].cycle_type == "self"
        assert "main.xaml" in cycles[0].workflow_ids

    def test_calculate_metrics(self, config, sample_workflow_index, temp_invocations_file):
        """Test metrics calculation."""
        generator = CallGraphGenerator(config)
        entry_points = ["main.xaml"]
        workflows = generator._build_workflow_nodes(sample_workflow_index, entry_points)
        
        invocations = generator._load_invocations(temp_invocations_file)
        generator._process_invocations(workflows, invocations)
        
        cycles = []  # No cycles for this test
        metrics = generator._calculate_metrics(workflows, cycles)
        
        assert metrics.total_workflows == 3
        assert metrics.entry_points == 1
        assert metrics.total_dependencies == 3  # 2 static + 1 missing
        assert metrics.static_invocations == 2
        assert metrics.missing_invocations == 1
        assert metrics.cycles_detected == 0

    def test_generate_complete_call_graph(self, config, sample_manifest, sample_workflow_index, temp_invocations_file):
        """Test complete call graph generation."""
        generator = CallGraphGenerator(config)
        
        call_graph = generator.generate_call_graph(
            sample_manifest, sample_workflow_index, temp_invocations_file
        )
        
        assert call_graph.project_id == "test-project"
        assert call_graph.project_slug == "test-project-generated"
        assert len(call_graph.workflows) == 3
        assert len(call_graph.entry_points) == 1
        assert call_graph.metrics.total_workflows == 3
        
        # Check workflow relationships
        main_node = call_graph.workflows["main.xaml"]
        assert main_node.is_entry_point is True
        assert len(main_node.dependencies) == 1