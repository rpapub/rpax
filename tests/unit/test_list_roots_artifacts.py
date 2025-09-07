"""Unit tests for rpax list roots command with artifacts directory."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from rpax.cli import app


class TestListRootsArtifacts:
    """Test list roots command with artifacts directory support."""

    def test_list_roots_from_artifacts_directory(self):
        """Test list roots command reading from artifacts directory."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a manifest.json file with entry points
            manifest_data = {
                "projectName": "TestProject",
                "entryPoints": [
                    {
                        "filePath": "Main.xaml",
                        "uniqueId": "abc-123",
                        "input": [
                            {"name": "inputArg", "type": "String"}
                        ],
                        "output": [
                            {"name": "outputArg", "type": "String"}
                        ]
                    }
                ]
            }

            manifest_file = temp_path / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest_data, f)

            # Also create workflows.index.json to make it a valid artifacts directory
            workflows_file = temp_path / "workflows.index.json"
            workflows_file.write_text('{"workflows": []}')

            result = runner.invoke(app, ["list", "roots", "--path", str(temp_path)])

            assert result.exit_code == 0
            assert "Entry Points (1 found)" in result.stdout
            assert "Main.xaml" in result.stdout
            assert "1" in result.stdout  # input count
            assert "1" in result.stdout  # output count

    def test_list_roots_from_artifacts_json_format(self):
        """Test list roots command with JSON output from artifacts."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create manifest.json
            manifest_data = {
                "projectName": "TestProject",
                "entryPoints": [
                    {
                        "filePath": "Workflow1.xaml",
                        "uniqueId": "unique-1",
                        "input": [],
                        "output": [{"name": "result", "type": "String"}]
                    }
                ]
            }

            manifest_file = temp_path / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest_data, f)

            # Also create workflows.index.json to make it a valid artifacts directory
            workflows_file = temp_path / "workflows.index.json"
            workflows_file.write_text('{"workflows": []}')

            result = runner.invoke(app, ["list", "roots", "--path", str(temp_path), "--format", "json"])

            assert result.exit_code == 0

            # Parse JSON output
            output_data = json.loads(result.stdout)
            assert "entry_points" in output_data
            assert output_data["total"] == 1
            assert output_data["entry_points"][0]["workflow"] == "Workflow1.xaml"
            assert output_data["entry_points"][0]["inputs"] == 0
            assert output_data["entry_points"][0]["outputs"] == 1

    def test_list_roots_from_artifacts_with_search(self):
        """Test list roots command with search filter from artifacts."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create manifest.json with multiple entry points
            manifest_data = {
                "projectName": "TestProject",
                "entryPoints": [
                    {
                        "filePath": "MainWorkflow.xaml",
                        "uniqueId": "main-id",
                        "input": [],
                        "output": []
                    },
                    {
                        "filePath": "TestWorkflow.xaml",
                        "uniqueId": "test-id",
                        "input": [],
                        "output": []
                    }
                ]
            }

            manifest_file = temp_path / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest_data, f)

            # Also create workflows.index.json to make it a valid artifacts directory
            workflows_file = temp_path / "workflows.index.json"
            workflows_file.write_text('{"workflows": []}')

            result = runner.invoke(app, ["list", "roots", "--path", str(temp_path), "--search", "main"])

            assert result.exit_code == 0
            assert "Entry Points (1 found)" in result.stdout
            assert "MainWorkflow.xaml" in result.stdout
            assert "TestWorkflow.xaml" not in result.stdout

    def test_list_roots_empty_entry_points(self):
        """Test list roots command with no entry points in artifacts."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create manifest.json with no entry points
            manifest_data = {
                "projectName": "TestProject",
                "entryPoints": []
            }

            manifest_file = temp_path / "manifest.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest_data, f)

            # Also create workflows.index.json to make it a valid artifacts directory
            workflows_file = temp_path / "workflows.index.json"
            workflows_file.write_text('{"workflows": []}')

            result = runner.invoke(app, ["list", "roots", "--path", str(temp_path)])

            assert result.exit_code == 0
            assert "No entry points defined" in result.stdout
