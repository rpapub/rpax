"""Tests for multi-project CLI support."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from rpax.cli import app
from typer.testing import CliRunner


class TestMultiProjectCLI:
    """Test multi-project CLI functionality."""
    
    def test_projects_command_with_empty_lake(self, tmp_path):
        """Test projects command with empty lake."""
        runner = CliRunner()
        
        # Create empty projects.json
        projects_file = tmp_path / "projects.json"
        projects_file.write_text(json.dumps({"projects": []}))
        
        result = runner.invoke(app, ["projects", str(tmp_path)])
        
        assert result.exit_code == 0
        assert "No projects found in lake" in result.stdout
    
    def test_projects_command_with_sample_data(self, tmp_path):
        """Test projects command with sample project data."""
        runner = CliRunner()
        
        # Create projects.json with sample data
        projects_data = {
            "projects": [
                {
                    "name": "Test Project 1",
                    "slug": "test-project-1-abcd1234",
                    "type": "process",
                    "totalWorkflows": 5,
                    "lastUpdated": "2025-09-06T10:00:00Z"
                },
                {
                    "name": "Test Project 2", 
                    "slug": "test-project-2-efgh5678",
                    "type": "library",
                    "totalWorkflows": 3,
                    "lastUpdated": "2025-09-06T11:00:00Z"
                }
            ]
        }
        
        projects_file = tmp_path / "projects.json"
        projects_file.write_text(json.dumps(projects_data))
        
        result = runner.invoke(app, ["projects", str(tmp_path)])
        
        assert result.exit_code == 0
        assert "Test Project 1" in result.stdout
        assert "Test Project 2" in result.stdout
        assert "Total: 2 project(s)" in result.stdout
    
    def test_projects_command_json_output(self, tmp_path):
        """Test projects command with JSON output."""
        runner = CliRunner()
        
        # Create projects.json
        projects_data = {
            "projects": [
                {
                    "name": "Test Project",
                    "slug": "test-project-abcd1234",
                    "type": "process",
                    "totalWorkflows": 5
                }
            ]
        }
        
        projects_file = tmp_path / "projects.json"
        projects_file.write_text(json.dumps(projects_data))
        
        result = runner.invoke(app, ["projects", str(tmp_path), "--format", "json"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.stdout)
        assert "projects" in output_data
        assert "total" in output_data
        assert output_data["total"] == 1
        assert len(output_data["projects"]) == 1
    
    def test_projects_command_search_filter(self, tmp_path):
        """Test projects command with search filtering.""" 
        runner = CliRunner()
        
        projects_data = {
            "projects": [
                {
                    "name": "Calculator Project",
                    "slug": "calculator-abcd1234",
                    "type": "process"
                },
                {
                    "name": "Invoice Processing",
                    "slug": "invoice-efgh5678", 
                    "type": "process"
                }
            ]
        }
        
        projects_file = tmp_path / "projects.json"
        projects_file.write_text(json.dumps(projects_data))
        
        result = runner.invoke(app, ["projects", str(tmp_path), "--search", "calc", "--format", "json"])
        
        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert output_data["total"] == 1
        assert "Calculator" in output_data["projects"][0]["name"]
    
    def test_projects_command_missing_projects_file(self, tmp_path):
        """Test projects command with missing projects.json."""
        runner = CliRunner()
        
        result = runner.invoke(app, ["projects", str(tmp_path)])
        
        assert result.exit_code == 1
        assert "No projects.json found" in result.stdout
    
    @patch('rpax.cli._resolve_project_path')
    @patch('rpax.cli.ProjectParser.parse_project_from_dir')
    @patch('rpax.cli.XamlDiscovery')
    @patch('rpax.cli.ArtifactGenerator')
    def test_parse_command_multiple_projects(
        self, 
        mock_artifact_gen,
        mock_xaml_discovery, 
        mock_project_parser,
        mock_resolve_path,
        tmp_path
    ):
        """Test parse command with multiple --path options."""
        runner = CliRunner()
        
        # Setup mocks
        mock_resolve_path.side_effect = [Path("project1"), Path("project2")]
        
        mock_project1 = Mock()
        mock_project1.name = "Project 1"
        mock_project1.project_type = "process"
        
        mock_project2 = Mock()
        mock_project2.name = "Project 2"
        mock_project2.project_type = "library"
        
        mock_project_parser.side_effect = [mock_project1, mock_project2]
        
        mock_workflow_index1 = Mock()
        mock_workflow_index1.total_workflows = 5
        mock_workflow_index1.failed_parses = 0
        
        mock_workflow_index2 = Mock()
        mock_workflow_index2.total_workflows = 3
        mock_workflow_index2.failed_parses = 1
        
        mock_discovery_instance = Mock()
        mock_xaml_discovery.return_value = mock_discovery_instance
        mock_discovery_instance.discover_workflows.side_effect = [
            mock_workflow_index1, 
            mock_workflow_index2
        ]
        
        mock_generator_instance = Mock()
        mock_artifact_gen.return_value = mock_generator_instance
        mock_generator_instance.generate_all_artifacts.side_effect = [
            {"artifact1": Path("file1")},
            {"artifact2": Path("file2")}
        ]
        mock_generator_instance.output_dir = tmp_path / "output"
        
        with patch('rpax.cli.load_config') as mock_load_config:
            mock_config = Mock()
            mock_config.output.dir = str(tmp_path)
            mock_config.project.name = None
            mock_config.scan.exclude = []
            mock_load_config.return_value = mock_config
            
            result = runner.invoke(app, [
                "parse", 
                "--path", "project1",
                "--path", "project2",
                "--out", str(tmp_path)
            ])
        
        assert result.exit_code == 0
        assert "Projects processed: 2" in result.stdout
        assert "Total workflows: 8" in result.stdout  # 5 + 3
        assert "Project 1" in result.stdout
        assert "Project 2" in result.stdout