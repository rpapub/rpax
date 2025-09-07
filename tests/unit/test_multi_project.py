"""Unit tests for multi-project lake functionality."""

import json
import tempfile
from pathlib import Path

from rpax.artifacts import ArtifactGenerator
from rpax.config import ProjectConfig, ProjectType, RpaxConfig
from rpax.models.project import UiPathProject


class TestMultiProjectLake:
    """Test multi-project lake functionality."""

    def test_project_slug_generation_with_id(self):
        """Test project slug generation when projectId exists."""
        project = UiPathProject(
            name="FrozenChlorine",
            project_id="f4aa3834-01a5-4557-a74a-d6d97b0cfbdf",
            main="StandardCalculator.xaml",
            uipath_schema_version="4.0",
        )

        # Create temporary project.json for content hashing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "FrozenChlorine",
                "projectId": "f4aa3834-01a5-4557-a74a-d6d97b0cfbdf",
                "main": "StandardCalculator.xaml",
                "schemaVersion": "4.0"
            }, f)
            project_json_path = Path(f.name)

        slug = project.generate_project_slug(project_json_path)
        
        # New implementation always uses name + hash format
        assert slug.startswith("frozenchlorine-")
        assert len(slug) > len("frozenchlorine-")  # Should have hash suffix
        
        # Cleanup
        project_json_path.unlink()

    def test_project_slug_generation_without_id(self):
        """Test project slug generation when projectId is missing."""
        project = UiPathProject(
            name="CPRIMA-USG-001-Violating",
            project_id=None,
            main="Main.xaml",
            uipath_schema_version="4.0",
        )

        # Create temporary project.json for content hashing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "CPRIMA-USG-001-Violating",
                "main": "Main.xaml",
                "projectType": "Process",
                "schemaVersion": "4.0"
            }, f)
            project_json_path = Path(f.name)

        slug = project.generate_project_slug(project_json_path)

        # Should be normalized name + hash
        assert slug.startswith("cprima-usg-001-viola")  # Note: truncated at 20 chars
        assert len(slug) > 20  # name + hash
        assert "-" in slug  # separator between name and hash

        # Cleanup
        project_json_path.unlink()

    def test_project_slug_normalization(self):
        """Test project name normalization for slug generation."""
        project = UiPathProject(
            name="My-Special/Project Name (v2)!",
            project_id=None,
            main="Main.xaml",
            uipath_schema_version="4.0",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"name": "My-Special/Project Name (v2)!"}, f)
            project_json_path = Path(f.name)

        slug = project.generate_project_slug(project_json_path)

        # Should normalize special characters
        assert slug.startswith("my-special-project-n")  # Note: truncated at 20 chars
        assert "/" not in slug
        assert "(" not in slug
        assert ")" not in slug
        assert "!" not in slug

        # Cleanup
        project_json_path.unlink()

    def test_artifact_generator_creates_project_subdirectory(self):
        """Test that ArtifactGenerator creates project-specific subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create config
            config = RpaxConfig(
                project=ProjectConfig(type=ProjectType.PROCESS),
            )

            # Create generator
            generator = ArtifactGenerator(config, temp_path)

            # Create mock project
            project = UiPathProject(
                name="TestProject",
                project_id="test-1234-5678-90ab",
                main="Main.xaml",
                uipath_schema_version="4.0",
                )

            # Create mock workflow index
            from rpax.models.workflow import WorkflowIndex
            workflow_index = WorkflowIndex(
                project_name="TestProject",
                project_root=str(temp_path),
                scan_timestamp="2025-09-05T12:00:00",
                total_workflows=1,
                successful_parses=1,
                failed_parses=0,
                workflows=[]
            )

            # Generate artifacts
            artifacts = generator.generate_all_artifacts(project, workflow_index, temp_path)

            # Check project subdirectory was created
            project_slug = project.generate_project_slug()
            project_dir = temp_path / project_slug
            assert project_dir.exists()
            assert project_dir.is_dir()

            # Check projects.json index was created
            projects_index = temp_path / "projects.json"
            assert projects_index.exists()

            with open(projects_index) as f:
                index_data = json.load(f)

            assert "rpaxSchemaVersion" in index_data
            assert "projects" in index_data
            assert len(index_data["projects"]) == 1

            project_entry = index_data["projects"][0]
            assert project_entry["slug"] == project_slug
            assert project_entry["name"] == "TestProject"
            assert project_entry["projectId"] == "test-1234-5678-90ab"
            assert project_entry["projectType"] == "process"

    def test_projects_index_updates_existing_project(self):
        """Test that projects.json index updates existing project entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create existing projects.json
            projects_file = temp_path / "projects.json"
            existing_data = {
                "schemaVersion": "1.0",
                "projects": [{
                    "slug": "existing-12345678",
                    "name": "ExistingProject",
                    "projectId": "existing-1234-5678-90ab",
                    "lastParsed": "2025-09-04T12:00:00Z"
                }]
            }

            with open(projects_file, "w") as f:
                json.dump(existing_data, f)

            # Create config and generator
            config = RpaxConfig(project=ProjectConfig(type=ProjectType.PROCESS))
            generator = ArtifactGenerator(config, temp_path)

            # Add new project
            project = UiPathProject(
                name="NewProject",
                project_id="new-proj-1234-5678",
                main="Main.xaml",
                uipath_schema_version="4.0",
                )

            from rpax.models.workflow import WorkflowIndex
            workflow_index = WorkflowIndex(
                project_name="NewProject",
                project_root=str(temp_path),
                scan_timestamp="2025-09-05T12:00:00",
                total_workflows=0,
                successful_parses=0,
                failed_parses=0,
                workflows=[]
            )

            # Generate artifacts
            generator.generate_all_artifacts(project, workflow_index, temp_path)

            # Check projects.json was updated
            with open(projects_file) as f:
                updated_data = json.load(f)

            assert len(updated_data["projects"]) == 2

            # Should be sorted by slug
            slugs = [p["slug"] for p in updated_data["projects"]]
            assert slugs == sorted(slugs)

            # Check both projects exist
            project_names = {p["name"] for p in updated_data["projects"]}
            assert "ExistingProject" in project_names
            assert "NewProject" in project_names
