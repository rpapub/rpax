"""Unit tests for activities CLI commands."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from typer.testing import CliRunner

from rpax.cli import app


class TestActivitiesCLI:
    """Test activities CLI command functionality."""

    def setup_test_artifacts(self, temp_path: Path) -> None:
        """Set up test artifacts directory structure."""
        # Create manifest.json
        manifest_file = temp_path / "manifest.json"
        manifest_file.write_text('{"projectName": "TestProject"}')

        # Create activities directories
        activities_tree_dir = temp_path / "activities.tree"
        activities_cfg_dir = temp_path / "activities.cfg"
        activities_refs_dir = temp_path / "activities.refs"
        metrics_dir = temp_path / "metrics"

        activities_tree_dir.mkdir()
        activities_cfg_dir.mkdir()
        activities_refs_dir.mkdir()
        metrics_dir.mkdir()

        # Create sample activity tree
        tree_data = {
            "workflowId": "TestWorkflow.xaml",
            "contentHash": "abc123",
            "extractedAt": "2025-09-05T12:00:00",
            "extractorVersion": "0.1.0",
            "variables": [{"name": "var1", "type": "String"}],
            "arguments": [{"name": "arg1", "direction": "In"}],
            "imports": ["System"],
            "rootNode": {
                "nodeId": "root",
                "activityType": "Sequence",
                "displayName": "Main Sequence",
                "properties": {"DisplayName": "Main Sequence"},
                "arguments": {},
                "children": [
                    {
                        "nodeId": "root.0",
                        "activityType": "WriteLine",
                        "displayName": "Log Message",
                        "properties": {"Text": "Hello World"},
                        "arguments": {"Text": "Hello World"},
                        "children": []
                    }
                ]
            }
        }

        with open(activities_tree_dir / "TestWorkflow.json", "w") as f:
            json.dump(tree_data, f)

        # Create sample control flow
        with open(activities_cfg_dir / "TestWorkflow.jsonl", "w") as f:
            f.write('{"from": "root", "to": "root.0", "type": "contains", "condition": null}\n')

        # Create sample resources
        refs_data = {
            "workflowId": "TestWorkflow",
            "references": [
                {
                    "type": "file",
                    "name": "ConfigFile",
                    "value": "config.json",
                    "nodeId": "root.0",
                    "property": "FileName",
                    "isDynamic": False
                }
            ]
        }

        with open(activities_refs_dir / "TestWorkflow.json", "w") as f:
            json.dump(refs_data, f)

        # Create sample metrics
        metrics_data = {
            "workflowId": "TestWorkflow",
            "totalNodes": 2,
            "maxDepth": 2,
            "loopCount": 0,
            "invokeCount": 0,
            "logCount": 1,
            "tryCatchCount": 0,
            "selectorCount": 0,
            "activityTypes": {"Sequence": 1, "WriteLine": 1}
        }

        with open(metrics_dir / "TestWorkflow.json", "w") as f:
            json.dump(metrics_data, f)

    def test_activities_tree_command_json(self):
        """Test activities tree command with JSON output."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_artifacts(temp_path)

            result = runner.invoke(app, [
                "activities", "tree", "TestWorkflow",
                "--path", str(temp_path), "--format", "json"
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data["workflowId"] == "TestWorkflow.xaml"
            assert output_data["rootNode"]["activityType"] == "Sequence"
            assert len(output_data["rootNode"]["children"]) == 1

    def test_activities_tree_command_table(self):
        """Test activities tree command with table output."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_artifacts(temp_path)

            result = runner.invoke(app, [
                "activities", "tree", "TestWorkflow",
                "--path", str(temp_path), "--format", "table"
            ])

            assert result.exit_code == 0
            assert "Activity Tree: TestWorkflow.xaml" in result.stdout
            assert "Main Sequence" in result.stdout
            assert "Log Message" in result.stdout

    def test_activities_flow_command(self):
        """Test activities flow command."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_artifacts(temp_path)

            result = runner.invoke(app, [
                "activities", "flow", "TestWorkflow",
                "--path", str(temp_path), "--format", "json"
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data["workflow"] == "TestWorkflow"
            assert len(output_data["edges"]) == 1
            assert output_data["edges"][0]["type"] == "contains"

    def test_activities_resources_command(self):
        """Test activities resources command."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_artifacts(temp_path)

            result = runner.invoke(app, [
                "activities", "refs", "TestWorkflow",
                "--path", str(temp_path), "--format", "json"
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data["workflowId"] == "TestWorkflow"
            assert len(output_data["references"]) == 1
            assert output_data["references"][0]["type"] == "file"
            assert output_data["references"][0]["value"] == "config.json"

    def test_activities_metrics_single_workflow(self):
        """Test activities metrics command for single workflow."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_artifacts(temp_path)

            result = runner.invoke(app, [
                "activities", "metrics", "TestWorkflow",
                "--path", str(temp_path), "--format", "json"
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert output_data["workflowId"] == "TestWorkflow"
            assert output_data["totalNodes"] == 2
            assert output_data["maxDepth"] == 2
            assert output_data["logCount"] == 1

    def test_activities_metrics_all_workflows(self):
        """Test activities metrics command for all workflows."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_artifacts(temp_path)

            result = runner.invoke(app, [
                "activities", "metrics",
                "--path", str(temp_path), "--format", "json"
            ])

            assert result.exit_code == 0
            output_data = json.loads(result.stdout)
            assert "metrics" in output_data
            assert output_data["total"] == 1
            assert output_data["metrics"][0]["workflowId"] == "TestWorkflow"

    def test_activities_command_validation_errors(self):
        """Test activities command validation and error handling."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test without manifest.json
            result = runner.invoke(app, [
                "activities", "tree", "TestWorkflow", "--path", str(temp_path)
            ])
            assert result.exit_code == 1
            assert "No manifest.json or projects.json found" in result.stdout

            # Create manifest but test invalid action
            manifest_file = temp_path / "manifest.json"
            manifest_file.write_text("{}")

            result = runner.invoke(app, [
                "activities", "invalid", "--path", str(temp_path)
            ])
            assert result.exit_code == 1
            assert "Invalid action 'invalid'" in result.stdout

            # Test missing workflow for tree action
            result = runner.invoke(app, [
                "activities", "tree", "--path", str(temp_path)
            ])
            assert result.exit_code == 1
            assert "Workflow name required" in result.stdout

    def test_activities_missing_files(self):
        """Test activities commands with missing artifact files."""
        runner = CliRunner()

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Only create manifest.json, no other artifacts
            manifest_file = temp_path / "manifest.json"
            manifest_file.write_text("{}")

            # Test tree with missing file
            result = runner.invoke(app, [
                "activities", "tree", "Missing", "--path", str(temp_path)
            ])
            assert result.exit_code == 1
            assert "Activity tree not found for Missing" in result.stdout

            # Test flow with missing file
            result = runner.invoke(app, [
                "activities", "flow", "Missing", "--path", str(temp_path)
            ])
            assert result.exit_code == 1
            assert "Control flow not found for Missing" in result.stdout

            # Test refs with missing file
            result = runner.invoke(app, [
                "activities", "refs", "Missing", "--path", str(temp_path)
            ])
            assert result.exit_code == 1
            assert "References not found for Missing" in result.stdout
