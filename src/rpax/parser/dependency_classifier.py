"""
UiPath dependency classification system for MCP-enhanced progressive disclosure.

Classifies dependencies into vendor/official vs custom/inhouse categories without
requiring access to NuGet feeds. Supports progressive enhancement through MCP
protocol where users/LLMs can provide missing mappings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel


class DependencyType(str, Enum):
    """Classification types for UiPath project dependencies."""
    VENDOR_OFFICIAL = "vendor_official"  # UiPath.* packages
    CUSTOM_LOCAL = "custom_local"       # Local/inhouse libraries  
    THIRD_PARTY = "third_party"         # External but not UiPath
    AMBIGUOUS = "ambiguous"             # Requires user/MCP classification
    UNKNOWN = "unknown"                 # Unclassified


@dataclass 
class DependencyInfo:
    """Information about a discovered dependency."""
    name: str
    version: str
    classification: DependencyType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    potential_local_paths: List[Path] = field(default_factory=list)
    user_provided_mapping: Optional[str] = None


class DependencyMappingCache(BaseModel):
    """Cached user/LLM-provided dependency mappings for MCP enhancement."""
    mappings: Dict[str, str] = {}  # package_name -> filesystem_path
    classifications: Dict[str, DependencyType] = {}  # package_name -> type
    confidence_overrides: Dict[str, float] = {}  # package_name -> confidence


class DependencyClassifier:
    """
    Classifies UiPath project dependencies for MCP-enhanced progressive disclosure.
    
    Design principles:
    1. Deterministic classification for clear patterns (UiPath.* = vendor)
    2. Heuristic classification for probable patterns (camelCase = custom)
    3. Request MCP assistance for ambiguous cases
    4. Cache learned mappings for future use
    """
    
    def __init__(self, lake_root: Path, mapping_cache: Optional[DependencyMappingCache] = None):
        self.lake_root = lake_root
        self.cache = mapping_cache or DependencyMappingCache()
        
        # Vendor package patterns (high confidence)
        self.vendor_patterns = [
            re.compile(r'^UiPath\..*$'),           # UiPath.Excel.Activities
            re.compile(r'^Microsoft\..*$'),       # Microsoft.* packages
            re.compile(r'^System\..*$'),          # System.* packages  
            re.compile(r'^Newtonsoft\..*$'),      # Newtonsoft.Json
        ]
        
        # Custom library heuristics (medium confidence)
        self.custom_heuristics = [
            re.compile(r'^[A-Z][a-zA-Z]*[A-Z][a-zA-Z]*$'),  # PascalCase compound words
            re.compile(r'^[A-Z][a-z]+[A-Z][a-z]+.*$'),      # CamelCase patterns
        ]
    
    def classify_dependency(self, name: str, version: str, project_root: Optional[Path] = None) -> DependencyInfo:
        """
        Classify a single dependency with confidence scoring.
        
        Args:
            name: Package name (e.g., "LuckyLawrencium", "UiPath.Excel.Activities")
            version: Package version (e.g., "0.2.0", "[2.23.3-preview]")
            project_root: Project root for local dependency discovery
            
        Returns:
            DependencyInfo with classification and reasoning
        """
        
        # Check cache first - user/LLM provided classifications take precedence
        if name in self.cache.classifications:
            return DependencyInfo(
                name=name,
                version=version,
                classification=self.cache.classifications[name],
                confidence=self.cache.confidence_overrides.get(name, 1.0),
                reasoning="User/LLM provided classification via MCP",
                user_provided_mapping=self.cache.mappings.get(name)
            )
        
        # Deterministic vendor classification (high confidence)
        for pattern in self.vendor_patterns:
            if pattern.match(name):
                return DependencyInfo(
                    name=name,
                    version=version,
                    classification=DependencyType.VENDOR_OFFICIAL,
                    confidence=0.95,
                    reasoning=f"Matches vendor pattern: {pattern.pattern}"
                )
        
        # Custom library heuristics (medium confidence)  
        for pattern in self.custom_heuristics:
            if pattern.match(name):
                potential_paths = self._find_potential_local_paths(name, project_root)
                return DependencyInfo(
                    name=name,
                    version=version,
                    classification=DependencyType.CUSTOM_LOCAL if potential_paths else DependencyType.AMBIGUOUS,
                    confidence=0.7 if potential_paths else 0.4,
                    reasoning=f"Matches custom library pattern: {pattern.pattern}",
                    potential_local_paths=potential_paths
                )
        
        # Ambiguous cases - require MCP assistance
        return DependencyInfo(
            name=name,
            version=version,
            classification=DependencyType.AMBIGUOUS,
            confidence=0.2,
            reasoning="Does not match known patterns - requires user classification"
        )
    
    def _find_potential_local_paths(self, package_name: str, project_root: Optional[Path] = None) -> List[Path]:
        """
        Find potential filesystem paths for custom dependencies.
        
        Search strategy:
        1. Look for projects with matching sanitized names in lake
        2. Search relative to current project root  
        3. Search common library locations
        
        Args:
            package_name: Name to search for (e.g., "LuckyLawrencium")
            project_root: Current project root for relative searches
            
        Returns:
            List of potential Path locations
        """
        candidates = []
        
        # Search in lake for projects with matching names
        if self.lake_root.exists():
            for project_dir in self.lake_root.rglob("project.json"):
                try:
                    # UiPath sanitizes project names for packages
                    project_parent = project_dir.parent
                    sanitized_name = self._sanitize_project_name(project_parent.name)
                    if sanitized_name == package_name:
                        candidates.append(project_parent)
                except Exception:
                    continue  # Skip malformed projects
        
        # Search relative to current project
        if project_root:
            relative_candidates = [
                project_root.parent / package_name,
                project_root.parent.parent / package_name,  # Up two levels
            ]
            candidates.extend([p for p in relative_candidates if p.exists()])
        
        return candidates
    
    def _sanitize_project_name(self, project_name: str) -> str:
        """
        Sanitize project name following UiPath Studio package naming rules.
        
        UiPath Studio conversion rules:
        - Spaces become dots: "Test Library" → "Test.Library"  
        - Multiple spaces become multiple dots: "A  B" → "A..B" (causes errors)
        - Preserved chars: a-zA-Z0-9_-. (underscores, dashes, dots, special chars like äöü)
        - Forbidden chars in project names: ;#~*°^
        
        Args:
            project_name: Raw project name from project.json
            
        Returns:
            Package name as generated by UiPath Studio
        """
        # Convert spaces to dots (this is the main transformation)
        sanitized = project_name.replace(' ', '.')
        return sanitized
    
    def classify_project_dependencies(self, dependencies: Dict[str, str], project_root: Optional[Path] = None) -> List[DependencyInfo]:
        """
        Classify all dependencies for a UiPath project.
        
        Args:
            dependencies: Dict from project.json dependencies section
            project_root: Project root path for local discovery
            
        Returns:
            List of classified dependencies
        """
        classified = []
        
        for name, version in dependencies.items():
            dep_info = self.classify_dependency(name, version, project_root)
            classified.append(dep_info)
            
        return classified
    
    def get_mcp_classification_requests(self, dependencies: List[DependencyInfo]) -> List[Dict[str, str]]:
        """
        Generate MCP requests for ambiguous dependencies requiring user classification.
        
        Args:
            dependencies: List of classified dependencies
            
        Returns:
            List of MCP request objects for user assistance
        """
        requests = []
        
        for dep in dependencies:
            if dep.classification == DependencyType.AMBIGUOUS:
                requests.append({
                    "type": "dependency_classification",
                    "package_name": dep.name,
                    "version": dep.version,
                    "reasoning": dep.reasoning,
                    "suggested_classifications": [
                        DependencyType.CUSTOM_LOCAL,
                        DependencyType.THIRD_PARTY
                    ],
                    "question": f"How should '{dep.name}' be classified?",
                    "options": {
                        "custom_local": "This is an in-house/custom library developed locally",
                        "third_party": "This is an external third-party package",
                        "provide_path": "Provide filesystem path to local project"
                    }
                })
        
        return requests
    
    def update_cache_from_mcp(self, package_name: str, classification: DependencyType, 
                             filesystem_path: Optional[str] = None, confidence: float = 1.0):
        """
        Update classification cache from MCP user/LLM response.
        
        Args:
            package_name: Package to update
            classification: User-provided classification
            filesystem_path: Optional filesystem path for local packages
            confidence: Confidence level (defaults to 1.0 for user-provided)
        """
        self.cache.classifications[package_name] = classification
        self.cache.confidence_overrides[package_name] = confidence
        
        if filesystem_path:
            self.cache.mappings[package_name] = filesystem_path
    
    def export_classification_summary(self, dependencies: List[DependencyInfo]) -> Dict[str, any]:
        """
        Export dependency classification summary for MCP/API consumption.
        
        Args:
            dependencies: Classified dependencies
            
        Returns:
            Summary dict with classification breakdown
        """
        summary = {
            "total_dependencies": len(dependencies),
            "by_classification": {},
            "high_confidence": [],
            "requires_assistance": [],
            "local_mappings": {}
        }
        
        # Count by classification type
        for dep in dependencies:
            dep_type = dep.classification.value
            summary["by_classification"][dep_type] = summary["by_classification"].get(dep_type, 0) + 1
            
            # High confidence classifications
            if dep.confidence >= 0.8:
                summary["high_confidence"].append({
                    "name": dep.name,
                    "classification": dep_type,
                    "confidence": dep.confidence
                })
            
            # Requires MCP assistance  
            if dep.classification == DependencyType.AMBIGUOUS:
                summary["requires_assistance"].append({
                    "name": dep.name,
                    "reasoning": dep.reasoning
                })
            
            # Local mappings found
            if dep.potential_local_paths:
                summary["local_mappings"][dep.name] = [str(p) for p in dep.potential_local_paths]
        
        return summary