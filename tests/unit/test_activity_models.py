"""Unit tests for activity data models."""

from rpax.models.activity import (
    ActivityNode,
    ActivityTree,
    ControlFlowEdge,
    ResourceReference,
    WorkflowControlFlow,
    WorkflowMetrics,
    WorkflowResources,
)


class TestActivityModels:
    """Test activity data models."""

    def test_activity_node_creation(self):
        """Test ActivityNode creation and basic functionality."""
        node = ActivityNode(
            node_id="test.0",
            activity_type="Sequence",
            display_name="Test Sequence",
            properties={"DisplayName": "Test Sequence"},
            arguments={"arg1": "value1"}
        )

        assert node.node_id == "test.0"
        assert node.activity_type == "Sequence"
        assert node.display_name == "Test Sequence"
        assert node.properties["DisplayName"] == "Test Sequence"
        assert node.arguments["arg1"] == "value1"
        assert len(node.children) == 0

    def test_activity_node_hierarchy(self):
        """Test ActivityNode parent-child relationships."""
        parent = ActivityNode("root", "Sequence", "Root")
        child1 = ActivityNode("root.0", "WriteLine", "Log 1")
        child2 = ActivityNode("root.1", "WriteLine", "Log 2")

        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert child1.parent_id == "root"
        assert child2.parent_id == "root"
        assert parent.get_depth() == 2  # Parent + children

        descendants = parent.get_all_descendants()
        assert len(descendants) == 2
        assert child1 in descendants
        assert child2 in descendants

    def test_activity_tree_functionality(self):
        """Test ActivityTree creation and methods."""
        root_node = ActivityNode("root", "Sequence", "Main Sequence")
        child_node = ActivityNode("root.0", "WriteLine", "Hello World")
        root_node.add_child(child_node)

        tree = ActivityTree(
            workflow_id="TestWorkflow.xaml",
            root_node=root_node,
            variables=[{"name": "var1", "type": "String"}],
            arguments=[{"name": "arg1", "direction": "In"}],
            imports=["System"],
            content_hash="abc123"
        )

        assert tree.workflow_id == "TestWorkflow.xaml"
        assert tree.root_node == root_node
        assert len(tree.variables) == 1
        assert len(tree.arguments) == 1
        assert len(tree.imports) == 1

        all_nodes = tree.get_all_nodes()
        assert len(all_nodes) == 2  # root + child
        assert root_node in all_nodes
        assert child_node in all_nodes

        found_node = tree.find_node_by_id("root.0")
        assert found_node == child_node

        found_node = tree.find_node_by_id("nonexistent")
        assert found_node is None

        writeline_nodes = tree.get_nodes_by_type("WriteLine")
        assert len(writeline_nodes) == 1
        assert child_node in writeline_nodes

    def test_control_flow_edge(self):
        """Test ControlFlowEdge model."""
        edge = ControlFlowEdge(
            from_node_id="root.0",
            to_node_id="root.1",
            edge_type="seq-next",
            condition="value > 0"
        )

        assert edge.from_node_id == "root.0"
        assert edge.to_node_id == "root.1"
        assert edge.edge_type == "seq-next"
        assert edge.condition == "value > 0"

        edge_str = str(edge)
        assert "root.0" in edge_str
        assert "root.1" in edge_str
        assert "seq-next" in edge_str
        assert "value > 0" in edge_str

    def test_workflow_control_flow(self):
        """Test WorkflowControlFlow model."""
        control_flow = WorkflowControlFlow("TestWorkflow.xaml")

        control_flow.add_edge("root", "root.0", "contains")
        control_flow.add_edge("root.0", "root.1", "seq-next")
        control_flow.add_edge("root.1", "root.2", "seq-next", "if condition")

        assert len(control_flow.edges) == 3

        successors = control_flow.get_successors("root.0")
        assert len(successors) == 1
        assert "root.1" in successors

        predecessors = control_flow.get_predecessors("root.1")
        assert len(predecessors) == 1
        assert "root.0" in predecessors

        no_successors = control_flow.get_successors("nonexistent")
        assert len(no_successors) == 0

    def test_resource_reference(self):
        """Test ResourceReference model."""
        ref = ResourceReference(
            resource_type="file",
            resource_name="ConfigFile",
            resource_value="config.json",
            node_id="root.0",
            property_name="FileName",
            is_dynamic=False,
            raw_value="config.json"
        )

        assert ref.resource_type == "file"
        assert ref.resource_name == "ConfigFile"
        assert ref.resource_value == "config.json"
        assert ref.node_id == "root.0"
        assert ref.property_name == "FileName"
        assert ref.is_dynamic is False
        assert ref.raw_value == "config.json"

    def test_workflow_resources(self):
        """Test WorkflowResources model."""
        resources = WorkflowResources("TestWorkflow.xaml")

        resources.add_reference("file", "Config", "config.json", "root.0", "FileName")
        resources.add_reference("selector", "Button", "<ctrl>Button", "root.1", "Selector", True)
        resources.add_reference("url", "API", "https://api.example.com", "root.2", "Url")

        assert len(resources.references) == 3

        file_refs = resources.get_by_type("file")
        assert len(file_refs) == 1
        assert file_refs[0].resource_name == "Config"

        selector_refs = resources.get_by_type("selector")
        assert len(selector_refs) == 1
        assert selector_refs[0].is_dynamic is True

        url_refs = resources.get_by_type("url")
        assert len(url_refs) == 1
        assert url_refs[0].resource_value == "https://api.example.com"

    def test_workflow_metrics(self):
        """Test WorkflowMetrics model."""
        metrics = WorkflowMetrics()

        # Test initial values
        assert metrics.total_nodes == 0
        assert metrics.max_depth == 0
        assert metrics.loop_count == 0
        assert len(metrics.activity_types) == 0

        # Test increment functionality
        metrics.increment_activity_type("Sequence")
        metrics.increment_activity_type("WriteLine")
        metrics.increment_activity_type("Sequence")

        assert len(metrics.activity_types) == 2
        assert metrics.activity_types["Sequence"] == 2
        assert metrics.activity_types["WriteLine"] == 1

        # Test updating metrics
        metrics.total_nodes = 10
        metrics.max_depth = 5
        metrics.loop_count = 2
        metrics.invoke_count = 3
        metrics.log_count = 4

        assert metrics.total_nodes == 10
        assert metrics.max_depth == 5
        assert metrics.loop_count == 2
        assert metrics.invoke_count == 3
        assert metrics.log_count == 4
