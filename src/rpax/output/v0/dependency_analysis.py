"""
v0 dependency analysis artifacts for MCP-enhanced progressive disclosure.

Generates dependency classification artifacts with MCP integration for
custom library mapping assistance.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rpax.models.project import UiPathProject
from rpax.parser.dependency_classifier import (
    DependencyClassifier,
    DependencyInfo,
    DependencyMappingCache,
    DependencyType
)


class DependencyAnalysisGenerator:
    """
    Generates v0 dependency analysis artifacts with MCP classification support.
    
    Artifacts created:
    - dependencies.json - Full dependency analysis with classifications
    - dependencies/by_type/ - Dependencies grouped by classification type
    - dependencies/mcp_requests.json - Requests for user/LLM assistance
    - dependencies/local_mappings.json - Discovered local filesystem mappings
    """
    
    def __init__(self, project: UiPathProject, project_root: Path, output_dir: Path, lake_root: Optional[Path] = None):
        self.project = project
        self.project_root = project_root
        self.output_dir = output_dir
        self.lake_root = lake_root or project_root.parent
        self.classifier = DependencyClassifier(self.lake_root)
        
    def generate_artifacts(self) -> Dict[str, Any]:
        """Generate all dependency analysis artifacts."""
        if not self.project.dependencies:
            return {}
        
        # Classify all project dependencies
        classified_dependencies = self.classifier.classify_project_dependencies(
            self.project.dependencies,
            self.project_root
        )
        
        # Generate artifacts
        artifacts = {}
        artifacts.update(self._generate_main_analysis(classified_dependencies))
        artifacts.update(self._generate_by_type_breakdown(classified_dependencies)) 
        artifacts.update(self._generate_mcp_requests(classified_dependencies))
        artifacts.update(self._generate_local_mappings(classified_dependencies))
        
        return artifacts

    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata."""
        return datetime.now().isoformat()
    
    def _generate_main_analysis(self, dependencies: List[DependencyInfo]) -> Dict[str, Any]:
        """Generate main dependency analysis artifact."""
        analysis = {
            "metadata": {
                "total_dependencies": len(dependencies),
                "analysis_timestamp": self._get_timestamp(),
                "project_name": self.project.name,
                "project_type": self.project.project_type
            },
            "summary": self.classifier.export_classification_summary(dependencies),
            "dependencies": []
        }
        
        # Add detailed dependency information
        for dep in dependencies:
            dep_data = {
                "name": dep.name,
                "version": dep.version,
                "classification": {
                    "type": dep.classification.value,
                    "confidence": dep.confidence,
                    "reasoning": dep.reasoning
                },
                "metadata": {
                    "is_vendor_official": dep.classification == DependencyType.VENDOR_OFFICIAL,
                    "is_custom_local": dep.classification == DependencyType.CUSTOM_LOCAL,
                    "requires_assistance": dep.classification == DependencyType.AMBIGUOUS,
                    "has_local_mappings": len(dep.potential_local_paths) > 0
                }
            }
            
            # Add potential local paths if found
            if dep.potential_local_paths:
                dep_data["potential_local_paths"] = [str(p) for p in dep.potential_local_paths]
            
            # Add user-provided mapping if available
            if dep.user_provided_mapping:
                dep_data["user_provided_mapping"] = dep.user_provided_mapping
            
            analysis["dependencies"].append(dep_data)
        
        return {
            "dependencies.json": analysis
        }
    
    def _generate_by_type_breakdown(self, dependencies: List[DependencyInfo]) -> Dict[str, Any]:
        """Generate dependencies grouped by classification type."""
        artifacts = {}
        
        # Group dependencies by type
        by_type: Dict[DependencyType, List[DependencyInfo]] = {}
        for dep in dependencies:
            if dep.classification not in by_type:
                by_type[dep.classification] = []
            by_type[dep.classification].append(dep)
        
        # Generate artifacts for each type
        for dep_type, deps in by_type.items():
            type_data = {
                "classification_type": dep_type.value,
                "count": len(deps),
                "dependencies": []
            }
            
            for dep in deps:
                type_data["dependencies"].append({
                    "name": dep.name,
                    "version": dep.version,
                    "confidence": dep.confidence,
                    "reasoning": dep.reasoning,
                    "potential_local_paths": [str(p) for p in dep.potential_local_paths] if dep.potential_local_paths else []
                })
            
            artifact_key = f"dependencies/by_type/{dep_type.value}.json"
            artifacts[artifact_key] = type_data
        
        return artifacts
    
    def _generate_mcp_requests(self, dependencies: List[DependencyInfo]) -> Dict[str, Any]:
        """Generate MCP assistance requests for ambiguous dependencies."""
        mcp_requests = self.classifier.get_mcp_classification_requests(dependencies)
        
        if not mcp_requests:
            return {}
        
        mcp_data = {
            "metadata": {
                "total_requests": len(mcp_requests),
                "project_name": self.project.name,
                "timestamp": self._get_timestamp()
            },
            "requests": mcp_requests,
            "instructions": {
                "purpose": "Classify ambiguous dependencies for enhanced project analysis",
                "background": "These dependencies could not be automatically classified as vendor/official or custom/local packages",
                "user_options": {
                    "custom_local": "Mark as in-house/custom library developed locally",
                    "third_party": "Mark as external third-party package",
                    "provide_path": "Provide filesystem path to local project source"
                },
                "benefit": "Accurate classification enables better cross-project analysis and dependency management"
            }
        }
        
        return {
            "dependencies/mcp_requests.json": mcp_data
        }
    
    def _generate_local_mappings(self, dependencies: List[DependencyInfo]) -> Dict[str, Any]:
        """Generate discovered local filesystem mappings."""
        local_mappings = {}
        potential_mappings = {}
        
        for dep in dependencies:
            if dep.user_provided_mapping:
                local_mappings[dep.name] = {
                    "path": dep.user_provided_mapping,
                    "source": "user_provided",
                    "confidence": 1.0
                }
            elif dep.potential_local_paths:
                potential_mappings[dep.name] = [
                    {
                        "path": str(path),
                        "exists": path.exists(),
                        "is_directory": path.is_dir() if path.exists() else False,
                        "confidence": 0.7  # Auto-discovered, medium confidence
                    }
                    for path in dep.potential_local_paths
                ]
        
        if not local_mappings and not potential_mappings:
            return {}
        
        mappings_data = {
            "metadata": {
                "project_name": self.project.name,
                "confirmed_mappings_count": len(local_mappings),
                "potential_mappings_count": len(potential_mappings),
                "timestamp": self._get_timestamp()
            },
            "confirmed_mappings": local_mappings,
            "potential_mappings": potential_mappings,
            "instructions": {
                "confirmed_mappings": "User or system confirmed dependency-to-filesystem mappings",
                "potential_mappings": "Auto-discovered potential mappings requiring verification",
                "next_steps": "Review potential mappings and confirm via MCP or configuration"
            }
        }
        
        return {
            "dependencies/local_mappings.json": mappings_data
        }
    
    def update_from_mcp_response(self, mcp_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update dependency classifications from MCP responses and regenerate artifacts.
        
        Args:
            mcp_responses: List of MCP responses with user/LLM classifications
            
        Returns:
            Updated artifacts with new classifications
        """
        # Update classifier cache from MCP responses
        for response in mcp_responses:
            package_name = response.get("package_name")
            classification_str = response.get("classification")
            filesystem_path = response.get("filesystem_path")
            
            if not package_name or not classification_str:
                continue
            
            try:
                classification = DependencyType(classification_str)
                self.classifier.update_cache_from_mcp(
                    package_name,
                    classification,
                    filesystem_path,
                    confidence=1.0  # User-provided classifications get full confidence
                )
            except ValueError:
                continue  # Skip invalid classifications
        
        # Regenerate artifacts with updated classifications
        return self.generate_artifacts()
    
    def export_mcp_schema(self) -> Dict[str, Any]:
        """Export MCP schema for dependency classification requests."""
        return {
            "request_type": "dependency_classification",
            "schema": {
                "type": "object",
                "properties": {
                    "package_name": {"type": "string", "description": "Name of the package to classify"},
                    "version": {"type": "string", "description": "Package version"},
                    "classification": {
                        "type": "string",
                        "enum": [t.value for t in DependencyType],
                        "description": "Classification type for the dependency"
                    },
                    "filesystem_path": {
                        "type": "string",
                        "description": "Optional filesystem path for local dependencies"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence in classification (0.0 to 1.0)"
                    }
                },
                "required": ["package_name", "classification"]
            },
            "example_request": {
                "type": "dependency_classification",
                "package_name": "CustomLibrary",
                "version": "1.0.0",
                "suggested_classifications": ["custom_local", "third_party"],
                "question": "How should 'CustomLibrary' be classified?",
                "options": {
                    "custom_local": "This is an in-house/custom library developed locally",
                    "third_party": "This is an external third-party package"
                }
            },
            "example_response": {
                "package_name": "CustomLibrary",
                "classification": "custom_local",
                "filesystem_path": "/path/to/local/CustomLibrary",
                "confidence": 1.0
            }
        }