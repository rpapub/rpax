"""Object Repository (.objects) parser for UiPath library projects.

Parses UiPath Object Repository libraries containing GUI selectors, UI elements,
and automation targets for MCP integration and resource discovery.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from rpax.utils.paths import normalize_path

logger = logging.getLogger(__name__)


@dataclass
class UISelector:
    """UI selector definition from Object Repository."""
    selector_type: str  # "full", "fuzzy", "scope"
    selector_value: str
    properties: Dict[str, str] = field(default_factory=dict)


@dataclass
class UITarget:
    """UI target element with selectors and metadata."""
    target_id: str
    friendly_name: str
    element_type: str
    reference: str
    selectors: List[UISelector] = field(default_factory=list)
    design_properties: Dict[str, Any] = field(default_factory=dict)
    activity_type: str = "None"
    content_hash: Optional[str] = None


@dataclass
class ObjectApp:
    """Application definition in Object Repository."""
    app_id: str
    name: str
    description: str
    reference: str
    targets: List[UITarget] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None


@dataclass
class ObjectRepository:
    """Complete Object Repository structure."""
    library_id: str
    library_type: str = "Library"
    apps: List[ObjectApp] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None


class ObjectRepositoryParser:
    """Parser for UiPath Object Repository (.objects) directories."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_repository(self, objects_path: Path) -> Optional[ObjectRepository]:
        """Parse complete Object Repository from .objects directory.
        
        Args:
            objects_path: Path to .objects directory
            
        Returns:
            ObjectRepository with all apps and targets, or None if parsing fails
        """
        self.logger.debug(f"Parsing Object Repository: {objects_path}")
        
        if not objects_path.exists() or not objects_path.is_dir():
            self.logger.warning(f"Object Repository path does not exist: {objects_path}")
            return None
            
        try:
            # Parse library metadata
            library_metadata = self._parse_library_metadata(objects_path)
            if not library_metadata:
                return None
                
            repository = ObjectRepository(
                library_id=library_metadata.get("Id", ""),
                library_type=library_metadata.get("Type", "Library"),
                created=library_metadata.get("Created"),
                updated=library_metadata.get("Updated")
            )
            
            # Parse all apps in the repository
            for item in objects_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    app = self._parse_app(item)
                    if app:
                        repository.apps.append(app)
                        
            self.logger.debug(f"Parsed {len(repository.apps)} apps from Object Repository")
            return repository
            
        except Exception as e:
            self.logger.error(f"Failed to parse Object Repository {objects_path}: {e}")
            return None

    def _parse_library_metadata(self, objects_path: Path) -> Optional[Dict[str, Any]]:
        """Parse library-level metadata from .objects/.metadata."""
        metadata_path = objects_path / ".metadata"
        if not metadata_path.exists():
            return None
            
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove BOM if present
                if content.startswith('\ufeff'):
                    content = content[1:]
                return json.loads(content)
        except Exception as e:
            self.logger.warning(f"Failed to parse library metadata {metadata_path}: {e}")
            return None

    def _parse_app(self, app_path: Path) -> Optional[ObjectApp]:
        """Parse application definition from app directory."""
        self.logger.debug(f"Parsing app: {app_path}")
        
        # Parse app metadata
        metadata_path = app_path / ".metadata"
        if not metadata_path.exists():
            self.logger.debug(f"No metadata found for app: {app_path}")
            return None
            
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove BOM if present
                if content.startswith('\ufeff'):
                    content = content[1:]
                app_metadata = json.loads(content)
                
            app = ObjectApp(
                app_id=app_metadata.get("Id", ""),
                name=app_metadata.get("Name", ""),
                description=app_metadata.get("Description", ""),
                reference=app_metadata.get("Reference", ""),
                created=app_metadata.get("Created"),
                updated=app_metadata.get("Updated")
            )
            
            # Parse targets recursively
            self._parse_targets_recursive(app_path, app)
            
            self.logger.debug(f"Parsed app '{app.name}' with {len(app.targets)} targets")
            return app
            
        except Exception as e:
            self.logger.warning(f"Failed to parse app {app_path}: {e}")
            return None

    def _parse_targets_recursive(self, path: Path, app: ObjectApp) -> None:
        """Recursively parse UI targets from directory structure."""
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if this directory contains a target
                target = self._parse_target(item)
                if target:
                    app.targets.append(target)
                else:
                    # Recurse into subdirectories
                    self._parse_targets_recursive(item, app)

    def _parse_target(self, target_path: Path) -> Optional[UITarget]:
        """Parse UI target from target directory."""
        # Look for ObjectRepositoryTargetData in .data subdirectory
        data_paths = [
            target_path / ".data" / "ObjectRepositoryTargetData" / ".content",
            target_path / "ObjectRepositoryTargetData" / ".content"
        ]
        
        content_path = None
        for path in data_paths:
            if path.exists():
                content_path = path
                break
                
        if not content_path:
            return None
            
        try:
            # Parse XML content - handle encoding issues
            try:
                tree = ET.parse(content_path)
                root = tree.getroot()
            except ET.ParseError as e:
                if "encoding specified in XML declaration is incorrect" in str(e):
                    # Try parsing with UTF-8 encoding override
                    with open(content_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Fix encoding declaration
                        if 'encoding="utf-16"' in content:
                            content = content.replace('encoding="utf-16"', 'encoding="utf-8"')
                        root = ET.fromstring(content)
                else:
                    raise e
            
            # Extract target metadata
            content_hash = root.get("ContentHash")
            reference = root.get("Reference", "")
            
            # Find TargetAnchorable element
            target_element = root.find(".//{http://schemas.uipath.com/workflow/activities/uix}TargetAnchorable")
            if target_element is None:
                # Try without namespace
                target_element = root.find(".//TargetAnchorable")
                
            if target_element is None:
                self.logger.debug(f"No TargetAnchorable found in {content_path}")
                return None
                
            # Extract target properties
            friendly_name = target_element.get("FriendlyName", "")
            element_type = target_element.get("ElementType", "")
            guid = target_element.get("Guid", "")
            
            # Extract activity type
            activity_type_element = root.find(".//{http://schemas.microsoft.com/winfx/2006/xaml}String[@x:Key='ActivityType']", 
                                            {"x": "http://schemas.microsoft.com/winfx/2006/xaml"})
            activity_type = activity_type_element.text if activity_type_element is not None else "None"
            
            target = UITarget(
                target_id=guid or target_path.name,
                friendly_name=friendly_name,
                element_type=element_type,
                reference=reference,
                activity_type=activity_type,
                content_hash=content_hash
            )
            
            # Extract selectors
            selectors = [
                ("full", target_element.get("FullSelectorArgument", "")),
                ("fuzzy", target_element.get("FuzzySelectorArgument", "")),
                ("scope", target_element.get("ScopeSelectorArgument", ""))
            ]
            
            for selector_type, selector_value in selectors:
                if selector_value:
                    # Parse selector properties (basic XML structure)
                    properties = self._parse_selector_properties(selector_value)
                    target.selectors.append(UISelector(
                        selector_type=selector_type,
                        selector_value=selector_value,
                        properties=properties
                    ))
            
            # Extract design-time properties
            design_props = {}
            for attr_name in ["CvTextArea", "CvTextArgument", "CvType", "DesignTimeRectangle", 
                            "DesignTimeScaleFactor", "SearchSteps", "Version", "Visibility"]:
                attr_value = target_element.get(attr_name)
                if attr_value:
                    design_props[attr_name] = attr_value
                    
            target.design_properties = design_props
            
            self.logger.debug(f"Parsed target: {friendly_name} ({element_type})")
            return target
            
        except Exception as e:
            self.logger.warning(f"Failed to parse target {target_path}: {e}")
            return None

    def _parse_selector_properties(self, selector_xml: str) -> Dict[str, str]:
        """Parse basic properties from selector XML string."""
        properties = {}
        
        if not selector_xml or not selector_xml.strip():
            return properties
            
        try:
            # Handle HTML entities in selectors
            import html
            selector_xml = html.unescape(selector_xml)
            
            # Simple regex-based extraction for common properties
            import re
            
            # Extract automation ID
            automationid_match = re.search(r"automationid='([^']*)'", selector_xml, re.IGNORECASE)
            if automationid_match:
                properties["automationid"] = automationid_match.group(1)
                
            # Extract class name
            cls_match = re.search(r"cls='([^']*)'", selector_xml, re.IGNORECASE)
            if cls_match:
                properties["cls"] = cls_match.group(1)
                
            # Extract name
            name_match = re.search(r"name='([^']*)'", selector_xml, re.IGNORECASE)
            if name_match:
                properties["name"] = name_match.group(1)
                
            # Extract role
            role_match = re.search(r"role='([^']*)'", selector_xml, re.IGNORECASE)
            if role_match:
                properties["role"] = role_match.group(1)
                
            # Extract app information
            app_match = re.search(r"app='([^']*)'", selector_xml, re.IGNORECASE)
            if app_match:
                properties["app"] = app_match.group(1)
                
            appid_match = re.search(r"appid='([^']*)'", selector_xml, re.IGNORECASE)
            if appid_match:
                properties["appid"] = appid_match.group(1)
                
        except Exception as e:
            self.logger.debug(f"Failed to parse selector properties: {e}")
            
        return properties

    def generate_mcp_resources(self, repository: ObjectRepository, project_id: str) -> List[Dict[str, Any]]:
        """Generate MCP resources from Object Repository data.
        
        Args:
            repository: Parsed ObjectRepository
            project_id: Project identifier for resource URIs
            
        Returns:
            List of MCP resource definitions
        """
        resources = []
        
        # Generate library-level resource
        library_resource = {
            "uri": f"rpax://{project_id}/object-repository",
            "name": f"Object Repository Library ({project_id})",
            "description": f"UiPath Object Repository with {len(repository.apps)} applications and UI targets",
            "mimeType": "application/json",
            "content": {
                "type": "object_repository_library",
                "library_id": repository.library_id,
                "library_type": repository.library_type,
                "apps_count": len(repository.apps),
                "created": repository.created,
                "updated": repository.updated,
                "apps": [
                    {
                        "app_id": app.app_id,
                        "name": app.name,
                        "description": app.description,
                        "targets_count": len(app.targets)
                    }
                    for app in repository.apps
                ]
            }
        }
        resources.append(library_resource)
        
        # Generate app-specific resources
        for app in repository.apps:
            app_resource = {
                "uri": f"rpax://{project_id}/object-repository/apps/{app.app_id}",
                "name": f"Object Repository App: {app.name}",
                "description": f"UI automation targets for {app.name} ({len(app.targets)} targets)",
                "mimeType": "application/json",
                "content": {
                    "type": "object_repository_app",
                    "app_id": app.app_id,
                    "name": app.name,
                    "description": app.description,
                    "reference": app.reference,
                    "created": app.created,
                    "updated": app.updated,
                    "targets": [
                        {
                            "target_id": target.target_id,
                            "friendly_name": target.friendly_name,
                            "element_type": target.element_type,
                            "activity_type": target.activity_type,
                            "selectors": [
                                {
                                    "type": selector.selector_type,
                                    "value": selector.selector_value,
                                    "properties": selector.properties
                                }
                                for selector in target.selectors
                            ],
                            "design_properties": target.design_properties,
                            "content_hash": target.content_hash
                        }
                        for target in app.targets
                    ]
                }
            }
            resources.append(app_resource)
            
        return resources