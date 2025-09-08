"""Schema validation and versioning system for rpax artifacts.

This module provides comprehensive schema validation with backward compatibility
support for all rpax artifact types, implementing versioned schema evolution.
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SchemaVersion:
    """Represents a semantic version with comparison support."""
    
    def __init__(self, version_str: str):
        self.raw = version_str
        parts = version_str.split('.')
        self.major = int(parts[0])
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0
    
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
    schema_path: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of schema validation with detailed feedback."""
    is_valid: bool
    schema_version: str
    issues: List[ValidationIssue]
    compatibility_info: Optional[Dict[str, Any]] = None
    
    @property
    def has_errors(self) -> bool:
        """Check if result has any error-level issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        """Check if result has any warning-level issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)


class SchemaRegistry:
    """Registry of all rpax artifact schemas with versioning support."""
    
    def __init__(self):
        self.schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.schema_dir = Path(__file__).parent / "schemas"
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all schema files from the schemas directory."""
        if not self.schema_dir.exists():
            return
        
        for schema_file in self.schema_dir.glob("*.schema.json"):
            try:
                with open(schema_file, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                
                # Extract artifact type and version from filename
                # Format: {artifact-type}.v{version}.schema.json
                filename = schema_file.stem.replace('.schema', '')
                if '.v' in filename:
                    artifact_type, version = filename.split('.v', 1)
                else:
                    # Legacy format without version
                    artifact_type = filename
                    version = "1.0.0"
                
                if artifact_type not in self.schemas:
                    self.schemas[artifact_type] = {}
                
                self.schemas[artifact_type][version] = schema_data
                
            except Exception as e:
                print(f"Warning: Failed to load schema {schema_file}: {e}")
    
    def get_schema(self, artifact_type: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get schema for artifact type and version."""
        if artifact_type not in self.schemas:
            return None
        
        if version is None:
            # Return latest version
            versions = sorted([SchemaVersion(v) for v in self.schemas[artifact_type].keys()])
            if not versions:
                return None
            latest_version = str(versions[-1])
            return self.schemas[artifact_type][latest_version]
        
        return self.schemas[artifact_type].get(version)
    
    def get_available_versions(self, artifact_type: str) -> List[str]:
        """Get all available versions for an artifact type."""
        if artifact_type not in self.schemas:
            return []
        return sorted(self.schemas[artifact_type].keys(), key=lambda v: SchemaVersion(v))
    
    def get_latest_version(self, artifact_type: str) -> Optional[str]:
        """Get the latest version for an artifact type."""
        versions = self.get_available_versions(artifact_type)
        return versions[-1] if versions else None


class ArtifactValidator:
    """Validates rpax artifacts against versioned schemas."""
    
    def __init__(self):
        self.registry = SchemaRegistry()
    
    def validate_artifact(self, artifact_data: Dict[str, Any], 
                         artifact_type: Optional[str] = None) -> ValidationResult:
        """Validate an artifact against its schema."""
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
        
        # Load appropriate schema
        schema = self.registry.get_schema(artifact_type, schema_version)
        if schema is None:
            # Try to find compatible schema
            available_versions = self.registry.get_available_versions(artifact_type)
            if not available_versions:
                return ValidationResult(
                    is_valid=False,
                    schema_version=schema_version,
                    issues=[ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"No schemas available for artifact type '{artifact_type}'",
                        "$"
                    )]
                )
            
            # Find best compatible schema
            target_version = SchemaVersion(schema_version)
            compatible_schema = None
            compatible_version = None
            
            for version_str in available_versions:
                version = SchemaVersion(version_str)
                if version.is_compatible_with(target_version):
                    compatible_schema = self.registry.get_schema(artifact_type, version_str)
                    compatible_version = version_str
            
            if compatible_schema is None:
                return ValidationResult(
                    is_valid=False,
                    schema_version=schema_version,
                    issues=[ValidationIssue(
                        ValidationSeverity.ERROR,
                        f"No compatible schema found for {artifact_type} v{schema_version}",
                        "$"
                    )]
                )
            
            schema = compatible_schema
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                f"Using compatible schema v{compatible_version} for v{schema_version}",
                "$"
            ))
        
        # Validate against schema
        try:
            jsonschema.validate(artifact_data, schema)
            
            # Additional validation checks
            additional_issues = self._validate_business_rules(artifact_data, artifact_type, schema_version)
            issues.extend(additional_issues)
            
            return ValidationResult(
                is_valid=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
                schema_version=schema_version,
                issues=issues
            )
            
        except jsonschema.ValidationError as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                e.message,
                self._format_json_path(e.absolute_path),
                self._format_json_path(e.schema_path)
            ))
            
            return ValidationResult(
                is_valid=False,
                schema_version=schema_version,
                issues=issues
            )
    
    def _infer_artifact_type(self, artifact_data: Dict[str, Any]) -> Optional[str]:
        """Infer artifact type from data structure."""
        # Look for distinctive fields that identify artifact types
        if "activities" in artifact_data and "totalActivities" in artifact_data:
            return "activity-instances"
        elif "workflows" in artifact_data and "project" in artifact_data:
            return "manifest"  
        elif "invocations" in artifact_data:
            return "invocations"
        
        return None
    
    def _validate_business_rules(self, artifact_data: Dict[str, Any], 
                                artifact_type: str, schema_version: str) -> List[ValidationIssue]:
        """Validate business logic rules beyond schema validation."""
        issues = []
        
        if artifact_type == "activity-instances":
            issues.extend(self._validate_activity_instances_rules(artifact_data, schema_version))
        
        return issues
    
    def _validate_activity_instances_rules(self, data: Dict[str, Any], 
                                         schema_version: str) -> List[ValidationIssue]:
        """Validate activity instances specific business rules."""
        issues = []
        
        activities = data.get("activities", [])
        total_activities = data.get("totalActivities", 0)
        
        # Check activity count consistency
        if len(activities) != total_activities:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                f"Activity count mismatch: declared {total_activities}, found {len(activities)}",
                "$.totalActivities"
            ))
        
        # Check activity ID uniqueness
        activity_ids = set()
        for i, activity in enumerate(activities):
            activity_id = activity.get("activity_id", "")
            if activity_id in activity_ids:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    f"Duplicate activity ID: {activity_id}",
                    f"$.activities[{i}].activity_id"
                ))
            activity_ids.add(activity_id)
        
        # Check parent-child relationships
        for i, activity in enumerate(activities):
            parent_id = activity.get("parent_activity_id")
            if parent_id and parent_id not in activity_ids:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    f"Parent activity not found: {parent_id}",
                    f"$.activities[{i}].parent_activity_id"
                ))
        
        # Schema version specific validations
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
        
        return issues
    
    def _format_json_path(self, path) -> str:
        """Format JSONSchema path as JSONPath."""
        if not path:
            return "$"
        
        parts = []
        for part in path:
            if isinstance(part, int):
                parts.append(f"[{part}]")
            else:
                parts.append(f".{part}")
        
        return "$" + "".join(parts)
    
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
        
        validator = ArtifactValidator()
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