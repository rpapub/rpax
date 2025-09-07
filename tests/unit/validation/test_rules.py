"""Tests for validation rules."""

import json

import pytest

from rpax.config import RpaxConfig
from rpax.validation.framework import ValidationResult, ValidationStatus
from rpax.validation.rules import (
    ArtifactsPresenceRule,
    CycleDetectionRule,
    KindsBoundedRule,
    ProvenanceRule,
    ReferentialIntegrityRule,
    RootsResolvableRule,
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
    # Create valid manifest.json
    manifest = {
        "rpaxVersion": "0.1.0",
        "rpaxSchemaVersion": "1.0",
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

    # Create valid workflows.index.json
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
            },
            {
                "id": "test-project-abc123#Helper.xaml#ghi789",
                "projectSlug": "test-project-abc123",
                "workflowId": "Helper.xaml",
                "contentHash": "ghi789abc...",
                "filePath": str(tmp_path / "project" / "Helper.xaml"),
                "parseSuccessful": True
            }
        ]
    }

    with open(tmp_path / "workflows.index.json", "w", encoding="utf-8") as f:
        json.dump(workflows_index, f, indent=2)

    # Create project directory and workflow files
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "Main.xaml").write_text("<Activity></Activity>", encoding="utf-8")
    (project_dir / "Helper.xaml").write_text("<Activity></Activity>", encoding="utf-8")

    return tmp_path


class TestArtifactsPresenceRule:
    """Test ArtifactsPresenceRule."""

    def test_valid_artifacts(self, sample_config, artifacts_dir):
        rule = ArtifactsPresenceRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.counters["artifacts_valid"] == 2

    def test_missing_manifest(self, sample_config, artifacts_dir):
        # Remove manifest.json
        (artifacts_dir / "manifest.json").unlink()

        rule = ArtifactsPresenceRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert "manifest.json" in result.issues[0].message

    def test_invalid_json(self, sample_config, artifacts_dir):
        # Write invalid JSON
        with open(artifacts_dir / "manifest.json", "w") as f:
            f.write("invalid json {")

        rule = ArtifactsPresenceRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert "Invalid JSON" in result.issues[0].message


class TestProvenanceRule:
    """Test ProvenanceRule."""

    def test_valid_provenance(self, sample_config, artifacts_dir):
        rule = ProvenanceRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.counters["provenance_fields"] == 3

    def test_missing_provenance_fields(self, sample_config, artifacts_dir):
        # Remove provenance fields
        with open(artifacts_dir / "manifest.json") as f:
            manifest = json.load(f)

        del manifest["rpaxVersion"]
        del manifest["generatedAt"]

        with open(artifacts_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        rule = ProvenanceRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 2


class TestRootsResolvableRule:
    """Test RootsResolvableRule."""

    def test_resolvable_roots(self, sample_config, artifacts_dir):
        rule = RootsResolvableRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.counters["roots_resolved"] == 2  # main + entry point

    def test_missing_main_workflow(self, sample_config, artifacts_dir):
        # Remove the main workflow file
        (artifacts_dir / "project" / "Main.xaml").unlink()

        rule = RootsResolvableRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 2  # main workflow missing twice (main + entry point)


class TestReferentialIntegrityRule:
    """Test ReferentialIntegrityRule."""

    def test_valid_references(self, sample_config, artifacts_dir):
        # Create invocations with valid references
        invocations = [
            {"kind": "invoke", "from": "test-project-abc123#Main.xaml#def456", "to": "test-project-abc123#Helper.xaml#ghi789"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = ReferentialIntegrityRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.counters["known_workflows"] == 2

    def test_missing_from_workflow(self, sample_config, artifacts_dir):
        # Create invocation with unknown 'from' workflow
        invocations = [
            {"kind": "invoke", "from": "unknown-workflow", "to": "test-project-abc123#Helper.xaml#ghi789"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = ReferentialIntegrityRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert "unknown 'from' workflow" in result.issues[0].message

    def test_missing_to_workflow(self, sample_config, artifacts_dir):
        # Create invocation with unknown 'to' workflow (should be warning, not error)
        invocations = [
            {"kind": "invoke", "from": "test-project-abc123#Main.xaml#def456", "to": "unknown-workflow"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = ReferentialIntegrityRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.WARN
        assert len(result.issues) == 1
        assert "unknown 'to' workflow" in result.issues[0].message


class TestKindsBoundedRule:
    """Test KindsBoundedRule."""

    def test_valid_kinds(self, sample_config, artifacts_dir):
        invocations = [
            {"kind": "invoke", "from": "a", "to": "b"},
            {"kind": "invoke-missing", "from": "c", "to": "d"},
            {"kind": "invoke-dynamic", "from": "e", "to": "f"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = KindsBoundedRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.counters["kind_invoke"] == 1
        assert result.counters["kind_invoke-missing"] == 1
        assert result.counters["kind_invoke-dynamic"] == 1

    def test_invalid_kind(self, sample_config, artifacts_dir):
        invocations = [
            {"kind": "invalid-kind", "from": "a", "to": "b"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = KindsBoundedRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert "Invalid invocation kind" in result.issues[0].message


class TestCycleDetectionRule:
    """Test CycleDetectionRule."""

    def test_no_cycles(self, sample_config, artifacts_dir):
        # Linear invocation: A -> B -> C
        invocations = [
            {"kind": "invoke", "from": "A", "to": "B"},
            {"kind": "invoke", "from": "B", "to": "C"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = CycleDetectionRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.PASS
        assert len(result.issues) == 0
        assert result.counters["cycles_detected"] == 0

    def test_simple_cycle(self, sample_config, artifacts_dir):
        # Simple cycle: A -> B -> A
        invocations = [
            {"kind": "invoke", "from": "A", "to": "B"},
            {"kind": "invoke", "from": "B", "to": "A"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = CycleDetectionRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.FAIL
        assert len(result.issues) == 1
        assert result.counters["cycles_detected"] == 1
        assert "Cycle detected" in result.issues[0].message

    def test_cycle_with_warn_mode(self, sample_config, artifacts_dir):
        # Configure to warn on cycles instead of fail
        sample_config.validation.fail_on_cycles = False

        invocations = [
            {"kind": "invoke", "from": "A", "to": "B"},
            {"kind": "invoke", "from": "B", "to": "A"}
        ]

        with open(artifacts_dir / "invocations.jsonl", "w") as f:
            for invocation in invocations:
                f.write(json.dumps(invocation) + "\n")

        rule = CycleDetectionRule()
        result = ValidationResult(status=ValidationStatus.PASS)

        rule.validate(artifacts_dir, sample_config, result)

        assert result.status == ValidationStatus.WARN
        assert len(result.issues) == 1
        assert result.counters["cycles_detected"] == 1
