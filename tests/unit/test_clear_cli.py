"""Unit tests for clear CLI command."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from rpax.cli import app


class TestClearCLI:
    """Test clear command functionality with safety guardrails."""

    def setup_test_lake(self, temp_path: Path) -> None:
        """Set up test lake structure with sample data."""
        # Create projects.json
        projects_file = temp_path / "projects.json"
        projects_file.write_text('{"projects": []}')

        # Create project directory with artifacts
        project_dir = temp_path / "test-proj-1234"
        project_dir.mkdir()

        # Create artifacts
        (project_dir / "manifest.json").write_text('{"projectName": "TestProject"}')
        (project_dir / "workflows.index.json").write_text('{"workflows": []}')
        (project_dir / "invocations.jsonl").write_text('{"invoker": "Main.xaml"}\n')

        # Create activities directory
        activities_dir = project_dir / "activities.tree"
        activities_dir.mkdir()
        (activities_dir / "Main.json").write_text('{"workflowId": "Main"}')

    def test_clear_dry_run_default(self):
        """Test that clear command runs in dry-run mode by default."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_lake(temp_path)

            result = runner.invoke(app, [
                "clear", "artifacts", "--path", str(temp_path)
            ])

            assert result.exit_code == 0
            assert "DRY RUN MODE" in result.stdout
            assert "No files will be deleted" in result.stdout

            # Verify files still exist
            assert (temp_path / "test-proj-1234" / "manifest.json").exists()

    def test_clear_invalid_scope(self):
        """Test validation of invalid scope parameter."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = runner.invoke(app, [
                "clear", "invalid", "--path", str(temp_path)
            ])

            assert result.exit_code == 1
            assert "Invalid scope 'invalid'" in result.stdout
            assert "artifacts, project, lake" in result.stdout

    def test_clear_nonexistent_lake(self):
        """Test validation of non-existent lake directory."""
        runner = CliRunner()

        result = runner.invoke(app, [
            "clear", "artifacts", "--path", "/nonexistent/path"
        ])

        assert result.exit_code == 1
        assert "Lake directory does not exist" in result.stdout

    def test_clear_project_scope_requires_project_param(self):
        """Test that project scope requires --project parameter."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = runner.invoke(app, [
                "clear", "project", "--path", str(temp_path)
            ])

            assert result.exit_code == 1
            assert "--project is required when scope is 'project'" in result.stdout

    def test_clear_project_scope_validates_project_exists(self):
        """Test that project scope validates project exists."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            result = runner.invoke(app, [
                "clear", "project", "--path", str(temp_path), "--project", "nonexistent"
            ])

            assert result.exit_code == 1
            assert "Project 'nonexistent' not found in lake" in result.stdout

    def test_clear_artifacts_scope_shows_summary(self):
        """Test that artifacts scope shows proper summary."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.setup_test_lake(temp_path)

            result = runner.invoke(app, [
                "clear", "artifacts", "--path", str(temp_path)
            ])

            assert result.exit_code == 0
            assert "Clear Operation Summary" in result.stdout
            assert "Scope: artifacts" in result.stdout
            assert "Items to delete:" in result.stdout
            assert "Total size:" in result.stdout

    def test_clear_empty_scope_shows_nothing_message(self):
        """Test that empty scope shows nothing to delete message."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create empty lake (just projects.json)
            (temp_path / "projects.json").write_text('{"projects": []}')

            result = runner.invoke(app, [
                "clear", "artifacts", "--path", str(temp_path)
            ])

            assert result.exit_code == 0
            assert "Nothing to delete in scope 'artifacts'" in result.stdout

    def test_clear_help_shows_safety_information(self):
        """Test that help shows comprehensive safety information."""
        runner = CliRunner()

        result = runner.invoke(app, ["clear", "--help"])

        assert result.exit_code == 0
        assert "SCOPES:" in result.stdout
        assert "artifacts - Clear generated artifacts" in result.stdout
        assert "project   - Clear all data for specific project" in result.stdout
        assert "lake      - Clear entire lake directory" in result.stdout
        assert "SAFETY FEATURES:" in result.stdout
        assert "Dry-run by default" in result.stdout
        assert "CLI-only and never exposed via API or MCP" in result.stdout
