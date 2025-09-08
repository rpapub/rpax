"""V0 Schema Lake Generator.

Main generator for the v0/ experimental schema optimized for MCP consumption.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from rpax import __version__
from rpax.output.base import OutputGenerator, ParsedProjectData
from .manifest_builder import ManifestBuilder
from .entry_point_builder import EntryPointBuilder
from .detail_levels import DetailLevelExtractor
from .dependency_analysis import DependencyAnalysisGenerator

logger = logging.getLogger(__name__)


class V0LakeGenerator(OutputGenerator):
    """Generates v0/ experimental schema artifacts.
    
    Creates clean, MCP-optimized lake structure with:
    - Lake-level project discovery
    - Entry points with complete recursive structures  
    - Progressive disclosure (low/medium/high detail levels)
    - Pre-computed common queries
    - Support for .xaml and .cs workflows
    """
    
    @property
    def schema_version(self) -> str:
        return "v0"
    
    def generate(self, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate complete v0/ schema structure.
        
        Args:
            data: Parsed project data
            
        Returns:
            Dictionary mapping artifact names to generated file paths
        """
        logger.info(f"Generating v0/ schema for project: {data.project.name}")
        
        # Create project directory with v0 subdirectory
        project_dir = self.create_project_directory(data.project_slug)
        v0_dir = project_dir / "v0"
        v0_dir.mkdir(exist_ok=True)
        
        artifacts = {}
        
        # Generate _meta directory with versioning
        meta_artifacts = self._generate_meta_directory(project_dir, data)
        artifacts.update(meta_artifacts)
        
        # Generate manifest.json as central navigation hub
        manifest_file = self._generate_manifest(v0_dir, data)
        artifacts["manifest"] = manifest_file
        
        # Generate entry_points directory with recursive structures
        entry_point_artifacts = self._generate_entry_points(v0_dir, data)
        artifacts.update(entry_point_artifacts)
        
        # Generate call_graphs at three detail levels
        call_graph_artifacts = self._generate_call_graphs(v0_dir, data)
        artifacts.update(call_graph_artifacts)
        
        # Generate workflows directory with individual resources
        workflow_artifacts = self._generate_workflows(v0_dir, data)
        artifacts.update(workflow_artifacts)
        
        # Generate resources directory (config, packages, etc.)
        resource_artifacts = self._generate_resources(v0_dir, data)
        artifacts.update(resource_artifacts)
        
        # Generate dependency analysis with MCP classification
        dependency_artifacts = self._generate_dependency_analysis(v0_dir, data)
        artifacts.update(dependency_artifacts)
        
        # Create legacy directory with existing artifacts for compatibility
        legacy_artifacts = self._create_legacy_compatibility(project_dir, data)
        artifacts.update(legacy_artifacts)
        
        logger.info(f"Generated {len(artifacts)} v0/ artifacts")
        return artifacts
    
    def _generate_meta_directory(self, project_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate _meta directory with schema versioning."""
        meta_dir = project_dir / "_meta"
        meta_dir.mkdir(exist_ok=True)
        
        artifacts = {}
        
        # Schema version file
        schema_version_file = meta_dir / "schema_version.txt"
        schema_version_file.write_text("v0")
        artifacts["schema_version"] = schema_version_file
        
        # rpax version file
        rpax_version_file = meta_dir / "rpax_version.txt"
        rpax_version_file.write_text(__version__)
        artifacts["rpax_version"] = rpax_version_file
        
        return artifacts
    
    def _generate_manifest(self, v0_dir: Path, data: ParsedProjectData) -> Path:
        """Generate manifest.json as central navigation hub."""
        builder = ManifestBuilder()
        manifest_data = builder.build_v0_manifest(data)
        
        manifest_file = v0_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Generated manifest: {manifest_file}")
        return manifest_file
    
    def _generate_entry_points(self, v0_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate entry_points directory with complete recursive structures."""
        entry_points_dir = v0_dir / "entry_points"
        entry_points_dir.mkdir(exist_ok=True)
        
        builder = EntryPointBuilder(data)
        
        artifacts = {}
        
        # Generate index.json
        index_data = builder.build_entry_points_index()
        index_file = entry_points_dir / "index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        artifacts["entry_points_index"] = index_file
        
        # Generate non_test directory
        non_test_dir = entry_points_dir / "non_test"
        non_test_dir.mkdir(exist_ok=True)
        
        # Generate _all_medium.json (THE KEY FILE for common MCP query)
        all_medium_data = builder.build_all_non_test_medium()
        all_medium_file = non_test_dir / "_all_medium.json"
        with open(all_medium_file, "w", encoding="utf-8") as f:
            json.dump(all_medium_data, f, indent=2, ensure_ascii=False)
        artifacts["entry_points_all_medium"] = all_medium_file
        
        # Generate individual entry point files at different detail levels
        for entry_point in data.project.entry_points:
            if not builder.is_test_workflow(entry_point.file_path):
                # Medium detail
                medium_data = builder.build_entry_point_medium(entry_point.file_path)
                medium_file = non_test_dir / f"{Path(entry_point.file_path).stem}_medium.json"
                with open(medium_file, "w", encoding="utf-8") as f:
                    json.dump(medium_data, f, indent=2, ensure_ascii=False)
                artifacts[f"entry_point_{Path(entry_point.file_path).stem}_medium"] = medium_file
                
                # High detail  
                high_data = builder.build_entry_point_high(entry_point.file_path)
                high_file = non_test_dir / f"{Path(entry_point.file_path).stem}_high.json"
                with open(high_file, "w", encoding="utf-8") as f:
                    json.dump(high_data, f, indent=2, ensure_ascii=False)
                artifacts[f"entry_point_{Path(entry_point.file_path).stem}_high"] = high_file
        
        # Generate test directory
        test_dir = entry_points_dir / "test"
        test_dir.mkdir(exist_ok=True)
        
        # Generate _all_medium.json for test workflows (explicit + discovered)
        all_test_medium_data = builder.build_all_test_medium()
        if all_test_medium_data["entry_points"]:  # Only if there are test entry points
            all_test_medium_file = test_dir / "_all_medium.json"
            with open(all_test_medium_file, "w", encoding="utf-8") as f:
                json.dump(all_test_medium_data, f, indent=2, ensure_ascii=False)
            artifacts["entry_points_all_test_medium"] = all_test_medium_file
            
            # Also generate _all_high.json for complete test workflow analysis
            all_test_high_data = builder.build_all_test_high()
            all_test_high_file = test_dir / "_all_high.json"
            with open(all_test_high_file, "w", encoding="utf-8") as f:
                json.dump(all_test_high_data, f, indent=2, ensure_ascii=False)
            artifacts["entry_points_all_test_high"] = all_test_high_file
            
            # Generate individual test workflow files at different detail levels
            for test_workflow_path in builder.get_all_test_workflows():
                # Medium detail
                medium_data = builder.build_entry_point_medium(test_workflow_path)
                medium_file = test_dir / f"{Path(test_workflow_path).stem}_medium.json"
                with open(medium_file, "w", encoding="utf-8") as f:
                    json.dump(medium_data, f, indent=2, ensure_ascii=False)
                artifacts[f"test_entry_point_{Path(test_workflow_path).stem}_medium"] = medium_file
                
                # High detail  
                high_data = builder.build_entry_point_high(test_workflow_path)
                high_file = test_dir / f"{Path(test_workflow_path).stem}_high.json"
                with open(high_file, "w", encoding="utf-8") as f:
                    json.dump(high_data, f, indent=2, ensure_ascii=False)
                artifacts[f"test_entry_point_{Path(test_workflow_path).stem}_high"] = high_file
        
        logger.debug(f"Generated entry points: {len(artifacts)} files")
        return artifacts
    
    def _generate_call_graphs(self, v0_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate call graphs at three detail levels."""
        call_graphs_dir = v0_dir / "call_graphs"
        call_graphs_dir.mkdir(exist_ok=True)
        
        detail_extractor = DetailLevelExtractor(data)
        artifacts = {}
        
        # Low detail (overview)
        low_data = detail_extractor.extract_call_graph_low()
        low_file = call_graphs_dir / "project_low.json"
        with open(low_file, "w", encoding="utf-8") as f:
            json.dump(low_data, f, indent=2, ensure_ascii=False)
        artifacts["call_graph_low"] = low_file
        
        # Medium detail (most common)
        medium_data = detail_extractor.extract_call_graph_medium()
        medium_file = call_graphs_dir / "project_medium.json"
        with open(medium_file, "w", encoding="utf-8") as f:
            json.dump(medium_data, f, indent=2, ensure_ascii=False)
        artifacts["call_graph_medium"] = medium_file
        
        # High detail (complete)
        high_data = detail_extractor.extract_call_graph_high()
        high_file = call_graphs_dir / "project_high.json"
        with open(high_file, "w", encoding="utf-8") as f:
            json.dump(high_data, f, indent=2, ensure_ascii=False)
        artifacts["call_graph_high"] = high_file
        
        logger.debug(f"Generated call graphs: {len(artifacts)} files")
        return artifacts
    
    def _generate_workflows(self, v0_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate workflows directory with individual workflow resources."""
        workflows_dir = v0_dir / "workflows"
        workflows_dir.mkdir(exist_ok=True)
        
        artifacts = {}
        
        # Generate index.json
        detail_extractor = DetailLevelExtractor(data)
        workflow_index_data = detail_extractor.extract_workflow_index()
        index_file = workflows_dir / "index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(workflow_index_data, f, indent=2, ensure_ascii=False)
        artifacts["workflows_index"] = index_file
        
        # Generate individual workflow directories
        for workflow in data.workflow_index.workflows:
            workflow_path = Path(workflow.relative_path)
            workflow_name = workflow_path.stem
            
            # Create workflow directory (maintaining hierarchy)
            workflow_dir = workflows_dir / workflow_path.parent / workflow_name
            workflow_dir.mkdir(parents=True, exist_ok=True)
            
            # Medium detail (default)
            medium_data = detail_extractor.extract_workflow_medium(workflow)
            medium_file = workflow_dir / "medium.json"
            with open(medium_file, "w", encoding="utf-8") as f:
                json.dump(medium_data, f, indent=2, ensure_ascii=False)
            artifacts[f"workflow_{workflow_name}_medium"] = medium_file
            
            # High detail (on demand)
            high_data = detail_extractor.extract_workflow_high(workflow)
            high_file = workflow_dir / "high.json"
            with open(high_file, "w", encoding="utf-8") as f:
                json.dump(high_data, f, indent=2, ensure_ascii=False)
            artifacts[f"workflow_{workflow_name}_high"] = high_file
        
        logger.debug(f"Generated workflows: {len(artifacts)} files")
        return artifacts
    
    def _generate_resources(self, v0_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate resources directory with external references."""
        resources_dir = v0_dir / "resources"
        resources_dir.mkdir(exist_ok=True)
        
        detail_extractor = DetailLevelExtractor(data)
        artifacts = {}
        
        # Static invocations (literal workflow calls)
        static_data = detail_extractor.extract_static_invocations()
        static_file = resources_dir / "static_invocations.json"
        with open(static_file, "w", encoding="utf-8") as f:
            json.dump(static_data, f, indent=2, ensure_ascii=False)
        artifacts["static_invocations"] = static_file
        
        # Package usage analysis
        package_data = detail_extractor.extract_package_usage()
        package_file = resources_dir / "package_usage.json"
        with open(package_file, "w", encoding="utf-8") as f:
            json.dump(package_data, f, indent=2, ensure_ascii=False)
        artifacts["package_usage"] = package_file
        
        # Config references (if any found)
        config_data = detail_extractor.extract_config_references()
        if config_data["references"]:  # Only create if there are config references
            config_file = resources_dir / "config_references.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            artifacts["config_references"] = config_file
        
        logger.debug(f"Generated resources: {len(artifacts)} files")
        return artifacts
    
    def _generate_dependency_analysis(self, v0_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Generate dependency analysis artifacts with MCP classification support."""
        if not data.project.dependencies:
            logger.debug("No dependencies found, skipping dependency analysis")
            return {}
        
        # Initialize dependency analysis generator
        lake_root = self.output_dir.parent if hasattr(self, 'output_dir') else v0_dir.parent
        dep_generator = DependencyAnalysisGenerator(
            data.project,
            data.project_root,
            v0_dir,
            lake_root
        )
        
        # Generate dependency analysis artifacts
        dep_artifacts_data = dep_generator.generate_artifacts()
        
        # Write artifacts to filesystem
        artifacts = {}
        for artifact_name, artifact_data in dep_artifacts_data.items():
            artifact_path = v0_dir / artifact_name
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(artifact_data, f, indent=2, ensure_ascii=False)
            
            artifacts[f"dependency_{artifact_name.replace('/', '_').replace('.json', '')}"] = artifact_path
        
        logger.debug(f"Generated dependency analysis: {len(artifacts)} files")
        return artifacts
    
    def _create_legacy_compatibility(self, project_dir: Path, data: ParsedProjectData) -> Dict[str, Path]:
        """Create legacy directory for backward compatibility.
        
        NOTE: This doesn't regenerate legacy artifacts, just creates the directory
        structure. Legacy artifacts would be copied here by the calling code.
        """
        legacy_dir = project_dir / "legacy"
        legacy_dir.mkdir(exist_ok=True)
        
        # Create README explaining the legacy directory
        readme_content = f"""# Legacy Artifacts Directory

This directory contains artifacts generated using the legacy (pre-v0/) schema
for backward compatibility with existing tools and scripts.

Generated by rpax {__version__} on {datetime.now().isoformat()}
Schema version: legacy
Project: {data.project.name}

For new integrations, use the v0/ directory which provides:
- Entry points with complete recursive structures
- Progressive disclosure (low/medium/high detail levels)  
- Pre-computed common MCP queries
- Clean naming conventions
- Better performance for MCP clients

See docs/adr/ADR-032_v0-experimental-schema.md for details.
"""
        
        readme_file = legacy_dir / "README.md"
        readme_file.write_text(readme_content)
        
        return {"legacy_readme": readme_file}