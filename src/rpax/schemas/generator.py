"""JSON Schema generation from Pydantic models for rpax artifacts."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..models.manifest import ProjectManifest
from ..models.workflow import Workflow, WorkflowIndex

logger = logging.getLogger(__name__)


class SchemaGenerator:
    """Generates JSON schemas from Pydantic models for artifact validation."""

    def __init__(self):
        self.schemas: dict[str, dict[str, Any]] = {}

    def generate_all_schemas(self) -> dict[str, dict[str, Any]]:
        """Generate JSON schemas for all rpax artifact types.
        
        Returns:
            Dictionary mapping artifact names to JSON schemas
        """
        logger.info("Generating JSON schemas for rpax artifacts")

        # Generate schema for each artifact type
        self.schemas = {
            "manifest": self._generate_manifest_schema(),
            "workflow_index": self._generate_workflow_index_schema(),
            "workflow": self._generate_workflow_schema(),
            "invocation": self._generate_invocation_schema(),
        }

        logger.info(f"Generated {len(self.schemas)} JSON schemas")
        return self.schemas

    def save_schemas(self, output_dir: Path) -> dict[str, Path]:
        """Save generated schemas to files.
        
        Args:
            output_dir: Directory to save schema files
            
        Returns:
            Dictionary mapping schema names to file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        schema_files = {}

        for schema_name, schema in self.schemas.items():
            schema_file = output_dir / f"{schema_name}.schema.json"

            with open(schema_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)

            schema_files[schema_name] = schema_file
            logger.debug(f"Saved schema: {schema_file}")

        return schema_files

    def _generate_manifest_schema(self) -> dict[str, Any]:
        """Generate JSON schema for manifest.json artifacts."""
        return self._model_to_schema(
            ProjectManifest,
            "rpax-manifest-v1",
            "JSON Schema for rpax manifest.json artifacts",
            "https://github.com/rpapub/rpax/schemas/manifest.v1.schema.json"
        )

    def _generate_workflow_index_schema(self) -> dict[str, Any]:
        """Generate JSON schema for workflows.index.json artifacts."""
        return self._model_to_schema(
            WorkflowIndex,
            "rpax-workflow-index-v1",
            "JSON Schema for rpax workflows.index.json artifacts",
            "https://github.com/rpapub/rpax/schemas/workflow-index.v1.schema.json"
        )

    def _generate_workflow_schema(self) -> dict[str, Any]:
        """Generate JSON schema for individual workflow objects."""
        return self._model_to_schema(
            Workflow,
            "rpax-workflow-v1",
            "JSON Schema for rpax individual workflow objects",
            "https://github.com/rpapub/rpax/schemas/workflow.v1.schema.json"
        )

    def _generate_invocation_schema(self) -> dict[str, Any]:
        """Generate JSON schema for invocation JSONL records."""
        # Define invocation schema manually since it's not a Pydantic model yet
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://github.com/rpapub/rpax/schemas/invocation.v1.schema.json",
            "title": "rpax-invocation-v1",
            "description": "JSON Schema for rpax invocation JSONL records",
            "type": "object",
            "required": ["kind", "from", "to"],
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["invoke", "invoke-missing", "invoke-dynamic"],
                    "description": "Type of workflow invocation"
                },
                "from": {
                    "type": "string",
                    "description": "Source workflow ID (composite format)"
                },
                "to": {
                    "type": "string",
                    "description": "Target workflow ID or reference"
                },
                "arguments": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Arguments passed to the workflow"
                },
                "activityName": {
                    "type": ["string", "null"],
                    "description": "Display name of the invoking activity"
                },
                "targetPath": {
                    "type": "string",
                    "description": "Original target path from XAML"
                },
                "lineNumber": {
                    "type": ["integer", "null"],
                    "description": "Line number in source XAML (if available)"
                }
            },
            "additionalProperties": False
        }

    def _model_to_schema(
        self,
        model_class: type[BaseModel],
        title: str,
        description: str,
        schema_id: str
    ) -> dict[str, Any]:
        """Convert Pydantic model to JSON schema.
        
        Args:
            model_class: Pydantic model class
            title: Schema title
            description: Schema description  
            schema_id: Schema $id URI
            
        Returns:
            JSON schema dictionary
        """
        try:
            # Generate schema using Pydantic v2 method
            schema = model_class.model_json_schema()

            # Enhance with metadata
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
            schema["$id"] = schema_id
            schema["title"] = title
            schema["description"] = description

            # Add version information
            schema["version"] = "1.0"

            return schema

        except Exception as e:
            logger.error(f"Failed to generate schema for {model_class.__name__}: {e}")
            # Return minimal schema as fallback
            return {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": schema_id,
                "title": title,
                "description": f"{description} (fallback schema due to generation error)",
                "type": "object",
                "additionalProperties": True
            }

    def get_schema_for_artifact(self, artifact_type: str) -> dict[str, Any] | None:
        """Get JSON schema for a specific artifact type.
        
        Args:
            artifact_type: Type of artifact ('manifest', 'workflow_index', etc.)
            
        Returns:
            JSON schema or None if not found
        """
        return self.schemas.get(artifact_type)

    def validate_schema_compliance(self) -> list[str]:
        """Validate that generated schemas are compliant with JSON Schema spec.
        
        Returns:
            List of validation errors (empty if all schemas are valid)
        """
        errors = []

        try:
            import jsonschema

            for schema_name, schema in self.schemas.items():
                try:
                    # Validate schema against JSON Schema meta-schema
                    jsonschema.Draft202012Validator.check_schema(schema)
                    logger.debug(f"Schema {schema_name} is valid")
                except Exception as e:
                    error_msg = f"Schema {schema_name} is invalid: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        except ImportError:
            logger.warning("jsonschema package not available for schema validation")
            errors.append("jsonschema package required for schema validation")

        return errors
