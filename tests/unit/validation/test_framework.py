"""Tests for validation framework core functionality."""

import json

import pytest

from rpax.config import RpaxConfig
from rpax.validation.framework import (
    ArtifactSet,
    ValidationFramework,
    ValidationIssue,
    ValidationResult,
    ValidationStatus,
)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    from rpax.config import OutputConfig, ProjectConfig, ScanConfig, ValidationConfig
    return RpaxConfig(
        project=ProjectConfig(name="TestProject", type="process"),
        scan=ScanConfig(exclude=[".local/**", ".settings/**"]),
        output=OutputConfig(dir="output"),
        validation=ValidationConfig(fail_on_missing=True, fail_on_cycles=True)
    )


@pytest.fixture
def artifacts_dir(tmp_path):
    """Create sample artifacts directory for testing."""
    # Create manifest.json
    manifest = {
        "rpaxVersion": "0.1.0",
        "schemaVersion": "1.0",
        "generatedAt": "2025-09-05T12:00:00Z",
        "projectName": "TestProject",
        "projectRoot": str(tmp_path / "project"),
        "mainWorkflow": "Main.xaml",
        "entryPoints": [
            {"filePath": "Main.xaml", "input": [], "output": []}
        ]
    }

    with open(tmp_path / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Create workflows.index.json
    workflows_index = {
        "projectName": "TestProject",
        "workflows": [
            {
                "id": "test-project-abc123#Main.xaml#def456",
                "projectSlug": "test-project-abc123",
                "workflowId": "Main.xaml",
                "contentHash": "def456789...",
                "filePath": str(tmp_path / "project" / "Main.xaml"),
                "parseSuccessful": True
            }
        ]
    }

    with open(tmp_path / "workflows.index.json", "w", encoding="utf-8") as f:
        json.dump(workflows_index, f, indent=2)

    # Create invocations.jsonl
    invocations = [
        {"kind": "invoke", "from": "test-project-abc123#Main.xaml#def456", "to": "test-project-abc123#Helper.xaml#ghi789"}
    ]

    with open(tmp_path / "invocations.jsonl", "w", encoding="utf-8") as f:
        for invocation in invocations:
            f.write(json.dumps(invocation) + "\n")

    # Create the project directory and workflow file
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "Main.xaml").write_text("<Activity></Activity>", encoding="utf-8")

    return tmp_path


class TestValidationIssue:
    """Test ValidationIssue class."""

    def test_create_issue(self):
        issue = ValidationIssue(
            rule="test_rule",
            severity=ValidationStatus.WARN,
            message="Test warning",
            artifact="test.json",
            path="$.field"
        )

        assert issue.rule == "test_rule"
        assert issue.severity == ValidationStatus.WARN
        assert issue.message == "Test warning"
        assert issue.artifact == "test.json"
        assert issue.path == "$.field"

    def test_string_representation(self):
        issue = ValidationIssue(
            rule="test_rule",
            severity=ValidationStatus.FAIL,
            message="Test error",
            artifact="test.json"
        )

        expected = "[FAIL] test_rule: Test error in test.json"
        assert str(issue) == expected


class TestValidationResult:
    """Test ValidationResult class."""

    def test_initial_status(self):
        result = ValidationResult(status=ValidationStatus.PASS)
        assert result.status == ValidationStatus.PASS
        assert result.exit_code == 0
        assert len(result.issues) == 0
        assert len(result.counters) == 0

    def test_add_issue_updates_status(self):
        result = ValidationResult(status=ValidationStatus.PASS)

        # Add warning - should change to warn
        result.add_issue("test", ValidationStatus.WARN, "Warning message")
        assert result.status == ValidationStatus.WARN
        assert result.exit_code == 0

        # Add fail - should change to fail
        result.add_issue("test", ValidationStatus.FAIL, "Error message")
        assert result.status == ValidationStatus.FAIL
        assert result.exit_code == 1

        # Add pass - should stay fail
        result.add_issue("test", ValidationStatus.PASS, "Pass message")
        assert result.status == ValidationStatus.FAIL

    def test_increment_counter(self):
        result = ValidationResult(status=ValidationStatus.PASS)

        result.increment_counter("test_counter")
        assert result.counters["test_counter"] == 1

        result.increment_counter("test_counter", 5)
        assert result.counters["test_counter"] == 6

    def test_to_dict(self):
        result = ValidationResult(status=ValidationStatus.WARN)
        result.add_issue("test", ValidationStatus.WARN, "Test message", "test.json", "$.path")
        result.increment_counter("test_count", 3)

        data = result.to_dict()

        assert data["status"] == "warn"
        assert data["exit_code"] == 0
        assert data["counters"]["test_count"] == 3
        assert len(data["issues"]) == 1

        issue = data["issues"][0]
        assert issue["rule"] == "test"
        assert issue["severity"] == "warn"
        assert issue["message"] == "Test message"
        assert issue["artifact"] == "test.json"
        assert issue["path"] == "$.path"


class TestArtifactSet:
    """Test ArtifactSet class."""

    def test_load_artifacts(self, artifacts_dir):
        artifacts = ArtifactSet.load(artifacts_dir)

        assert artifacts.artifacts_dir == artifacts_dir
        assert artifacts.manifest is not None
        assert artifacts.workflows_index is not None
        assert len(artifacts.invocations) == 1

        # Check manifest content
        assert artifacts.manifest["rpaxVersion"] == "0.1.0"
        assert artifacts.manifest["projectName"] == "TestProject"

        # Check workflows index
        assert artifacts.workflows_index["projectName"] == "TestProject"
        assert len(artifacts.workflows_index["workflows"]) == 1

        # Check invocations
        assert artifacts.invocations[0]["kind"] == "invoke"

    def test_load_missing_files(self, tmp_path):
        # Load from empty directory
        artifacts = ArtifactSet.load(tmp_path)

        assert artifacts.manifest is None
        assert artifacts.workflows_index is None
        assert len(artifacts.invocations) == 0


class TestValidationFramework:
    """Test ValidationFramework class."""

    def test_create_framework(self, sample_config):
        framework = ValidationFramework(sample_config)
        assert framework.config == sample_config
        assert len(framework.rules) == 0

    def test_add_rules(self, sample_config):
        framework = ValidationFramework(sample_config)

        # Mock rule
        class MockRule:
            @property
            def name(self):
                return "mock_rule"

            def validate(self, artifacts_dir, config, result):
                result.increment_counter("mock_executed")

        rule = MockRule()
        framework.add_rule(rule)

        assert len(framework.rules) == 1
        assert framework.rules[0] == rule

    def test_validate_execution(self, sample_config, artifacts_dir):
        framework = ValidationFramework(sample_config)

        # Mock rule that adds an issue
        class MockRule:
            @property
            def name(self):
                return "mock_rule"

            def validate(self, artifacts_dir, config, result):
                result.add_issue(self.name, ValidationStatus.WARN, "Mock warning")
                result.increment_counter("mock_executed")

        framework.add_rule(MockRule())
        result = framework.validate(artifacts_dir)

        assert result.status == ValidationStatus.WARN
        assert len(result.issues) == 1
        assert result.counters["mock_executed"] == 1
        assert result.issues[0].rule == "mock_rule"

    def test_rule_exception_handling(self, sample_config, artifacts_dir):
        framework = ValidationFramework(sample_config)

        # Rule that raises exception
        class FailingRule:
            @property
            def name(self):
                return "failing_rule"

            def validate(self, artifacts_dir, config, result):
                raise ValueError("Test error")

        framework.add_rule(FailingRule())
        result = framework.validate(artifacts_dir)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert "Rule execution failed" in result.issues[0].message

    def test_create_default_rules(self, sample_config):
        framework = ValidationFramework(sample_config)
        framework.create_default_rules()

        # Should have created all default rules
        assert len(framework.rules) == 7

        rule_names = [rule.name for rule in framework.rules]
        expected_rules = [
            "artifacts_presence",
            "provenance",
            "roots_resolvable",
            "referential_integrity",
            "kinds_bounded",
            "arguments_presence",
            "cycle_detection"
        ]

        for expected in expected_rules:
            assert expected in rule_names
