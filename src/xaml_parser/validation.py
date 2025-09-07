"""Output validation for strict JSON schema compliance.

This module provides validation functions to ensure parser output
conforms to strict JSON schemas, enabling reliable data lake integration.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import WorkflowContent, ParseResult, ParseDiagnostics


class ValidationError(Exception):
    """Raised when output validation fails."""
    
    def __init__(self, message: str, field_path: str = "", schema_violations: List[str] = None):
        self.field_path = field_path
        self.schema_violations = schema_violations or []
        super().__init__(message)


class OutputValidator:
    """Validates parser output against JSON schemas."""
    
    def __init__(self, schemas_dir: Optional[Path] = None):
        """Initialize validator with schema directory.
        
        Args:
            schemas_dir: Directory containing JSON schemas
        """
        if schemas_dir is None:
            schemas_dir = Path(__file__).parent / "schemas"
        self.schemas_dir = schemas_dir
        self._schemas_cache = {}
    
    def validate_parse_result(self, result: ParseResult) -> List[str]:
        """Validate complete parse result against schema.
        
        Args:
            result: Parse result to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Basic structure validation
        if not isinstance(result.success, bool):
            errors.append("ParseResult.success must be boolean")
        
        if not isinstance(result.errors, list):
            errors.append("ParseResult.errors must be list")
        elif not all(isinstance(e, str) and len(e.strip()) > 0 for e in result.errors):
            errors.append("ParseResult.errors must contain non-empty strings")
        
        if not isinstance(result.warnings, list):
            errors.append("ParseResult.warnings must be list")
        elif not all(isinstance(w, str) and len(w.strip()) > 0 for w in result.warnings):
            errors.append("ParseResult.warnings must contain non-empty strings")
        
        if not isinstance(result.parse_time_ms, (int, float)) or result.parse_time_ms < 0:
            errors.append("ParseResult.parse_time_ms must be non-negative number")
        
        # Validate content if present
        if result.content is not None:
            content_errors = self.validate_workflow_content(result.content)
            errors.extend([f"content.{err}" for err in content_errors])
        
        # Validate diagnostics if present
        if result.diagnostics is not None:
            diag_errors = self.validate_diagnostics(result.diagnostics)
            errors.extend([f"diagnostics.{err}" for err in diag_errors])
        
        # Validate config
        if result.config_used:
            config_errors = self.validate_config(result.config_used)
            errors.extend([f"config_used.{err}" for err in config_errors])
        
        return errors
    
    def validate_workflow_content(self, content: WorkflowContent) -> List[str]:
        """Validate workflow content structure.
        
        Args:
            content: Workflow content to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate required fields
        if not isinstance(content.arguments, list):
            errors.append("arguments must be list")
        else:
            for i, arg in enumerate(content.arguments):
                arg_errors = self._validate_argument(arg)
                errors.extend([f"arguments[{i}].{err}" for err in arg_errors])
        
        if not isinstance(content.variables, list):
            errors.append("variables must be list")
        else:
            for i, var in enumerate(content.variables):
                var_errors = self._validate_variable(var)
                errors.extend([f"variables[{i}].{err}" for err in var_errors])
        
        if not isinstance(content.activities, list):
            errors.append("activities must be list")
        else:
            activity_ids = set()
            for i, activity in enumerate(content.activities):
                act_errors = self._validate_activity(activity, activity_ids)
                errors.extend([f"activities[{i}].{err}" for err in act_errors])
        
        # Validate expression language
        if content.expression_language not in ["VisualBasic", "CSharp"]:
            errors.append("expression_language must be 'VisualBasic' or 'CSharp'")
        
        # Validate counts
        if not isinstance(content.total_activities, int) or content.total_activities < 0:
            errors.append("total_activities must be non-negative integer")
        elif content.total_activities != len(content.activities):
            errors.append(f"total_activities ({content.total_activities}) != len(activities) ({len(content.activities)})")
        
        if not isinstance(content.total_arguments, int) or content.total_arguments < 0:
            errors.append("total_arguments must be non-negative integer")
        elif content.total_arguments != len(content.arguments):
            errors.append(f"total_arguments ({content.total_arguments}) != len(arguments) ({len(content.arguments)})")
        
        if not isinstance(content.total_variables, int) or content.total_variables < 0:
            errors.append("total_variables must be non-negative integer")
        elif content.total_variables != len(content.variables):
            errors.append(f"total_variables ({content.total_variables}) != len(variables) ({len(content.variables)})")
        
        return errors
    
    def validate_diagnostics(self, diagnostics: ParseDiagnostics) -> List[str]:
        """Validate diagnostics structure.
        
        Args:
            diagnostics: Diagnostics to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate integer fields
        integer_fields = [
            'total_elements_processed', 'activities_found', 'arguments_found',
            'variables_found', 'annotations_found', 'expressions_found',
            'namespaces_detected', 'skipped_elements', 'xml_depth', 'file_size_bytes'
        ]
        
        for field in integer_fields:
            value = getattr(diagnostics, field, None)
            if not isinstance(value, int) or value < 0:
                errors.append(f"{field} must be non-negative integer")
        
        # Validate processing steps
        if not isinstance(diagnostics.processing_steps, list):
            errors.append("processing_steps must be list")
        elif not all(isinstance(step, str) and len(step.strip()) > 0 for step in diagnostics.processing_steps):
            errors.append("processing_steps must contain non-empty strings")
        
        # Validate performance metrics
        if not isinstance(diagnostics.performance_metrics, dict):
            errors.append("performance_metrics must be dict")
        else:
            for key, value in diagnostics.performance_metrics.items():
                if not key.endswith('_ms'):
                    errors.append(f"performance_metrics key '{key}' must end with '_ms'")
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"performance_metrics['{key}'] must be non-negative number")
        
        return errors
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate parser configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Required boolean fields
        bool_fields = [
            'extract_arguments', 'extract_variables', 'extract_activities',
            'extract_expressions', 'extract_viewstate', 'extract_namespaces',
            'extract_assembly_references', 'preserve_raw_metadata', 'strict_mode'
        ]
        
        for field in bool_fields:
            if field in config and not isinstance(config[field], bool):
                errors.append(f"{field} must be boolean")
        
        # Max depth validation
        if 'max_depth' in config:
            if not isinstance(config['max_depth'], int) or config['max_depth'] < 1:
                errors.append("max_depth must be positive integer")
        
        # Expression language validation
        if 'expression_language' in config:
            if config['expression_language'] not in ['VisualBasic', 'CSharp']:
                errors.append("expression_language must be 'VisualBasic' or 'CSharp'")
        
        return errors
    
    def _validate_argument(self, arg: Any) -> List[str]:
        """Validate single workflow argument."""
        errors = []
        
        if not hasattr(arg, 'name') or not isinstance(arg.name, str) or len(arg.name.strip()) == 0:
            errors.append("name must be non-empty string")
        
        if not hasattr(arg, 'type') or not isinstance(arg.type, str) or len(arg.type.strip()) == 0:
            errors.append("type must be non-empty string")
        
        if not hasattr(arg, 'direction') or arg.direction not in ['in', 'out', 'inout']:
            errors.append("direction must be 'in', 'out', or 'inout'")
        
        return errors
    
    def _validate_variable(self, var: Any) -> List[str]:
        """Validate single workflow variable."""
        errors = []
        
        if not hasattr(var, 'name') or not isinstance(var.name, str) or len(var.name.strip()) == 0:
            errors.append("name must be non-empty string")
        
        if not hasattr(var, 'type') or not isinstance(var.type, str) or len(var.type.strip()) == 0:
            errors.append("type must be non-empty string")
        
        if not hasattr(var, 'scope') or not isinstance(var.scope, str) or len(var.scope.strip()) == 0:
            errors.append("scope must be non-empty string")
        
        return errors
    
    def _validate_activity(self, activity: Any, activity_ids: set) -> List[str]:
        """Validate single activity."""
        errors = []
        
        if not hasattr(activity, 'tag') or not isinstance(activity.tag, str) or len(activity.tag.strip()) == 0:
            errors.append("tag must be non-empty string")
        
        if not hasattr(activity, 'activity_id'):
            errors.append("activity_id is required")
        else:
            activity_id = activity.activity_id
            if not isinstance(activity_id, str) or not re.match(r'^activity_\d+$', activity_id):
                errors.append("activity_id must match pattern 'activity_\\d+'")
            elif activity_id in activity_ids:
                errors.append(f"duplicate activity_id '{activity_id}'")
            else:
                activity_ids.add(activity_id)
        
        # Validate required dict fields
        dict_fields = ['visible_attributes', 'invisible_attributes', 'configuration']
        for field in dict_fields:
            if not hasattr(activity, field) or not isinstance(getattr(activity, field), dict):
                errors.append(f"{field} must be dict")
        
        # Validate required list fields
        list_fields = ['variables', 'expressions', 'child_activities']
        for field in list_fields:
            if not hasattr(activity, field) or not isinstance(getattr(activity, field), list):
                errors.append(f"{field} must be list")
        
        # Validate depth level
        if not hasattr(activity, 'depth_level') or not isinstance(activity.depth_level, int) or activity.depth_level < 0:
            errors.append("depth_level must be non-negative integer")
        
        # Validate child activity IDs
        if hasattr(activity, 'child_activities'):
            for i, child_id in enumerate(activity.child_activities):
                if not isinstance(child_id, str) or not re.match(r'^activity_\d+$', child_id):
                    errors.append(f"child_activities[{i}] must match pattern 'activity_\\d+'")
        
        return errors
    
    def validate_and_raise(self, result: ParseResult) -> None:
        """Validate parse result and raise ValidationError if invalid.
        
        Args:
            result: Parse result to validate
            
        Raises:
            ValidationError: If validation fails
        """
        errors = self.validate_parse_result(result)
        if errors:
            raise ValidationError(
                f"Parse result validation failed with {len(errors)} errors",
                schema_violations=errors
            )


# Default validator instance
_default_validator = None

def get_validator() -> OutputValidator:
    """Get default validator instance."""
    global _default_validator
    if _default_validator is None:
        _default_validator = OutputValidator()
    return _default_validator


def validate_output(result: ParseResult, strict: bool = True) -> List[str]:
    """Validate parser output with optional strict mode.
    
    Args:
        result: Parse result to validate
        strict: If True, raises exception on validation failure
        
    Returns:
        List of validation errors (empty if valid)
        
    Raises:
        ValidationError: If strict=True and validation fails
    """
    validator = get_validator()
    errors = validator.validate_parse_result(result)
    
    if strict and errors:
        raise ValidationError(
            f"Output validation failed with {len(errors)} errors",
            schema_violations=errors
        )
    
    return errors