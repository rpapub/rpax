"""Simple schema validation for rpax artifacts without external dependencies.

This module provides basic schema validation and versioning support for rpax 
artifacts using only standard library components.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class SchemaVersion:
    """Represents a semantic version with comparison support."""
    
    def __init__(self, version_str: str):
        self.raw = version_str
        parts = version_str.split('.')
        self.major = int(parts[0])
        self.minor = int(parts[1])  
        self.patch = int(parts[2])
    
    def __str__(self):
        return self.raw
    
    def __eq__(self, other):
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other):
        return self < other or self == other
    
    def is_compatible_with(self, other) -> bool:
        """Check if this version is backward compatible with another."""
        # Same major version is compatible
        return self.major == other.major


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"  
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue with context."""
    severity: ValidationSeverity
    message: str
    path: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of schema validation with detailed feedback."""
    is_valid: bool
    schema_version: str
    issues: List[ValidationIssue]
    
    @property
    def has_errors(self) -> bool:
        """Check if result has any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if result has any warning-level issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)


class SimpleArtifactValidator:
    """Simple validator for rpax artifacts using basic validation rules."""
    
    def __init__(self):
        self.supported_versions = {
            "activity-instances": ["1.0.0", "1.1.0"]
        }
    
    def validate_artifact(self, artifact_data: Dict[str, Any], 
                         artifact_type: Optional[str] = None) -> ValidationResult:
        """Validate an artifact against basic schema rules."""
        issues = []
        
        # Determine artifact type if not provided
        if artifact_type is None:
            artifact_type = self._infer_artifact_type(artifact_data)
            if artifact_type is None:
                return ValidationResult(
                    is_valid=False,
                    schema_version="unknown",
                    issues=[ValidationIssue(
                        ValidationSeverity.ERROR,
                        "Could not determine artifact type",
                        "$"
                    )]
                )
        
        # Get schema version from artifact
        schema_version = artifact_data.get("schemaVersion", "1.0.0")
        
        # Check if version is supported
        supported = self.supported_versions.get(artifact_type, [])
        if schema_version not in supported:
            # Try to find compatible version
            target_version = SchemaVersion(schema_version)
            compatible_found = False
            
            for supported_version in supported:
                if SchemaVersion(supported_version).is_compatible_with(target_version):
                    compatible_found = True
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        f"Using compatible validation for v{schema_version}",
                        "$"
                    ))
                    break
            
            if not compatible_found:
                return ValidationResult(
                    is_valid=False,
                    schema_version=schema_version,
                    issues=[ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"Unsupported schema version {schema_version} for {artifact_type}",
                        "$"
                    )]
                )
        
        # Perform validation based on artifact type
        if artifact_type == "activity-instances":
            validation_issues = self._validate_activity_instances(artifact_data, schema_version)
            issues.extend(validation_issues)
        
        return ValidationResult(
            is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            schema_version=schema_version,
            issues=issues
        )
    
    def _infer_artifact_type(self, artifact_data: Dict[str, Any]) -> Optional[str]:
        """Infer artifact type from data structure."""
        if "activities" in artifact_data and "totalActivities" in artifact_data:
            return "activity-instances"
        elif "workflows" in artifact_data and "project" in artifact_data:
            return "manifest"  
        elif "invocations" in artifact_data:
            return "invocations"
        
        return None
    
    def _validate_activity_instances(self, data: Dict[str, Any], 
                                   schema_version: str) -> List[ValidationIssue]:
        """Validate activity instances artifact."""
        issues = []
        
        # Required fields for all versions
        required_fields = ["schemaVersion", "workflowId", "totalActivities", "activities"]
        for field in required_fields:
            if field not in data:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Missing required field: {field}",
                    f"$.{field}"
                ))
        
        # Version-specific required fields
        if SchemaVersion(schema_version) >= SchemaVersion("1.1.0"):
            v11_required = ["projectId"]
            for field in v11_required:
                if field not in data:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"Missing required field for v{schema_version}: {field}",
                        f"$.{field}"
                    ))
        
        # Validate activities if present
        activities = data.get("activities", [])
        total_activities = data.get("totalActivities", 0)
        
        # Check activity count consistency
        if len(activities) != total_activities:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                f"Activity count mismatch: declared {total_activities}, found {len(activities)}",
                "$.totalActivities"
            ))
        
        # Validate individual activities
        activity_ids = set()
        for i, activity in enumerate(activities):
            activity_path = f"$.activities[{i}]"
            
            # Required activity fields
            activity_required = [
                "activity_id", "workflow_id", "activity_type", "node_id", 
                "depth", "arguments", "configuration", "properties", 
                "metadata", "expressions", "variables_referenced", "selectors", "is_visible"
            ]
            
            for field in activity_required:
                if field not in activity:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"Activity missing required field: {field}",
                        f"{activity_path}.{field}"
                    ))
            
            # Validate activity ID format
            activity_id = activity.get("activity_id", "")
            if activity_id:
                if not self._validate_activity_id_format(activity_id):
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"Invalid activity ID format: {activity_id}",
                        f"{activity_path}.activity_id"
                    ))
                
                # Check for duplicates
                if activity_id in activity_ids:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"Duplicate activity ID: {activity_id}",
                        f"{activity_path}.activity_id"
                    ))
                activity_ids.add(activity_id)
            
            # Validate depth is non-negative integer
            depth = activity.get("depth")
            if depth is not None and (not isinstance(depth, int) or depth < 0):
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Invalid depth value: {depth} (must be non-negative integer)",
                    f"{activity_path}.depth"
                ))
            
            # Validate is_visible is boolean
            is_visible = activity.get("is_visible")
            if is_visible is not None and not isinstance(is_visible, bool):
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Invalid is_visible value: {is_visible} (must be boolean)",
                    f"{activity_path}.is_visible"
                ))
        
        # Check parent-child relationships
        for i, activity in enumerate(activities):
            parent_id = activity.get("parent_activity_id")
            if parent_id and parent_id not in activity_ids:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    f"Parent activity not found: {parent_id}",
                    f"$.activities[{i}].parent_activity_id"
                ))
        
        # Version-specific validations
        if SchemaVersion(schema_version) >= SchemaVersion("1.1.0"):
            # v1.1+ specific validations
            if "visibleActivities" in data:
                visible_count = sum(1 for a in activities if a.get("is_visible", True))
                declared_visible = data["visibleActivities"]
                if visible_count != declared_visible:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        f"Visible activity count mismatch: declared {declared_visible}, found {visible_count}",
                        "$.visibleActivities"
                    ))
            
            if "activitiesWithSelectors" in data:
                selector_count = sum(1 for a in activities if a.get("selectors") and len(a["selectors"]) > 0)
                declared_selector_count = data["activitiesWithSelectors"]
                if selector_count != declared_selector_count:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        f"Activities with selectors count mismatch: declared {declared_selector_count}, found {selector_count}",
                        "$.activitiesWithSelectors"
                    ))
        
        return issues
    
    def _validate_activity_id_format(self, activity_id: str) -> bool:
        """Validate activity ID format: {projectId}#{workflowId}#{nodeId}#{contentHash}"""
        parts = activity_id.split('#')
        if len(parts) != 4:
            return False
        
        # Check content hash format (8 hex characters)
        content_hash = parts[3]
        if len(content_hash) != 8:
            return False
        
        try:
            int(content_hash, 16)  # Should be valid hex
        except ValueError:
            return False
        
        # Other parts should be non-empty
        return all(part.strip() for part in parts[:3])
    
    def validate_compatibility(self, old_version: str, new_version: str, 
                              artifact_type: str) -> Tuple[bool, List[str]]:
        """Check if a version upgrade is backward compatible."""
        old_ver = SchemaVersion(old_version)
        new_ver = SchemaVersion(new_version)
        
        issues = []
        
        # Major version changes break compatibility
        if old_ver.major != new_ver.major:
            issues.append(f"Major version change from {old_version} to {new_version} breaks compatibility")
            return False, issues
        
        # Minor version increases are compatible (new optional fields)
        if new_ver.minor > old_ver.minor:
            issues.append(f"Minor version increase from {old_version} to {new_version} should be compatible")
        
        # Patch version changes should be fully compatible
        if new_ver.patch != old_ver.patch:
            issues.append(f"Patch version change from {old_version} to {new_version} should be fully compatible")
        
        return True, issues
    
    def generate_migration_guide(self, old_version: str, new_version: str, 
                                artifact_type: str) -> List[str]:
        """Generate migration steps for version upgrades."""
        migration_steps = []
        
        old_ver = SchemaVersion(old_version)
        new_ver = SchemaVersion(new_version)
        
        if artifact_type == "activity-instances":
            if old_ver < SchemaVersion("1.1.0") and new_ver >= SchemaVersion("1.1.0"):
                migration_steps.extend([
                    "Add 'projectId' field to root object",
                    "Add optional 'performanceMetrics' object with generation metrics",
                    "Add 'visibleActivities' and 'activitiesWithSelectors' counts",
                    "Add 'business_logic_complexity' metrics to activity instances",
                    "Update schemaVersion to '1.1.0'"
                ])
        
        return migration_steps


def validate_artifact_file(file_path: Path, artifact_type: Optional[str] = None) -> ValidationResult:
    """Convenience function to validate an artifact file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        validator = SimpleArtifactValidator()
        return validator.validate_artifact(data, artifact_type)
        
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            schema_version="unknown",
            issues=[ValidationIssue(
                ValidationSeverity.ERROR,
                f"Failed to load artifact file: {e}",
                str(file_path)
            )]
        )