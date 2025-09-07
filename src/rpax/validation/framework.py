"""Core validation framework for rpax artifacts.

Implements the lightweight validation approach from ADR-010 with pluggable rules
and configurable behavior for CI/CD pipeline integration.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..config import RpaxConfig

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Validation status according to ADR-010."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationIssue:
    """A single validation issue found during validation."""
    rule: str
    severity: ValidationStatus
    message: str
    artifact: str | None = None
    path: str | None = None

    def __str__(self) -> str:
        location = ""
        if self.artifact:
            location += f" in {self.artifact}"
        if self.path:
            location += f" at {self.path}"
        return f"[{self.severity.value.upper()}] {self.rule}: {self.message}{location}"


@dataclass
class ValidationResult:
    """Results of validation run according to ADR-010."""
    status: ValidationStatus
    issues: list[ValidationIssue] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Exit code for CI: 0 = pass/warn, 1 = fail."""
        return 0 if self.status != ValidationStatus.FAIL else 1

    def add_issue(self, rule: str, severity: ValidationStatus, message: str,
                  artifact: str | None = None, path: str | None = None) -> None:
        """Add a validation issue."""
        issue = ValidationIssue(rule, severity, message, artifact, path)
        self.issues.append(issue)

        # Update overall status (fail > warn > pass)
        if severity == ValidationStatus.FAIL:
            self.status = ValidationStatus.FAIL
        elif severity == ValidationStatus.WARN and self.status == ValidationStatus.PASS:
            self.status = ValidationStatus.WARN

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[name] = self.counters.get(name, 0) + value

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "status": self.status.value,
            "exit_code": self.exit_code,
            "counters": self.counters,
            "issues": [
                {
                    "rule": issue.rule,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "artifact": issue.artifact,
                    "path": issue.path
                }
                for issue in self.issues
            ]
        }


class ValidationRule(ABC):
    """Base class for validation rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Rule name for identification."""
        pass

    @abstractmethod
    def validate(self, artifacts_dir: Path, config: RpaxConfig, result: ValidationResult) -> None:
        """Execute validation rule.
        
        Args:
            artifacts_dir: Directory containing parser artifacts
            config: rpax configuration
            result: Validation result to update with issues/counters
        """
        pass


@dataclass
class ArtifactSet:
    """Loaded parser artifacts for validation."""
    artifacts_dir: Path
    manifest: dict | None = None
    workflows_index: dict | None = None
    invocations: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, artifacts_dir: Path) -> "ArtifactSet":
        """Load artifacts from directory."""
        artifacts = cls(artifacts_dir)

        # Load manifest.json
        manifest_path = artifacts_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                artifacts.manifest = json.load(f)

        # Load workflows.index.json
        workflows_path = artifacts_dir / "workflows.index.json"
        if workflows_path.exists():
            with open(workflows_path, encoding="utf-8") as f:
                artifacts.workflows_index = json.load(f)

        # Load invocations.jsonl (if exists)
        invocations_path = artifacts_dir / "invocations.jsonl"
        if invocations_path.exists():
            with open(invocations_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):  # Skip comments and empty lines
                        try:
                            artifacts.invocations.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Skip malformed lines (placeholder files may have invalid JSON)
                            continue

        return artifacts


class ValidationFramework:
    """Main validation framework implementing ADR-010."""

    def __init__(self, config: RpaxConfig):
        self.config = config
        self.rules: list[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self.rules.append(rule)

    def validate(self, artifacts_dir: Path) -> ValidationResult:
        """Run validation on parser artifacts.
        
        Args:
            artifacts_dir: Directory containing parser artifacts
            
        Returns:
            ValidationResult with status, issues, and counters
        """
        result = ValidationResult(status=ValidationStatus.PASS)

        logger.info(f"Starting validation of artifacts in {artifacts_dir}")
        logger.info(f"Running {len(self.rules)} validation rules")

        # Execute all rules
        for rule in self.rules:
            logger.debug(f"Executing rule: {rule.name}")
            try:
                rule.validate(artifacts_dir, self.config, result)
            except Exception as e:
                logger.error(f"Rule {rule.name} failed with error: {e}")
                result.add_issue(
                    rule.name,
                    ValidationStatus.FAIL,
                    f"Rule execution failed: {e}"
                )

        logger.info(f"Validation completed with status: {result.status.value}")
        logger.info(f"Found {len(result.issues)} issues")

        return result

    def create_default_rules(self) -> None:
        """Create default validation rules according to ADR-010."""
        from .rules import (
            ArgumentsPresenceRule,
            ArtifactsPresenceRule,
            CycleDetectionRule,
            KindsBoundedRule,
            ProvenanceRule,
            ReferentialIntegrityRule,
            RootsResolvableRule,
        )

        self.add_rule(ArtifactsPresenceRule())
        self.add_rule(ProvenanceRule())
        self.add_rule(RootsResolvableRule())
        self.add_rule(ReferentialIntegrityRule())
        self.add_rule(KindsBoundedRule())
        self.add_rule(ArgumentsPresenceRule())
        self.add_rule(CycleDetectionRule())
