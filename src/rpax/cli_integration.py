"""Integrated CLI pipeline with activity resources and error collection.

Provides unified artifact generation pipeline that integrates:
- ActivityResourceManager for activity-centric resources
- ErrorCollector for run-scoped lake-level error handling  
- URI resolver for navigation
- Both legacy and V0 schema support
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from rpax import __version__
from rpax.artifacts import ArtifactGenerator  
from rpax.config import RpaxConfig
from rpax.diagnostics import ErrorCollector, ErrorContext, ErrorSeverity, create_error_collector
from rpax.output.base import ParsedProjectData
from rpax.output.v0 import V0LakeGenerator
from rpax.resources import ActivityResourceManager

logger = logging.getLogger(__name__)


class IntegratedArtifactPipeline:
    """Unified pipeline integrating activity resources and error collection."""
    
    def __init__(self, config: RpaxConfig, lake_root: Path, command: str):
        """Initialize integrated pipeline.
        
        Args:
            config: rpax configuration
            lake_root: Lake root directory
            command: CLI command being executed
        """
        self.config = config
        self.lake_root = lake_root
        self.output_dir = Path(config.output.dir)
        
        # Initialize integrated components
        self.error_collector = create_error_collector(lake_root, command)
        self.activity_resource_manager = ActivityResourceManager(config)
    
    def generate_project_artifacts(
        self,
        data: ParsedProjectData,
        schema_version: str = "legacy"
    ) -> Dict[str, Path]:
        """Generate all artifacts with integrated components.
        
        Args:
            data: Parsed project data
            schema_version: Schema version ("legacy" or "v0")
            
        Returns:
            Dictionary mapping artifact names to generated file paths
        """
        artifacts = {}
        
        try:
            # Generate core artifacts based on schema version
            if schema_version == "v0":
                core_artifacts = self._generate_v0_artifacts(data)
            else:
                core_artifacts = self._generate_legacy_artifacts(data)
            
            artifacts.update(core_artifacts)
            
            # Generate integrated activity resources
            if self.config.output.generate_activities:
                try:
                    activity_artifacts = self._generate_activity_resources(data, schema_version)
                    artifacts.update(activity_artifacts)
                    
                    logger.info(f"Generated activity resources: {len(activity_artifacts)} artifacts")
                    
                except Exception as e:
                    self.error_collector.collect_error(
                        e,
                        ErrorContext(
                            operation="generate_activity_resources",
                            component="ActivityResourceManager",
                            project_slug=data.project_slug,
                            project_root=str(data.project_root)
                        ),
                        ErrorSeverity.WARNING
                    )
                    logger.warning(f"Failed to generate activity resources: {e}")
            
        except Exception as e:
            # Collect critical errors for lake-level diagnostics
            self.error_collector.collect_error(
                e,
                ErrorContext(
                    operation="generate_project_artifacts",
                    component="IntegratedArtifactPipeline",
                    project_slug=data.project_slug,
                    project_root=str(data.project_root)
                ),
                ErrorSeverity.CRITICAL
            )
            raise
        
        return artifacts
    
    def _generate_v0_artifacts(self, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate V0 schema artifacts."""
        try:
            generator = V0LakeGenerator(self.output_dir)
            artifacts = generator.generate(data)
            
            logger.debug(f"Generated V0 artifacts: {len(artifacts)} files")
            return artifacts
            
        except Exception as e:
            self.error_collector.collect_error(
                e,
                ErrorContext(
                    operation="generate_v0_artifacts",
                    component="V0LakeGenerator",
                    project_slug=data.project_slug
                )
            )
            raise
    
    def _generate_legacy_artifacts(self, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate legacy schema artifacts."""
        try:
            generator = ArtifactGenerator(self.config, self.output_dir)
            artifacts = generator.generate_all_artifacts(
                data.project, data.workflow_index, data.project_root
            )
            
            logger.debug(f"Generated legacy artifacts: {len(artifacts)} files")
            return artifacts
            
        except Exception as e:
            self.error_collector.collect_error(
                e,
                ErrorContext(
                    operation="generate_legacy_artifacts",
                    component="ArtifactGenerator",
                    project_slug=data.project_slug
                )
            )
            raise
    
    def _generate_activity_resources(
        self,
        data: ParsedProjectData,
        schema_version: str
    ) -> Dict[str, Path]:
        """Generate activity resources integrated with pipeline."""
        
        if schema_version == "v0":
            # Generate V0 activity resources with progressive disclosure
            return self.activity_resource_manager.generate_v0_activity_resources(
                data.workflow_index,
                data.project_root,
                data.project_slug,
                self.output_dir / data.project_slug / "v0"
            )
        else:
            # Generate legacy activity resources
            return self.activity_resource_manager.generate_activity_resources(
                data.workflow_index,
                data.project_root,
                data.project_slug,
                self.output_dir / data.project_slug
            )
    
    def finalize_run(self) -> Optional[Path]:
        """Flush errors and finalize run-scoped operations.
        
        Returns:
            Path to error summary file, or None if no errors
        """
        return self.error_collector.flush_to_filesystem()
    
    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return self.error_collector.has_errors()
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors have been collected."""
        return self.error_collector.has_critical_errors()
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get error counts by severity."""
        return self.error_collector.get_error_counts()


def create_integrated_pipeline(
    config: RpaxConfig,
    lake_root: Path,
    command: str
) -> IntegratedArtifactPipeline:
    """Create integrated artifact pipeline.
    
    Args:
        config: rpax configuration
        lake_root: Lake root directory  
        command: CLI command being executed
        
    Returns:
        IntegratedArtifactPipeline instance
    """
    return IntegratedArtifactPipeline(config, lake_root, command)


# Example of how to integrate with CLI parse command
def integrated_parse_project(
    project_path: Path,
    config: RpaxConfig,
    schema_version: str = "legacy"
) -> Dict[str, Path]:
    """Integrated project parsing with error collection and activity resources.
    
    Args:
        project_path: Path to UiPath project
        config: rpax configuration
        schema_version: Schema version to generate
        
    Returns:
        Dictionary of generated artifacts
        
    Raises:
        Exception: If critical errors occur during processing
    """
    from rpax.parser.project import ProjectParser
    from rpax.parser.workflow_discovery import create_workflow_discovery
    from rpax.output.base import ParsedProjectData
    from slugify import slugify
    
    # Initialize integrated pipeline
    lake_root = Path(config.output.dir).parent
    pipeline = create_integrated_pipeline(config, lake_root, "parse")
    
    try:
        # Parse project data
        project = ProjectParser.parse_project_from_dir(project_path)
        
        # Discover workflows
        discovery = create_workflow_discovery(
            project_path,
            exclude_patterns=config.scan.exclude,
            include_coded_workflows=(schema_version == "v0" and config.parser.include_coded_workflows)
        )
        workflow_index = discovery.discover_workflows()
        
        # Create parsed data structure
        project_slug = slugify(project.name)
        parsed_data = ParsedProjectData(
            project=project,
            workflow_index=workflow_index,
            project_root=project_path,
            project_slug=project_slug,
            timestamp=datetime.now()
        )
        
        # Generate all artifacts with integration
        artifacts = pipeline.generate_project_artifacts(parsed_data, schema_version)
        
        return artifacts
        
    except Exception as e:
        # Error already collected by pipeline
        raise
        
    finally:
        # Always flush errors at end of run
        error_file = pipeline.finalize_run()
        if pipeline.has_errors():
            logger.info(f"Errors logged to: {error_file}")
            
            # Show error summary
            error_summary = pipeline.get_error_summary()
            if error_summary:
                logger.info(f"Error summary: {error_summary}")
        
        # Raise if critical errors occurred
        if pipeline.has_critical_errors():
            raise RuntimeError("Critical errors occurred during processing")