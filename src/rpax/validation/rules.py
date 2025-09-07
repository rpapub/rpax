"""Validation rules implementing ADR-010 requirements.

Each rule validates a specific aspect of parser artifacts for pipeline readiness.
"""

import json
import logging
from pathlib import Path

from ..config import RpaxConfig
from .framework import ArtifactSet, ValidationResult, ValidationRule, ValidationStatus

logger = logging.getLogger(__name__)


class ArtifactsPresenceRule(ValidationRule):
    """Validate that required artifacts are present."""

    @property
    def name(self) -> str:
        return "artifacts_presence"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        required_files = [
            "manifest.json",
            "workflows.index.json"
        ]

        for file_name in required_files:
            file_path = artifacts_dir / file_name
            if not file_path.exists():
                result.add_issue(
                    self.name,
                    ValidationStatus.FAIL,
                    f"Required artifact missing: {file_name}",
                    artifact=file_name
                )
            else:
                # Verify it's valid JSON
                try:
                    with open(file_path, encoding="utf-8") as f:
                        json.load(f)
                    result.increment_counter("artifacts_valid")
                except json.JSONDecodeError as e:
                    result.add_issue(
                        self.name,
                        ValidationStatus.FAIL,
                        f"Invalid JSON in {file_name}: {e}",
                        artifact=file_name
                    )


class ProvenanceRule(ValidationRule):
    """Validate that tool version and run metadata are present."""

    @property
    def name(self) -> str:
        return "provenance"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)

        if not artifacts.manifest:
            result.add_issue(
                self.name,
                ValidationStatus.FAIL,
                "Manifest required for provenance validation",
                artifact="manifest.json"
            )
            return

        required_fields = [
            "rpaxVersion",
            "rpaxSchemaVersion",
            "generatedAt"
        ]

        for field in required_fields:
            if field not in artifacts.manifest:
                result.add_issue(
                    self.name,
                    ValidationStatus.FAIL,
                    f"Missing provenance field: {field}",
                    artifact="manifest.json",
                    path=f"$.{field}"
                )

        result.increment_counter("provenance_fields", len(required_fields))


class RootsResolvableRule(ValidationRule):
    """Validate that all declared entry points exist on disk."""

    @property
    def name(self) -> str:
        return "roots_resolvable"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)

        if not artifacts.manifest:
            return  # Will be caught by artifacts_presence rule

        project_root = Path(artifacts.manifest.get("projectRoot", "."))
        entry_points = artifacts.manifest.get("entryPoints", [])
        main_workflow = artifacts.manifest.get("mainWorkflow")

        # Check main workflow
        if main_workflow:
            main_path = project_root / main_workflow
            if not main_path.exists():
                result.add_issue(
                    self.name,
                    ValidationStatus.FAIL,
                    f"Main workflow not found: {main_workflow}",
                    artifact="manifest.json",
                    path="$.mainWorkflow"
                )
            else:
                result.increment_counter("roots_resolved")

        # Check entry points
        for i, entry_point in enumerate(entry_points):
            if isinstance(entry_point, dict) and "filePath" in entry_point:
                entry_path = project_root / entry_point["filePath"]
                if not entry_path.exists():
                    result.add_issue(
                        self.name,
                        ValidationStatus.FAIL,
                        f"Entry point not found: {entry_point['filePath']}",
                        artifact="manifest.json",
                        path=f"$.entryPoints[{i}].filePath"
                    )
                else:
                    result.increment_counter("roots_resolved")


class ReferentialIntegrityRule(ValidationRule):
    """Validate referential integrity in invocations."""

    @property
    def name(self) -> str:
        return "referential_integrity"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)

        if not artifacts.workflows_index:
            return  # Will be caught by artifacts_presence rule

        # Build set of known workflow IDs
        known_workflows = set()
        workflows = artifacts.workflows_index.get("workflows", [])
        for workflow in workflows:
            if "id" in workflow:
                known_workflows.add(workflow["id"])

        result.increment_counter("known_workflows", len(known_workflows))

        # Validate invocations
        for i, invocation in enumerate(artifacts.invocations):
            if invocation.get("kind") == "invoke":
                from_id = invocation.get("from")
                to_id = invocation.get("to")

                if from_id and from_id not in known_workflows:
                    result.add_issue(
                        self.name,
                        ValidationStatus.FAIL,
                        f"Invocation references unknown 'from' workflow: {from_id}",
                        artifact="invocations.jsonl",
                        path=f"$[{i}].from"
                    )

                if to_id and to_id not in known_workflows:
                    result.add_issue(
                        self.name,
                        ValidationStatus.WARN,
                        f"Invocation references unknown 'to' workflow: {to_id}",
                        artifact="invocations.jsonl",
                        path=f"$[{i}].to"
                    )


class KindsBoundedRule(ValidationRule):
    """Validate that invocation kinds are bounded to allowed values."""

    @property
    def name(self) -> str:
        return "kinds_bounded"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)

        allowed_kinds = {"invoke", "invoke-missing", "invoke-dynamic"}

        for i, invocation in enumerate(artifacts.invocations):
            kind = invocation.get("kind")
            if kind and kind not in allowed_kinds:
                result.add_issue(
                    self.name,
                    ValidationStatus.FAIL,
                    f"Invalid invocation kind: {kind}. Allowed: {', '.join(sorted(allowed_kinds))}",
                    artifact="invocations.jsonl",
                    path=f"$[{i}].kind"
                )
            elif kind in allowed_kinds:
                result.increment_counter(f"kind_{kind}")


class ArgumentsPresenceRule(ValidationRule):
    """Validate that invoked workflows have arguments blocks."""

    @property
    def name(self) -> str:
        return "arguments_presence"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)

        # For now, just count invocations with arguments
        # Full implementation would require activity-level parsing
        for invocation in artifacts.invocations:
            if "arguments" in invocation:
                result.increment_counter("invocations_with_arguments")
            else:
                result.increment_counter("invocations_without_arguments")


class CycleDetectionRule(ValidationRule):
    """Detect cycles in workflow invocation graph."""

    @property
    def name(self) -> str:
        return "cycle_detection"

    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)

        # Build adjacency list from invocations
        graph: dict[str, set[str]] = {}

        for invocation in artifacts.invocations:
            if invocation.get("kind") == "invoke":
                from_id = invocation.get("from")
                to_id = invocation.get("to")

                if from_id and to_id:
                    if from_id not in graph:
                        graph[from_id] = set()
                    graph[from_id].add(to_id)

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles_found = []

        def has_cycle_util(node: str, path: list[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle_util(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles_found.append(" -> ".join(cycle))
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                has_cycle_util(node, [])

        result.increment_counter("cycles_detected", len(cycles_found))

        for cycle in cycles_found:
            severity = ValidationStatus.FAIL if config.validation.fail_on_cycles else ValidationStatus.WARN
            result.add_issue(
                self.name,
                severity,
                f"Cycle detected: {cycle}",
                artifact="invocations.jsonl"
            )
