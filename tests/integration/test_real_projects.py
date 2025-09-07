"""Integration tests using real UiPath test projects."""

from pathlib import Path

import pytest

from rpax.parser.project import ProjectParser
from rpax.parser.xaml import XamlDiscovery


class TestRealUiPathProjects:
    """Integration tests with actual UiPath projects."""

    # Test project paths as defined in CLAUDE.md
    FROZEN_CHLORINE = Path("D:/github.com/rpapub/FrozenChlorine")
    VIOLATION_PROJECT = Path("D:/github.com/rpapub/PropulsiveForce/CPRIMA-USG-001_ShouldStopPresence/Violation")
    COMPLIANT_PROJECT = Path("D:/github.com/rpapub/PropulsiveForce/CPRIMA-USG-001_ShouldStopPresence/NoViolation")

    @pytest.fixture(autouse=True)
    def check_test_projects_available(self):
        """Skip integration tests if test projects are not available."""
        test_projects = [self.FROZEN_CHLORINE, self.VIOLATION_PROJECT, self.COMPLIANT_PROJECT]

        for project_path in test_projects:
            if not project_path.exists():
                pytest.skip(f"Test project not available: {project_path}")

            project_json = project_path / "project.json"
            if not project_json.exists():
                pytest.skip(f"Project.json not found: {project_json}")

    @pytest.mark.integration
    def test_frozen_chlorine_parsing(self):
        """Test parsing of complex FrozenChlorine project."""
        project = ProjectParser.parse_project_from_dir(self.FROZEN_CHLORINE)

        # Verify project metadata
        assert project.name == "FrozenChlorine"
        assert project.project_id == "f4aa3834-01a5-4557-a74a-d6d97b0cfbdf"
        assert project.description == "RPA UiPath process automating the Windows Calculator App"
        assert project.main == "StandardCalculator.xaml"
        assert project.is_process is True

        # Verify dependencies
        assert "LuckyLawrencium" in project.dependencies
        assert "UiPath.System.Activities.Runtime" in project.dependencies

        # Verify entry points
        assert len(project.entry_points) == 2
        entry_point_paths = [ep.file_path for ep in project.entry_points]
        assert "StandardCalculator.xaml" in entry_point_paths
        assert "PathKeeper.xaml" in entry_point_paths

        # Test workflow discovery
        discovery = XamlDiscovery(self.FROZEN_CHLORINE, exclude_patterns=[
            ".local/**", ".settings/**", ".screenshots/**", "TestResults/**"
        ])
        workflow_index = discovery.discover_workflows()

        # Should find multiple workflows
        assert workflow_index.total_workflows > 5  # Has many workflows including tests
        assert workflow_index.successful_parses > 0
        assert workflow_index.success_rate > 0.8  # Most should parse successfully

        # Should find main workflows
        workflow_paths = [w.relative_path for w in workflow_index.workflows]
        assert "StandardCalculator.xaml" in workflow_paths
        assert "PathKeeper.xaml" in workflow_paths

        # Should properly exclude test directories
        excluded_workflows = [path for path in workflow_paths if any(
            excl in path for excl in [".local", ".settings", ".screenshots"]
        )]
        assert len(excluded_workflows) == 0  # These should be excluded

    @pytest.mark.integration
    def test_violation_project_parsing(self):
        """Test parsing of CPRIMA violation project."""
        project = ProjectParser.parse_project_from_dir(self.VIOLATION_PROJECT)

        # Verify project metadata
        assert project.name == "CPRIMA-USG-001-Violating"
        assert "violating rule cprima-usg-001" in project.description.lower()
        assert project.main == "Main.xaml"
        assert project.is_process is True

        # Verify minimal dependencies
        assert "UiPath.System.Activities" in project.dependencies
        assert "UiPath.Testing.Activities" in project.dependencies

        # Test workflow discovery
        discovery = XamlDiscovery(self.VIOLATION_PROJECT)
        workflow_index = discovery.discover_workflows()

        # Should be a simple project
        assert workflow_index.total_workflows >= 1  # At least Main.xaml
        assert workflow_index.successful_parses >= 1

        # Should find Main.xaml
        workflow_paths = [w.relative_path for w in workflow_index.workflows]
        assert "Main.xaml" in workflow_paths

    @pytest.mark.integration
    def test_compliant_project_parsing(self):
        """Test parsing of CPRIMA compliant project."""
        project = ProjectParser.parse_project_from_dir(self.COMPLIANT_PROJECT)

        # Verify project metadata
        assert project.name == "CPRIMA-USG-001-Compliant"
        assert "complies with the custom Workflow Analyzer rule" in project.description
        assert project.main == "Main.xaml"
        assert project.is_process is True

        # Same dependencies as violation project
        assert "UiPath.System.Activities" in project.dependencies
        assert "UiPath.Testing.Activities" in project.dependencies

        # Test workflow discovery
        discovery = XamlDiscovery(self.COMPLIANT_PROJECT)
        workflow_index = discovery.discover_workflows()

        # Should be similar structure to violation project
        assert workflow_index.total_workflows >= 1
        assert workflow_index.successful_parses >= 1

        workflow_paths = [w.relative_path for w in workflow_index.workflows]
        assert "Main.xaml" in workflow_paths

    @pytest.mark.integration
    def test_all_projects_parse_without_crashes(self):
        """Test that all test projects can be parsed without crashes (MVP acceptance criteria)."""
        projects = [
            (self.FROZEN_CHLORINE, "FrozenChlorine"),
            (self.VIOLATION_PROJECT, "CPRIMA-USG-001-Violating"),
            (self.COMPLIANT_PROJECT, "CPRIMA-USG-001-Compliant")
        ]

        parsed_projects = []
        workflow_indices = []

        for project_path, expected_name in projects:
            # Test project.json parsing
            project = ProjectParser.parse_project_from_dir(project_path)
            assert project.name == expected_name
            parsed_projects.append(project)

            # Test XAML discovery
            discovery = XamlDiscovery(project_path, exclude_patterns=[
                ".local/**", ".settings/**", ".screenshots/**", "TestResults/**"
            ])
            workflow_index = discovery.discover_workflows()
            assert workflow_index.total_workflows > 0
            workflow_indices.append(workflow_index)

        # All projects should be parsed successfully
        assert len(parsed_projects) == 3
        assert len(workflow_indices) == 3

        # All should have reasonable success rates
        for index in workflow_indices:
            assert index.success_rate >= 0.5  # At least 50% workflows parse successfully

    @pytest.mark.integration
    def test_workflow_identity_consistency(self):
        """Test workflow identity system consistency across projects."""
        discovery = XamlDiscovery(self.FROZEN_CHLORINE, exclude_patterns=[
            ".local/**", ".settings/**", ".screenshots/**"
        ])
        workflow_index = discovery.discover_workflows()

        # Check identity format consistency
        for workflow in workflow_index.workflows:
            # Should have composite ID format
            assert "#" in workflow.id
            id_parts = workflow.id.split("#")
            assert len(id_parts) == 3  # project_slug#workflow_id#content_hash

            project_slug, workflow_id, content_hash_short = id_parts
            assert project_slug == workflow.project_slug
            assert workflow_id == workflow.workflow_id
            assert content_hash_short == workflow.content_hash[:16]  # Short hash in composite ID
            assert len(content_hash_short) == 16  # First 16 chars of SHA-256
            assert len(workflow.content_hash) == 64  # Full SHA-256 stored

            # POSIX path normalization
            assert "\\" not in workflow.relative_path

            # ADR-014: wfId is the canonical path ID (POSIX relative path)
            assert workflow.workflow_id == workflow.relative_path

            # Should have original path for provenance
            assert workflow.original_path is not None

    @pytest.mark.integration
    def test_error_handling_with_real_projects(self):
        """Test graceful error handling with real project edge cases."""
        # Test with FrozenChlorine which has complex structure
        discovery = XamlDiscovery(self.FROZEN_CHLORINE)
        workflow_index = discovery.discover_workflows()

        # Should handle any parsing issues gracefully
        total_workflows = workflow_index.total_workflows
        successful = workflow_index.successful_parses
        failed = workflow_index.failed_parses

        assert total_workflows == successful + failed

        # If there are any failures, they should be recorded properly
        if failed > 0:
            failed_workflows = [w for w in workflow_index.workflows if not w.parse_successful]
            assert len(failed_workflows) == failed

            for failed_workflow in failed_workflows:
                assert len(failed_workflow.parse_errors) > 0
                assert failed_workflow.content_hash is not None  # Should still generate hash

    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_project_performance(self):
        """Test performance with large project (FrozenChlorine)."""
        import time

        start_time = time.time()

        # Parse project metadata
        project = ProjectParser.parse_project_from_dir(self.FROZEN_CHLORINE)

        # Discover all workflows
        discovery = XamlDiscovery(self.FROZEN_CHLORINE)
        workflow_index = discovery.discover_workflows()

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (adjust as needed)
        assert duration < 30.0  # 30 seconds max for this project

        # Should find a reasonable number of workflows
        assert workflow_index.total_workflows > 0

        print(f"Parsed {workflow_index.total_workflows} workflows in {duration:.2f} seconds")
