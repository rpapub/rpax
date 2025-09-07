"""Unit tests for CLI project path resolution."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from typer.testing import CliRunner

from rpax.cli import _resolve_project_path, app


class TestProjectPathResolution:
    """Test CLI project path smart detection functionality."""

    def test_resolve_project_json_file_path(self):
        """Test resolving project.json file path to parent directory."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_file = temp_path / "project.json"
            project_file.write_text('{"name": "TestProject", "main": "Main.xaml", "schemaVersion": "4.0"}')

            result = _resolve_project_path(project_file)

            assert result == temp_path
            assert result.is_dir()

    def test_resolve_directory_path(self):
        """Test resolving directory path containing project.json."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_file = temp_path / "project.json"
            project_file.write_text('{"name": "TestProject", "main": "Main.xaml", "schemaVersion": "4.0"}')

            result = _resolve_project_path(temp_path)

            assert result == temp_path
            assert result.is_dir()

    def test_resolve_nonexistent_project_json_file(self):
        """Test error handling for non-existent project.json file."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nonexistent_file = temp_path / "project.json"

            with pytest.raises(FileNotFoundError, match="Project file not found"):
                _resolve_project_path(nonexistent_file)

    def test_resolve_directory_without_project_json(self):
        """Test error handling for directory without project.json."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with pytest.raises(FileNotFoundError, match="No project.json found in directory"):
                _resolve_project_path(temp_path)

    def test_case_insensitive_project_json_detection(self):
        """Test case-insensitive detection of project.json filename."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Test uppercase filename
            project_file = temp_path / "PROJECT.JSON"
            project_file.write_text('{"name": "TestProject", "main": "Main.xaml", "schemaVersion": "4.0"}')

            result = _resolve_project_path(project_file)

            assert result == temp_path
            assert result.is_dir()


class TestCliParseCommand:
    """Test CLI parse command with different path types."""

    def test_parse_with_project_json_file(self):
        """Test parse command with project.json file path."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_file = temp_path / "project.json"
            project_file.write_text("""{
                "name": "TestProject",
                "main": "Main.xaml",
                "schemaVersion": "4.0",
                "targetFramework": "Windows"
            }""")

            # Create Main.xaml for discovery
            main_file = temp_path / "Main.xaml"
            main_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sads"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
    <Sequence DisplayName="Main Sequence">
        <WriteLine Text="Hello World" />
    </Sequence>
</Activity>""")

            result = runner.invoke(app, [
                "parse", str(project_file),
                "--out", str(temp_path / ".test-output")
            ])

            assert result.exit_code == 0
            assert "Detected project.json file" in result.stdout
            assert "TestProject" in result.stdout

    def test_parse_with_directory_path(self):
        """Test parse command with directory path (backward compatibility)."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_file = temp_path / "project.json"
            project_file.write_text("""{
                "name": "TestProject",
                "main": "Main.xaml",
                "schemaVersion": "4.0",
                "targetFramework": "Windows"
            }""")

            # Create Main.xaml for discovery
            main_file = temp_path / "Main.xaml"
            main_file.write_text("""<?xml version="1.0" encoding="utf-8"?>
<Activity mc:Ignorable="sap sap2010 sads"
    xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
    <Sequence DisplayName="Main Sequence">
        <WriteLine Text="Hello World" />
    </Sequence>
</Activity>""")

            result = runner.invoke(app, [
                "parse", str(temp_path),
                "--out", str(temp_path / ".test-output")
            ])

            assert result.exit_code == 0
            assert "Found project.json" in result.stdout
            assert "TestProject" in result.stdout
