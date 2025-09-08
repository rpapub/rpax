"""Enhanced workflow discovery for both XAML and coded workflows.

Extends the original XAML discovery to include .cs coded workflows
as first-class citizens in the workflow index.
"""

import hashlib
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import List, Optional

from rpax.models.workflow import Workflow, WorkflowIndex
from rpax.parser.xaml import XamlDiscovery
from rpax.parser.coded_workflow import CodedWorkflowParser, discover_coded_workflows

logger = logging.getLogger(__name__)


class EnhancedWorkflowDiscovery(XamlDiscovery):
    """Enhanced workflow discovery that includes both XAML and coded workflows."""
    
    def __init__(self, project_root: Path, exclude_patterns: List[str] = None):
        """Initialize enhanced workflow discovery.
        
        Args:
            project_root: Root directory of UiPath project
            exclude_patterns: Glob patterns to exclude from discovery
        """
        super().__init__(project_root, exclude_patterns)
        self.coded_parser = CodedWorkflowParser()
    
    def discover_workflows(self) -> WorkflowIndex:
        """Discover all workflows (XAML and coded) in the project.
        
        Returns:
            WorkflowIndex: Complete index of discovered workflows including coded workflows
        """
        # Start with XAML discovery from parent class
        xaml_index = super().discover_workflows()
        
        # Add coded workflows
        coded_workflows = self._discover_coded_workflows()
        
        # Combine workflows
        all_workflows = list(xaml_index.workflows) + coded_workflows
        
        # Update statistics
        total_workflows = len(all_workflows)
        successful_parses = xaml_index.successful_parses + len(coded_workflows)
        failed_parses = xaml_index.failed_parses  # Coded workflow parsing failures would be logged but not counted here
        
        return WorkflowIndex(
            project_name=xaml_index.project_name,
            project_root=xaml_index.project_root,
            scan_timestamp=xaml_index.scan_timestamp,
            total_workflows=total_workflows,
            successful_parses=successful_parses,
            failed_parses=failed_parses,
            workflows=all_workflows,
            excluded_patterns=xaml_index.excluded_patterns,
            excluded_files=xaml_index.excluded_files
        )
    
    def _discover_coded_workflows(self) -> List[Workflow]:
        """Discover and parse coded workflow .cs files."""
        coded_workflows = []
        
        # Find coded workflow files
        coded_files = discover_coded_workflows(self.project_root, self.exclude_patterns)
        
        logger.info(f"Found {len(coded_files)} coded workflow files")
        
        for coded_file in coded_files:
            try:
                # Get relative path
                relative_path = coded_file.relative_to(self.project_root)
                relative_path_str = str(relative_path).replace("\\", "/")
                
                # Skip if excluded
                if self._is_excluded(coded_file):
                    continue
                
                # Parse the coded workflow
                coded_info = self.coded_parser.parse_coded_workflow(coded_file, relative_path_str)
                
                if coded_info:
                    # Convert coded workflow info to Workflow model
                    workflow = self._create_coded_workflow_entry(coded_info, coded_file)
                    coded_workflows.append(workflow)
                    
            except Exception as e:
                logger.error(f"Failed to process coded workflow {coded_file}: {e}")
                continue
        
        return coded_workflows
    
    def _create_coded_workflow_entry(self, coded_info, file_path: Path) -> Workflow:
        """Create Workflow model entry for a coded workflow."""
        # Generate IDs similar to XAML workflows
        relative_path_str = coded_info.relative_path
        project_slug = self._generate_project_slug()
        workflow_id = relative_path_str.replace("\\", "/")
        content_hash = self._generate_content_hash(file_path)
        composite_id = f"{project_slug}#{workflow_id}#{content_hash}"
        
        # Get file metadata
        stat = file_path.stat()
        file_size = stat.st_size
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        
        # Convert coded workflow arguments to workflow format
        arguments = []
        for arg in coded_info.arguments:
            arguments.append({
                "name": arg.name,
                "type": arg.type,
                "direction": arg.direction,
                "default_value": arg.default_value,
                "annotation": None
            })
        
        return Workflow(
            id=composite_id,
            project_slug=project_slug,
            workflow_id=workflow_id,
            content_hash=content_hash,
            file_path=str(file_path),
            file_name=file_path.name,
            relative_path=relative_path_str,
            display_name=coded_info.class_name,  # Use class name as display name
            description=f"Coded workflow class: {coded_info.class_name}",
            discovered_at=datetime.now(UTC).isoformat(),
            file_size=file_size,
            last_modified=last_modified.isoformat(),
            
            # Coded workflow specific data
            arguments=arguments,
            variables=[],  # Coded workflows don't have XAML-style variables
            
            # Add coded workflow metadata in custom fields if needed
            namespace=coded_info.namespace,
            base_class=coded_info.base_class,
            using_statements=coded_info.using_statements,
            workflow_type="coded"  # Mark as coded workflow
        )
    
    def _generate_project_slug(self) -> str:
        """Generate project slug from project root name."""
        return self.project_root.name.lower().replace(" ", "-").replace("_", "-")
    
    def _generate_content_hash(self, file_path: Path) -> str:
        """Generate content hash for a file."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()[:12]
        except Exception as e:
            logger.warning(f"Failed to generate content hash for {file_path}: {e}")
            return "unknown-hash"


def create_workflow_discovery(project_root: Path, exclude_patterns: List[str] = None, 
                            include_coded_workflows: bool = True) -> XamlDiscovery:
    """Factory function to create appropriate workflow discovery instance.
    
    Args:
        project_root: Root directory of UiPath project
        exclude_patterns: Glob patterns to exclude from discovery
        include_coded_workflows: Whether to include coded workflow discovery
        
    Returns:
        XamlDiscovery or EnhancedWorkflowDiscovery instance
    """
    if include_coded_workflows:
        return EnhancedWorkflowDiscovery(project_root, exclude_patterns)
    else:
        return XamlDiscovery(project_root, exclude_patterns)