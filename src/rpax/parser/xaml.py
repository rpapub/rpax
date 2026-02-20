"""XAML workflow discovery and basic parsing functionality."""

import fnmatch
import hashlib
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from dataclasses import asdict

from rpax.models.workflow import Workflow, WorkflowIndex
from rpax.parser.namespace_analyzer import NamespaceAnalyzer

# Import standalone XAML parser
from cpmf_uips_xaml import XamlParser


class XamlDiscovery:
    """XAML workflow discovery and indexing."""

    def __init__(self, project_root: Path, exclude_patterns: list[str] | None = None):
        """Initialize XAML discovery.
        
        Args:
            project_root: Root directory of UiPath project
            exclude_patterns: Glob patterns to exclude from discovery
        """
        self.project_root = project_root.resolve()
        self.exclude_patterns = exclude_patterns or []
        
        # Initialize XAML parser and namespace analyzer for content extraction
        self.xaml_parser = XamlParser()
        self.namespace_analyzer = NamespaceAnalyzer()

    def discover_workflows(self) -> WorkflowIndex:
        """Discover all XAML workflows in the project.
        
        Returns:
            WorkflowIndex: Complete index of discovered workflows
        """
        workflows = []
        excluded_files = []

        for xaml_file in self._find_xaml_files():
            relative_path_str = str(xaml_file.relative_to(self.project_root)).replace("\\", "/")

            if self._is_excluded(xaml_file):
                excluded_files.append(relative_path_str)
                continue

            try:
                workflow = self._create_workflow_entry(xaml_file)
                workflows.append(workflow)
            except Exception as e:
                # Create workflow entry with parse error
                workflow = self._create_workflow_entry(xaml_file, parse_error=str(e))
                workflows.append(workflow)

        # Build index
        successful_parses = sum(1 for w in workflows if w.parse_successful)
        failed_parses = len(workflows) - successful_parses

        return WorkflowIndex(
            project_name=self.project_root.name,
            project_root=str(self.project_root),
            scan_timestamp=datetime.now(UTC).isoformat(),
            total_workflows=len(workflows),
            successful_parses=successful_parses,
            failed_parses=failed_parses,
            workflows=workflows,
            excluded_patterns=self.exclude_patterns,
            excluded_files=excluded_files
        )

    def _find_xaml_files(self) -> Iterator[Path]:
        """Find all .xaml files in project directory recursively."""
        for root, dirs, files in os.walk(self.project_root):
            # Don't filter directories here - let _is_excluded handle it per file
            for file in files:
                if file.lower().endswith(".xaml"):
                    yield Path(root) / file

    def _is_excluded(self, file_path: Path) -> bool:
        """Check if file should be excluded based on patterns."""
        relative_path = file_path.relative_to(self.project_root)
        relative_str = str(relative_path).replace("\\", "/")  # POSIX format

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(relative_str, pattern):
                return True
        return False

    def _is_dir_excluded(self, dir_path: Path) -> bool:
        """Check if directory should be excluded from traversal."""
        try:
            relative_path = dir_path.relative_to(self.project_root)
            relative_str = str(relative_path).replace("\\", "/") + "/**"

            for pattern in self.exclude_patterns:
                if fnmatch.fnmatch(relative_str, pattern):
                    return True
        except ValueError:
            # Directory is outside project root
            return True
        return False

    def _create_workflow_entry(self, xaml_file: Path, parse_error: str | None = None) -> Workflow:
        """Create workflow entry from XAML file with complete content extraction.
        
        Args:
            xaml_file: Path to XAML file
            parse_error: Optional parse error message
            
        Returns:
            Workflow: Workflow model instance with complete metadata
        """
        # Read file for content hash
        try:
            content = xaml_file.read_bytes()
            content_hash = Workflow.generate_content_hash(content)
        except Exception:
            content_hash = "error"

        # Generate normalized paths and IDs according to ADR-014
        relative_path = Workflow.normalize_path(xaml_file, self.project_root)
        project_slug = self._generate_project_slug()
        workflow_id = relative_path  # ADR-014: wfId is the canonical path ID, not dot-separated
        composite_id = Workflow.generate_composite_id(project_slug, workflow_id, content_hash)

        # File metadata
        try:
            stat = xaml_file.stat()
            file_size = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
        except Exception:
            file_size = 0
            last_modified = datetime.now(UTC).isoformat()

        # Extract XAML content metadata using standalone parser (ISSUE-060)
        xaml_content = None
        xaml_parse_errors = []
        namespaces = {}
        packages_used = []
        
        if parse_error is None:
            try:
                parse_result = self.xaml_parser.parse_file(xaml_file)
                if parse_result.success and parse_result.content:
                    xaml_content = parse_result.content
                else:
                    xaml_parse_errors = parse_result.errors
                    
                # Extract namespaces and packages regardless of content parsing success
                try:
                    namespace_analysis = self.namespace_analyzer.analyze_workflow_packages(xaml_file)
                    namespaces = namespace_analysis.get("namespaces", {})
                    packages_used = namespace_analysis.get("packages_used", [])
                except Exception as e:
                    xaml_parse_errors.append(f"Namespace analysis failed: {str(e)}")
                    
            except Exception as e:
                xaml_parse_errors = [f"XAML parsing failed: {str(e)}"]

        # Extract display name and description from XAML content
        display_name = xaml_file.stem  # Default to filename
        description = None
        root_annotation = None
        arguments = []
        variables = []
        activities = []
        expression_language = "VisualBasic"
        total_activities = 0
        total_arguments = 0
        total_variables = 0

        if xaml_content:
            # Use parsed display name if available, otherwise keep filename
            if xaml_content.display_name:
                display_name = xaml_content.display_name
            
            # Extract workflow metadata
            root_annotation = xaml_content.root_annotation
            description = xaml_content.description
            expression_language = xaml_content.expression_language
            
            # Convert dataclass objects to dictionaries for JSON serialization
            arguments = [asdict(arg) for arg in xaml_content.arguments]
            variables = [asdict(var) for var in xaml_content.variables]
            activities = [asdict(act) for act in xaml_content.activities]
            
            # Statistics
            total_activities = xaml_content.total_activities
            total_arguments = xaml_content.total_arguments
            total_variables = xaml_content.total_variables

        # Store original path casing for provenance (ADR-014)
        try:
            original_relative = str(xaml_file.relative_to(self.project_root))
        except ValueError:
            original_relative = str(xaml_file)

        # Combine parse errors
        all_errors = []
        if parse_error:
            all_errors.append(parse_error)
        all_errors.extend(xaml_parse_errors)

        return Workflow(
            id=composite_id,
            project_slug=project_slug,
            workflow_id=workflow_id,
            content_hash=content_hash,
            file_path=str(xaml_file),
            file_name=xaml_file.name,
            relative_path=relative_path,
            original_path=original_relative.replace("\\", "/"),  # Store original casing
            display_name=display_name,
            description=description,
            discovered_at=datetime.now(UTC).isoformat(),
            file_size=file_size,
            last_modified=last_modified,
            # XAML content metadata (ISSUE-060)
            root_annotation=root_annotation,
            arguments=arguments,
            variables=variables,
            activities=activities,
            expression_language=expression_language,
            total_activities=total_activities,
            total_arguments=total_arguments,
            total_variables=total_variables,
            # Package usage from XAML namespaces
            namespaces=namespaces,
            packages_used=packages_used,
            # Parsing status
            parse_successful=len(all_errors) == 0,
            parse_errors=all_errors
        )

    def _generate_project_slug(self) -> str:
        """Generate project slug according to ADR-014: kebab(name) + "-" + shortHash(project.json)."""
        try:
            # Find and read project.json
            project_json_path = self.project_root / "project.json"
            if not project_json_path.exists():
                # Fallback to directory name if no project.json
                return self.project_root.name.lower().replace(" ", "-").replace("_", "-")

            with open(project_json_path, encoding="utf-8") as f:
                project_data = json.load(f)

            # Generate kebab-case name
            project_name = project_data.get("name", self.project_root.name)
            kebab_name = project_name.lower().replace(" ", "-").replace("_", "-")

            # Generate short hash of project.json content
            project_json_content = json.dumps(project_data, sort_keys=True).encode("utf-8")
            project_hash = hashlib.sha256(project_json_content).hexdigest()[:8]

            return f"{kebab_name}-{project_hash}"

        except Exception:
            # Fallback to directory name on any error
            return self.project_root.name.lower().replace(" ", "-").replace("_", "-")
