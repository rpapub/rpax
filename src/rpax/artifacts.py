"""Artifact generation for rpax outputs."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rpax import __version__
from rpax.config import RpaxConfig
from rpax.models.activity import (
    ActivityTree,
)
from rpax.models.manifest import ProjectManifest
from rpax.models.project import UiPathProject
from rpax.models.workflow import WorkflowIndex
from rpax.models.packages import ProjectPackageAnalysis, analyze_package_usage
from rpax.parser.xaml_analyzer import XamlAnalyzer
from rpax.parser.enhanced_xaml_analyzer import EnhancedXamlAnalyzer

logger = logging.getLogger(__name__)


class ArtifactGenerator:
    """Generates rpax artifacts from parsed project data."""

    def __init__(self, config: RpaxConfig, output_dir: Path | None = None):
        """Initialize artifact generator.
        
        Args:
            config: rpax configuration
            output_dir: Optional override for output directory
        """
        self.config = config
        self.output_dir = Path(output_dir or config.output.dir)
        self.timestamp = datetime.now(UTC).isoformat()

    def generate_all_artifacts(
        self,
        project: UiPathProject,
        workflow_index: WorkflowIndex,
        project_root: Path
    ) -> dict[str, Path]:
        """Generate all artifacts for a project.
        
        Args:
            project: Parsed UiPath project
            workflow_index: Discovered workflows
            project_root: Root directory of project
            
        Returns:
            Dict mapping artifact names to file paths
        """
        # Generate project slug for multi-project support
        project_json_path = project_root / "project.json"
        project_slug = project.generate_project_slug(project_json_path)

        # Create project-specific subdirectory
        project_dir = self.output_dir / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)

        # Store original output_dir and temporarily switch to project_dir
        original_output_dir = self.output_dir
        self.output_dir = project_dir

        artifacts = {}

        # Generate manifest.json
        manifest_file = self._generate_manifest(project, workflow_index, project_root)
        artifacts["manifest"] = manifest_file

        # Generate workflows.index.json
        index_file = self._generate_workflow_index(workflow_index)
        artifacts["workflow_index"] = index_file

        # Generate invocations.jsonl with actual XAML analysis
        invocations_file = self._generate_invocations_placeholder(workflow_index)
        artifacts["invocations"] = invocations_file

        # Generate call graph artifact (ISSUE-038 - first-class call graph)
        manifest_data = self._load_manifest_for_callgraph(manifest_file)
        call_graph_file = self._generate_call_graph_artifact(manifest_data, workflow_index, invocations_file)
        artifacts["call_graph"] = call_graph_file

        # Generate activities artifacts (according to ADR-009)
        if self.config.output.generate_activities:
            activities_artifacts = self._generate_activities_artifacts(workflow_index, project_root)
            artifacts.update(activities_artifacts)

        # Generate pseudocode artifacts (ISSUE-027)
        pseudocode_artifacts = self._generate_pseudocode_artifacts(workflow_index, project, project_root)
        artifacts.update(pseudocode_artifacts)

        # Generate expanded pseudocode artifacts (ISSUE-036, ISSUE-040)
        if self.config.pseudocode.generate_expanded:
            expanded_artifacts = self._generate_expanded_pseudocode_artifacts(
                call_graph_file, pseudocode_artifacts.get("pseudocode_index")
            )
            artifacts.update(expanded_artifacts)

        # Generate Object Repository artifacts for Library projects
        if project.project_type.lower() == "library":
            object_repository_artifacts = self._generate_object_repository_artifacts(project_root)
            artifacts.update(object_repository_artifacts)

        # Generate package analysis artifacts
        package_artifacts = self._generate_package_analysis_artifacts(project, workflow_index)
        artifacts.update(package_artifacts)

        # Restore original output directory
        self.output_dir = original_output_dir

        # Update projects.json index
        self._update_projects_index(project, project_slug, project_root, project_dir)

        return artifacts

    def _generate_manifest(
        self,
        project: UiPathProject,
        workflow_index: WorkflowIndex,
        project_root: Path
    ) -> Path:
        """Generate project manifest.json."""
        manifest = ProjectManifest(
            project_name=project.name,
            project_id=project.project_id,
            project_type=project.project_type,
            project_root=str(project_root),
            rpax_version=__version__,
            generated_at=self.timestamp,
            main_workflow=project.main,
            description=project.description,
            project_version=project.project_version,
            uipath_schema_version=project.uipath_schema_version,
            studio_version=project.studio_version,
            target_framework=project.target_framework,
            expression_language=project.expression_language,
            runtime_options=project.runtime_options,
            design_options=project.design_options,
            entry_points=project.entry_points,
            dependencies=project.dependencies,
            total_workflows=workflow_index.total_workflows,
            total_invocations=0,  # TODO: Calculate from invocation analysis
            parse_errors=workflow_index.failed_parses,
            scan_config=self._serialize_scan_config(),
            validation_config=self._serialize_validation_config()
        )

        manifest_file = self.output_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(by_alias=True), f, indent=2, ensure_ascii=False)

        return manifest_file

    def _generate_workflow_index(self, workflow_index: WorkflowIndex) -> Path:
        """Generate workflows.index.json."""
        index_file = self.output_dir / "workflows.index.json"

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(
                workflow_index.model_dump(by_alias=True),
                f,
                indent=2,
                ensure_ascii=False
            )

        return index_file

    def _generate_invocations_placeholder(self, workflow_index: WorkflowIndex) -> Path:
        """Generate invocations.jsonl file with actual XAML analysis."""
        invocations_file = self.output_dir / "invocations.jsonl"

        try:
            # Import XAML analyzer
            from rpax.parser.xaml_analyzer import XamlAnalyzer
            analyzer = XamlAnalyzer()

            # Determine project root from workflow index
            project_root = Path(workflow_index.project_root)

            # Analyze all workflows for invocations
            with open(invocations_file, "w", encoding="utf-8") as f:
                f.write(f"# Invocations JSONL file - generated {self.timestamp}\n")
                f.write("# Workflow invocations extracted from XAML analysis\n")

                invocation_count = 0

                # Use the passed workflow index to iterate over workflows
                for workflow in workflow_index.workflows:
                        workflow_path = Path(workflow.file_path)
                        if workflow_path.exists():
                            try:
                                invocations, arguments = analyzer.analyze_workflow(workflow_path)

                                # Write invocations as JSONL
                                for invocation in invocations:
                                    # Convert invocation to manifest ID format
                                    from_id = workflow.id

                                    # Try to resolve target workflow ID
                                    to_id = self._resolve_target_workflow_id(invocation.target_path, workflow_path, project_root, workflow_index)

                                    invocation_record = {
                                        "kind": invocation.kind,
                                        "from": from_id,
                                        "to": to_id,
                                        "arguments": invocation.arguments,
                                        "activityName": invocation.activity_name,
                                        "targetPath": invocation.target_path
                                    }

                                    f.write(json.dumps(invocation_record, ensure_ascii=False) + "\n")
                                    invocation_count += 1

                            except Exception as e:
                                logger.warning(f"Failed to analyze workflow {workflow_path}: {e}")

                logger.info(f"Generated {invocation_count} invocation records")

        except ImportError:
            # Fallback to placeholder if XAML analyzer not available
            with open(invocations_file, "w", encoding="utf-8") as f:
                f.write(f"# Invocations JSONL file - generated {self.timestamp}\n")
                f.write("# Placeholder: XAML analyzer not available\n")
                f.write("# Each line will contain a JSON object representing a workflow invocation\n")

        return invocations_file

    def _resolve_target_workflow_id(
        self, 
        target_path: str, 
        current_workflow_path: Path, 
        project_root: Path, 
        workflow_index: WorkflowIndex
    ) -> str:
        """Resolve target workflow path to workflow ID using proper workflow lookup."""
        try:
            # For dynamic invocations, return the expression as-is
            if any(indicator in target_path for indicator in ["{", "}", "[", "]", "Path.Combine", "+"]):
                return f"dynamic:{target_path}"

            # Normalize the target path to forward slashes for consistent comparison
            target_path_normalized = target_path.replace("\\", "/")

            # First, try direct lookup in workflow index by relative path
            for workflow in workflow_index.workflows:
                workflow_relative_path = workflow.relative_path
                
                # Check exact match
                if workflow_relative_path == target_path_normalized:
                    return workflow.id
                
                # Check if workflow file name matches (for project root workflows)
                if workflow_relative_path.endswith(f"/{target_path_normalized}") or workflow_relative_path == target_path_normalized:
                    return workflow.id

            # If direct lookup failed, try filesystem-based resolution
            current_dir = current_workflow_path.parent
            possible_paths = [
                project_root / target_path,  # From project root (most common for test workflows)
                current_dir / target_path,   # Relative to current workflow
                current_dir.parent / target_path,  # Relative to parent directory
            ]

            # Check if any of the possible paths exist and find matching workflow
            for possible_path in possible_paths:
                if possible_path.exists() and possible_path.is_file():
                    try:
                        # Calculate relative path from project root
                        relative_path = possible_path.relative_to(project_root)
                        relative_path_str = str(relative_path).replace("\\", "/")
                        
                        # Find the matching workflow in the index
                        for workflow in workflow_index.workflows:
                            if workflow.relative_path == relative_path_str:
                                return workflow.id
                    except ValueError:
                        # Path is outside project root
                        continue

            # File not found - return missing indicator
            return f"missing:{target_path}"

        except Exception as e:
            logger.debug(f"Failed to resolve target workflow {target_path}: {e}")
            return f"unknown:{target_path}"

    def _serialize_scan_config(self) -> dict[str, Any]:
        """Serialize scan configuration for manifest."""
        return {
            "exclude": self.config.scan.exclude,
            "followDynamic": self.config.scan.follow_dynamic,
            "maxDepth": self.config.scan.max_depth
        }

    def _serialize_validation_config(self) -> dict[str, Any]:
        """Serialize validation configuration for manifest."""
        return {
            "failOnMissing": self.config.validation.fail_on_missing,
            "failOnCycles": self.config.validation.fail_on_cycles,
            "warnOnDynamic": self.config.validation.warn_on_dynamic
        }

    def generate_summary_report(self, artifacts: dict[str, Path]) -> Path:
        """Generate a human-readable summary report."""
        if not self.config.output.summaries:
            return None

        summary_file = self.output_dir / "summary.md"

        # Read manifest for summary data
        with open(artifacts["manifest"], encoding="utf-8") as f:
            manifest_data = json.load(f)

        # Read workflow index for details
        with open(artifacts["workflow_index"], encoding="utf-8") as f:
            index_data = json.load(f)

        summary_content = self._build_summary_markdown(manifest_data, index_data)

        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary_content)

        return summary_file

    def _build_summary_markdown(self, manifest: dict[str, Any], index: dict[str, Any]) -> str:
        """Build summary markdown content."""
        lines = [
            "# rpax Analysis Summary",
            "",
            f"**Project**: {manifest.get('projectName', 'Unknown')}",
            f"**Type**: {manifest.get('projectType', 'Unknown').title()}",
            f"**Generated**: {manifest.get('generatedAt', 'Unknown')}",
            f"**rpax Version**: {manifest.get('rpaxVersion', 'Unknown')}",
            "",
            "## Project Overview",
            "",
            f"- **Main Workflow**: `{manifest.get('mainWorkflow', 'Unknown')}`",
            f"- **Studio Version**: {manifest.get('studioVersion', 'Unknown')}",
            f"- **Target Framework**: {manifest.get('targetFramework', 'Unknown')}",
            f"- **Expression Language**: {manifest.get('expressionLanguage', 'Unknown')}",
            "",
            "## Analysis Results",
            "",
            f"- **Total Workflows**: {manifest.get('totalWorkflows', 0)}",
            f"- **Parse Errors**: {manifest.get('parseErrors', 0)}",
            f"- **Success Rate**: {((manifest.get('totalWorkflows', 0) - manifest.get('parseErrors', 0)) / max(manifest.get('totalWorkflows', 1), 1) * 100):.1f}%",
            "",
            "## Dependencies",
            "",
        ]

        dependencies = manifest.get("dependencies", {})
        if dependencies:
            for dep, version in dependencies.items():
                lines.append(f"- `{dep}`: {version}")
        else:
            lines.append("- No dependencies found")

        lines.extend([
            "",
            "## Entry Points",
            "",
        ])

        entry_points = manifest.get("entryPoints", [])
        if entry_points:
            for ep in entry_points:
                lines.append(f"- `{ep.get('filePath', 'Unknown')}`")
                if ep.get("input"):
                    lines.append(f"  - Inputs: {len(ep['input'])}")
                if ep.get("output"):
                    lines.append(f"  - Outputs: {len(ep['output'])}")
        else:
            lines.append("- No entry points defined")

        lines.extend([
            "",
            "## Generated Artifacts",
            "",
            "- `manifest.json` - Project metadata and analysis summary",
            "- `workflows.index.json` - Complete workflow inventory",
            "- `invocations.jsonl` - Workflow invocation data (placeholder in v0.0.1)",
            "",
            "---",
            f"*Generated by [rpax](https://github.com/rpapub/rpax) v{manifest.get('rpaxVersion', 'Unknown')}*"
        ])

        return "\n".join(lines)

    def _generate_activities_artifacts(self, workflow_index: WorkflowIndex, project_root: Path) -> dict[str, Path]:
        """Generate activities artifacts according to ADR-009.
        
        Args:
            workflow_index: Discovered workflows
            project_root: Root directory of project
            
        Returns:
            Dict mapping artifact names to file paths
        """
        activities_artifacts = {}

        # Create activities directories
        activities_instances_dir = self.output_dir / "activities.instances"  # NEW: Activity instances directory
        activities_tree_dir = self.output_dir / "activities.tree"
        activities_cfg_dir = self.output_dir / "activities.cfg"
        activities_refs_dir = self.output_dir / "activities.refs"
        metrics_dir = self.output_dir / "metrics"
        paths_dir = self.output_dir / "paths"

        activities_instances_dir.mkdir(parents=True, exist_ok=True)  # NEW: Create instances directory
        activities_tree_dir.mkdir(parents=True, exist_ok=True)
        activities_cfg_dir.mkdir(parents=True, exist_ok=True)
        activities_refs_dir.mkdir(parents=True, exist_ok=True)
        metrics_dir.mkdir(parents=True, exist_ok=True)
        paths_dir.mkdir(parents=True, exist_ok=True)

        # Choose analyzer based on configuration
        if self.config.parser.use_enhanced:
            analyzer = EnhancedXamlAnalyzer()
            logger.info(f"Using enhanced XAML parser for {workflow_index.total_workflows} workflows")
        else:
            analyzer = XamlAnalyzer()
            logger.info(f"Using legacy XAML parser for {workflow_index.total_workflows} workflows")

        for workflow in workflow_index.workflows:
            try:
                workflow_path = project_root / workflow.relative_path
                workflow_id = workflow.relative_path.replace("\\", "/").replace(".xaml", "")

                logger.debug(f"Processing activities for {workflow_id}")

                # Extract activity tree
                activity_tree = analyzer.extract_activity_tree(workflow_path)
                if activity_tree:
                    # Generate activities.tree/<wfId>.json
                    tree_file = activities_tree_dir / f"{workflow_id}.json"
                    # Ensure parent directory exists for nested workflows
                    tree_file.parent.mkdir(parents=True, exist_ok=True)
                    tree_data = self._serialize_activity_tree(activity_tree)

                    with open(tree_file, "w", encoding="utf-8") as f:
                        json.dump(tree_data, f, indent=2)

                    activities_artifacts[f"activities_tree_{workflow_id}"] = tree_file

                # NEW: Generate activities.instances/<wfId>.json (ADR-009 ActivityInstance)
                instances_artifact = self._generate_activity_instances(workflow, workflow_path, workflow_id)
                if instances_artifact:
                    activities_artifacts[f"activities_instances_{workflow_id}"] = instances_artifact

                # Extract control flow
                control_flow = analyzer.extract_control_flow(workflow_path)
                if control_flow:
                    # Generate activities.cfg/<wfId>.jsonl
                    cfg_file = activities_cfg_dir / f"{workflow_id}.jsonl"
                    cfg_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(cfg_file, "w", encoding="utf-8") as f:
                        for edge in control_flow.edges:
                            edge_data = {
                                "from": edge.from_node_id,
                                "to": edge.to_node_id,
                                "type": edge.edge_type,
                                "condition": edge.condition
                            }
                            f.write(json.dumps(edge_data) + "\n")

                    activities_artifacts[f"activities_cfg_{workflow_id}"] = cfg_file

                # Extract resource references
                resources = analyzer.extract_resources(workflow_path)
                if resources:
                    # Generate activities.refs/<wfId>.json
                    refs_file = activities_refs_dir / f"{workflow_id}.json"
                    refs_file.parent.mkdir(parents=True, exist_ok=True)
                    refs_data = {
                        "workflowId": workflow_id,
                        "references": [
                            {
                                "type": ref.resource_type,
                                "name": ref.resource_name,
                                "value": ref.resource_value,
                                "nodeId": ref.node_id,
                                "property": ref.property_name,
                                "isDynamic": ref.is_dynamic,
                                "rawValue": ref.raw_value
                            } for ref in resources.references
                        ]
                    }

                    with open(refs_file, "w", encoding="utf-8") as f:
                        json.dump(refs_data, f, indent=2)

                    activities_artifacts[f"activities_refs_{workflow_id}"] = refs_file

                # Calculate and generate metrics
                if activity_tree:
                    metrics = analyzer.calculate_metrics(activity_tree)
                    metrics_file = metrics_dir / f"{workflow_id}.json"
                    metrics_file.parent.mkdir(parents=True, exist_ok=True)
                    metrics_data = {
                        "workflowId": workflow_id,
                        "totalNodes": metrics.total_nodes,
                        "maxDepth": metrics.max_depth,
                        "loopCount": metrics.loop_count,
                        "invokeCount": metrics.invoke_count,
                        "logCount": metrics.log_count,
                        "tryCatchCount": metrics.try_catch_count,
                        "selectorCount": metrics.selector_count,
                        "activityTypes": metrics.activity_types
                    }

                    with open(metrics_file, "w", encoding="utf-8") as f:
                        json.dump(metrics_data, f, indent=2)

                    activities_artifacts[f"metrics_{workflow_id}"] = metrics_file

            except Exception as e:
                logger.warning(f"Failed to generate activities for {workflow.relative_path}: {e}")

        logger.info(f"Generated {len(activities_artifacts)} activities artifacts")
        return activities_artifacts

    def _serialize_activity_tree(self, activity_tree) -> dict[str, Any]:
        """Serialize activity tree to JSON-compatible format.
        
        Handles both legacy ActivityTree and enhanced activity tree formats.
        """
        # Check if this is an enhanced activity tree (has .data attribute)
        if hasattr(activity_tree, 'data'):
            # Enhanced activity tree - return the pre-serialized JSON data
            return activity_tree.data
        
        # Legacy ActivityTree - use original serialization logic
        def serialize_node(node):
            return {
                "nodeId": node.node_id,
                "activityType": node.activity_type,
                "displayName": node.display_name,
                "properties": node.properties,
                "arguments": node.arguments,
                "parentId": node.parent_id,
                "continueOnError": node.continue_on_error,
                "timeout": node.timeout,
                "viewStateId": node.view_state_id,
                "children": [serialize_node(child) for child in node.children]
            }

        return {
            "workflowId": activity_tree.workflow_id,
            "contentHash": activity_tree.content_hash,
            "extractedAt": activity_tree.extracted_at.isoformat(),
            "extractorVersion": activity_tree.extractor_version,
            "variables": activity_tree.variables,
            "arguments": activity_tree.arguments,
            "imports": activity_tree.imports,
            "rootNode": serialize_node(activity_tree.root_node)
        }

    def _generate_activity_instances(self, workflow, workflow_path: Path, workflow_id: str) -> Path | None:
        """Generate activities.instances/{wfId}.json artifact as specified in ADR-009.
        
        Enhanced with performance monitoring, error handling, and configuration support.
        
        Args:
            workflow: Workflow object from workflow index
            workflow_path: Path to XAML workflow file
            workflow_id: Workflow identifier
            
        Returns:
            Path to generated instances file or None if failed
        """
        import time
        start_time = time.time()
        
        try:
            # Import and use the standalone XAML parser 
            from xaml_parser import XamlParser
            from xaml_parser.extractors import ActivityExtractor
            from xaml_parser.utils import ActivityUtils
            from dataclasses import asdict
            
            # Check if activity instances generation is enabled
            if not getattr(self.config.output, 'generate_activity_instances', True):
                logger.debug(f"Activity instances generation disabled for {workflow_id}")
                return None
            
            # Parse XAML file with error handling
            parser = XamlParser()
            parse_result = parser.parse_file(workflow_path)
            
            if not parse_result.success or not parse_result.content:
                logger.warning(f"Failed to parse XAML for activity instances: {workflow_path} - Errors: {parse_result.errors}")
                return None
            
            logger.debug(f"Successfully parsed XAML: {len(parse_result.content.activities)} activities found")
            
            # Extract project ID from workflow object or generate from path
            project_id = self._extract_project_id(workflow, workflow_path)
            
            # Create activity extractor with default config
            extractor_config = {
                'extract_expressions': True,
                'expression_language': parse_result.content.expression_language
            }
            extractor = ActivityExtractor(extractor_config)
            
            # Re-parse XAML to get XML root element for activity extraction
            from xml.etree.ElementTree import parse as xml_parse
            try:
                tree = xml_parse(workflow_path)
                xml_root = tree.getroot()
            except Exception as e:
                logger.warning(f"Failed to parse XML for activity extraction: {e}")
                return None
                
            # Extract activity instances with complete business logic
            activities = extractor.extract_activity_instances(
                xml_root,
                parse_result.content.namespaces,
                workflow_id,
                project_id
            )
            
            # Generate artifact according to implementation plan schema
            artifact = {
                "schemaVersion": "1.0.0",
                "workflowId": workflow_id,
                "generatedAt": datetime.now(UTC).isoformat(),
                "totalActivities": len(activities),
                "activities": [asdict(activity) for activity in activities]
            }
            
            # Write to activities.instances/{wfId}.json
            instances_dir = self.output_dir / "activities.instances"
            instances_dir.mkdir(exist_ok=True)
            
            # Sanitize workflow ID for filename (replace path separators)
            safe_workflow_id = workflow_id.replace("/", "_").replace("\\", "_")
            instances_file = instances_dir / f"{safe_workflow_id}.json"
            
            # Ensure parent directory exists for nested workflows
            instances_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(instances_file, "w", encoding="utf-8") as f:
                json.dump(artifact, f, indent=2, ensure_ascii=False)
            
            # Performance monitoring
            elapsed_time = time.time() - start_time
            activities_per_second = len(activities) / elapsed_time if elapsed_time > 0 else 0
            
            logger.debug(f"Generated activity instances artifact: {instances_file}")
            logger.debug(f"  - Activities extracted: {len(activities)}")
            logger.debug(f"  - Processing time: {elapsed_time:.2f}s")
            logger.debug(f"  - Activities/second: {activities_per_second:.1f}")
            
            # Warn if processing is slow (potential performance issue)
            if elapsed_time > 5.0:  # More than 5 seconds
                logger.warning(f"Slow activity extraction for {workflow_id}: {elapsed_time:.2f}s for {len(activities)} activities")
            
            return instances_file
            
        except Exception as e:
            logger.error(f"Failed to generate activity instances for {workflow_id}: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def _extract_project_id(self, workflow, workflow_path: Path) -> str:
        """Extract or generate project ID for activity instances.
        
        Args:
            workflow: Workflow object from workflow index
            workflow_path: Path to XAML workflow file
            
        Returns:
            Project ID string for activity identification
        """
        # Try to get project ID from workflow object
        project_id = getattr(workflow, 'project_id', None)
        if project_id:
            return project_id[:20]  # Limit length
        
        # Generate project slug from directory structure
        project_json_path = workflow_path.parent
        while project_json_path != project_json_path.parent:  # Not at root
            if (project_json_path / "project.json").exists():
                break
            project_json_path = project_json_path.parent
        
        # Create project ID from directory name
        project_name = project_json_path.name.lower().replace(" ", "-")
        
        # Try to load project.json for proper ID
        try:
            import json
            project_json_file = project_json_path / "project.json"
            if project_json_file.exists():
                with open(project_json_file, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                    if 'projectId' in project_data and project_data['projectId']:
                        return project_data['projectId'][:8]  # Use first 8 chars of UUID
                    elif 'name' in project_data:
                        return project_data['name'].lower().replace(" ", "-")[:20]
        except Exception:
            pass  # Fall back to directory name
        
        return project_name[:20]

    def _update_projects_index(
        self,
        project: UiPathProject,
        project_slug: str,
        project_root: Path,
        project_dir: Path
    ) -> None:
        """Update projects.json index with current project information.
        
        Args:
            project: Parsed UiPath project
            project_slug: Generated project slug
            project_root: Root directory of project
            project_dir: Project artifacts directory
        """
        projects_index_file = self.output_dir / "projects.json"

        # Load existing index or create new one
        if projects_index_file.exists():
            try:
                with open(projects_index_file, encoding="utf-8") as f:
                    index_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to read existing projects.json, creating new one: {e}")
                index_data = {"rpaxSchemaVersion": "1.0", "projects": []}
        else:
            index_data = {"rpaxSchemaVersion": "1.0", "projects": []}

        # Find existing project entry or create new one
        project_entry = None
        for p in index_data["projects"]:
            if p.get("slug") == project_slug:
                project_entry = p
                break

        if project_entry is None:
            project_entry = {"slug": project_slug}
            index_data["projects"].append(project_entry)

        # Update project entry
        project_entry.update({
            "name": project.name,
            "projectId": project.project_id,
            "projectType": project.project_type,
            "path": str(project_root),
            "lastParsed": self.timestamp,
            "artifactsPath": str(project_dir)
        })

        # Sort projects by slug for consistency
        index_data["projects"].sort(key=lambda p: p["slug"])

        # Write updated index
        with open(projects_index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated projects index with {len(index_data['projects'])} projects")
    
    def _generate_pseudocode_artifacts(
        self,
        workflow_index: WorkflowIndex,
        project: UiPathProject,
        project_root: Path
    ) -> dict[str, Path]:
        """Generate pseudocode artifacts for all workflows.
        
        Args:
            workflow_index: Discovered workflows
            project: Project metadata
            project_root: Root directory of project
            
        Returns:
            Dict mapping artifact names to file paths
        """
        from rpax.pseudocode import PseudocodeGenerator
        
        artifacts = {}
        pseudocode_dir = self.output_dir / "pseudocode"
        pseudocode_dir.mkdir(exist_ok=True)
        
        generator = PseudocodeGenerator()
        pseudocode_artifacts = []
        
        logger.info(f"Generating pseudocode for {len(workflow_index.workflows)} workflows")
        
        # Generate pseudocode for each workflow
        for workflow in workflow_index.workflows:
            xaml_path = project_root / workflow.relative_path
            
            try:
                artifact = generator.generate_workflow_pseudocode(xaml_path)
                pseudocode_artifacts.append(artifact)
                
                # Write individual pseudocode file
                output_file = pseudocode_dir / f"{workflow.workflow_id}.json"
                # Ensure parent directory exists for nested workflows (e.g., Framework/, Tests/)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(artifact.model_dump(by_alias=True), f, indent=2, ensure_ascii=False)
                
                artifacts[f"pseudocode_{workflow.workflow_id}"] = output_file
                logger.debug(f"Generated pseudocode for {workflow.workflow_id}: {artifact.total_lines} lines")
                
            except Exception as e:
                logger.error(f"Failed to generate pseudocode for {workflow.workflow_id}: {e}")
                # Create empty artifact for failed workflows
                empty_artifact = generator._create_empty_artifact(workflow.workflow_id, error=str(e))
                pseudocode_artifacts.append(empty_artifact)
        
        # Generate pseudocode index
        project_slug = project.generate_project_slug(project_root / "project.json")
        # Use project_id if available, otherwise fall back to project_slug
        effective_project_id = project.project_id or project_slug
        index = generator.generate_project_pseudocode_index(
            project_slug, effective_project_id, pseudocode_artifacts
        )
        
        # Write pseudocode index
        index_file = pseudocode_dir / "index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index.model_dump(by_alias=True), f, indent=2, ensure_ascii=False)
        
        artifacts["pseudocode_index"] = index_file
        
        logger.info(f"Generated pseudocode artifacts: {len(pseudocode_artifacts)} workflows, index file")
        return artifacts

    def _load_manifest_for_callgraph(self, manifest_file: Path) -> "ProjectManifest":
        """Load manifest data for call graph generation."""
        from rpax.models.manifest import ProjectManifest
        
        with open(manifest_file, encoding="utf-8") as f:
            manifest_data = json.load(f)
        
        return ProjectManifest(**manifest_data)

    def _generate_call_graph_artifact(
        self,
        manifest: "ProjectManifest", 
        workflow_index: WorkflowIndex,
        invocations_file: Path
    ) -> Path:
        """Generate call graph artifact (ISSUE-038)."""
        from rpax.graph.callgraph_generator import CallGraphGenerator
        
        logger.info("Generating call graph artifact")
        
        generator = CallGraphGenerator(self.config)
        call_graph = generator.generate_call_graph(manifest, workflow_index, invocations_file)
        
        # Write call graph artifact
        call_graph_file = self.output_dir / "call-graph.json"
        with open(call_graph_file, "w", encoding="utf-8") as f:
            json.dump(call_graph.model_dump(by_alias=True), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Call graph artifact generated: {call_graph_file}")
        return call_graph_file

    def _generate_expanded_pseudocode_artifacts(
        self,
        call_graph_file: Path,
        pseudocode_index_file: Path
    ) -> dict[str, Path]:
        """Generate expanded pseudocode artifacts using recursive expansion (ISSUE-036, ISSUE-040)."""
        from rpax.pseudocode.recursive_generator import (
            RecursivePseudocodeGenerator,
            load_call_graph_artifact,
            load_pseudocode_artifacts,
        )
        
        logger.info("Generating expanded pseudocode artifacts")
        
        # Load call graph and pseudocode artifacts
        call_graph = load_call_graph_artifact(call_graph_file)
        pseudocode_dir = self.output_dir / "pseudocode"
        pseudocode_artifacts = load_pseudocode_artifacts(pseudocode_dir)
        
        # Create recursive generator
        generator = RecursivePseudocodeGenerator(self.config, call_graph)
        
        # Create expanded pseudocode directory
        expanded_dir = self.output_dir / "expanded-pseudocode"
        expanded_dir.mkdir(exist_ok=True)
        
        artifacts = {}
        expanded_count = 0
        
        # Generate expanded pseudocode for each workflow
        for workflow_id, base_artifact in pseudocode_artifacts.items():
            try:
                # Generate expanded artifact
                expanded_artifact = generator.generate_expanded_artifact(
                    workflow_id, base_artifact, pseudocode_artifacts
                )
                
                # Write expanded artifact to file
                safe_workflow_name = workflow_id.replace("/", "_").replace("\\", "_")
                expanded_file = expanded_dir / f"{safe_workflow_name}.expanded.json"
                
                with open(expanded_file, "w", encoding="utf-8") as f:
                    json.dump(expanded_artifact.model_dump(by_alias=True), f, indent=2, ensure_ascii=False)
                
                artifacts[f"expanded_pseudocode_{safe_workflow_name}"] = expanded_file
                expanded_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to generate expanded pseudocode for {workflow_id}: {e}")
        
        # Generate expanded pseudocode index
        expanded_index = self._generate_expanded_pseudocode_index(expanded_count, call_graph)
        expanded_index_file = expanded_dir / "index.json"
        
        with open(expanded_index_file, "w", encoding="utf-8") as f:
            json.dump(expanded_index, f, indent=2, ensure_ascii=False)
        
        artifacts["expanded_pseudocode_index"] = expanded_index_file
        
        logger.info(f"Generated expanded pseudocode artifacts: {expanded_count} workflows")
        return artifacts

    def _generate_expanded_pseudocode_index(self, workflow_count: int, call_graph) -> dict:
        """Generate index for expanded pseudocode artifacts."""
        return {
            "schemaVersion": "1.0.0",
            "generatedAt": self.timestamp,
            "rpaxVersion": "0.0.1",  # Would get from rpax.__version__
            "projectId": call_graph.project_id,
            "projectSlug": call_graph.project_slug,
            "totalExpandedWorkflows": workflow_count,
            "expansionConfig": {
                "maxDepth": self.config.pseudocode.max_expansion_depth,
                "cycleHandling": self.config.pseudocode.cycle_handling,
                "generateExpanded": self.config.pseudocode.generate_expanded
            }
        }

    def _generate_object_repository_artifacts(self, project_root: Path) -> dict[str, Path]:
        """Generate Object Repository artifacts for Library projects.
        
        Args:
            project_root: Root directory of project
            
        Returns:
            Dict mapping artifact names to file paths
        """
        artifacts = {}
        
        # Look for .objects directory
        objects_path = project_root / ".objects"
        if not objects_path.exists():
            logger.debug(f"No Object Repository found in {project_root}")
            return artifacts
            
        try:
            from rpax.parser.object_repository import ObjectRepositoryParser
            
            parser = ObjectRepositoryParser()
            repository = parser.parse_repository(objects_path)
            
            if not repository:
                logger.warning(f"Failed to parse Object Repository in {objects_path}")
                return artifacts
                
            # Create object-repository directory
            object_repo_dir = self.output_dir / "object-repository"
            object_repo_dir.mkdir(exist_ok=True)
            
            # Generate repository summary
            repository_summary = {
                "schemaVersion": "1.0.0",
                "generatedAt": self.timestamp,
                "libraryId": repository.library_id,
                "libraryType": repository.library_type,
                "created": repository.created,
                "updated": repository.updated,
                "totalApps": len(repository.apps),
                "totalTargets": sum(len(app.targets) for app in repository.apps),
                "apps": [
                    {
                        "appId": app.app_id,
                        "name": app.name,
                        "description": app.description,
                        "targetsCount": len(app.targets),
                        "created": app.created,
                        "updated": app.updated
                    }
                    for app in repository.apps
                ]
            }
            
            # Write repository summary
            summary_file = object_repo_dir / "repository-summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(repository_summary, f, indent=2, ensure_ascii=False)
                
            artifacts["object_repository_summary"] = summary_file
            
            # Generate detailed app artifacts
            apps_dir = object_repo_dir / "apps"
            apps_dir.mkdir(exist_ok=True)
            
            for app in repository.apps:
                app_data = {
                    "appId": app.app_id,
                    "name": app.name,
                    "description": app.description,
                    "reference": app.reference,
                    "created": app.created,
                    "updated": app.updated,
                    "totalTargets": len(app.targets),
                    "targets": [
                        {
                            "targetId": target.target_id,
                            "friendlyName": target.friendly_name,
                            "elementType": target.element_type,
                            "activityType": target.activity_type,
                            "contentHash": target.content_hash,
                            "reference": target.reference,
                            "selectors": [
                                {
                                    "type": selector.selector_type,
                                    "value": selector.selector_value,
                                    "properties": selector.properties
                                }
                                for selector in target.selectors
                            ],
                            "designProperties": target.design_properties
                        }
                        for target in app.targets
                    ]
                }
                
                # Sanitize app name for filename
                safe_app_name = "".join(c if c.isalnum() or c in ".-_" else "_" for c in app.name)
                app_file = apps_dir / f"{safe_app_name}.json"
                
                with open(app_file, "w", encoding="utf-8") as f:
                    json.dump(app_data, f, indent=2, ensure_ascii=False)
                    
                artifacts[f"object_repository_app_{safe_app_name}"] = app_file
            
            # Generate MCP resources file
            project_id = getattr(self, 'project_id', 'unknown')
            mcp_resources = parser.generate_mcp_resources(repository, project_id)
            
            mcp_resources_file = object_repo_dir / "mcp-resources.json"
            with open(mcp_resources_file, "w", encoding="utf-8") as f:
                json.dump({
                    "schemaVersion": "1.0.0",
                    "generatedAt": self.timestamp,
                    "resources": mcp_resources
                }, f, indent=2, ensure_ascii=False)
                
            artifacts["object_repository_mcp_resources"] = mcp_resources_file
            
            logger.info(f"Generated Object Repository artifacts: {len(repository.apps)} apps, "
                      f"{sum(len(app.targets) for app in repository.apps)} targets")
            
        except ImportError:
            logger.warning("Object Repository parser not available")
        except Exception as e:
            logger.error(f"Failed to generate Object Repository artifacts: {e}")
            
        return artifacts

    def _generate_package_analysis_artifacts(
        self,
        project: UiPathProject,
        workflow_index: WorkflowIndex
    ) -> dict[str, Path]:
        """Generate package analysis artifacts showing dependency usage.
        
        Args:
            project: Parsed UiPath project
            workflow_index: Discovered workflows with namespace information
            
        Returns:
            Dict mapping artifact names to file paths
        """
        artifacts = {}
        
        try:
            # Collect package usage from all workflows
            workflow_packages = {}
            for workflow in workflow_index.workflows:
                if workflow.packages_used:
                    workflow_packages[workflow.workflow_id] = workflow.packages_used
            
            # Analyze package usage patterns
            package_analysis = analyze_package_usage(
                project.dependencies,
                workflow_packages
            )
            
            # Set project context - we need to pass project_root from the caller
            # For now, use a fallback method to generate slug
            package_analysis.project_slug = project.project_id or project.name.lower().replace(" ", "-")
            package_analysis.project_name = project.name
            
            # Generate package analysis artifact
            packages_file = self.output_dir / "packages-analysis.json"
            with open(packages_file, "w", encoding="utf-8") as f:
                json.dump(
                    package_analysis.model_dump(by_alias=True),
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            
            artifacts["packages_analysis"] = packages_file
            
            # Generate package usage summary for each workflow
            workflow_packages_dir = self.output_dir / "workflow-packages"
            workflow_packages_dir.mkdir(exist_ok=True)
            
            for workflow in workflow_index.workflows:
                if workflow.namespaces or workflow.packages_used:
                    # Sanitize workflow ID for filename
                    safe_workflow_id = workflow.workflow_id.replace("/", "_").replace("\\", "_")
                    workflow_packages_file = workflow_packages_dir / f"{safe_workflow_id}.json"
                    
                    workflow_package_data = {
                        "workflowId": workflow.workflow_id,
                        "workflowPath": workflow.relative_path,
                        "namespaces": workflow.namespaces,
                        "packagesUsed": workflow.packages_used,
                        "totalNamespaces": len(workflow.namespaces),
                        "totalPackages": len(workflow.packages_used)
                    }
                    
                    # Ensure parent directory exists for nested workflows
                    workflow_packages_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(workflow_packages_file, "w", encoding="utf-8") as f:
                        json.dump(workflow_package_data, f, indent=2, ensure_ascii=False)
                    
                    artifacts[f"workflow_packages_{safe_workflow_id}"] = workflow_packages_file
            
            logger.info(f"Generated package analysis artifacts: {len(package_analysis.packages)} packages analyzed")
            
            if package_analysis.has_unused_packages:
                logger.warning(f"Found {len(package_analysis.unused_packages)} unused packages: {', '.join(package_analysis.unused_packages)}")
            
            if package_analysis.has_undeclared_packages:
                logger.warning(f"Found {len(package_analysis.undeclared_packages)} undeclared packages: {', '.join(package_analysis.undeclared_packages)}")
                
        except Exception as e:
            logger.error(f"Failed to generate package analysis artifacts: {e}")
            
        return artifacts
