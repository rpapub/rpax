"""Artifact validation against JSON schemas for rpax."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ValidationError:
    """Represents a schema validation error."""

    def __init__(self, path: str, message: str, schema_path: str = ""):
        self.path = path
        self.message = message
        self.schema_path = schema_path

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class ArtifactValidator:
    """Validates rpax artifacts against JSON schemas."""

    def __init__(self, schemas: dict[str, dict[str, Any]] | None = None):
        self.schemas = schemas or {}
        self.jsonschema_available = self._check_jsonschema_availability()

    def _check_jsonschema_availability(self) -> bool:
        """Check if jsonschema library is available."""
        try:
            import jsonschema
            return True
        except ImportError:
            logger.warning("jsonschema library not available - validation will be limited")
            return False

    def validate_artifact_file(self, artifact_path: Path, artifact_type: str) -> list[ValidationError]:
        """Validate an artifact file against its schema.
        
        Args:
            artifact_path: Path to artifact file
            artifact_type: Type of artifact ('manifest', 'workflow_index', etc.)
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if file exists
        if not artifact_path.exists():
            errors.append(ValidationError(str(artifact_path), "File does not exist"))
            return errors

        # Load artifact data
        try:
            with open(artifact_path, encoding="utf-8") as f:
                if artifact_path.suffix == ".jsonl":
                    # Handle JSONL files (like invocations.jsonl)
                    artifact_data = []
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            try:
                                artifact_data.append(json.loads(line))
                            except json.JSONDecodeError as e:
                                errors.append(ValidationError(
                                    f"{artifact_path}:line {line_num}",
                                    f"Invalid JSON: {e}"
                                ))
                else:
                    # Handle regular JSON files
                    artifact_data = json.load(f)
        except Exception as e:
            errors.append(ValidationError(str(artifact_path), f"Failed to load file: {e}"))
            return errors

        # Get schema for artifact type
        schema = self.schemas.get(artifact_type)
        if not schema:
            errors.append(ValidationError(str(artifact_path), f"No schema available for artifact type: {artifact_type}"))
            return errors

        # Validate against schema
        if self.jsonschema_available:
            schema_errors = self._validate_with_jsonschema(artifact_data, schema, artifact_type)
            errors.extend(schema_errors)
        else:
            # Basic validation without jsonschema
            basic_errors = self._basic_validation(artifact_data, artifact_type)
            errors.extend(basic_errors)

        return errors

    def validate_artifact_data(self, data: Any, artifact_type: str) -> list[ValidationError]:
        """Validate artifact data directly against schema.
        
        Args:
            data: Artifact data to validate
            artifact_type: Type of artifact
            
        Returns:
            List of validation errors
        """
        errors = []

        schema = self.schemas.get(artifact_type)
        if not schema:
            errors.append(ValidationError("data", f"No schema available for artifact type: {artifact_type}"))
            return errors

        if self.jsonschema_available:
            errors.extend(self._validate_with_jsonschema(data, schema, artifact_type))
        else:
            errors.extend(self._basic_validation(data, artifact_type))

        return errors

    def _validate_with_jsonschema(self, data: Any, schema: dict[str, Any], artifact_type: str) -> list[ValidationError]:
        """Validate using jsonschema library."""
        errors = []

        try:
            import jsonschema

            # Handle JSONL data (list of objects)
            if isinstance(data, list) and artifact_type == "invocation":
                # Validate each invocation record
                for i, record in enumerate(data):
                    try:
                        jsonschema.validate(record, schema)
                    except jsonschema.ValidationError as e:
                        errors.append(ValidationError(
                            f"record[{i}].{e.json_path}",
                            e.message
                        ))
                    except Exception as e:
                        errors.append(ValidationError(
                            f"record[{i}]",
                            f"Validation error: {e}"
                        ))
            else:
                # Validate single object
                try:
                    jsonschema.validate(data, schema)
                except jsonschema.ValidationError as e:
                    errors.append(ValidationError(
                        e.json_path or "root",
                        e.message
                    ))
                except Exception as e:
                    errors.append(ValidationError("root", f"Validation error: {e}"))

        except Exception as e:
            errors.append(ValidationError("validation", f"Schema validation failed: {e}"))

        return errors

    def _basic_validation(self, data: Any, artifact_type: str) -> list[ValidationError]:
        """Basic validation without jsonschema library."""
        errors = []

        if artifact_type == "manifest":
            errors.extend(self._validate_manifest_basic(data))
        elif artifact_type == "workflow_index":
            errors.extend(self._validate_workflow_index_basic(data))
        elif artifact_type == "invocation":
            errors.extend(self._validate_invocations_basic(data))

        return errors

    def _validate_manifest_basic(self, data: Any) -> list[ValidationError]:
        """Basic validation for manifest data."""
        errors = []

        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Manifest must be an object"))
            return errors

        # Check required fields
        required_fields = ["projectName", "rpaxVersion", "generatedAt"]
        for field in required_fields:
            if field not in data:
                errors.append(ValidationError(field, f"Required field missing: {field}"))

        # Check data types
        if "totalWorkflows" in data and not isinstance(data["totalWorkflows"], int):
            errors.append(ValidationError("totalWorkflows", "Must be an integer"))

        return errors

    def _validate_workflow_index_basic(self, data: Any) -> list[ValidationError]:
        """Basic validation for workflow index data."""
        errors = []

        if not isinstance(data, dict):
            errors.append(ValidationError("root", "Workflow index must be an object"))
            return errors

        # Check workflows array
        if "workflows" in data:
            if not isinstance(data["workflows"], list):
                errors.append(ValidationError("workflows", "Must be an array"))
            else:
                for i, workflow in enumerate(data["workflows"]):
                    if not isinstance(workflow, dict):
                        errors.append(ValidationError(f"workflows[{i}]", "Must be an object"))
                    elif "id" not in workflow:
                        errors.append(ValidationError(f"workflows[{i}].id", "Required field missing"))

        return errors

    def _validate_invocations_basic(self, data: Any) -> list[ValidationError]:
        """Basic validation for invocations data."""
        errors = []

        if not isinstance(data, list):
            errors.append(ValidationError("root", "Invocations must be an array"))
            return errors

        for i, invocation in enumerate(data):
            if not isinstance(invocation, dict):
                errors.append(ValidationError(f"[{i}]", "Must be an object"))
                continue

            # Check required fields
            required_fields = ["kind", "from", "to"]
            for field in required_fields:
                if field not in invocation:
                    errors.append(ValidationError(f"[{i}].{field}", f"Required field missing: {field}"))

            # Check kind enum
            if "kind" in invocation:
                valid_kinds = ["invoke", "invoke-missing", "invoke-dynamic"]
                if invocation["kind"] not in valid_kinds:
                    errors.append(ValidationError(
                        f"[{i}].kind",
                        f"Invalid kind: {invocation['kind']}. Must be one of: {', '.join(valid_kinds)}"
                    ))

        return errors

    def validate_all_artifacts(self, artifacts_dir: Path) -> dict[str, list[ValidationError]]:
        """Validate all artifacts in a directory.
        
        Args:
            artifacts_dir: Directory containing artifacts
            
        Returns:
            Dictionary mapping artifact names to validation errors
        """
        results = {}

        # Define artifact files and their types
        artifact_files = {
            "manifest": artifacts_dir / "manifest.json",
            "workflow_index": artifacts_dir / "workflows.index.json",
            "invocations": artifacts_dir / "invocations.jsonl"
        }

        for artifact_type, artifact_path in artifact_files.items():
            if artifact_path.exists():
                errors = self.validate_artifact_file(artifact_path, artifact_type)
                results[artifact_type] = errors

                if errors:
                    logger.warning(f"Validation errors in {artifact_path}: {len(errors)} issues found")
                else:
                    logger.info(f"Artifact {artifact_path} is valid")

        return results

    def has_validation_errors(self, results: dict[str, list[ValidationError]]) -> bool:
        """Check if any validation results contain errors.
        
        Args:
            results: Validation results from validate_all_artifacts
            
        Returns:
            True if any errors were found
        """
        return any(errors for errors in results.values())
