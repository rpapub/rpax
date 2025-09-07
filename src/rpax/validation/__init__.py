"""Validation layer for rpax parser artifacts.

This module implements the lightweight validation layer (ADR-010) focused on pipeline readiness
rather than semantic correctness. It validates parser artifacts for downstream consumption.
"""

from .framework import ValidationFramework, ValidationResult, ValidationRule
from .rules import (
    ArgumentsPresenceRule,
    ArtifactsPresenceRule,
    CycleDetectionRule,
    KindsBoundedRule,
    ProvenanceRule,
    ReferentialIntegrityRule,
    RootsResolvableRule,
)

__all__ = [
    "ValidationFramework",
    "ValidationResult",
    "ValidationRule",
    "ArtifactsPresenceRule",
    "RootsResolvableRule",
    "ReferentialIntegrityRule",
    "KindsBoundedRule",
    "ArgumentsPresenceRule",
    "CycleDetectionRule",
    "ProvenanceRule"
]
