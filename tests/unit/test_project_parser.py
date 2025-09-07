"""Unit tests for UiPath project.json parsing."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from rpax.parser.project import ProjectParser


class TestProjectParser:
    """Test ProjectParser functionality."""

    def test_find_project_file_exists(self):
        """Test finding existing project.json file."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_file = temp_path / "project.json"
            project_file.touch()

            found = ProjectParser.find_project_file(temp_path)
            assert found == project_file

    def test_find_project_file_not_exists(self):
        """Test finding non-existent project.json file."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            found = ProjectParser.find_project_file(temp_path)
            assert found is None

    def test_parse_minimal_project(self):
        """Test parsing minimal valid project.json."""
        project_data = {
            "name": "TestProject",
            "main": "Main.xaml",
            "schemaVersion": "4.0",
            "targetFramework": "Windows"
        }

        with TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "project.json"
            with open(project_file, "w") as f:
                json.dump(project_data, f)

            project = ProjectParser.parse_project(project_file)
            assert project.name == "TestProject"
            assert project.main == "Main.xaml"
            assert project.uipath_schema_version == "4.0"
            assert project.target_framework == "Windows"

    def test_parse_complex_project(self):
        """Test parsing complex project with all fields."""
        project_data = {
            "name": "ComplexProject",
            "projectId": "12345-67890",
            "description": "Test project",
            "main": "StandardCalculator.xaml",
            "dependencies": {
                "UiPath.System.Activities": "[22.10.4]",
                "CustomLib": "1.0.0"
            },
            "schemaVersion": "4.0",
            "studioVersion": "22.10.5.0",
            "targetFramework": "Windows",
            "expressionLanguage": "VisualBasic",
            "entryPoints": [
                {
                    "filePath": "StandardCalculator.xaml",
                    "uniqueId": "abc-123",
                    "input": [
                        {
                            "name": "Term1",
                            "type": "System.String",
                            "required": False,
                            "hasDefault": False
                        }
                    ],
                    "output": [
                        {
                            "name": "Result",
                            "type": "System.String"
                        }
                    ]
                }
            ],
            "designOptions": {
                "outputType": "Process",
                "projectProfile": "Development"
            }
        }

        with TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "project.json"
            with open(project_file, "w") as f:
                json.dump(project_data, f)

            project = ProjectParser.parse_project(project_file)
            assert project.name == "ComplexProject"
            assert project.project_id == "12345-67890"
            assert project.description == "Test project"
            assert len(project.dependencies) == 2
            assert len(project.entry_points) == 1

            entry_point = project.entry_points[0]
            assert entry_point.file_path == "StandardCalculator.xaml"
            assert len(entry_point.input) == 1
            assert len(entry_point.output) == 1
            assert entry_point.input[0].name == "Term1"
            assert entry_point.output[0].name == "Result"

            assert project.project_type == "process"
            assert project.is_process is True
            assert project.is_library is False

    def test_parse_library_project(self):
        """Test parsing library project type detection."""
        project_data = {
            "name": "LibraryProject",
            "main": "Main.xaml",
            "schemaVersion": "4.0",
            "designOptions": {
                "outputType": "Library"
            }
        }

        with TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "project.json"
            with open(project_file, "w") as f:
                json.dump(project_data, f)

            project = ProjectParser.parse_project(project_file)
            assert project.project_type == "library"
            assert project.is_library is True
            assert project.is_process is False

    def test_parse_project_file_not_found(self):
        """Test parsing non-existent file."""
        with TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "nonexistent.json"

            with pytest.raises(FileNotFoundError):
                ProjectParser.parse_project(project_file)

    def test_parse_project_invalid_json(self):
        """Test parsing invalid JSON."""
        with TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "project.json"
            with open(project_file, "w") as f:
                f.write("{invalid json")

            with pytest.raises(ValueError, match="Invalid JSON"):
                ProjectParser.parse_project(project_file)

    def test_parse_project_missing_required_fields(self):
        """Test parsing project with missing required fields."""
        project_data = {
            "description": "Missing required fields"
        }

        with TemporaryDirectory() as temp_dir:
            project_file = Path(temp_dir) / "project.json"
            with open(project_file, "w") as f:
                json.dump(project_data, f)

            with pytest.raises(ValueError, match="Invalid project structure"):
                ProjectParser.parse_project(project_file)

    def test_parse_project_from_dir(self):
        """Test parsing project from directory."""
        project_data = {
            "name": "DirProject",
            "main": "Main.xaml",
            "schemaVersion": "4.0"
        }

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_file = temp_path / "project.json"
            with open(project_file, "w") as f:
                json.dump(project_data, f)

            project = ProjectParser.parse_project_from_dir(temp_path)
            assert project.name == "DirProject"

    def test_parse_project_from_dir_no_project_file(self):
        """Test parsing from directory with no project.json."""
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with pytest.raises(FileNotFoundError, match="No project.json found"):
                ProjectParser.parse_project_from_dir(temp_path)
