"""Unit tests for XAML workflow discovery."""

from pathlib import Path
from tempfile import TemporaryDirectory

from rpax.models.workflow import Workflow
from rpax.parser.xaml import XamlDiscovery


class TestXamlDiscovery:
    """Test XAML workflow discovery functionality."""

    def test_discover_empty_project(self):
        """Test discovery in empty project directory."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            discovery = XamlDiscovery(temp_path)

            index = discovery.discover_workflows()
            assert index.project_name == temp_path.name
            assert index.total_workflows == 0
            assert index.successful_parses == 0
            assert index.failed_parses == 0
            assert len(index.workflows) == 0

    def test_discover_single_workflow(self):
        """Test discovery of single XAML workflow."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a simple XAML file
            xaml_file = temp_path / "Main.xaml"
            xaml_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
</Activity>""")

            discovery = XamlDiscovery(temp_path)
            index = discovery.discover_workflows()

            assert index.total_workflows == 1
            assert index.successful_parses == 1
            assert index.failed_parses == 0
            assert len(index.workflows) == 1

            workflow = index.workflows[0]
            assert workflow.file_name == "Main.xaml"
            assert workflow.relative_path == "Main.xaml"
            assert workflow.display_name == "Main"
            assert workflow.parse_successful is True

    def test_discover_multiple_workflows(self):
        """Test discovery of multiple XAML workflows."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple XAML files
            (temp_path / "Main.xaml").write_text("<Activity></Activity>")
            (temp_path / "Helper.xaml").write_text("<Activity></Activity>")

            sub_dir = temp_path / "workflows"
            sub_dir.mkdir()
            (sub_dir / "SubWorkflow.xaml").write_text("<Activity></Activity>")

            discovery = XamlDiscovery(temp_path)
            index = discovery.discover_workflows()

            assert index.total_workflows == 3
            assert index.successful_parses == 3
            assert len(index.workflows) == 3

            # Check relative paths
            relative_paths = [w.relative_path for w in index.workflows]
            assert "Main.xaml" in relative_paths
            assert "Helper.xaml" in relative_paths
            assert "workflows/SubWorkflow.xaml" in relative_paths

    def test_exclude_patterns(self):
        """Test exclusion patterns functionality."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create workflows
            (temp_path / "Main.xaml").write_text("<Activity></Activity>")

            # Create excluded directories and files
            local_dir = temp_path / ".local"
            local_dir.mkdir()
            (local_dir / "LocalWorkflow.xaml").write_text("<Activity></Activity>")

            settings_dir = temp_path / ".settings"
            settings_dir.mkdir()
            (settings_dir / "SettingsWorkflow.xaml").write_text("<Activity></Activity>")

            discovery = XamlDiscovery(
                temp_path,
                exclude_patterns=[".local/**", ".settings/**"]
            )
            index = discovery.discover_workflows()

            assert index.total_workflows == 1  # Only Main.xaml
            assert len(index.excluded_files) == 2  # Two excluded

            workflow_paths = [w.relative_path for w in index.workflows]
            assert "Main.xaml" in workflow_paths
            assert ".local/LocalWorkflow.xaml" not in workflow_paths
            assert ".settings/SettingsWorkflow.xaml" not in workflow_paths

            # Check excluded files are tracked
            excluded_paths = index.excluded_files
            assert ".local/LocalWorkflow.xaml" in excluded_paths
            assert ".settings/SettingsWorkflow.xaml" in excluded_paths

    def test_workflow_identity_generation(self):
        """Test workflow identity and hash generation."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create XAML with specific content
            xaml_content = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="TestWorkflow">
  <Sequence DisplayName="Test Sequence">
    <WriteLine Text="Hello World" />
  </Sequence>
</Activity>"""

            xaml_file = temp_path / "TestWorkflow.xaml"
            xaml_file.write_text(xaml_content)

            discovery = XamlDiscovery(temp_path)
            index = discovery.discover_workflows()

            workflow = index.workflows[0]

            # Check identity components
            expected_slug = temp_path.name.lower().replace(" ", "-").replace("_", "-")
            assert workflow.project_slug == expected_slug
            assert workflow.workflow_id == "TestWorkflow.xaml"
            assert len(workflow.content_hash) == 64  # Full SHA256

            # Check composite ID format (uses truncated hash)
            expected_id = f"{workflow.project_slug}#{workflow.workflow_id}#{workflow.content_hash[:16]}"
            assert workflow.id == expected_id

    def test_path_normalization(self):
        """Test POSIX path normalization."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            nested_dir = temp_path / "some" / "nested" / "path"
            nested_dir.mkdir(parents=True)
            xaml_file = nested_dir / "NestedWorkflow.xaml"
            xaml_file.write_text("<Activity></Activity>")

            discovery = XamlDiscovery(temp_path)
            index = discovery.discover_workflows()

            workflow = index.workflows[0]
            # Should be POSIX format regardless of OS
            assert workflow.relative_path == "some/nested/path/NestedWorkflow.xaml"
            assert workflow.workflow_id == "some/nested/path/NestedWorkflow.xaml"

    def test_case_insensitive_xaml_discovery(self):
        """Test case-insensitive XAML file discovery."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different cases
            (temp_path / "Main.xaml").write_text("<Activity></Activity>")
            (temp_path / "Helper.XAML").write_text("<Activity></Activity>")
            (temp_path / "Test.Xaml").write_text("<Activity></Activity>")

            # Create non-XAML file
            (temp_path / "ReadMe.txt").write_text("Not a workflow")

            discovery = XamlDiscovery(temp_path)
            index = discovery.discover_workflows()

            # Should find all 3 XAML files regardless of case
            assert index.total_workflows == 3

            file_names = [w.file_name for w in index.workflows]
            assert "Main.xaml" in file_names
            assert "Helper.XAML" in file_names
            assert "Test.Xaml" in file_names

    def test_parse_error_handling(self):
        """Test handling of parse errors."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create valid workflow
            (temp_path / "Valid.xaml").write_text("<Activity></Activity>")

            # Create workflow that will cause parse error (unreadable file)
            error_file = temp_path / "Error.xaml"
            error_file.touch()
            # Make file unreadable by removing read permissions
            # Note: This test is OS-dependent

            discovery = XamlDiscovery(temp_path)

            # Override _create_workflow_entry to simulate parse error
            original_method = discovery._create_workflow_entry
            def mock_create_workflow_entry(xaml_file, parse_error=None):
                if xaml_file.name == "Error.xaml":
                    return original_method(xaml_file, "Simulated parse error")
                return original_method(xaml_file, parse_error)

            discovery._create_workflow_entry = mock_create_workflow_entry

            index = discovery.discover_workflows()

            assert index.total_workflows == 2
            assert index.successful_parses == 1
            assert index.failed_parses == 1

            # Find the error workflow
            error_workflow = None
            for workflow in index.workflows:
                if workflow.file_name == "Error.xaml":
                    error_workflow = workflow
                    break

            assert error_workflow is not None
            assert error_workflow.parse_successful is False
            assert len(error_workflow.parse_errors) == 1
            assert "Simulated parse error" in error_workflow.parse_errors


class TestWorkflowModel:
    """Test Workflow model functionality."""

    def test_generate_content_hash(self):
        """Test content hash generation."""
        content1 = b"<Activity>Test</Activity>"
        content2 = b"<Activity>Different</Activity>"

        hash1 = Workflow.generate_content_hash(content1)
        hash2 = Workflow.generate_content_hash(content2)

        assert len(hash1) == 64
        assert len(hash2) == 64
        assert hash1 != hash2

        # Same content should generate same hash
        hash1_again = Workflow.generate_content_hash(content1)
        assert hash1 == hash1_again

    def test_generate_composite_id(self):
        """Test composite ID generation."""
        composite_id = Workflow.generate_composite_id("myproject", "Main.Process", "abc123def456")
        assert composite_id == "myproject#Main.Process#abc123def456"

    def test_normalize_path(self):
        """Test path normalization."""
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            file_path = project_root / "some" / "nested" / "file.xaml"

            normalized = Workflow.normalize_path(file_path, project_root)
            assert normalized == "some/nested/file.xaml"
