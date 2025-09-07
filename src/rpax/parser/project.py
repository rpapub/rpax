"""UiPath project.json parser implementation."""

import json
from pathlib import Path

from rpax.models.project import UiPathProject


class ProjectParser:
    """Parser for UiPath project.json files."""

    @staticmethod
    def find_project_file(project_root: Path) -> Path | None:
        """Find project.json file in the given directory.
        
        Args:
            project_root: Directory to search for project.json
            
        Returns:
            Path to project.json if found, None otherwise
        """
        project_file = project_root / "project.json"
        if project_file.exists() and project_file.is_file():
            return project_file
        return None

    @staticmethod
    def parse_project(project_file: Path) -> UiPathProject:
        """Parse UiPath project.json file into structured model.
        
        Args:
            project_file: Path to project.json file
            
        Returns:
            UiPathProject: Parsed and validated project model
            
        Raises:
            FileNotFoundError: If project file doesn't exist
            ValueError: If project file is invalid JSON or missing required fields
        """
        if not project_file.exists():
            raise FileNotFoundError(f"Project file not found: {project_file}")

        try:
            with open(project_file, encoding="utf-8") as f:
                project_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in project file {project_file}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to read project file {project_file}: {e}")

        try:
            return UiPathProject(**project_data)
        except Exception as e:
            raise ValueError(f"Invalid project structure in {project_file}: {e}")

    @classmethod
    def parse_project_from_dir(cls, project_dir: Path) -> UiPathProject:
        """Parse project from directory by finding and parsing project.json.
        
        Args:
            project_dir: Directory containing UiPath project
            
        Returns:
            UiPathProject: Parsed project model
            
        Raises:
            FileNotFoundError: If no project.json found in directory
            ValueError: If project.json is invalid
        """
        project_file = cls.find_project_file(project_dir)
        if project_file is None:
            raise FileNotFoundError(f"No project.json found in {project_dir}")

        return cls.parse_project(project_file)
