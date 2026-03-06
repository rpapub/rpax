"""Tier 1 code quality review rules for rpax.

These rules operate entirely on existing artifacts — no additional XAML parsing needed.
Each rule maps to a dimension of the UiPath code review checklist documented in
docs/llm/context/review-research.md.
"""

import json
import logging
from pathlib import Path

from ..config import RpaxConfig
from ..validation.framework import (
    ArtifactSet,
    ValidationResult,
    ValidationRule,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

# Argument direction values as stored in workflows.index.json
_DIRECTION_PREFIX = {
    "in": "in_",
    "out": "out_",
    "io": "io_",
    "inout": "io_",
}


class ArgumentNamingRule(ValidationRule):
    """Check that workflow arguments follow the in_/out_/io_ prefix convention.

    UiPath naming convention: arguments must be prefixed with in_, out_, or io_
    depending on their direction (ST-NMG-* category in Workflow Analyzer).
    """

    @property
    def name(self) -> str:
        return "argument_naming"

    def validate(
        self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult
    ) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)
        if not artifacts.workflows_index:
            return

        violations = 0
        workflows_checked = 0

        for wf in artifacts.workflows_index.get("workflows", []):
            workflow_id = wf.get("workflowId", "")
            args = wf.get("arguments", []) or []
            if not args:
                continue

            workflows_checked += 1
            for arg in args:
                arg_name = arg.get("name", "")
                direction = (arg.get("direction") or "").lower()

                if not arg_name or not direction:
                    continue

                expected_prefix = _DIRECTION_PREFIX.get(direction)
                if expected_prefix and not arg_name.startswith(expected_prefix):
                    violations += 1
                    result.add_issue(
                        self.name,
                        ValidationStatus.WARN,
                        f"Argument '{arg_name}' ({direction}) should start with '{expected_prefix}'",
                        artifact="workflows.index.json",
                        path=workflow_id,
                    )

        result.increment_counter("argument_naming_workflows_checked", workflows_checked)
        result.increment_counter("argument_naming_violations", violations)


class WorkflowSizeRule(ValidationRule):
    """Flag workflows that exceed the recommended activity count.

    Large workflows are hard to read, test, and maintain.
    Corresponds to the 'no workflows > 30-50 activities' guideline.
    """

    def __init__(self, max_activities: int = 50) -> None:
        self._max_activities = max_activities

    @property
    def name(self) -> str:
        return "workflow_size"

    def validate(
        self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult
    ) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)
        if not artifacts.workflows_index:
            return

        oversized = 0

        for wf in artifacts.workflows_index.get("workflows", []):
            total = wf.get("totalActivities") or 0
            workflow_id = wf.get("workflowId", "")

            if total > self._max_activities:
                oversized += 1
                result.add_issue(
                    self.name,
                    ValidationStatus.WARN,
                    f"Workflow '{workflow_id}' has {total} activities (threshold: {self._max_activities})",
                    artifact="workflows.index.json",
                    path=workflow_id,
                )

        result.increment_counter("oversized_workflows", oversized)


class AnnotationCoverageRule(ValidationRule):
    """Flag non-trivial workflows with zero annotated activities.

    Complex workflows with no annotations are hard to review and hand over.
    """

    def __init__(self, min_activities: int = 5) -> None:
        self._min_activities = min_activities

    @property
    def name(self) -> str:
        return "annotation_coverage"

    def validate(
        self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult
    ) -> None:
        metrics_dir = artifacts_dir / "metrics"
        if not metrics_dir.exists():
            logger.debug("metrics/ directory not found — skipping annotation_coverage rule")
            return

        checked = 0
        violations = 0

        for metrics_path in sorted(metrics_dir.rglob("*.json")):
            try:
                with open(metrics_path, encoding="utf-8") as f:
                    metrics = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Skipping %s: %s", metrics_path, exc)
                continue

            total_nodes = metrics.get("totalNodes") or 0
            annotated = metrics.get("annotatedActivityCount") or 0
            workflow_id = metrics.get("workflowId") or metrics_path.stem

            checked += 1
            if total_nodes >= self._min_activities and annotated == 0:
                violations += 1
                result.add_issue(
                    self.name,
                    ValidationStatus.WARN,
                    f"Workflow '{workflow_id}' has {total_nodes} activities but no annotations",
                    artifact=str(metrics_path.relative_to(artifacts_dir)),
                    path=workflow_id,
                )

        result.increment_counter("annotation_coverage_checked", checked)
        result.increment_counter("annotation_coverage_violations", violations)


class ErrorHandlingRule(ValidationRule):
    """Flag non-trivial workflows with no TryCatch error handling.

    Workflows above the activity threshold should have at least one TryCatch
    block to handle unexpected errors gracefully.
    """

    def __init__(self, min_activities: int = 10) -> None:
        self._min_activities = min_activities

    @property
    def name(self) -> str:
        return "error_handling"

    def validate(
        self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult
    ) -> None:
        metrics_dir = artifacts_dir / "metrics"
        if not metrics_dir.exists():
            logger.debug("metrics/ directory not found — skipping error_handling rule")
            return

        checked = 0
        violations = 0

        for metrics_path in sorted(metrics_dir.rglob("*.json")):
            try:
                with open(metrics_path, encoding="utf-8") as f:
                    metrics = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Skipping %s: %s", metrics_path, exc)
                continue

            total_nodes = metrics.get("totalNodes") or 0
            try_catch_count = metrics.get("tryCatchCount") or 0
            workflow_id = metrics.get("workflowId") or metrics_path.stem

            checked += 1
            if total_nodes >= self._min_activities and try_catch_count == 0:
                violations += 1
                result.add_issue(
                    self.name,
                    ValidationStatus.WARN,
                    f"Workflow '{workflow_id}' has {total_nodes} activities but no TryCatch",
                    artifact=str(metrics_path.relative_to(artifacts_dir)),
                    path=workflow_id,
                )

        result.increment_counter("error_handling_checked", checked)
        result.increment_counter("error_handling_violations", violations)


def _normalise_workflow_path(path_str: str) -> str:
    """Strip .xaml/.XAML suffix and normalise backslashes to forward slashes."""
    return path_str.replace("\\", "/").removesuffix(".xaml").removesuffix(".XAML")


def _build_id_maps(
    workflows_index: dict,
) -> tuple[dict[str, str], dict[str, list[str]], set[str]]:
    """Return (full_id→wf_id, wf_id→[full_ids], all_full_ids) from workflows index."""
    full_id_to_wf_id: dict[str, str] = {}
    wf_id_to_full_ids: dict[str, list[str]] = {}
    all_full_ids: set[str] = set()
    for wf in workflows_index.get("workflows", []):
        full_id = wf.get("id", "")
        wf_id = wf.get("workflowId", "")
        if full_id and wf_id:
            full_id_to_wf_id[full_id] = wf_id
            wf_id_to_full_ids.setdefault(wf_id, []).append(full_id)
            all_full_ids.add(full_id)
    return full_id_to_wf_id, wf_id_to_full_ids, all_full_ids


def _collect_entry_full_ids(
    manifest: dict, wf_id_to_full_ids: dict[str, list[str]]
) -> set[str]:
    """Resolve declared entry points to their full artifact IDs."""
    entry_wf_ids: set[str] = set()
    main_wf = manifest.get("mainWorkflow")
    if main_wf:
        entry_wf_ids.add(_normalise_workflow_path(main_wf))
    for ep in manifest.get("entryPoints", []):
        if isinstance(ep, dict):
            fp = ep.get("filePath", "")
            if fp:
                entry_wf_ids.add(_normalise_workflow_path(fp))
        elif isinstance(ep, str):
            entry_wf_ids.add(_normalise_workflow_path(ep))

    reachable: set[str] = set()
    for wf_id in entry_wf_ids:
        reachable.update(wf_id_to_full_ids.get(wf_id, []))
    return reachable


def _bfs_reachable(
    seed: set[str], invocations: list[dict]
) -> set[str]:
    """Return all workflow full IDs reachable via invoke edges from seed."""
    graph: dict[str, set[str]] = {}
    for inv in invocations:
        if inv.get("kind") == "invoke":
            from_id = inv.get("from", "")
            to_id = inv.get("to", "")
            if from_id and to_id:
                graph.setdefault(from_id, set()).add(to_id)

    reachable = set(seed)
    queue = list(seed)
    while queue:
        current = queue.pop(0)
        for neighbour in graph.get(current, set()):
            if neighbour not in reachable:
                reachable.add(neighbour)
                queue.append(neighbour)
    return reachable


class OrphanWorkflowRule(ValidationRule):
    """Flag workflows that are not reachable from any declared entry point.

    Orphaned workflows represent dead code: they cannot be invoked through
    normal process execution paths. A high orphan ratio often indicates
    accumulated technical debt.
    """

    @property
    def name(self) -> str:
        return "orphan_workflows"

    def validate(
        self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult
    ) -> None:
        artifacts = ArtifactSet.load(artifacts_dir)
        if not artifacts.manifest or not artifacts.workflows_index:
            return

        full_id_to_wf_id, wf_id_to_full_ids, all_full_ids = _build_id_maps(
            artifacts.workflows_index
        )
        if not all_full_ids:
            return

        seed = _collect_entry_full_ids(artifacts.manifest, wf_id_to_full_ids)
        reachable = _bfs_reachable(seed, artifacts.invocations)

        orphan_full_ids = all_full_ids - reachable
        total = len(all_full_ids)
        orphan_count = len(orphan_full_ids)

        result.increment_counter("total_workflows", total)
        result.increment_counter("reachable_workflows", total - orphan_count)
        result.increment_counter("orphan_workflows", orphan_count)

        for full_id in sorted(orphan_full_ids, key=lambda x: full_id_to_wf_id.get(x, x)):
            display = full_id_to_wf_id.get(full_id, full_id)
            result.add_issue(
                self.name,
                ValidationStatus.WARN,
                f"Workflow '{display}' is not reachable from any entry point",
                artifact="invocations.jsonl",
                path=display,
            )
